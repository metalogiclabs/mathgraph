#!/usr/bin/env python3
"""Crystal Chess V20: exact color-symmetry transport of V14/V15/V16.

This is not a new learned chess rule. It compiles the ordinary color/rank
automorphism of chess so that already-qualified White-pawn-vs-Black-king
capabilities also execute for the exact Black-pawn-vs-White-king mirror.

The complete source boundaries are already warranted. Because Board.mirror()
is a bijection of those declared boundaries, complete mirrored coverage counts
are inherited exactly. This executable gate independently checks the runtime
mapping on deterministic held-out samples and verifies every sampled shortcut
against Syzygy WDL.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import sys

import chess
import chess.syzygy

from crystal_chess_stockfish_hybrid_uci_v17 import CrystalOracle, mirror_move

SCHEMA = "mathgraph.crystal-chess.color-symmetry.v20"
SOURCE = {
    "KPPvK": {
        "nonterminal": 5_145_060,
        "covered": 1_112_360,
        "authority_run": 36357299241,
    },
    "KPPPvK": {
        "nonterminal": 170_297,
        "covered": 38_358,
        "authority_run": 36359645338,
    },
    "KPPPPvK": {
        "nonterminal": 488_607,
        "covered": 76_169,
        "authority_run": 36359934616,
    },
}


def make_board(wk: int, bk: int, pawns: tuple[int, ...], turn: bool) -> chess.Board:
    board = chess.Board(None)
    board.turn = turn
    board.castling_rights = chess.BB_EMPTY
    board.ep_square = None
    board.halfmove_clock = 0
    board.fullmove_number = 1
    board.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
    for pawn in pawns:
        board.set_piece_at(pawn, chess.Piece(chess.PAWN, chess.WHITE))
    return board


def random_canonical(rng: random.Random, family: str) -> chess.Board:
    if family == "KPPvK":
        squares = [chess.square(f, r) for f in range(8) for r in range(1, 6)]
        pawns = tuple(rng.sample(squares, 2))
    elif family == "KPPPvK":
        pawns = (
            chess.square(1, rng.randrange(1, 4)),
            chess.square(2, rng.randrange(1, 4)),
            chess.square(3, rng.randrange(1, 4)),
        )
    elif family == "KPPPPvK":
        pawns = (
            chess.square(1, rng.randrange(1, 4)),
            chess.square(2, rng.randrange(1, 4)),
            chess.square(3, rng.randrange(1, 4)),
            chess.square(4, rng.randrange(1, 4)),
        )
    else:
        raise ValueError(family)
    wk, bk = rng.sample(list(chess.SQUARES), 2)
    return make_board(wk, bk, pawns, bool(rng.getrandbits(1)))


def wdl_preserved(tb: chess.syzygy.Tablebase, board: chess.Board, move: chess.Move) -> bool:
    root = int(tb.probe_wdl(board))
    child = board.copy(stack=False)
    child.push(move)
    return -int(tb.probe_wdl(child)) == root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--roles", type=Path, required=True)
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--per-family", type=int, default=50000)
    ap.add_argument("--seed", type=int, default=20260928)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    oracle = CrystalOracle(args.guard, args.roles)
    results = {}

    with chess.syzygy.open_tablebase(str(args.tablebase_dir), load_wdl=True, load_dtz=False) as tb:
        for family in ("KPPvK", "KPPPvK", "KPPPPvK"):
            c = Counter()
            seen = set()
            while c["sampled"] < args.per_family:
                board = random_canonical(rng, family)
                if not board.is_valid() or not any(board.legal_moves):
                    continue
                fen = board.fen()
                if fen in seen:
                    continue
                seen.add(fen)
                c["sampled"] += 1

                direct = oracle._choose_white_canonical(board)
                mirrored_board = board.mirror()
                symmetric = oracle.choose(mirrored_board)

                if direct is None:
                    c["direct_unknown"] += 1
                    if symmetric is not None:
                        c["unknown_mismatch"] += 1
                    continue

                c["direct_shortcuts"] += 1
                if symmetric is None:
                    c["missing_mirror"] += 1
                    continue

                direct_move, direct_auth = direct
                sym_move, sym_auth = symmetric
                expected = mirror_move(direct_move)
                if sym_move != expected:
                    c["move_mismatch"] += 1
                if sym_move not in mirrored_board.legal_moves:
                    c["illegal_mirror"] += 1
                if not sym_auth.endswith("_COLOR_MIRROR"):
                    c["authority_mismatch"] += 1

                c["direct_wdl_wrong"] += int(not wdl_preserved(tb, board, direct_move))
                c["mirror_wdl_wrong"] += int(not wdl_preserved(tb, mirrored_board, sym_move))

            source = SOURCE[family]
            results[family] = {
                **dict(c),
                "sample_shortcut_ratio": c["direct_shortcuts"] / c["sampled"],
                "complete_source_nonterminal": source["nonterminal"],
                "complete_source_covered": source["covered"],
                "complete_mirrored_nonterminal_by_bijection": source["nonterminal"],
                "complete_mirrored_covered_by_bijection": source["covered"],
                "complete_mirrored_coverage_ratio": source["covered"] / source["nonterminal"],
                "source_authority_run": source["authority_run"],
            }

    bad = sum(
        row.get(k, 0)
        for row in results.values()
        for k in (
            "unknown_mismatch",
            "missing_mirror",
            "move_mismatch",
            "illegal_mirror",
            "authority_mismatch",
            "direct_wdl_wrong",
            "mirror_wdl_wrong",
        )
    )
    status = (
        "WARRANTED_EXACT_COLOR_SYMMETRY_RUNTIME_TRANSPORT"
        if bad == 0
        else "COLOR_SYMMETRY_RUNTIME_COUNTEREXAMPLE"
    )
    result = {
        "schema": SCHEMA,
        "status": status,
        "source_complete_authorities": SOURCE,
        "method": {
            "automorphism": "python-chess Board.mirror plus square_mirror on move endpoints",
            "dependency": "complete V14/V15/V16 safety authority",
            "runtime_truth": "no Syzygy lookup at runtime",
        },
        "sample_verification": results,
        "claim_boundary": {
            "warranted_if_green": [
                "runtime mirrored decisions equal the exact mirror of the canonical oracle decision",
                "mirrored runtime moves are legal",
                "all sampled mirrored shortcuts preserve exact Syzygy WDL",
                "complete mirrored coverage counts inherit by bijection from the complete source boundaries",
            ],
            "not_claimed": [
                "new strategic capability",
                "general chess strength gain",
                "leaderboard Elo gain",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"CRYSTAL_CHESS_COLOR_SYMMETRY_V20={status}")
    for family, row in results.items():
        print(
            f"{family}: sample={row['sampled']} shortcuts={row['direct_shortcuts']} "
            f"move_mismatch={row.get('move_mismatch',0)} mirror_wdl_wrong={row.get('mirror_wdl_wrong',0)} "
            f"complete_mirror={row['complete_mirrored_covered_by_bijection']}/"
            f"{row['complete_mirrored_nonterminal_by_bijection']}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
