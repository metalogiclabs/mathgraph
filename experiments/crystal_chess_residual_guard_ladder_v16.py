#!/usr/bin/env python3
"""Crystal Chess V16: residual-only exact guard refinement ladder.

Parent V14 found the best single global guard family on the complete restricted
KPPvK boundary:

    pair@8 -> 1,112,360 / 5,145,060 shortcut states
              7,983,218 / 35,703,558 child expansions removed

But V14 evaluated deeper signatures as separate global guards. Crystal's actual
developmental rule is different: preserve the already-warranted pair guard,
then spend representation only on its exact residual.

V16 therefore uses the same complete boundary, same frozen KPvK capability,
same exact Syzygy WDL authority, and the same already-declared nested structural
vocabulary. No new chess feature is added.

Admission ladder, support >= 8 and zero failures:
1. Pair signature globally safe -> admit.
2. Otherwise, if its distance signature is safe -> admit.
3. Otherwise, if its relational signature is safe -> admit.
4. Otherwise fail closed to unchanged full legal-child expansion.

Because distance contains pair, and relational contains distance, global
complete-boundary statistics are enough to qualify residual children without
replaying already-safe parents. The second execution pass uses no WDL probes.

This tests the exact Crystal rule:
    warranted capability -> residual -> minimum existing separator -> reclose
rather than training a new global classifier.
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

import chess
import chess.syzygy

from crystal_chess_kpvk_v0 import coordinate_feature_bank
from crystal_chess_kppvk_complete_census_v12 import (
    acquire_policy,
    exact_wdl,
    precompute_roles,
)
from crystal_chess_verified_hybrid_search_v14 import (
    BASE_V12_AUTHORITY,
    BASE_V12_RUN,
    EXPECTED_V12_NONTERMINAL,
    EXPECTED_V12_PORTFOLIO_SUCCESS,
    TIER_NAMES,
    candidate_bindings,
    iter_boundary,
    signature,
)


SCHEMA = "mathgraph.crystal-chess.residual-guard-ladder.v16"
BASE_V14_AUTHORITY = (
    "metalogiclabs/mathgraph:crystal-chess-verified-hybrid-search-v14"
    "@55be612bbf8cf3bd26ef10d5474873443f0f7edd"
)
BASE_V14_RUN = 36357299241
SUPPORT = 8
PAIR_TIER = 1
DIST_TIER = 2
REL_TIER = 3
EXPECTED_V14_PAIR_CLASSES = 6408
EXPECTED_V14_PAIR_COVERAGE = 1112360
EXPECTED_BASELINE_CHILDREN = 35703558


def safe_keys(
    stats: dict[tuple[object, ...], list[int]],
    *,
    support: int,
) -> set[tuple[object, ...]]:
    return {
        key
        for key, (count, failures) in stats.items()
        if failures == 0 and count >= support
    }


def write_guard(
    path: Path,
    pair_safe: set[tuple[object, ...]],
    distance_safe_residual: set[tuple[object, ...]],
    relational_safe_residual: set[tuple[object, ...]],
    stats,
) -> tuple[str, dict[str, int]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    counts = {}

    with gzip.open(path, "wt", encoding="utf-8") as handle:
        header = {
            "schema": SCHEMA + ".guard",
            "base_v14_authority": BASE_V14_AUTHORITY,
            "base_v14_run": BASE_V14_RUN,
            "minimum_support": SUPPORT,
            "tiers": ["pair", "distance", "relational"],
            "rule": "first-safe-tier over residual-only ladder",
        }
        line = json.dumps(header, sort_keys=True, separators=(",", ":"))
        handle.write(line + "\n")
        h.update((line + "\n").encode("utf-8"))

        for tier_name, tier_idx, keys in (
            ("pair", PAIR_TIER, pair_safe),
            ("distance", DIST_TIER, distance_safe_residual),
            ("relational", REL_TIER, relational_safe_residual),
        ):
            counts[tier_name] = len(keys)
            rows = sorted(keys, key=repr)
            for key in rows:
                support, failures = stats[tier_idx][key]
                if failures != 0 or support < SUPPORT:
                    raise AssertionError("unsafe guard row escaped admission")
                row = {
                    "tier": tier_name,
                    "tier_index": tier_idx,
                    "signature": list(key),
                    "support": support,
                }
                line = json.dumps(row, sort_keys=True, separators=(",", ":"))
                handle.write(line + "\n")
                h.update((line + "\n").encode("utf-8"))

    return h.hexdigest(), counts


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
        for r in range(1, 6)
    ]

    # Complete-boundary source truth. Keep all nested signatures because each
    # child signature deterministically names its parent.
    stats = [
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
            bindings = candidate_bindings(
                board, p0, p1, wk, bk, turn, role_map
            )
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

                for tier in (PAIR_TIER, DIST_TIER, REL_TIER):
                    sig = signature(
                        board, anchor, other, role, tier
                    )
                    cell = stats[tier][sig]
                    cell[0] += 1
                    cell[1] += int(not ok)

            if state_success:
                pass1["portfolio_success"] += 1

    if pass1["nonterminal_states"] != EXPECTED_V12_NONTERMINAL:
        raise AssertionError(
            (
                "V12 nonterminal mismatch",
                pass1["nonterminal_states"],
                EXPECTED_V12_NONTERMINAL,
            )
        )
    if pass1["portfolio_success"] != EXPECTED_V12_PORTFOLIO_SUCCESS:
        raise AssertionError(
            (
                "V12 portfolio mismatch",
                pass1["portfolio_success"],
                EXPECTED_V12_PORTFOLIO_SUCCESS,
            )
        )
    if pass1["baseline_child_expansions"] != EXPECTED_BASELINE_CHILDREN:
        raise AssertionError(
            (
                "baseline child mismatch",
                pass1["baseline_child_expansions"],
                EXPECTED_BASELINE_CHILDREN,
            )
        )

    all_pair_safe = safe_keys(stats[PAIR_TIER], support=SUPPORT)
    all_distance_safe = safe_keys(stats[DIST_TIER], support=SUPPORT)
    all_relational_safe = safe_keys(stats[REL_TIER], support=SUPPORT)

    if len(all_pair_safe) != EXPECTED_V14_PAIR_CLASSES:
        raise AssertionError(
            (
                "V14 pair-class reproduction mismatch",
                len(all_pair_safe),
                EXPECTED_V14_PAIR_CLASSES,
            )
        )

    # Residual-only admission. Signature nesting is exact:
    # pair = dist[:7], distance = relational[:12].
    distance_safe_residual = {
        sig
        for sig in all_distance_safe
        if tuple(sig[:7]) not in all_pair_safe
    }
    relational_safe_residual = {
        sig
        for sig in all_relational_safe
        if tuple(sig[:7]) not in all_pair_safe
        and tuple(sig[:12]) not in distance_safe_residual
    }

    # Independent execution pass: no WDL probes. Each state takes one child
    # only if at least one binding is covered by the earliest admitted tier.
    pass2 = Counter()
    tier_state_coverage = Counter()
    tier_binding_hits = Counter()

    for p0, p1, wk, bk, turn, board in iter_boundary(pawn_squares):
        pass2["legal_states"] += 1
        legal_count = board.legal_moves.count()
        if legal_count == 0:
            pass2["terminal_states"] += 1
            continue

        pass2["nonterminal_states"] += 1
        pass2["baseline_child_expansions"] += legal_count
        bindings = candidate_bindings(
            board, p0, p1, wk, bk, turn, role_map
        )

        best_tier = None
        for anchor, other, role, _move in bindings:
            pair_sig = signature(
                board, anchor, other, role, PAIR_TIER
            )
            if pair_sig in all_pair_safe:
                tier_binding_hits["pair"] += 1
                best_tier = "pair"
                break

        if best_tier is None:
            for anchor, other, role, _move in bindings:
                dist_sig = signature(
                    board, anchor, other, role, DIST_TIER
                )
                if dist_sig in distance_safe_residual:
                    tier_binding_hits["distance"] += 1
                    best_tier = "distance"
                    break

        if best_tier is None:
            for anchor, other, role, _move in bindings:
                rel_sig = signature(
                    board, anchor, other, role, REL_TIER
                )
                if rel_sig in relational_safe_residual:
                    tier_binding_hits["relational"] += 1
                    best_tier = "relational"
                    break

        if best_tier is not None:
            tier_state_coverage[best_tier] += 1
            pass2["covered_states"] += 1
            pass2["hybrid_child_expansions"] += 1
            pass2["saved_child_expansions"] += legal_count - 1
        else:
            pass2["hybrid_child_expansions"] += legal_count

    if pass2["nonterminal_states"] != pass1["nonterminal_states"]:
        raise AssertionError("source/execution nonterminal drift")
    if pass2["baseline_child_expansions"] != pass1["baseline_child_expansions"]:
        raise AssertionError("source/execution baseline drift")
    if tier_state_coverage["pair"] != EXPECTED_V14_PAIR_COVERAGE:
        raise AssertionError(
            (
                "V14 pair coverage reproduction mismatch",
                tier_state_coverage["pair"],
                EXPECTED_V14_PAIR_COVERAGE,
            )
        )

    baseline = int(pass2["baseline_child_expansions"])
    hybrid = int(pass2["hybrid_child_expansions"])
    covered = int(pass2["covered_states"])
    saved = int(pass2["saved_child_expansions"])
    nonterminal = int(pass2["nonterminal_states"])

    guard_digest, guard_counts = write_guard(
        args.guard_output,
        all_pair_safe,
        distance_safe_residual,
        relational_safe_residual,
        stats,
    )

    result = {
        "schema": SCHEMA,
        "status": (
            "WARRANTED_COMPLETE_RESTRICTED_KPPVK_RESIDUAL_GUARD_LADDER_GAIN"
            if saved > 7983218
            else "NO_ADDITIONAL_RESIDUAL_GUARD_GAIN"
        ),
        "base_v12_authority": BASE_V12_AUTHORITY,
        "base_v12_run": BASE_V12_RUN,
        "base_v14_authority": BASE_V14_AUTHORITY,
        "base_v14_run": BASE_V14_RUN,
        "authority": {
            "kind": "Syzygy WDL",
            "tablebase_files": manifest,
        },
        "boundary": {
            "material": "KPPvK",
            "white_pawn_root_ranks": [2, 3, 4, 5, 6],
            "complete_enumeration": True,
            "both_sides_to_move": True,
        },
        "frozen_kpvk_capability": {
            "kpvk_nonterminal_states": kpvk_nonterminal,
            "role_frequency": frequency,
            "precomputed_contexts": len(role_map),
            "kpvk_enumeration": kpvk_enum,
        },
        "source_reproduction": dict(pass1),
        "guard_ladder": {
            "minimum_support": SUPPORT,
            "pair_safe_classes": len(all_pair_safe),
            "distance_safe_residual_classes": len(
                distance_safe_residual
            ),
            "relational_safe_residual_classes": len(
                relational_safe_residual
            ),
            "serialized_counts": guard_counts,
            "semantic_guard_sha256": guard_digest,
            "state_coverage_by_first_tier": dict(
                tier_state_coverage
            ),
            "binding_hits_by_first_tier": dict(
                tier_binding_hits
            ),
        },
        "performance": {
            "nonterminal_states": nonterminal,
            "covered_states": covered,
            "state_coverage_ratio": covered / nonterminal,
            "baseline_child_expansions": baseline,
            "hybrid_child_expansions": hybrid,
            "saved_child_expansions": saved,
            "child_reduction_ratio": saved / baseline,
            "expansion_speedup_factor": baseline / hybrid,
            "baseline_v14_saved_children": 7983218,
            "incremental_saved_children_vs_v14": saved - 7983218,
            "incremental_covered_states_vs_v14": (
                covered - EXPECTED_V14_PAIR_COVERAGE
            ),
            "certified_failure_mass": 0,
        },
        "method": {
            "development_rule": (
                "preserve pair@8, refine only its residual into distance, "
                "then refine only the remaining residual into relational"
            ),
            "new_feature_vocabulary": False,
            "execution_pass_uses_wdl": False,
            "fallback": "unchanged full legal-child frontier",
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "V12 complete portfolio census is exactly reproduced",
                "V14 pair@8 safe classes and coverage are exactly reproduced",
                "every newly admitted distance/relational class has zero failures on the complete source boundary",
                "the second execution pass uses no WDL truth and falls back unchanged outside the guard ladder",
            ],
            "unknown": [
                "prospective transfer of the residual-refined guard to richer material",
                "production-engine wall-clock gain",
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

    print(
        "CRYSTAL_CHESS_RESIDUAL_GUARD_LADDER_V16="
        + result["status"]
    )
    print(
        f"covered={covered}/{nonterminal} "
        f"ratio={covered/nonterminal:.8f} "
        f"pair={tier_state_coverage['pair']} "
        f"distance_add={tier_state_coverage['distance']} "
        f"relational_add={tier_state_coverage['relational']}"
    )
    print(
        f"baseline_children={baseline} hybrid_children={hybrid} "
        f"saved={saved} reduction={saved/baseline:.8f} "
        f"speedup={baseline/hybrid:.6f}x "
        f"incremental_saved_vs_v14={saved-7983218}"
    )
    print(
        f"guard_classes pair={len(all_pair_safe)} "
        f"distance_residual={len(distance_safe_residual)} "
        f"relational_residual={len(relational_safe_residual)} "
        f"digest={guard_digest}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
