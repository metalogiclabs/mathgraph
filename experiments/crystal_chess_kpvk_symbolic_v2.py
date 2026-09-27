#!/usr/bin/env python3
"""Crystal Chess V2: verified symbolic recognizer/controller for KPvK.

V1 established an exact proof crystal. V2 tests whether a finite explicit rule
system can *recognize* the protected outcome and admissible proof-progress moves
without tablebase lookup at play time.

Candidate generator: deterministic CART decision trees over the generic V0
geometry bank plus local move geometry. Authority: exhaustive replay against
the independently reconstructed V1 attractor/rank and final Syzygy check.

The tree learner is discovery-only. Promotion requires zero errors on the
complete declared finite boundary.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import chess
import chess.syzygy
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    coordinate_feature_bank,
    enumerate_records,
    make_kpvk,
)
from crystal_chess_kpvk_proof_v1 import (
    V0_AUTHORITY,
    build_graph,
    solve_white_attractor,
    target_rank,
)


SCHEMA = "mathgraph.crystal-chess.kpvk-symbolic-controller.v2"
V1_AUTHORITY = (
    "metalogiclabs/mathgraph@9bf64df92686573f6a92dff271fc13014200a44d"
)


def tree_payload(clf: DecisionTreeClassifier, feature_names: list[str]) -> dict:
    t = clf.tree_
    return {
        "feature_names": feature_names,
        "children_left": t.children_left.tolist(),
        "children_right": t.children_right.tolist(),
        "feature": t.feature.tolist(),
        "threshold": [float(x) for x in t.threshold.tolist()],
        "value": t.value.tolist(),
        "classes": clf.classes_.tolist(),
    }


def tree_sha256(clf: DecisionTreeClassifier, feature_names: list[str]) -> str:
    raw = json.dumps(
        tree_payload(clf, feature_names),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def tree_stats(clf: DecisionTreeClassifier) -> dict[str, int]:
    return {
        "node_count": int(clf.tree_.node_count),
        "leaf_count": int(clf.get_n_leaves()),
        "max_depth": int(clf.get_depth()),
    }


def action_features(board: chess.Board, move: chess.Move) -> tuple[int, ...]:
    piece = board.piece_at(move.from_square)
    assert piece is not None
    dx = chess.square_file(move.to_square) - chess.square_file(move.from_square)
    dy = chess.square_rank(move.to_square) - chess.square_rank(move.from_square)
    return (
        int(piece.piece_type),
        dx,
        dy,
        int(move.promotion or 0),
        int(board.is_capture(move)),
    )


def child_is_white_win(edge, rank) -> bool:
    if edge.internal_target is not None:
        return rank[edge.internal_target] is not None
    return edge.external_white_outcome == 2


def move_is_admissible(rec, edge, parent_rank, rank) -> bool:
    """Exact V1 strategy obligation for the side to move.

    White-winning region:
      White chooses a fastest rank-decreasing witness.
      Black, being lost, chooses a maximal-delay reply (also rank r-1).
    Draw region:
      either side preserves the draw.
    """
    tr = target_rank(edge, rank)
    if parent_rank is not None:
        return tr == parent_rank - 1
    return not child_is_white_win(edge, rank)


def build_move_dataset(records, edges, rank):
    state_dim = len(records[0].features)
    rows = []
    labels = []
    state_indices = []
    move_counts = Counter()

    for i, rec in enumerate(records):
        board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
        legal = list(board.legal_moves)
        if len(legal) != len(edges[i]):
            raise AssertionError(("edge/move mismatch", i, len(legal), len(edges[i])))
        for move, edge in zip(legal, edges[i]):
            af = action_features(board, move)
            rows.append(rec.features + af)
            label = int(move_is_admissible(rec, edge, rank[i], rank))
            labels.append(label)
            state_indices.append(i)
            move_counts[label] += 1

    X = np.asarray(rows, dtype=np.int16)
    y = np.asarray(labels, dtype=np.int8)
    s = np.asarray(state_indices, dtype=np.int32)
    assert X.shape[1] == state_dim + 5
    return X, y, s, move_counts


def exact_error_counts(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, int]:
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    return {
        "false_positive_unsafe": fp,
        "false_negative_missed": fn,
        "total_errors": fp + fn,
    }


def heldout_policy_coverage(
    records,
    state_indices: np.ndarray,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    heldout_file: int,
) -> dict[str, int | float]:
    mask = np.asarray(
        [chess.square_file(records[int(i)].pawn) == heldout_file for i in state_indices],
        dtype=bool,
    )
    yt = y_true[mask]
    yp = y_pred[mask]
    si = state_indices[mask]
    errors = exact_error_counts(yt, yp)

    states_with_moves = set(int(x) for x in si.tolist())
    state_has_safe_pred = {i: False for i in states_with_moves}
    state_has_true = {i: False for i in states_with_moves}
    for idx, truth, pred in zip(si.tolist(), yt.tolist(), yp.tolist()):
        if truth:
            state_has_true[int(idx)] = True
        if truth and pred:
            state_has_safe_pred[int(idx)] = True

    required_states = [i for i, has in state_has_true.items() if has]
    covered = sum(state_has_safe_pred[i] for i in required_states)
    return {
        **errors,
        "heldout_move_rows": int(mask.sum()),
        "states_requiring_choice": len(required_states),
        "states_with_at_least_one_true_positive_choice": int(covered),
        "safe_choice_state_coverage": (
            covered / len(required_states) if required_states else 1.0
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path("crystal_chess_kpvk_symbolic_v2.json")
    )
    args = parser.parse_args()
    started = time.time()

    feature_bank = coordinate_feature_bank()
    feature_names = [name for name, _ in feature_bank]
    cache = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        records, enumeration = enumerate_records(
            tablebase, cache, [fn for _, fn in feature_bank]
        )
        if enumeration["mirror_mismatches"] or enumeration["mirror_invalid"]:
            raise AssertionError(enumeration)
        edges, graph_stats = build_graph(records, tablebase, cache)
        rank, passes = solve_white_attractor(records, edges)

        # V1 final authority check.
        outcome = np.asarray([int(r is not None) for r in rank], dtype=np.int8)
        oracle = np.asarray(
            [
                int((rec.wdl if rec.turn == chess.WHITE else -rec.wdl) == 2)
                for rec in records
            ],
            dtype=np.int8,
        )
        if not np.array_equal(outcome, oracle):
            raise AssertionError("V1/Syzygy outcome mismatch")

    X_state = np.asarray([rec.features for rec in records], dtype=np.int16)
    outcome_tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    outcome_tree.fit(X_state, outcome)
    outcome_pred = outcome_tree.predict(X_state).astype(np.int8)
    outcome_errors = int(np.sum(outcome_pred != outcome))
    if outcome_errors:
        raise AssertionError(("full outcome tree not exact", outcome_errors))

    action_feature_names = [
        "mover_piece_type",
        "move_dx",
        "move_dy",
        "promotion_piece_type",
        "is_capture",
    ]
    X_move, y_move, state_indices, move_counts = build_move_dataset(
        records, edges, rank
    )
    policy_tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    policy_tree.fit(X_move, y_move)
    policy_pred = policy_tree.predict(X_move).astype(np.int8)
    policy_errors = exact_error_counts(y_move, policy_pred)
    if policy_errors["total_errors"]:
        raise AssertionError(("full policy tree not exact", policy_errors))

    # Prospective structural holdout: rook-pawn file a is never shown to the
    # discovery tree. Any errors remain CANDIDATE evidence only and cannot
    # contaminate the exhaustive full-boundary warrant above.
    pawn_files = np.asarray(
        [chess.square_file(rec.pawn) for rec in records], dtype=np.int8
    )
    train_state = pawn_files != 0
    test_state = pawn_files == 0
    outcome_holdout_tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    outcome_holdout_tree.fit(X_state[train_state], outcome[train_state])
    holdout_outcome_pred = outcome_holdout_tree.predict(
        X_state[test_state]
    ).astype(np.int8)
    holdout_outcome_errors = int(
        np.sum(holdout_outcome_pred != outcome[test_state])
    )

    move_train_mask = np.asarray(
        [chess.square_file(records[int(i)].pawn) != 0 for i in state_indices],
        dtype=bool,
    )
    policy_holdout_tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    policy_holdout_tree.fit(X_move[move_train_mask], y_move[move_train_mask])
    holdout_policy_pred = policy_holdout_tree.predict(X_move).astype(np.int8)
    heldout_policy = heldout_policy_coverage(
        records, state_indices, y_move, holdout_policy_pred, 0
    )

    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_BOUNDED_KPVK_SYMBOLIC_CONTROLLER",
        "lineage": {
            "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
            "v0_authority": V0_AUTHORITY,
            "v1_authority": V1_AUTHORITY,
        },
        "boundary": {
            "states": len(records),
            "legal_move_rows": int(len(y_move)),
            "feature_bank": feature_names,
            "local_action_features": action_feature_names,
        },
        "outcome_recognizer": {
            **tree_stats(outcome_tree),
            "sha256": tree_sha256(outcome_tree, feature_names),
            "complete_boundary_errors": outcome_errors,
            "raw_states_per_leaf": len(records) / outcome_tree.get_n_leaves(),
        },
        "policy_recognizer": {
            **tree_stats(policy_tree),
            "sha256": tree_sha256(
                policy_tree, feature_names + action_feature_names
            ),
            **policy_errors,
            "move_label_distribution": {
                str(k): int(v) for k, v in sorted(move_counts.items())
            },
            "raw_move_rows_per_leaf": len(y_move) / policy_tree.get_n_leaves(),
            "semantics": (
                "winning region: rank-optimal move; draw region: draw-preserving move"
            ),
        },
        "heldout_rook_pawn_transfer": {
            "train_files": ["b", "c", "d"],
            "test_file": "a",
            "outcome_test_states": int(test_state.sum()),
            "outcome_errors": holdout_outcome_errors,
            "outcome_accuracy": (
                1.0 - holdout_outcome_errors / int(test_state.sum())
            ),
            "outcome_tree": tree_stats(outcome_holdout_tree),
            "policy": heldout_policy,
            "policy_tree": tree_stats(policy_holdout_tree),
            "epistemic_state": (
                "WARRANTED only if zero unsafe false positives and complete "
                "required-state choice coverage; otherwise CANDIDATE/REJECTED"
            ),
        },
        "v1_requalification": {
            "white_win_states": int(outcome.sum()),
            "draw_states": int(len(outcome) - outcome.sum()),
            "max_rank": int(max(r for r in rank if r is not None)),
            "fixed_point_passes": int(passes),
            "material_only_exit_candidate_mismatches": int(
                graph_stats["exit_oracle_mismatch_count"]
            ),
            "syzygy_mismatches": 0,
        },
        "epistemic_boundary": {
            "warranted": [
                "explicit outcome tree exactly reproduces the complete declared KPvK outcome partition",
                "explicit local move tree exactly reproduces the complete declared V1 admissible-move relation",
                "the tree learner is discovery-only; exhaustive replay is promotion authority",
            ],
            "candidate": [
                "rook-pawn holdout transfer if nonzero-error controls remain informative",
                "same explicit recognizer/controller grammar transfers across material classes",
            ],
            "unknown": [
                "general chess",
                "cross-material zero-oracle transfer",
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

    print("CRYSTAL_CHESS_KPVK_SYMBOLIC_V2=PASS")
    print(
        f"outcome_tree leaves={outcome_tree.get_n_leaves()} "
        f"depth={outcome_tree.get_depth()} errors={outcome_errors}"
    )
    print(
        f"policy_tree leaves={policy_tree.get_n_leaves()} "
        f"depth={policy_tree.get_depth()} errors={policy_errors['total_errors']}"
    )
    print(
        f"heldout_a outcome_errors={holdout_outcome_errors} "
        f"policy_unsafe_fp={heldout_policy['false_positive_unsafe']} "
        f"policy_choice_coverage={heldout_policy['safe_choice_state_coverage']:.6f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
