#!/usr/bin/env python3
"""Crystal Chess V19: prospective transfer of the frozen residual guard ladder.

Source authority:
* V16 residual ladder preserves the complete-boundary V14 pair@8 guard.
* It adds distance signatures only on the pair residual, then relational
  signatures only on the remaining residual.
* Every admitted source signature has support >= 8 and zero Syzygy-WDL
  failures on complete restricted KPPvK.

Prospective targets, with no target-driven guard change:
* K+3P vs K: files b,c,d, pawn ranks 2..4, all legal kings, both turns.
* K+4P vs K: files b,c,d,e, pawn ranks 2..4, all legal kings, both turns.

An anchor capability is admitted only when the frozen residual ladder accepts
its relation to EVERY other pawn. Exact target WDL is queried only after the
candidate is committed. Unsupported states retain the full legal frontier.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import chess
import chess.syzygy

from crystal_chess_kpvk_v0 import coordinate_feature_bank
from crystal_chess_kppvk_complete_census_v12 import (
    acquire_policy,
    exact_wdl,
    parse_role_move,
    precompute_roles,
)
from crystal_chess_verified_hybrid_search_v14 import signature


SCHEMA = "mathgraph.crystal-chess.residual-ladder-transfer.v19"
SOURCE_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-residual-guard-ladder-v16"
    "@4f7902ddc9e65a6357c39221203211145c85f2e2"
)
SOURCE_RUN = 36359443246
EXPECTED_GUARD_SHA256 = (
    "7c19923878b0fe4502871cc025582137471f93227c76dff537c1870da3401285"
)
OLD = {
    "KPPPvK": {
        "nonterminal": 170297,
        "coverage": 38358,
        "coverage_ratio": 0.22524178,
        "child_reduction": 0.26489818,
    },
    "KPPPPvK": {
        "nonterminal": 488607,
        "coverage": 76169,
        "coverage_ratio": 0.15589011,
        "child_reduction": 0.19909766,
    },
}


def load_ladder(
    path: Path,
) -> tuple[dict[str, object], dict[str, set[tuple[object, ...]]], str]:
    h = hashlib.sha256()
    tiers = {"pair": set(), "distance": set(), "relational": set()}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        header_line = handle.readline()
        if not header_line:
            raise ValueError("empty ladder guard")
        h.update(header_line.encode("utf-8"))
        header = json.loads(header_line)
        for line in handle:
            if not line.strip():
                continue
            h.update(line.encode("utf-8"))
            row = json.loads(line)
            tier = str(row["tier"])
            if tier not in tiers:
                raise ValueError(f"unexpected tier {tier}")
            tiers[tier].add(tuple(row["signature"]))
    digest = h.hexdigest()
    if digest != EXPECTED_GUARD_SHA256:
        raise AssertionError(("ladder guard digest mismatch", digest))
    if not all(tiers.values()):
        raise AssertionError("missing ladder tier")
    return header, tiers, digest


def make_board(
    wk: int,
    bk: int,
    pawns: tuple[int, ...],
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
    for pawn in pawns:
        board.set_piece_at(pawn, chess.Piece(chess.PAWN, chess.WHITE))
    return board


def pawn_tuples(files: tuple[int, ...]):
    def rec(i: int, prefix: list[int]):
        if i == len(files):
            yield tuple(prefix)
            return
        f = files[i]
        for rank in range(1, 4):  # ranks 2..4
            prefix.append(chess.square(f, rank))
            yield from rec(i + 1, prefix)
            prefix.pop()
    yield from rec(0, [])


def iter_target(files: tuple[int, ...]):
    for pawns in pawn_tuples(files):
        for wk in chess.SQUARES:
            if wk in pawns:
                continue
            for bk in chess.SQUARES:
                if bk == wk or bk in pawns:
                    continue
                for turn in (False, True):
                    board = make_board(wk, bk, pawns, turn)
                    if board.is_valid():
                        yield pawns, wk, bk, turn, board


def pair_admitted(
    board: chess.Board,
    anchor: int,
    other: int,
    role: str,
    tiers: dict[str, set[tuple[object, ...]]],
) -> tuple[bool, str | None]:
    pair = signature(board, anchor, other, role, 1)
    if pair in tiers["pair"]:
        return True, "pair"
    distance = signature(board, anchor, other, role, 2)
    if distance in tiers["distance"]:
        return True, "distance"
    relational = signature(board, anchor, other, role, 3)
    if relational in tiers["relational"]:
        return True, "relational"
    return False, None


def guarded_candidates(
    board: chess.Board,
    pawns: tuple[int, ...],
    wk: int,
    bk: int,
    turn: bool,
    role_map: dict[tuple[int, int, int, int], str],
    tiers: dict[str, set[tuple[object, ...]]],
) -> list[tuple[chess.Move, tuple[str, ...]]]:
    seen: set[chess.Move] = set()
    out: list[tuple[chess.Move, tuple[str, ...]]] = []
    for anchor in pawns:
        role = role_map[(wk, bk, anchor, int(turn))]
        move = parse_role_move(board, anchor, role)
        if move is None:
            continue
        used: list[str] = []
        ok = True
        for other in pawns:
            if other == anchor:
                continue
            admitted, tier = pair_admitted(board, anchor, other, role, tiers)
            if not admitted or tier is None:
                ok = False
                break
            used.append(tier)
        if ok and move not in seen:
            seen.add(move)
            out.append((move, tuple(used)))
    return out


def evaluate_target(
    tb: chess.syzygy.Tablebase,
    *,
    files: tuple[int, ...],
    name: str,
    role_map: dict[tuple[int, int, int, int], str],
    tiers: dict[str, set[tuple[object, ...]]],
) -> dict[str, object]:
    c = Counter()
    wrong_examples: list[dict[str, object]] = []
    tier_use = Counter()

    for pawns, wk, bk, turn, board in iter_target(files):
        c["legal_states"] += 1
        legal_count = board.legal_moves.count()
        if legal_count == 0:
            c["terminal_states"] += 1
            continue
        c["nonterminal_states"] += 1
        c["baseline_child_expansions"] += legal_count

        candidates = guarded_candidates(
            board, pawns, wk, bk, turn, role_map, tiers
        )
        if not candidates:
            c["hybrid_child_expansions"] += legal_count
            continue

        c["qualified_states"] += 1
        c["hybrid_child_expansions"] += 1
        c["saved_child_expansions"] += legal_count - 1
        root = exact_wdl(tb, board)

        for move, used_tiers in candidates:
            c["qualified_candidates"] += 1
            for tier in used_tiers:
                tier_use[tier] += 1
            board.push(move)
            consequence = -exact_wdl(tb, board)
            board.pop()
            safe = consequence == root
            c["safe_candidates"] += int(safe)
            c["wrong_candidates"] += int(not safe)
            if not safe and len(wrong_examples) < 50:
                wrong_examples.append(
                    {
                        "fen": board.fen(),
                        "move": move.uci(),
                        "root_wdl": root,
                        "child_consequence": consequence,
                        "tiers": list(used_tiers),
                    }
                )

    nonterminal = int(c["nonterminal_states"])
    baseline = int(c["baseline_child_expansions"])
    hybrid = int(c["hybrid_child_expansions"])
    old = OLD[name]
    if nonterminal != int(old["nonterminal"]):
        raise AssertionError(
            ("target boundary drift", name, nonterminal, old["nonterminal"])
        )

    return {
        **dict(c),
        "state_coverage_ratio": (
            c["qualified_states"] / nonterminal if nonterminal else 0.0
        ),
        "candidate_precision": (
            c["safe_candidates"] / c["qualified_candidates"]
            if c["qualified_candidates"] else 1.0
        ),
        "zero_false_positive": c["wrong_candidates"] == 0,
        "child_reduction_ratio": (
            c["saved_child_expansions"] / baseline if baseline else 0.0
        ),
        "expansion_speedup_factor": baseline / hybrid if hybrid else 1.0,
        "tier_relation_uses": dict(tier_use),
        "wrong_examples": wrong_examples,
        "prior_v14_pair_transfer": old,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    started = time.time()

    header, tiers, digest = load_ladder(args.guard)

    bank = coordinate_feature_bank()
    feature_fns = [fn for _name, fn in bank]
    pawn_squares = [
        chess.square(f, r)
        for f in range(8)
        for r in range(1, 6)
    ]

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tb:
        policy, frequency, enumeration, nonterminal = acquire_policy(
            tb, feature_fns
        )
        role_map = precompute_roles(policy, feature_fns, pawn_squares)

        k3 = evaluate_target(
            tb,
            files=(1, 2, 3),
            name="KPPPvK",
            role_map=role_map,
            tiers=tiers,
        )
        k4 = evaluate_target(
            tb,
            files=(1, 2, 3, 4),
            name="KPPPPvK",
            role_map=role_map,
            tiers=tiers,
        )

    all_safe = bool(
        k3["zero_false_positive"] and k4["zero_false_positive"]
    )
    both_gain = bool(
        int(k3["qualified_states"]) > int(OLD["KPPPvK"]["coverage"])
        and int(k4["qualified_states"]) > int(OLD["KPPPPvK"]["coverage"])
        and float(k3["child_reduction_ratio"]) > float(OLD["KPPPvK"]["child_reduction"])
        and float(k4["child_reduction_ratio"]) > float(OLD["KPPPPvK"]["child_reduction"])
    )
    status = (
        "WARRANTED_PROSPECTIVE_RESIDUAL_LADDER_TRANSFER_GAIN"
        if all_safe and both_gain
        else (
            "WARRANTED_PROSPECTIVE_RESIDUAL_LADDER_SAFE_TRANSFER"
            if all_safe
            else "EXACT_RESIDUAL_LADDER_TRANSFER_COUNTEREXAMPLE"
        )
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "source_authority": SOURCE_AUTHORITY,
        "source_run": SOURCE_RUN,
        "guard": {
            "digest": digest,
            "header": header,
            "classes": {k: len(v) for k, v in tiers.items()},
        },
        "target_results": {
            "KPPPvK": k3,
            "KPPPPvK": k4,
        },
        "frozen_kpvk": {
            "nonterminal_states": nonterminal,
            "role_frequency": frequency,
            "enumeration": enumeration,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "the residual ladder is byte-identical to the complete KPPvK source artifact",
                "no richer-target label changes any signature, tier, support threshold, or admission rule",
                "every admitted richer-target candidate preserves exact Syzygy WDL",
                "unsupported states retain unchanged full legal-child search",
            ],
            "unknown": [
                "transfer beyond these declared K+3P/K+4P boundaries",
                "systems gain from replacing V14 pair guard with this ladder",
                "general chess",
            ],
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"CRYSTAL_CHESS_RESIDUAL_LADDER_TRANSFER_V19={status}")
    for name, row in (("KPPPvK", k3), ("KPPPPvK", k4)):
        print(
            f"{name}: coverage={row['qualified_states']}/{row['nonterminal_states']} "
            f"ratio={row['state_coverage_ratio']:.8f} "
            f"wrong={row['wrong_candidates']} "
            f"precision={row['candidate_precision']:.8f} "
            f"child_reduction={row['child_reduction_ratio']:.8f} "
            f"prior_coverage={row['prior_v14_pair_transfer']['coverage']} "
            f"prior_reduction={row['prior_v14_pair_transfer']['child_reduction']:.8f}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
