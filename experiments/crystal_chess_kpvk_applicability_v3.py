#!/usr/bin/env python3
"""Crystal Chess V3: counterexample-driven applicability boundary discovery.

The V2 full-boundary symbolic controller is exact, but b/c/d -> a rook-pawn
zero-shot transfer is unsafe. V3 withholds each canonical pawn file in turn
and removes raw horizontal file identity from the transferable grammar.

This is not a new solver. It asks a narrower Crystal question:
which source families may safely share one compiled capability?

Promotion rule:
- a transfer is SAFE only when held-out outcome errors = 0,
  policy unsafe false positives = 0, and every state requiring a choice has
  at least one true-positive predicted choice.
- otherwise the target family remains separated / UNKNOWN for that capability.
"""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import platform
import sys
import time

import chess
import chess.syzygy
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from crystal_chess_kpvk_v0 import coordinate_feature_bank, enumerate_records
from crystal_chess_kpvk_proof_v1 import build_graph, solve_white_attractor
from crystal_chess_kpvk_symbolic_v2 import (
    build_move_dataset,
    exact_error_counts,
    heldout_policy_coverage,
)

SCHEMA = "mathgraph.crystal-chess.kpvk-applicability-v3"
V2_AUTHORITY = "metalogiclabs/mathgraph@a63930060e626dfb41eec1cff837e7fa0e63ac13"

# Forbid literal horizontal file identity. Relative geometry, vertical
# coordinates and generic distance-to-board-boundary observables remain.
FORBIDDEN_STATE_FEATURES = {"pawn_file", "wk_file", "bk_file"}


def fit_tree(X, y):
    clf = DecisionTreeClassifier(
        criterion="entropy", splitter="best", random_state=0
    )
    clf.fit(X, y)
    return clf


def evaluate_transfer(
    records,
    X_state,
    outcome,
    X_move,
    y_move,
    state_indices,
    heldout_file,
):
    pawn_files = np.asarray(
        [chess.square_file(rec.pawn) for rec in records], dtype=np.int8
    )
    train_state = pawn_files != heldout_file
    test_state = pawn_files == heldout_file

    outcome_tree = fit_tree(X_state[train_state], outcome[train_state])
    outcome_pred = outcome_tree.predict(X_state[test_state]).astype(np.int8)
    outcome_errors = int(np.sum(outcome_pred != outcome[test_state]))

    move_train = np.asarray(
        [
            chess.square_file(records[int(i)].pawn) != heldout_file
            for i in state_indices
        ],
        dtype=bool,
    )
    policy_tree = fit_tree(X_move[move_train], y_move[move_train])
    policy_pred_all = policy_tree.predict(X_move).astype(np.int8)
    policy = heldout_policy_coverage(
        records,
        state_indices,
        y_move,
        policy_pred_all,
        heldout_file,
    )

    safe = (
        outcome_errors == 0
        and policy["false_positive_unsafe"] == 0
        and policy["safe_choice_state_coverage"] == 1.0
    )
    result = {
        "heldout_file": chess.FILE_NAMES[heldout_file],
        "train_files": [
            chess.FILE_NAMES[i] for i in range(4) if i != heldout_file
        ],
        "outcome": {
            "test_states": int(test_state.sum()),
            "errors": outcome_errors,
            "accuracy": 1.0 - outcome_errors / int(test_state.sum()),
            "tree_nodes": int(outcome_tree.tree_.node_count),
            "tree_leaves": int(outcome_tree.get_n_leaves()),
            "tree_depth": int(outcome_tree.get_depth()),
        },
        "policy": {
            **policy,
            "tree_nodes": int(policy_tree.tree_.node_count),
            "tree_leaves": int(policy_tree.get_n_leaves()),
            "tree_depth": int(policy_tree.get_depth()),
        },
        "safe_transfer": bool(safe),
    }
    del outcome_tree, policy_tree, policy_pred_all
    gc.collect()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("crystal_chess_kpvk_applicability_v3.json")
    )
    args = parser.parse_args()
    started = time.time()

    full_bank = coordinate_feature_bank()
    full_names = [name for name, _ in full_bank]
    kept_indices = [
        i for i, name in enumerate(full_names)
        if name not in FORBIDDEN_STATE_FEATURES
    ]
    kept_names = [full_names[i] for i in kept_indices]

    cache = {}
    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        records, enumeration = enumerate_records(
            tablebase, cache, [fn for _, fn in full_bank]
        )
        if enumeration["mirror_mismatches"] or enumeration["mirror_invalid"]:
            raise AssertionError(enumeration)
        edges, graph_stats = build_graph(records, tablebase, cache)
        rank, passes = solve_white_attractor(records, edges)

    outcome = np.asarray([int(r is not None) for r in rank], dtype=np.int8)
    X_state_full = np.asarray([rec.features for rec in records], dtype=np.int16)
    X_state = X_state_full[:, kept_indices]

    X_move_full, y_move, state_indices, _ = build_move_dataset(records, edges, rank)
    # Move rows begin with the same state feature bank, followed by 5 local
    # action observables. Keep allowed state columns + all local action columns.
    action_cols = list(range(len(full_names), len(full_names) + 5))
    X_move = X_move_full[:, kept_indices + action_cols]
    del X_move_full, X_state_full
    gc.collect()

    transfers = []
    for heldout_file in range(4):
        transfers.append(
            evaluate_transfer(
                records,
                X_state,
                outcome,
                X_move,
                y_move,
                state_indices,
                heldout_file,
            )
        )

    safe_files = [x["heldout_file"] for x in transfers if x["safe_transfer"]]
    unsafe_files = [x["heldout_file"] for x in transfers if not x["safe_transfer"]]

    # Empirical applicability classes are the minimum conclusion licensed by
    # the withheld-file tests: files that cannot be zero-shot recovered must
    # not share an unqualified transport claim.
    result = {
        "schema": SCHEMA,
        "status": (
            "WARRANTED_BOUNDED_FILE_TRANSFER_MAP"
            if transfers
            else "UNKNOWN"
        ),
        "lineage": {"v2_authority": V2_AUTHORITY},
        "grammar": {
            "kept_state_features": kept_names,
            "forbidden_raw_identity_features": sorted(FORBIDDEN_STATE_FEATURES),
            "local_action_features_retained": 5,
        },
        "boundary": {
            "states": len(records),
            "legal_move_rows": int(len(y_move)),
            "canonical_files": ["a", "b", "c", "d"],
            "v1_fixed_point_passes": int(passes),
            "v1_max_rank": int(max(r for r in rank if r is not None)),
            "material_only_exit_counterexamples_requalified": int(
                graph_stats["exit_oracle_mismatch_count"]
            ),
        },
        "leave_one_file_out": transfers,
        "summary": {
            "safe_zero_shot_targets": safe_files,
            "unsafe_zero_shot_targets": unsafe_files,
            "all_files_share_one_unqualified_capability": len(unsafe_files) == 0,
            "minimum_warranted_consequence": (
                "unsafe targets require an applicability separator or a newly "
                "acquired capability; safe targets may reuse the shared grammar"
            ),
        },
        "epistemic_boundary": {
            "warranted": [
                "exact held-out transfer measurements for each canonical pawn file under the declared identity-free grammar"
            ],
            "candidate": [
                "minimum applicability partition inferred from these counterexamples"
            ],
            "unknown": [
                "cross-material applicability",
                "general chess",
                "held-out 8-piece op1 transfer",
            ],
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "python_chess_version": getattr(chess, "__version__", "unknown"),
        },
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print("CRYSTAL_CHESS_KPVK_APPLICABILITY_V3=PASS")
    for x in transfers:
        print(
            f"heldout={x['heldout_file']} "
            f"outcome_errors={x['outcome']['errors']} "
            f"unsafe_fp={x['policy']['false_positive_unsafe']} "
            f"choice_coverage={x['policy']['safe_choice_state_coverage']:.6f} "
            f"safe={x['safe_transfer']}"
        )
    print("safe_targets=" + ",".join(safe_files))
    print("unsafe_targets=" + ",".join(unsafe_files))
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
