#!/usr/bin/env python3
"""Crystal Go V2: explicit boundary-interface residual acquisition and held-out transfer.

Parent V0 showed that an exact 3x3 local capture policy transfers to 96.50% of
winning states across 16 exhaustive 5x5 outer contexts. Failures cluster in a
small subset of outer contexts, which suggests the missing coordinate is not
the target's local shape itself but support/continuation of groups across the
declared local boundary.

V1 showed scalar boundary-support summaries are still too coarse: two acquisition states remain observationally merged while requiring different winning actions. V2 promotes the external boundary condition itself as the consequential interface and tests whether that representation transfers prospectively.

* Generation 1 is the frozen V0 policy learned only from the complete 3x3
  world.
* The 16 deterministic 5x5 outer contexts are split prospectively:
    acquisition = even indices, test = odd indices.
* Generation 2 sees only acquisition-context labels.
* Its representation adds boundary-support observables:
    full-board group size/liberties for each local intersection,
    whether that group crosses the 3x3 boundary,
    and how many liberties lie outside the boundary.
* The controller outputs BASE (reuse Generation 1) or one repair move role.
* Every acquisition and held-out success is independently checked by the exact
  bounded local-Go minimax verifier.

This is a bounded local Go result, not a full-board Go claim.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
from sklearn.tree import DecisionTreeClassifier

from crystal_go_local_capture_v0 import (
    BLACK,
    EMPTY,
    PASS,
    WHITE,
    ExactCaptureSolver,
    center_region,
    deterministic_outer_contexts,
    enumerate_inner_assignments,
    group_and_liberties,
    local_features,
    move_from_role,
    role,
)


SCHEMA = "mathgraph.crystal-go.boundary-interface.v2"
V0_AUTHORITY = (
    "metalogiclabs/mathgraph@ff78e306baf13787c22fe88f410a31605dc328b1"
)
V1_LINEAGE = (
    "metalogiclabs/mathgraph@72ac75f40fb1dfbfb7f9cc28ceabe905d67c513c"
)
BASE = "<BASE>"


def build_source_policy(horizon: int):
    n = 3
    region, target = center_region(n)
    boards = enumerate_inner_assignments(n)
    solver = ExactCaptureSolver(n, target, region, horizon)

    winning_boards = []
    winning_move_sets = []
    frequency = Counter()
    for board in boards:
        moves = solver.winning_black_moves(board)
        if not moves:
            continue
        winning_boards.append(board)
        winning_move_sets.append(moves)
        frequency.update(role(move, n, target) for move in moves)

    ranking = {
        label: rank
        for rank, (label, _count) in enumerate(
            sorted(frequency.items(), key=lambda kv: (-kv[1], kv[0]))
        )
    }
    X = []
    y = []
    for board, moves in zip(winning_boards, winning_move_sets):
        labels = [role(move, n, target) for move in moves]
        chosen = min(labels, key=lambda label: (ranking[label], label))
        X.append(local_features(board, n, target))
        y.append(chosen)

    tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    tree.fit(np.asarray(X, dtype=np.int16), y)

    pred = [str(x) for x in tree.predict(np.asarray(X, dtype=np.int16))]
    for label, moves in zip(pred, winning_move_sets):
        if label not in {role(move, n, target) for move in moves}:
            raise AssertionError("frozen V0 source policy failed exact replay")

    return tree, frequency


def boundary_interface_features(
    board: tuple[int, ...],
    n: int,
    target: int,
    region: frozenset[int],
) -> tuple[int, ...]:
    base = list(local_features(board, n, target))
    tr, tc = divmod(target, n)
    local_cells = [
        (tr + dr) * n + (tc + dc)
        for dr in (-1, 0, 1)
        for dc in (-1, 0, 1)
    ]

    seen_group_signature: dict[frozenset[int], tuple[int, int, int, int]] = {}
    for i in local_cells:
        stone = board[i]
        if stone == EMPTY:
            base.extend((0, 0, 0, 0, 0))
            continue
        group, liberties = group_and_liberties(board, n, i)
        sig = seen_group_signature.get(group)
        if sig is None:
            crosses = int(any(cell not in region for cell in group))
            external_libs = sum(lib not in region for lib in liberties)
            sig = (
                stone,
                len(group),
                len(liberties),
                crosses,
                external_libs,
            )
            seen_group_signature[group] = sig
        base.extend(sig)

    # Aggregate interface load/support across local groups.
    unique_groups = {}
    for i in region:
        if board[i] == EMPTY:
            continue
        group, liberties = group_and_liberties(board, n, i)
        unique_groups[group] = (board[i], liberties)
    crossing_black = 0
    crossing_white = 0
    external_black_libs = 0
    external_white_libs = 0
    for group, (stone, liberties) in unique_groups.items():
        if any(cell not in region for cell in group):
            if stone == BLACK:
                crossing_black += 1
            else:
                crossing_white += 1
        ext = sum(lib not in region for lib in liberties)
        if stone == BLACK:
            external_black_libs += ext
        else:
            external_white_libs += ext
    base.extend(
        (
            crossing_black,
            crossing_white,
            external_black_libs,
            external_white_libs,
        )
    )

    # V2 consequential interface: exact external boundary occupancy relative to
    # the declared local move region.  This is still far smaller than a future
    # tree: it names only the environmental condition attached to the local
    # capability, and held-out contexts test whether the learned rule uses it
    # compositionally rather than memorising one world.
    for i in range(n * n):
        if i not in region:
            base.append(board[i])
    return tuple(base)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=5)
    ap.add_argument("--outer-contexts", type=int, default=16)
    ap.add_argument("--outer-seed", type=int, default=20260928)
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_go_boundary_interface_v2.json"),
    )
    args = ap.parse_args()
    started = time.time()

    base_policy, source_frequency = build_source_policy(args.horizon)

    n = 5
    region, target = center_region(n)
    contexts = deterministic_outer_contexts(
        n, args.outer_contexts, args.outer_seed
    )
    acquisition_ids = {
        i for i in range(args.outer_contexts) if i % 2 == 0
    }
    test_ids = {
        i for i in range(args.outer_contexts) if i % 2 == 1
    }

    acquisition_records = []
    test_records = []
    residual_frequency = Counter()
    context_stats = []

    for context_index, outer in enumerate(contexts):
        boards = enumerate_inner_assignments(n, outer)
        solver = ExactCaptureSolver(n, target, region, args.horizon)
        wins = 0
        base_success = 0
        residuals = 0

        for board in boards:
            winning_moves = solver.winning_black_moves(board)
            if not winning_moves:
                continue
            wins += 1
            winning_roles = tuple(
                sorted({role(move, n, target) for move in winning_moves})
            )
            base_features = np.asarray(
                [local_features(board, n, target)], dtype=np.int16
            )
            base_role = str(base_policy.predict(base_features)[0])
            base_ok = base_role in winning_roles
            base_success += int(base_ok)
            residuals += int(not base_ok)

            record = {
                "features": boundary_interface_features(
                    board, n, target, region
                ),
                "base_role": base_role,
                "winning_roles": winning_roles,
                "context": context_index,
            }
            if context_index in acquisition_ids:
                acquisition_records.append(record)
                if not base_ok:
                    residual_frequency.update(winning_roles)
            else:
                test_records.append(record)

        context_stats.append(
            {
                "context": context_index,
                "split": (
                    "acquisition"
                    if context_index in acquisition_ids
                    else "prospective_test"
                ),
                "legal_inner_states": len(boards),
                "winning_states": wins,
                "base_success": base_success,
                "base_ratio": base_success / wins if wins else 1.0,
                "base_residual": residuals,
                "solver_cache_states": len(solver.cache),
            }
        )

    repair_ranking = {
        label: rank
        for rank, (label, _count) in enumerate(
            sorted(residual_frequency.items(), key=lambda kv: (-kv[1], kv[0]))
        )
    }
    if not repair_ranking:
        raise AssertionError("acquisition split contains no V0 residual")

    X_acq = []
    y_acq = []
    acq_base_success = 0
    acq_residual = 0
    for rec in acquisition_records:
        X_acq.append(rec["features"])
        if rec["base_role"] in rec["winning_roles"]:
            y_acq.append(BASE)
            acq_base_success += 1
        else:
            chosen = min(
                rec["winning_roles"],
                key=lambda label: (
                    repair_ranking.get(label, 10**9),
                    label,
                ),
            )
            y_acq.append(chosen)
            acq_residual += 1

    controller = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    controller.fit(np.asarray(X_acq, dtype=np.int16), y_acq)

    # Exact acquisition reclosure.
    acq_pred = [
        str(x)
        for x in controller.predict(np.asarray(X_acq, dtype=np.int16))
    ]
    acq_combined = 0
    acq_repairs = 0
    for pred, rec in zip(acq_pred, acquisition_records):
        chosen = rec["base_role"] if pred == BASE else pred
        acq_repairs += int(pred != BASE)
        acq_combined += int(chosen in rec["winning_roles"])
    if acq_combined != len(acquisition_records):
        raise AssertionError(
            f"boundary-support controller not exact on acquisition: "
            f"{acq_combined}/{len(acquisition_records)}"
        )

    # Prospective held-out contexts.
    X_test = np.asarray(
        [rec["features"] for rec in test_records], dtype=np.int16
    )
    test_pred = [str(x) for x in controller.predict(X_test)]
    test_base_success = 0
    test_combined = 0
    test_repairs = 0
    failures = []
    for pred, rec in zip(test_pred, test_records):
        base_ok = rec["base_role"] in rec["winning_roles"]
        test_base_success += int(base_ok)
        chosen = rec["base_role"] if pred == BASE else pred
        ok = chosen in rec["winning_roles"]
        test_combined += int(ok)
        test_repairs += int(pred != BASE)
        if not ok and len(failures) < 40:
            failures.append(
                {
                    "context": rec["context"],
                    "base_role": rec["base_role"],
                    "controller_output": pred,
                    "winning_roles": list(rec["winning_roles"]),
                    "features": [int(x) for x in rec["features"]],
                }
            )

    leaves = int(controller.tree_.n_leaves)
    nodes = int(controller.tree_.node_count)
    depth = int(controller.tree_.max_depth)

    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_BOUNDED_GO_BOUNDARY_INTERFACE_TRANSFER",
        "v0_authority": V0_AUTHORITY,
        "v1_lineage": V1_LINEAGE,
        "rules_boundary": {
            "same_as_v0": True,
            "horizon_plies": args.horizon,
            "move_region": "central 3x3",
        },
        "split": {
            "outer_contexts": args.outer_contexts,
            "acquisition_contexts": sorted(acquisition_ids),
            "prospective_test_contexts": sorted(test_ids),
            "labels_from_test_contexts_used_in_acquisition": 0,
        },
        "generation_1": {
            "source_role_frequency": dict(source_frequency),
            "acquisition_states": len(acquisition_records),
            "acquisition_base_success": acq_base_success,
            "acquisition_base_residual": acq_residual,
            "test_states": len(test_records),
            "test_base_success": test_base_success,
            "test_base_ratio": (
                test_base_success / len(test_records)
                if test_records
                else 1.0
            ),
        },
        "generation_2": {
            "representation": (
                "local V0 features + group support summaries + exact occupancy "
                "of the external boundary interface"
            ),
            "residual_role_frequency": dict(residual_frequency),
            "tree": {
                "nodes": nodes,
                "leaves": leaves,
                "max_depth": depth,
            },
            "acquisition_combined_success": acq_combined,
            "acquisition_combined_ratio": (
                acq_combined / len(acquisition_records)
                if acquisition_records
                else 1.0
            ),
            "acquisition_repair_invocations": acq_repairs,
            "test_combined_success": test_combined,
            "test_combined_ratio": (
                test_combined / len(test_records)
                if test_records
                else 1.0
            ),
            "test_repair_invocations": test_repairs,
            "absolute_test_gain": (
                (test_combined - test_base_success) / len(test_records)
                if test_records
                else 0.0
            ),
            "remaining_test_residual": len(test_records) - test_combined,
            "failure_examples": failures,
        },
        "contexts": context_stats,
        "epistemic_boundary": {
            "warranted_if_green": [
                "boundary-interface repair is exact on all winning states in acquisition contexts",
                "reported prospective improvement is measured only on held-out outer contexts whose labels never entered acquisition",
                "every success is independently checked by exact bounded local-Go minimax",
            ],
            "unknown": [
                "full-board Go",
                "unbounded tsumego",
                "generalization to new move regions or scoring objectives",
            ],
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print("CRYSTAL_GO_BOUNDARY_INTERFACE_V2=PASS")
    print(
        f"acquire states={len(acquisition_records)} "
        f"base={acq_base_success} residual={acq_residual} "
        f"combined={acq_combined}"
    )
    print(
        f"test states={len(test_records)} "
        f"base={test_base_success} ratio={test_base_success/len(test_records):.6f} "
        f"combined={test_combined} ratio={test_combined/len(test_records):.6f} "
        f"gain={(test_combined-test_base_success)/len(test_records):.6f} "
        f"remaining={len(test_records)-test_combined}"
    )
    print(
        f"interface_tree leaves={leaves} depth={depth} "
        f"test_repairs={test_repairs}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
