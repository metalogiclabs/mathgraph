#!/usr/bin/env python3
"""Crystal Chess V3: compile an exact goal-relative KPvK move certificate.

The V2 result shows full protected-future congruence is almost raw-state
identity.  ROS says that is stronger than the actual obligation.  For exact
WDL play we only need, at each nonterminal state, one legal move whose exact
child consequence equals the state's protected Syzygy WDL.

This experiment:
1. enumerates the complete canonical KPvK boundary;
2. computes every WDL-preserving legal move using Syzygy authority;
3. assigns each state a preferred optimal *relative move role*;
4. learns a symbolic decision tree over the same generic geometry bank used
   in V0 (no hand-authored opposition/key-square concepts);
5. independently replays the resulting tree against all states and accepts
   only if every emitted role has a concrete legal move with exact protected
   consequence;
6. separately trains on pawn files a-c and prospectively audits file d.

The tree is an accelerator/certificate constructor, not epistemic authority.
Syzygy remains the checker.
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
from typing import Iterable

import chess
import chess.syzygy
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    PROTECTED_INTERFACE,
    coordinate_feature_bank,
    enumerate_records,
    make_kpvk,
    probe_wdl,
)


SCHEMA = "mathgraph.crystal-chess.kpvk-goal-certificate.v3"
V2_AUTHORITY = (
    "metalogiclabs/mathgraph@bd9f5cc02d4a8f3ff4a49ade2cdb690b39cd92ef"
)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def move_role(board: chess.Board, move: chess.Move) -> str:
    piece = board.piece_at(move.from_square)
    if piece is None:
        raise AssertionError("legal move without source piece")
    ff = chess.square_file(move.from_square)
    fr = chess.square_rank(move.from_square)
    tf = chess.square_file(move.to_square)
    tr = chess.square_rank(move.to_square)
    df = tf - ff
    dr = tr - fr
    if piece.piece_type == chess.KING:
        return f"K:{df:+d},{dr:+d}"
    if piece.piece_type == chess.PAWN:
        if move.promotion:
            promo = chess.piece_symbol(move.promotion).upper()
            return f"P:{df:+d},{dr:+d}={promo}"
        return f"P:{df:+d},{dr:+d}"
    raise AssertionError(f"unexpected KPvK moving piece: {piece}")


def optimal_roles(
    board: chess.Board,
    root_wdl: int,
    tablebase: chess.syzygy.Tablebase,
    cache: dict[tuple[str, bool], int],
) -> tuple[str, ...]:
    roles: set[str] = set()
    best = -99
    scored: list[tuple[chess.Move, int]] = []
    for move in board.legal_moves:
        child = board.copy(stack=False)
        child.push(move)
        consequence = -probe_wdl(tablebase, child, cache)
        best = max(best, consequence)
        scored.append((move, consequence))
    if not scored:
        return ()
    if best != root_wdl:
        raise AssertionError(
            f"Syzygy negamax mismatch root={root_wdl} best={best} fen={board.fen()}"
        )
    for move, consequence in scored:
        if consequence == root_wdl:
            roles.add(move_role(board, move))
    if not roles:
        raise AssertionError("nonterminal state has no WDL-preserving role")
    return tuple(sorted(roles))


def choose_preferred_roles(
    role_sets: list[tuple[str, ...]],
    indices: Iterable[int],
) -> tuple[list[str], dict[str, int]]:
    indices = list(indices)
    frequencies: Counter[str] = Counter()
    for i in indices:
        frequencies.update(role_sets[i])
    ranking = {
        role: rank
        for rank, (role, _count) in enumerate(
            sorted(frequencies.items(), key=lambda kv: (-kv[1], kv[0]))
        )
    }
    chosen: list[str] = []
    for roles in role_sets:
        if not roles:
            chosen.append("<terminal>")
            continue
        chosen.append(min(roles, key=lambda r: (ranking.get(r, 10**9), r)))
    return chosen, dict(frequencies)


def encode_labels(labels: list[str], indices: list[int]) -> tuple[np.ndarray, list[str]]:
    classes = sorted({labels[i] for i in indices})
    lookup = {label: j for j, label in enumerate(classes)}
    y = np.asarray([lookup[labels[i]] for i in indices], dtype=np.int32)
    return y, classes


def verify_policy(
    clf: DecisionTreeClassifier,
    X: np.ndarray,
    indices: list[int],
    class_labels: list[str],
    role_sets: list[tuple[str, ...]],
) -> dict[str, object]:
    if not indices:
        return {
            "states": 0,
            "valid": 0,
            "invalid": 0,
            "valid_ratio": 1.0,
            "invalid_examples": [],
        }
    pred = clf.predict(X[indices])
    invalid: list[dict[str, object]] = []
    valid = 0
    for pos, state_index in enumerate(indices):
        label_id = int(pred[pos])
        role = class_labels[label_id]
        allowed = role_sets[state_index]
        if role in allowed:
            valid += 1
        elif len(invalid) < 20:
            invalid.append(
                {
                    "state_index": state_index,
                    "predicted_role": role,
                    "optimal_roles": list(allowed),
                }
            )
    return {
        "states": len(indices),
        "valid": valid,
        "invalid": len(indices) - valid,
        "valid_ratio": valid / len(indices),
        "invalid_examples": invalid,
    }


def tree_digest(clf: DecisionTreeClassifier) -> str:
    tree = clf.tree_
    payload = {
        "children_left": tree.children_left.tolist(),
        "children_right": tree.children_right.tolist(),
        "feature": tree.feature.tolist(),
        "threshold": [float(x) for x in tree.threshold.tolist()],
        "value": tree.value.tolist(),
        "classes": clf.classes_.tolist(),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def tree_summary(clf: DecisionTreeClassifier) -> dict[str, object]:
    tree = clf.tree_
    used = Counter(int(x) for x in tree.feature if int(x) >= 0)
    return {
        "nodes": int(tree.node_count),
        "leaves": int(tree.n_leaves),
        "max_depth": int(tree.max_depth),
        "used_feature_counts": {str(k): v for k, v in sorted(used.items())},
        "sha256": tree_digest(clf),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_chess_kpvk_goal_certificate_v3.json"),
    )
    parser.add_argument("--random-state", type=int, default=0)
    args = parser.parse_args()
    started = time.time()

    tb_files = sorted(args.tablebase_dir.glob("*.rtbw"))
    if not tb_files:
        raise SystemExit(f"no .rtbw files found in {args.tablebase_dir}")
    manifest = [
        {
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in tb_files
    ]

    bank = coordinate_feature_bank()
    feature_names = [name for name, _fn in bank]
    feature_fns = [fn for _name, fn in bank]
    cache: dict[tuple[str, bool], int] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        records, enumeration = enumerate_records(tablebase, cache, feature_fns)
        assert records
        assert enumeration["mirror_invalid"] == 0
        assert enumeration["mirror_mismatches"] == 0

        role_sets: list[tuple[str, ...]] = []
        nonterminal: list[int] = []
        terminal: list[int] = []
        for i, rec in enumerate(records):
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
            roles = optimal_roles(board, rec.wdl, tablebase, cache)
            role_sets.append(roles)
            if roles:
                nonterminal.append(i)
            else:
                terminal.append(i)

    X = np.asarray([rec.features for rec in records], dtype=np.int16)

    # Prefer globally reusable optimal roles, then fit the smallest ordinary
    # CART representation that exactly reproduces those choices.
    labels, role_frequency = choose_preferred_roles(role_sets, nonterminal)
    y, class_labels = encode_labels(labels, nonterminal)
    clf = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=args.random_state,
    )
    clf.fit(X[nonterminal], y)
    full_audit = verify_policy(
        clf, X, nonterminal, class_labels, role_sets
    )
    if full_audit["invalid"] != 0:
        raise AssertionError(full_audit["invalid_examples"])

    # Prospective transfer: acquire policy only on pawn files a-c, then audit
    # the untouched d-file positions. The learner is not allowed to see d-file
    # labels when constructing this tree.
    train_abc = [
        i for i in nonterminal if chess.square_file(records[i].pawn) <= 2
    ]
    heldout_d = [
        i for i in nonterminal if chess.square_file(records[i].pawn) == 3
    ]
    transfer_labels, transfer_frequency = choose_preferred_roles(
        role_sets, train_abc
    )
    y_abc, transfer_classes = encode_labels(transfer_labels, train_abc)
    transfer_tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=args.random_state,
    )
    transfer_tree.fit(X[train_abc], y_abc)
    train_audit = verify_policy(
        transfer_tree, X, train_abc, transfer_classes, role_sets
    )
    heldout_audit = verify_policy(
        transfer_tree, X, heldout_d, transfer_classes, role_sets
    )
    if train_audit["invalid"] != 0:
        raise AssertionError(train_audit["invalid_examples"])

    full_summary = tree_summary(clf)
    transfer_summary = tree_summary(transfer_tree)
    full_summary["used_features"] = [
        feature_names[int(k)]
        for k in sorted(map(int, full_summary["used_feature_counts"].keys()))
    ]
    transfer_summary["used_features"] = [
        feature_names[int(k)]
        for k in sorted(map(int, transfer_summary["used_feature_counts"].keys()))
    ]

    role_count_hist = Counter(len(x) for x in role_sets if x)
    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_BOUNDED_KPVK_GOAL_CERTIFICATE_COMPILER",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v2_authority": V2_AUTHORITY,
        "protected_interface": PROTECTED_INTERFACE,
        "method": {
            "obligation": (
                "emit one concrete move role whose child Syzygy consequence "
                "equals the root protected WDL"
            ),
            "representation": "generic geometry -> symbolic CART policy",
            "authority": "Syzygy checker; learned tree is only a candidate accelerator",
            "role_choice": "highest-frequency available optimal role",
        },
        "authority": {
            "kind": "Syzygy WDL",
            "python_chess_version": getattr(chess, "__version__", "unknown"),
            "tablebase_files": manifest,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "enumeration": enumeration,
        "coverage": {
            "states": len(records),
            "nonterminal_states": len(nonterminal),
            "terminal_states": len(terminal),
            "distinct_move_roles": len(
                {role for roles in role_sets for role in roles}
            ),
            "optimal_role_count_histogram": {
                str(k): v for k, v in sorted(role_count_hist.items())
            },
        },
        "full_exact_policy": {
            "role_frequency": role_frequency,
            "class_labels": class_labels,
            "tree": full_summary,
            "audit": full_audit,
            "states_per_leaf": len(nonterminal) / int(full_summary["leaves"]),
            "compression_vs_state_table": (
                len(nonterminal) / int(full_summary["leaves"])
            ),
        },
        "prospective_file_d_transfer": {
            "train_files": ["a", "b", "c"],
            "heldout_file": "d",
            "train_states": len(train_abc),
            "heldout_states": len(heldout_d),
            "train_role_frequency": transfer_frequency,
            "class_labels": transfer_classes,
            "tree": transfer_summary,
            "train_audit": train_audit,
            "heldout_audit": heldout_audit,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                (
                    "the full learned symbolic policy emits an exact WDL-preserving "
                    "move role on every nonterminal state in the complete declared "
                    "canonical KPvK boundary"
                ),
                (
                    "horizontal reflection from V0 extends the canonical a-d policy "
                    "to e-h under the already-qualified symmetry boundary"
                ),
            ],
            "prospective_only": [
                (
                    "file-d accuracy of the policy trained without file-d labels; "
                    "this is evidence of within-material transfer, not richer-material transfer"
                )
            ],
            "unknown": [
                "transfer to richer material classes",
                "general chess solution",
            ],
        },
        "cache": {
            "unique_wdl_positions_probed_or_certified": len(cache)
        },
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("CRYSTAL_CHESS_GOAL_CERTIFICATE_V3=PASS")
    print(
        f"states={len(records)} nonterminal={len(nonterminal)} "
        f"roles={result['coverage']['distinct_move_roles']}"
    )
    print(
        f"exact_tree leaves={full_summary['leaves']} "
        f"depth={full_summary['max_depth']} "
        f"compression={result['full_exact_policy']['compression_vs_state_table']:.3f}x"
    )
    print(
        f"heldout_d valid={heldout_audit['valid']}/{heldout_audit['states']} "
        f"ratio={heldout_audit['valid_ratio']:.6f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
