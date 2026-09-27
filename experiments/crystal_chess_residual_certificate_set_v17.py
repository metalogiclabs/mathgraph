#!/usr/bin/env python3
"""Crystal Chess V17: residual-only certificate-set guard genesis.

Purpose
-------
V14/V15/V16 use one preferred frozen KPvK role per pawn projection. V13 proved
that arbitrary witness identity is presentation: exact strategy semantics are
sets of admissible certificates.

V17 tests that distinction without globally relearning chess.

Stage A (no richer labels in acquisition):
* Load the byte-identical zero-error V14 pair guard.
* On richer states, enumerate *all* exact KPvK WDL-preserving relative roles
  for each pawn projection.
* Admit a move only when every pair interface against every other pawn is in
  the original V14 safe-signature bank.

Stage B (residual-only acquisition):
* On the complete V15 K+3P b-c-d ranks-2..4 world, consider only states still
  uncovered by Stage A.
* Exact K+3P WDL audits candidate moves only after commitment.
* New pair signatures are retained only when they have support >= the frozen
  V14 threshold and zero errors on every occurrence in this residual.
* Freeze the union of V14 signatures + residual-earned signatures.

Prospective test:
* Apply the frozen union unchanged to the complete V16 K+4P b-c-d-e
  ranks-2..4 world.
* K+4P truth is queried only after commitment.
* Full legal-child fallback remains unchanged outside admitted states.

This isolates two possible earned distinctions:
1. admissible-certificate set vs preferred witness;
2. only then, residual-earned pair-interface signatures.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import platform
import sys
import time

import chess
import chess.syzygy

from crystal_chess_kpvk_v0 import coordinate_feature_bank, make_kpvk, probe_wdl
from crystal_chess_goal_certificate_v3 import optimal_roles
from crystal_chess_kppvk_complete_census_v12 import (
    acquire_policy,
    exact_wdl,
    parse_role_move,
    precompute_roles,
)
from crystal_chess_verified_hybrid_search_v14 import (
    TIER_NAMES,
    candidate_bindings,
    signature,
)


SCHEMA = "mathgraph.crystal-chess.residual-certificate-set.v17"
V14_RUN = 36357299241
V15_RUN = 36359645338
V16_RUN = 36359934616
V14_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-verified-hybrid-search-v14"
    "@55be612bbf8cf3bd26ef10d5474873443f0f7edd"
)
V15_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-hybrid-guard-transfer-v15"
    "@7f258e22057e8ffe1bb51c72ddca5d1ca3316949"
)
V16_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-hybrid-guard-transfer-v16"
    "@80599fe6c9dd509a18119bcee6f52f91290d7b33"
)


def make_multi_pawn_board(
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


def source_pawn_tuples() -> list[tuple[int, int, int]]:
    return [
        (
            chess.square(1, rb),
            chess.square(2, rc),
            chess.square(3, rd),
        )
        for rb in range(1, 4)
        for rc in range(1, 4)
        for rd in range(1, 4)
    ]


def target_pawn_tuples() -> list[tuple[int, int, int, int]]:
    return [
        (
            chess.square(1, rb),
            chess.square(2, rc),
            chess.square(3, rd),
            chess.square(4, re),
        )
        for rb in range(1, 4)
        for rc in range(1, 4)
        for rd in range(1, 4)
        for re in range(1, 4)
    ]


def iter_boundary(pawn_sets):
    for pawns in pawn_sets:
        for wk in chess.SQUARES:
            if wk in pawns:
                continue
            for bk in chess.SQUARES:
                if bk in pawns or bk == wk:
                    continue
                for turn in (False, True):
                    board = make_multi_pawn_board(wk, bk, pawns, turn)
                    if board.is_valid():
                        yield pawns, wk, bk, turn, board


def load_guard(path: Path) -> tuple[dict[str, object], set[tuple[object, ...]]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        header = json.loads(handle.readline())
        signatures = {
            tuple(json.loads(line)["signature"])
            for line in handle
            if line.strip()
        }
    if not signatures:
        raise AssertionError("empty V14 guard")
    return header, signatures


def preferred_candidates(
    board: chess.Board,
    pawns: tuple[int, ...],
    wk: int,
    bk: int,
    turn: bool,
    role_map,
    tier: int,
    bank: set[tuple[object, ...]],
) -> list[chess.Move]:
    out: list[chess.Move] = []
    seen: set[chess.Move] = set()
    for anchor in pawns:
        role = role_map[(wk, bk, anchor, int(turn))]
        other0 = next(other for other in pawns if other != anchor)
        binding = None
        for b_anchor, _b_other, b_role, move in candidate_bindings(
            board, anchor, other0, wk, bk, turn, role_map
        ):
            if b_anchor == anchor and b_role == role:
                binding = move
                break
        if binding is None:
            continue
        if all(
            signature(board, anchor, other, role, tier) in bank
            for other in pawns
            if other != anchor
        ):
            if binding not in seen:
                seen.add(binding)
                out.append(binding)
    return out


def local_roles(
    *,
    wk: int,
    bk: int,
    anchor: int,
    turn: bool,
    tb: chess.syzygy.Tablebase,
    cache: dict[tuple[str, bool], int],
    role_cache: dict[tuple[int, int, int, int], tuple[str, ...]],
) -> tuple[str, ...]:
    key = (wk, bk, anchor, int(turn))
    cached = role_cache.get(key)
    if cached is not None:
        return cached
    local = make_kpvk(wk, bk, anchor, turn)
    root = probe_wdl(tb, local, cache)
    roles = optimal_roles(local, root, tb, cache)
    role_cache[key] = roles
    return roles


def set_candidates(
    *,
    board: chess.Board,
    pawns: tuple[int, ...],
    wk: int,
    bk: int,
    turn: bool,
    tb: chess.syzygy.Tablebase,
    cache: dict[tuple[str, bool], int],
    role_cache: dict[tuple[int, int, int, int], tuple[str, ...]],
    tier: int,
    bank: set[tuple[object, ...]],
) -> list[tuple[chess.Move, int, str, tuple[tuple[object, ...], ...]]]:
    """All local exact-role moves satisfying the universal pair bank."""

    out = []
    seen: set[chess.Move] = set()
    for anchor in pawns:
        for role in local_roles(
            wk=wk,
            bk=bk,
            anchor=anchor,
            turn=turn,
            tb=tb,
            cache=cache,
            role_cache=role_cache,
        ):
            move = parse_role_move(board, anchor, role)
            if move is None or move in seen:
                continue
            sigs = tuple(
                signature(board, anchor, other, role, tier)
                for other in pawns
                if other != anchor
            )
            if all(sig in bank for sig in sigs):
                seen.add(move)
                out.append((move, anchor, role, sigs))
    return out


def all_local_candidates(
    *,
    board: chess.Board,
    pawns: tuple[int, ...],
    wk: int,
    bk: int,
    turn: bool,
    tb: chess.syzygy.Tablebase,
    cache: dict[tuple[str, bool], int],
    role_cache: dict[tuple[int, int, int, int], tuple[str, ...]],
    tier: int,
) -> list[tuple[chess.Move, int, str, tuple[tuple[object, ...], ...]]]:
    """All concrete moves induced by exact local KPvK role sets."""

    out = []
    seen: set[tuple[chess.Move, int, str]] = set()
    for anchor in pawns:
        for role in local_roles(
            wk=wk,
            bk=bk,
            anchor=anchor,
            turn=turn,
            tb=tb,
            cache=cache,
            role_cache=role_cache,
        ):
            move = parse_role_move(board, anchor, role)
            if move is None:
                continue
            key = (move, anchor, role)
            if key in seen:
                continue
            seen.add(key)
            sigs = tuple(
                signature(board, anchor, other, role, tier)
                for other in pawns
                if other != anchor
            )
            out.append((move, anchor, role, sigs))
    return out


def audit_moves(
    tb: chess.syzygy.Tablebase,
    board: chess.Board,
    moves: list[chess.Move],
    root: int,
) -> tuple[int, int]:
    safe = wrong = 0
    for move in moves:
        child = board.copy(stack=False)
        child.push(move)
        consequence = -exact_wdl(tb, child)
        if consequence == root:
            safe += 1
        else:
            wrong += 1
    return safe, wrong


def evaluate_boundary(
    *,
    name: str,
    pawn_sets,
    tb: chess.syzygy.Tablebase,
    cache: dict[tuple[str, bool], int],
    role_cache,
    role_map,
    tier: int,
    base_bank: set[tuple[object, ...]],
    union_bank: set[tuple[object, ...]],
) -> dict[str, object]:
    counters = {
        "preferred": Counter(),
        "certificate_set": Counter(),
        "residual_union": Counter(),
    }
    wrong_examples = {key: [] for key in counters}

    for pawns, wk, bk, turn, board in iter_boundary(pawn_sets):
        legal_count = board.legal_moves.count()
        for counter in counters.values():
            counter["legal_states"] += 1
            if legal_count == 0:
                counter["terminal_states"] += 1
            else:
                counter["nonterminal_states"] += 1
                counter["baseline_children"] += legal_count
        if legal_count == 0:
            continue

        pref = preferred_candidates(
            board, pawns, wk, bk, turn, role_map, tier, base_bank
        )
        set_base = set_candidates(
            board=board,
            pawns=pawns,
            wk=wk,
            bk=bk,
            turn=turn,
            tb=tb,
            cache=cache,
            role_cache=role_cache,
            tier=tier,
            bank=base_bank,
        )
        set_union = set_candidates(
            board=board,
            pawns=pawns,
            wk=wk,
            bk=bk,
            turn=turn,
            tb=tb,
            cache=cache,
            role_cache=role_cache,
            tier=tier,
            bank=union_bank,
        )

        root = None
        for key, candidates in (
            ("preferred", pref),
            ("certificate_set", [row[0] for row in set_base]),
            ("residual_union", [row[0] for row in set_union]),
        ):
            counter = counters[key]
            counter["qualified_states"] += int(bool(candidates))
            counter["qualified_moves"] += len(candidates)
            if candidates:
                if root is None:
                    root = exact_wdl(tb, board)
                safe, wrong = audit_moves(tb, board, candidates, root)
                counter["safe_moves"] += safe
                counter["wrong_moves"] += wrong
                counter["all_safe_states"] += int(wrong == 0)
                counter["saved_children"] += legal_count - 1
                counter["hybrid_children"] += 1
                if wrong and len(wrong_examples[key]) < 30:
                    wrong_examples[key].append(
                        {
                            "fen": board.fen(),
                            "pawns": [chess.square_name(p) for p in pawns],
                            "wrong": wrong,
                            "candidate_moves": [m.uci() for m in candidates],
                        }
                    )
            else:
                counter["hybrid_children"] += legal_count

    rows = {}
    for key, counter in counters.items():
        n = int(counter["nonterminal_states"])
        baseline = int(counter["baseline_children"])
        hybrid = int(counter["hybrid_children"])
        rows[key] = {
            **dict(counter),
            "coverage_ratio": (
                int(counter["qualified_states"]) / n if n else 0.0
            ),
            "candidate_precision": (
                int(counter["safe_moves"]) / int(counter["qualified_moves"])
                if counter["qualified_moves"]
                else 1.0
            ),
            "zero_false_positive": int(counter["wrong_moves"]) == 0,
            "child_reduction_ratio": (
                int(counter["saved_children"]) / baseline if baseline else 0.0
            ),
            "expansion_speedup": baseline / hybrid if hybrid else 1.0,
            "wrong_examples": wrong_examples[key],
        }
    return {
        "name": name,
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    started = time.time()

    header, base_bank = load_guard(args.guard)
    tier = int(header["tier_index"])
    threshold = int(header["minimum_support"])
    if str(header["tier"]) != TIER_NAMES[tier]:
        raise AssertionError("guard metadata mismatch")

    bank = coordinate_feature_bank()
    feature_fns = [fn for _name, fn in bank]
    pawn_squares = [
        chess.square(f, r)
        for f in range(8)
        for r in range(1, 6)
    ]
    cache: dict[tuple[str, bool], int] = {}
    role_cache: dict[tuple[int, int, int, int], tuple[str, ...]] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tb:
        policy, frequency, kpvk_enum, kpvk_nonterminal = acquire_policy(
            tb, feature_fns
        )
        role_map = precompute_roles(policy, feature_fns, pawn_squares)

        # Residual-only acquisition on V15 source.
        stats: dict[tuple[object, ...], list[int]] = defaultdict(
            lambda: [0, 0]
        )
        source_counts = Counter()

        for pawns, wk, bk, turn, board in iter_boundary(
            source_pawn_tuples()
        ):
            legal_count = board.legal_moves.count()
            if legal_count == 0:
                continue
            source_counts["nonterminal_states"] += 1

            # Stage 0: original preferred guard.
            pref = preferred_candidates(
                board, pawns, wk, bk, turn, role_map, tier, base_bank
            )
            if pref:
                source_counts["preferred_covered"] += 1

            # Stage A: same frozen bank, but all exact local certificates.
            set_base = set_candidates(
                board=board,
                pawns=pawns,
                wk=wk,
                bk=bk,
                turn=turn,
                tb=tb,
                cache=cache,
                role_cache=role_cache,
                tier=tier,
                bank=base_bank,
            )
            if set_base:
                source_counts["set_covered"] += 1
                continue

            # Only this residual is allowed to earn new distinctions.
            source_counts["acquisition_residual"] += 1
            root = exact_wdl(tb, board)
            for move, _anchor, _role, sigs in all_local_candidates(
                board=board,
                pawns=pawns,
                wk=wk,
                bk=bk,
                turn=turn,
                tb=tb,
                cache=cache,
                role_cache=role_cache,
                tier=tier,
            ):
                child = board.copy(stack=False)
                child.push(move)
                ok = -exact_wdl(tb, child) == root
                source_counts["acquisition_candidate_moves"] += 1
                source_counts["acquisition_safe_moves"] += int(ok)
                source_counts["acquisition_wrong_moves"] += int(not ok)
                for sig in sigs:
                    if sig in base_bank:
                        continue
                    cell = stats[sig]
                    cell[0] += 1
                    cell[1] += int(not ok)

        residual_bank = {
            sig
            for sig, (support, failures) in stats.items()
            if failures == 0 and support >= threshold
        }
        union_bank = set(base_bank) | residual_bank

        source_eval = evaluate_boundary(
            name="complete_K+3P_bcd_ranks2_4",
            pawn_sets=source_pawn_tuples(),
            tb=tb,
            cache=cache,
            role_cache=role_cache,
            role_map=role_map,
            tier=tier,
            base_bank=base_bank,
            union_bank=union_bank,
        )

        target_eval = evaluate_boundary(
            name="complete_K+4P_bcde_ranks2_4",
            pawn_sets=target_pawn_tuples(),
            tb=tb,
            cache=cache,
            role_cache=role_cache,
            role_map=role_map,
            tier=tier,
            base_bank=base_bank,
            union_bank=union_bank,
        )

    target_union = target_eval["rows"]["residual_union"]
    target_set = target_eval["rows"]["certificate_set"]
    status = (
        "WARRANTED_PROSPECTIVE_RESIDUAL_CERTIFICATE_SET_TRANSFER"
        if int(target_union["qualified_states"])
        > int(target_set["qualified_states"])
        and bool(target_union["zero_false_positive"])
        else "EXACT_RESIDUAL_CERTIFICATE_SET_TRANSFER"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "lineage": {
            "v14": V14_AUTHORITY,
            "v14_run": V14_RUN,
            "v15": V15_AUTHORITY,
            "v15_run": V15_RUN,
            "v16": V16_AUTHORITY,
            "v16_run": V16_RUN,
        },
        "frozen_guard": {
            "tier": str(header["tier"]),
            "tier_index": tier,
            "minimum_support": threshold,
            "source_safe_signatures": len(base_bank),
        },
        "stage_A_certificate_set": {
            "distinction": (
                "replace one preferred local witness with the full exact local "
                "KPvK WDL-preserving certificate set; no richer labels"
            ),
        },
        "stage_B_residual_acquisition": {
            "source": "only K+3P states still uncovered after Stage A",
            "source_counts": dict(source_counts),
            "candidate_pair_signatures": len(stats),
            "new_zero_error_signatures": len(residual_bank),
            "union_signatures": len(union_bank),
            "admission": (
                "support >= frozen V14 threshold and zero errors on every "
                "occurrence in Stage-A residual"
            ),
        },
        "source_reclosure": source_eval,
        "prospective_target": target_eval,
        "epistemic_boundary": {
            "warranted_if_green": [
                "Stage A changes only witness-set semantics and reads no richer target label for guard acquisition",
                "Stage B acquires new signatures only from the Stage-A K+3P residual",
                "K+4P labels never alter the frozen bank before prospective evaluation",
                "every promoted target shortcut has zero exact Syzygy WDL errors",
                "outside admitted states full legal-child fallback remains unchanged",
            ],
            "unknown": [
                "transfer to mixed-piece material",
                "production alpha-beta wall-clock gain",
                "general chess solution",
            ],
        },
        "cache": {
            "local_projection_role_sets": len(role_cache),
            "wdl_cache": len(cache),
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

    print(f"CRYSTAL_CHESS_RESIDUAL_CERTIFICATE_SET_V17={status}")
    print(
        f"source preferred={source_eval['rows']['preferred']['qualified_states']} "
        f"set={source_eval['rows']['certificate_set']['qualified_states']} "
        f"union={source_eval['rows']['residual_union']['qualified_states']} "
        f"new_signatures={len(residual_bank)}"
    )
    print(
        f"target preferred={target_eval['rows']['preferred']['qualified_states']} "
        f"set={target_eval['rows']['certificate_set']['qualified_states']} "
        f"union={target_eval['rows']['residual_union']['qualified_states']} "
        f"wrong={target_union['wrong_moves']} "
        f"prune={target_union['child_reduction_ratio']:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
