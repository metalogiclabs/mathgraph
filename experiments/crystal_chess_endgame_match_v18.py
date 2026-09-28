#!/usr/bin/env python3
"""Crystal Chess V18: generate and analyse a paired endgame match.

The match is deliberately bounded. It measures the shipped V17 UCI hybrid
against its identical pinned Stockfish fallback on positions where Crystal is
already certified to fire. It is not a general-chess rating.

Opening construction:
* KPPvK, KPPPvK, KPPPPvK qualified material families.
* White to move, halfmove clock 0.
* The frozen V17 oracle must admit a shortcut.
* Exact Syzygy WDL verifies the committed shortcut only after admission.
* No WDL label is used to decide whether an opening is selected beyond that
  post-admission safety check.

Analysis:
* paired openings, colours reversed by fastchess;
* score and bounded logistic Elo estimate from Crystal's perspective;
* deterministic paired bootstrap interval over opening pairs.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import random

import chess
import chess.pgn
import chess.syzygy

from crystal_chess_stockfish_hybrid_uci_v17 import CrystalOracle
from crystal_chess_richer_transfer_v5 import make_kppvk
from crystal_chess_hybrid_guard_transfer_v15 import make_kpppvk


SCHEMA = "mathgraph.crystal-chess.endgame-match.v18"


def make_kppppvk(
    wk: int,
    bk: int,
    p0: int,
    p1: int,
    p2: int,
    p3: int,
    turn: bool,
) -> chess.Board:
    board = chess.Board(None)
    board.turn = turn
    board.castling_rights = chess.BB_EMPTY
    board.ep_square = None
    board.halfmove_clock = 0
    board.fullmove_number = 1
    board.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
    for pawn in (p0, p1, p2, p3):
        board.set_piece_at(pawn, chess.Piece(chess.PAWN, chess.WHITE))
    return board


def random_board(rng: random.Random, family: str) -> chess.Board:
    if family == "KPPvK":
        pawn_squares = [
            chess.square(f, r) for f in range(8) for r in range(1, 6)
        ]
        p0, p1 = rng.sample(pawn_squares, 2)
        wk, bk = rng.sample(list(chess.SQUARES), 2)
        return make_kppvk(wk, bk, p0, p1, chess.WHITE)
    if family == "KPPPvK":
        pawns = (
            chess.square(1, rng.randrange(1, 4)),
            chess.square(2, rng.randrange(1, 4)),
            chess.square(3, rng.randrange(1, 4)),
        )
        wk, bk = rng.sample(list(chess.SQUARES), 2)
        return make_kpppvk(wk, bk, *pawns, chess.WHITE)
    if family == "KPPPPvK":
        pawns = (
            chess.square(1, rng.randrange(1, 4)),
            chess.square(2, rng.randrange(1, 4)),
            chess.square(3, rng.randrange(1, 4)),
            chess.square(4, rng.randrange(1, 4)),
        )
        wk, bk = rng.sample(list(chess.SQUARES), 2)
        return make_kppppvk(wk, bk, *pawns, chess.WHITE)
    raise ValueError(family)


def verify_shortcut(
    tb: chess.syzygy.Tablebase,
    board: chess.Board,
    move: chess.Move,
) -> tuple[bool, int]:
    root = int(tb.probe_wdl(board))
    child = board.copy(stack=False)
    child.push(move)
    consequence = -int(tb.probe_wdl(child))
    return consequence == root, root


def generate_book(args) -> int:
    rng = random.Random(args.seed)
    oracle = CrystalOracle(args.guard, args.roles)
    families = ("KPPvK", "KPPPvK", "KPPPPvK")
    wanted = args.per_family
    selected: list[tuple[str, chess.Board, str, int]] = []
    seen: set[str] = set()
    counts = Counter()
    wdl_counts = Counter()

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tb:
        while any(counts[f] < wanted for f in families):
            family = families[len(selected) % len(families)]
            if counts[family] >= wanted:
                family = next(f for f in families if counts[f] < wanted)
            board = random_board(rng, family)
            if not board.is_valid() or not any(board.legal_moves):
                continue
            board.halfmove_clock = 0
            board.fullmove_number = 1
            fen = board.fen()
            if fen in seen:
                continue
            choice = oracle.choose(board)
            if choice is None:
                continue
            move, authority = choice
            ok, root = verify_shortcut(tb, board, move)
            if not ok:
                raise AssertionError((family, fen, move.uci(), authority))
            seen.add(fen)
            counts[family] += 1
            wdl_counts[(family, root)] += 1
            selected.append((family, board, authority, root))

    args.book.parent.mkdir(parents=True, exist_ok=True)
    with args.book.open("w", encoding="utf-8") as out:
        for _family, board, _authority, _root in selected:
            out.write(board.epd() + "\n")

    manifest = {
        "schema": SCHEMA + ".book",
        "seed": args.seed,
        "per_family": wanted,
        "total_openings": len(selected),
        "counts": dict(counts),
        "wdl_counts": {
            f"{family}:{wdl}": count
            for (family, wdl), count in sorted(wdl_counts.items())
        },
        "all_openings_crystal_certified": True,
        "all_shortcuts_exact_wdl_preserving": True,
        "book": str(args.book),
    }
    args.manifest.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("CRYSTAL_CHESS_ENDGAME_MATCH_BOOK_V18=PASS")
    print(f"openings={len(selected)} counts={dict(counts)}")
    return 0


def crystal_points(game: chess.pgn.Game, crystal_name: str) -> float:
    result = game.headers.get("Result", "*")
    white = game.headers.get("White", "")
    black = game.headers.get("Black", "")
    if result == "1/2-1/2":
        return 0.5
    if result == "1-0":
        return 1.0 if white == crystal_name else 0.0
    if result == "0-1":
        return 1.0 if black == crystal_name else 0.0
    raise ValueError(f"unfinished result {result}")


def elo_from_score(score: float) -> float | None:
    if not (0.0 < score < 1.0):
        return None
    return 400.0 * math.log10(score / (1.0 - score))


def analyse(args) -> int:
    games: list[chess.pgn.Game] = []
    with args.pgn.open("r", encoding="utf-8", errors="replace") as handle:
        while True:
            game = chess.pgn.read_game(handle)
            if game is None:
                break
            games.append(game)

    if len(games) % 2:
        raise AssertionError(f"expected paired games, got {len(games)}")

    wins = losses = draws = 0
    pair_points: list[float] = []
    terminations = Counter()
    for i in range(0, len(games), 2):
        pts = 0.0
        for game in games[i : i + 2]:
            p = crystal_points(game, args.crystal_name)
            pts += p
            if p == 1.0:
                wins += 1
            elif p == 0.0:
                losses += 1
            else:
                draws += 1
            terminations[game.headers.get("Termination", "unknown")] += 1
        pair_points.append(pts)

    n = len(games)
    total_points = wins + 0.5 * draws
    score = total_points / n
    elo = elo_from_score(score)

    rng = random.Random(20260928)
    boot_elos: list[float] = []
    if pair_points:
        for _ in range(20000):
            sampled = [pair_points[rng.randrange(len(pair_points))] for _ in pair_points]
            s = sum(sampled) / (2.0 * len(sampled))
            e = elo_from_score(s)
            if e is not None:
                boot_elos.append(e)
    boot_elos.sort()
    ci = None
    if boot_elos:
        lo = boot_elos[int(0.025 * (len(boot_elos) - 1))]
        hi = boot_elos[int(0.975 * (len(boot_elos) - 1))]
        ci = [lo, hi]

    result = {
        "schema": SCHEMA + ".result",
        "crystal_name": args.crystal_name,
        "games": n,
        "opening_pairs": len(pair_points),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "score_fraction": score,
        "bounded_logistic_elo_estimate": elo,
        "paired_bootstrap_95pct_elo_interval": ci,
        "terminations": dict(terminations),
        "claim_boundary": {
            "description": (
                "paired fastchess match restricted to Crystal-certified exact "
                "K+2P/K+3P/K+4P endgame starts under the declared time control"
            ),
            "not_general_chess_elo": True,
        },
    }
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("CRYSTAL_CHESS_ENDGAME_MATCH_V18=PASS")
    print(
        f"games={n} W/L/D={wins}/{losses}/{draws} score={score:.6f} "
        f"bounded_elo={elo} ci95={ci}"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)

    g = sub.add_parser("generate")
    g.add_argument("--guard", type=Path, required=True)
    g.add_argument("--roles", type=Path, required=True)
    g.add_argument("--tablebase-dir", type=Path, required=True)
    g.add_argument("--book", type=Path, required=True)
    g.add_argument("--manifest", type=Path, required=True)
    g.add_argument("--per-family", type=int, default=50)
    g.add_argument("--seed", type=int, default=20260928)

    a = sub.add_parser("analyse")
    a.add_argument("--pgn", type=Path, required=True)
    a.add_argument("--crystal-name", default="CrystalV17")
    a.add_argument("--output", type=Path, required=True)

    args = ap.parse_args()
    return generate_book(args) if args.mode == "generate" else analyse(args)


if __name__ == "__main__":
    raise SystemExit(main())
