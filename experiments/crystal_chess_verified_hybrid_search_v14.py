#!/usr/bin/env python3
"""Crystal Chess V14: verified hybrid-search pruning on complete KPPvK.

This experiment asks the smallest consequential performance question exposed by V12:

    Can a frozen KPvK capability portfolio remove ordinary child search in a
    larger exact chess world without changing the game-theoretic answer?

Boundary:
* White K+2P vs Black K.
* Both pawns are on root ranks 2..6.
* No castling/en-passant; halfmove clock 0.
* Every legal root state in the boundary is enumerated exactly.
* The KPvK policy is acquired/frozen before KPPvK evaluation.
* Syzygy WDL is verifier authority only.

Method:
1. Reproduce the complete V12 portfolio census.
2. Compile conservative structural guards for candidate capabilities. A
   (tier, signature) is admitted only when EVERY occurrence on the complete
   boundary preserves the exact root WDL, and it has at least the declared
   support threshold.
3. Re-enumerate the complete boundary without consulting WDL. If an admitted
   guard applies, the hybrid search expands one certified child; otherwise it
   falls back to the full legal-move frontier unchanged.
4. Compare full one-ply child expansion with verified-hybrid expansion.

This is a bounded exact search-pruning result, not a general-chess solution,
not an Elo claim, and not yet a UCI engine.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from typing import Iterable

import chess
import chess.syzygy

from crystal_chess_kpvk_v0 import coordinate_feature_bank
from crystal_chess_kppvk_complete_census_v12 import (
    acquire_policy,
    exact_wdl,
    parse_role_move,
    precompute_roles,
)
from crystal_chess_richer_transfer_v5 import make_kppvk


SCHEMA = "mathgraph.crystal-chess.verified-hybrid-search.v14"
BASE_V12_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-kppvk-complete-census-v12"
    "@7f161d23b24d11de3b4df6f38a3cbc1612cf07fb"
)
BASE_V12_RUN = 36353531129
EXPECTED_V12_NONTERMINAL = 5_145_060
EXPECTED_V12_PORTFOLIO_SUCCESS = 2_463_896
SUPPORT_THRESHOLDS = (8, 32, 128)
TIER_NAMES = ("role", "pair", "distance", "relational")


def sq_file(sq: int) -> int:
    return chess.square_file(sq)


def sq_rank(sq: int) -> int:
    return chess.square_rank(sq)


def sign(x: int) -> int:
    return (x > 0) - (x < 0)


def cheb(a: int, b: int) -> int:
    return max(abs(sq_file(a) - sq_file(b)), abs(sq_rank(a) - sq_rank(b)))


def file_edge(sq: int) -> int:
    f = sq_file(sq)
    return min(f, 7 - f)


def board_edge(sq: int) -> int:
    f, r = sq_file(sq), sq_rank(sq)
    return min(f, 7 - f, r, 7 - r)


def signature(
    board: chess.Board,
    anchor: int,
    other: int,
    role: str,
    tier: int,
) -> tuple[object, ...]:
    """A nested family of increasingly discriminating structural guards.

    None of these signatures contains WDL, DTZ, a tablebase index, a FEN,
    or an absolute state identifier.
    """

    wk = board.king(chess.WHITE)
    bk = board.king(chess.BLACK)
    if wk is None or bk is None:
        raise AssertionError("missing king")

    base: tuple[object, ...] = (int(board.turn), role)
    if tier == 0:
        return base

    df = sq_file(other) - sq_file(anchor)
    dr = sq_rank(other) - sq_rank(anchor)
    pair = base + (
        sq_rank(anchor),
        file_edge(anchor),
        abs(df),
        dr,
        sign(df),
    )
    if tier == 1:
        return pair

    dist = pair + (
        cheb(wk, anchor),
        cheb(bk, anchor),
        cheb(wk, other),
        cheb(bk, other),
        cheb(wk, bk),
    )
    if tier == 2:
        return dist

    relational = dist + (
        sign(sq_file(wk) - sq_file(anchor)),
        sign(sq_rank(wk) - sq_rank(anchor)),
        sign(sq_file(bk) - sq_file(anchor)),
        sign(sq_rank(bk) - sq_rank(anchor)),
        board_edge(wk),
        board_edge(bk),
    )
    if tier == 3:
        return relational

    raise ValueError(tier)


def iter_boundary(pawn_squares: list[int]) -> Iterable[tuple[int, int, int, int, bool, chess.Board]]:
    for p0_i, p0 in enumerate(pawn_squares):
        for p1 in pawn_squares[p0_i + 1 :]:
            for wk in chess.SQUARES:
                if wk in (p0, p1):
                    continue
                for bk in chess.SQUARES:
                    if bk in (p0, p1, wk):
                        continue
                    for turn in (False, True):
                        board = make_kppvk(wk, bk, p0, p1, turn)
                        if board.is_valid():
                            yield p0, p1, wk, bk, turn, board


def candidate_bindings(
    board: chess.Board,
    p0: int,
    p1: int,
    wk: int,
    bk: int,
    turn: bool,
    role_map: dict[tuple[int, int, int, int], str],
) -> list[tuple[int, int, str, chess.Move]]:
    out: list[tuple[int, int, str, chess.Move]] = []
    for anchor, other in ((p0, p1), (p1, p0)):
        role = role_map[(wk, bk, anchor, int(turn))]
        move = parse_role_move(board, anchor, role)
        if move is not None:
            out.append((anchor, other, role, move))
    return out


def guard_digest(
    stats: dict[tuple[object, ...], list[int]],
    threshold: int,
) -> tuple[str, int, int]:
    safe = [
        (key, counts[0])
        for key, counts in stats.items()
        if counts[1] == 0 and counts[0] >= threshold
    ]
    safe.sort(key=lambda row: repr(row[0]))
    h = hashlib.sha256()
    support_mass = 0
    for key, support in safe:
        payload = json.dumps(
            {"signature": list(key), "support": support},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        h.update(payload)
        h.update(b"\n")
        support_mass += support
    return h.hexdigest(), len(safe), support_mass


def write_best_guard(
    path: Path,
    stats: dict[tuple[object, ...], list[int]],
    tier: int,
    threshold: int,
) -> tuple[int, str]:
    rows = [
        (key, counts[0])
        for key, counts in stats.items()
        if counts[1] == 0 and counts[0] >= threshold
    ]
    rows.sort(key=lambda row: repr(row[0]))
    path.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        header = {
            "schema": SCHEMA + ".guard",
            "tier": TIER_NAMES[tier],
            "tier_index": tier,
            "minimum_support": threshold,
            "base_v12_authority": BASE_V12_AUTHORITY,
        }
        line = json.dumps(header, sort_keys=True, separators=(",", ":"))
        handle.write(line + "\n")
        h.update((line + "\n").encode("utf-8"))
        for key, support in rows:
            row = {"signature": list(key), "support": support}
            line = json.dumps(row, sort_keys=True, separators=(",", ":"))
            handle.write(line + "\n")
            h.update((line + "\n").encode("utf-8"))
    return len(rows), h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--guard-output", type=Path, required=True)
    args = ap.parse_args()
    started = time.time()

    files = sorted(args.tablebase_dir.glob("*.rtbw"))
    names = {p.name for p in files}
    for req in ("KPvK.rtbw", "KPPvK.rtbw"):
        if req not in names:
            raise SystemExit(f"missing {req}")
    manifest = [
        {
            "name": p.name,
            "size": p.stat().st_size,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }
        for p in files
    ]

    bank = coordinate_feature_bank()
    feature_fns = [fn for _name, fn in bank]
    pawn_squares = [
        chess.square(f, r)
        for f in range(8)
        for r in range(1, 6)  # root ranks 2..6
    ]

    # tier -> signature -> [support, failures]
    stats: list[dict[tuple[object, ...], list[int]]] = [
        defaultdict(lambda: [0, 0]) for _ in TIER_NAMES
    ]

    pass1 = Counter()
    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tb:
        policy, frequency, kpvk_enum, kpvk_nonterminal = acquire_policy(
            tb, feature_fns
        )
        role_map = precompute_roles(policy, feature_fns, pawn_squares)

        for p0, p1, wk, bk, turn, board in iter_boundary(pawn_squares):
            pass1["legal_states"] += 1
            legal_count = board.legal_moves.count()
            if legal_count == 0:
                pass1["terminal_states"] += 1
                continue

            pass1["nonterminal_states"] += 1
            pass1["baseline_child_expansions"] += legal_count
            root = exact_wdl(tb, board)
            bindings = candidate_bindings(board, p0, p1, wk, bk, turn, role_map)
            pass1["candidate_bindings"] += len(bindings)

            outcome_cache: dict[chess.Move, bool] = {}
            state_success = False
            for anchor, other, role, move in bindings:
                ok = outcome_cache.get(move)
                if ok is None:
                    board.push(move)
                    consequence = -exact_wdl(tb, board)
                    board.pop()
                    ok = consequence == root
                    outcome_cache[move] = ok
                    pass1["candidate_child_probes"] += 1
                state_success = state_success or ok
                for tier in range(len(TIER_NAMES)):
                    sig = signature(board, anchor, other, role, tier)
                    cell = stats[tier][sig]
                    cell[0] += 1
                    cell[1] += int(not ok)

            if state_success:
                pass1["portfolio_success"] += 1

    if pass1["nonterminal_states"] != EXPECTED_V12_NONTERMINAL:
        raise AssertionError(
            ("V12 nonterminal reproduction mismatch",
             pass1["nonterminal_states"], EXPECTED_V12_NONTERMINAL)
        )
    if pass1["portfolio_success"] != EXPECTED_V12_PORTFOLIO_SUCCESS:
        raise AssertionError(
            ("V12 portfolio reproduction mismatch",
             pass1["portfolio_success"], EXPECTED_V12_PORTFOLIO_SUCCESS)
        )

    guard_summaries: dict[str, dict[str, object]] = {}
    for tier, tier_name in enumerate(TIER_NAMES):
        total_classes = len(stats[tier])
        impure = sum(1 for support, failures in stats[tier].values() if failures)
        for threshold in SUPPORT_THRESHOLDS:
            digest, safe_classes, safe_support = guard_digest(stats[tier], threshold)
            key = f"{tier_name}@{threshold}"
            guard_summaries[key] = {
                "tier": tier,
                "tier_name": tier_name,
                "minimum_support": threshold,
                "all_classes": total_classes,
                "impure_classes": impure,
                "safe_classes": safe_classes,
                "safe_binding_support_mass": safe_support,
                "safe_signature_sha256": digest,
                "covered_states": 0,
                "saved_child_expansions": 0,
                "hybrid_child_expansions": 0,
            }

    # Independent execution pass: no WDL lookup is used here. The admitted
    # signature table is the complete-boundary certificate compiled above.
    pass2 = Counter()
    for p0, p1, wk, bk, turn, board in iter_boundary(pawn_squares):
        pass2["legal_states"] += 1
        legal_count = board.legal_moves.count()
        if legal_count == 0:
            pass2["terminal_states"] += 1
            continue
        pass2["nonterminal_states"] += 1
        pass2["baseline_child_expansions"] += legal_count
        bindings = candidate_bindings(board, p0, p1, wk, bk, turn, role_map)

        # Precompute each binding's nested structural signatures once.
        sigs = [
            [
                signature(board, anchor, other, role, tier)
                for tier in range(len(TIER_NAMES))
            ]
            for anchor, other, role, _move in bindings
        ]

        for key, summary in guard_summaries.items():
            tier = int(summary["tier"])
            threshold = int(summary["minimum_support"])
            covered = False
            for binding_sigs in sigs:
                support, failures = stats[tier].get(binding_sigs[tier], [0, 0])
                if failures == 0 and support >= threshold:
                    covered = True
                    break
            hybrid = 1 if covered else legal_count
            summary["hybrid_child_expansions"] = (
                int(summary["hybrid_child_expansions"]) + hybrid
            )
            if covered:
                summary["covered_states"] = int(summary["covered_states"]) + 1
                summary["saved_child_expansions"] = (
                    int(summary["saved_child_expansions"]) + legal_count - 1
                )

    if dict(pass1)[ "nonterminal_states" ] != dict(pass2)["nonterminal_states"]:
        raise AssertionError("pass1/pass2 nonterminal boundary drift")
    if dict(pass1)["baseline_child_expansions"] != dict(pass2)["baseline_child_expansions"]:
        raise AssertionError("pass1/pass2 baseline frontier drift")

    baseline = int(pass2["baseline_child_expansions"])
    nonterminal = int(pass2["nonterminal_states"])
    for summary in guard_summaries.values():
        covered = int(summary["covered_states"])
        saved = int(summary["saved_child_expansions"])
        hybrid = int(summary["hybrid_child_expansions"])
        summary["state_coverage_ratio"] = covered / nonterminal
        summary["child_reduction_ratio"] = saved / baseline
        summary["baseline_mean_branching"] = baseline / nonterminal
        summary["hybrid_mean_expansions"] = hybrid / nonterminal
        summary["expansion_speedup_factor"] = baseline / hybrid if hybrid else 1.0
        summary["certified_failure_mass"] = 0

    ranked = sorted(
        guard_summaries.items(),
        key=lambda kv: (
            -int(kv[1]["saved_child_expansions"]),
            -int(kv[1]["covered_states"]),
            int(kv[1]["safe_classes"]),
            -int(kv[1]["minimum_support"]),
        ),
    )
    best_key, best = ranked[0]

    guard_count, guard_file_sha = write_best_guard(
        args.guard_output,
        stats[int(best["tier"])],
        int(best["tier"]),
        int(best["minimum_support"]),
    )
    if guard_count != int(best["safe_classes"]):
        raise AssertionError("guard serialization class-count drift")

    complete_reproduction = (
        pass1["nonterminal_states"] == EXPECTED_V12_NONTERMINAL
        and pass1["portfolio_success"] == EXPECTED_V12_PORTFOLIO_SUCCESS
    )
    zero_regression = all(
        int(s["certified_failure_mass"]) == 0 for s in guard_summaries.values()
    )
    measurable_gain = int(best["saved_child_expansions"]) > 0
    status = (
        "WARRANTED_COMPLETE_RESTRICTED_KPPVK_VERIFIED_HYBRID_SEARCH_GAIN"
        if complete_reproduction and zero_regression and measurable_gain
        else "NO_VERIFIED_HYBRID_GAIN"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "base_v12_authority": BASE_V12_AUTHORITY,
        "base_v12_run": BASE_V12_RUN,
        "authority": {"kind": "Syzygy WDL", "tablebase_files": manifest},
        "boundary": {
            "material": "KPPvK",
            "white_pawn_root_ranks": [2, 3, 4, 5, 6],
            "complete_enumeration": True,
            "castling": False,
            "en_passant": False,
            "root_halfmove_clock": 0,
        },
        "frozen_kpvk_capability": {
            "kpvk_nonterminal_states": kpvk_nonterminal,
            "role_frequency": frequency,
            "precomputed_contexts": len(role_map),
        },
        "pass1_exact_certificate_compilation": dict(pass1),
        "v12_reproduction": {
            "expected_nonterminal": EXPECTED_V12_NONTERMINAL,
            "expected_portfolio_success": EXPECTED_V12_PORTFOLIO_SUCCESS,
            "exact": complete_reproduction,
        },
        "guard_family": {
            "tiers": list(TIER_NAMES),
            "support_thresholds": list(SUPPORT_THRESHOLDS),
            "configs": guard_summaries,
        },
        "best_guard": {
            "key": best_key,
            **best,
            "guard_file": str(args.guard_output),
            "guard_file_sha256": guard_file_sha,
        },
        "performance_boundary": {
            "baseline": (
                "complete one-ply legal-child expansion at every nonterminal root"
            ),
            "hybrid": (
                "one certified child when a complete-boundary safe structural "
                "guard applies; otherwise unchanged full legal-child fallback"
            ),
            "correctness": (
                "every admitted guard class has zero WDL-preservation failures "
                "over every occurrence on the complete declared boundary"
            ),
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "V12 complete KPPvK portfolio census is exactly reproduced",
                "the compiled guard is zero-false-positive on the complete declared KPPvK boundary",
                "fallback is unchanged outside certified states",
                "reported child-expansion reduction is exact for the declared one-ply search boundary",
            ],
            "unknown": [
                "prospective transfer of this KPPvK guard to richer material",
                "wall-clock gain in a production alpha-beta engine",
                "UCI Elo gain",
                "general chess solution",
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

    print(f"CRYSTAL_CHESS_VERIFIED_HYBRID_SEARCH_V14={status}")
    print(
        "v12_reproduction="
        f"{pass1['portfolio_success']}/{pass1['nonterminal_states']}"
    )
    print(
        f"best_guard={best_key} safe_classes={best['safe_classes']} "
        f"coverage={best['covered_states']}/{nonterminal} "
        f"coverage_ratio={best['state_coverage_ratio']:.8f}"
    )
    print(
        f"baseline_children={baseline} hybrid_children={best['hybrid_child_expansions']} "
        f"saved={best['saved_child_expansions']} "
        f"reduction={best['child_reduction_ratio']:.8f} "
        f"speedup={best['expansion_speedup_factor']:.6f}x"
    )
    print(f"guard_sha256={guard_file_sha}")
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
