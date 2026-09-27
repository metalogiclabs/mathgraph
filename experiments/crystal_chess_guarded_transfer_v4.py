#!/usr/bin/env python3
"""Crystal Chess V4: fail-closed guarded zero-shot transfer inside KPvK.

V3 forced a policy decision everywhere and achieved 93.684% on untouched
file-d states. ROS capabilities are guarded: act only where qualification
supports the continuation; otherwise emit UNKNOWN.

This experiment learns three independent exact policies on file pairs drawn
from a,b,c. Each policy is qualified on the third unseen observed file at the
*leaf* level. A leaf becomes live only when:
  * validation support >= MIN_VALIDATION_SUPPORT, and
  * every validation state entering the leaf confirms the predicted role is
    an exact Syzygy-optimal role.

The final file-d test is untouched by training and guard qualification.
Crystal acts only when all three independently qualified capabilities fire and
agree on the same relative move role. Otherwise it returns UNKNOWN.

The claim is therefore precision/coverage, not forced accuracy.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
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
    PROTECTED_INTERFACE,
    coordinate_feature_bank,
    enumerate_records,
    make_kpvk,
)
from crystal_chess_goal_certificate_v3 import (
    V2_AUTHORITY,
    choose_preferred_roles,
    encode_labels,
    file_sha256,
    optimal_roles,
    tree_summary,
)


SCHEMA = "mathgraph.crystal-chess.kpvk-guarded-transfer.v4"
V3_AUTHORITY = (
    "metalogiclabs/mathgraph@73be9f4159816bf18a3ca70a1fb3eeb9793536a6"
)


@dataclass
class FoldCapability:
    name: str
    train_files: tuple[int, ...]
    validation_file: int
    model: DecisionTreeClassifier
    class_labels: list[str]
    trusted_leaves: set[int]
    validation_leaf_support: dict[int, int]
    validation_states: int
    validation_covered: int
    validation_errors: int


def fit_fold(
    name: str,
    train_files: tuple[int, ...],
    validation_file: int,
    records,
    X: np.ndarray,
    role_sets: list[tuple[str, ...]],
    nonterminal: list[int],
    min_support: int,
) -> FoldCapability:
    train = [
        i for i in nonterminal
        if chess.square_file(records[i].pawn) in train_files
    ]
    validation = [
        i for i in nonterminal
        if chess.square_file(records[i].pawn) == validation_file
    ]
    labels, _freq = choose_preferred_roles(role_sets, train)
    y, classes = encode_labels(labels, train)
    clf = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    clf.fit(X[train], y)

    pred = clf.predict(X[validation])
    leaves = clf.apply(X[validation])
    by_leaf: dict[int, list[bool]] = defaultdict(list)
    predicted_role_by_leaf: dict[int, str] = {}
    for pos, state_index in enumerate(validation):
        leaf = int(leaves[pos])
        role = classes[int(pred[pos])]
        predicted_role_by_leaf.setdefault(leaf, role)
        by_leaf[leaf].append(role in role_sets[state_index])

    trusted: set[int] = set()
    support: dict[int, int] = {}
    for leaf, verdicts in by_leaf.items():
        support[leaf] = len(verdicts)
        if len(verdicts) >= min_support and all(verdicts):
            trusted.add(leaf)

    covered = 0
    errors = 0
    for pos, state_index in enumerate(validation):
        leaf = int(leaves[pos])
        if leaf not in trusted:
            continue
        covered += 1
        role = classes[int(pred[pos])]
        if role not in role_sets[state_index]:
            errors += 1
    assert errors == 0

    return FoldCapability(
        name=name,
        train_files=train_files,
        validation_file=validation_file,
        model=clf,
        class_labels=classes,
        trusted_leaves=trusted,
        validation_leaf_support=support,
        validation_states=len(validation),
        validation_covered=covered,
        validation_errors=errors,
    )


def capability_output(
    cap: FoldCapability,
    row: np.ndarray,
) -> tuple[str | None, int]:
    leaf = int(cap.model.apply(row.reshape(1, -1))[0])
    if leaf not in cap.trusted_leaves:
        return None, leaf
    label = int(cap.model.predict(row.reshape(1, -1))[0])
    return cap.class_labels[label], leaf


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-validation-support", type=int, default=4)
    args = parser.parse_args()
    started = time.time()

    bank = coordinate_feature_bank()
    feature_names = [name for name, _ in bank]
    feature_fns = [fn for _, fn in bank]

    tb_files = sorted(args.tablebase_dir.glob("*.rtbw"))
    manifest = [
        {"name": p.name, "size": p.stat().st_size, "sha256": file_sha256(p)}
        for p in tb_files
    ]
    cache: dict[tuple[str, bool], int] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        records, enumeration = enumerate_records(tablebase, cache, feature_fns)
        assert enumeration["mirror_mismatches"] == 0
        role_sets: list[tuple[str, ...]] = []
        nonterminal: list[int] = []
        for i, rec in enumerate(records):
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
            roles = optimal_roles(board, rec.wdl, tablebase, cache)
            role_sets.append(roles)
            if roles:
                nonterminal.append(i)

    X = np.asarray([rec.features for rec in records], dtype=np.int16)

    specs = [
        ("ab_to_c", (0, 1), 2),
        ("ac_to_b", (0, 2), 1),
        ("bc_to_a", (1, 2), 0),
    ]
    caps = [
        fit_fold(
            name,
            train_files,
            validation_file,
            records,
            X,
            role_sets,
            nonterminal,
            args.min_validation_support,
        )
        for name, train_files, validation_file in specs
    ]

    heldout_d = [
        i for i in nonterminal if chess.square_file(records[i].pawn) == 3
    ]

    acted = 0
    correct = 0
    wrong = 0
    unknown = 0
    disagreements = 0
    inactive = 0
    predicted_roles: Counter[str] = Counter()
    wrong_examples: list[dict[str, object]] = []
    unknown_examples: list[dict[str, object]] = []

    for i in heldout_d:
        outputs = [capability_output(cap, X[i]) for cap in caps]
        live = [role for role, _leaf in outputs if role is not None]
        if len(live) != len(caps):
            unknown += 1
            inactive += 1
            if len(unknown_examples) < 20:
                unknown_examples.append(
                    {
                        "state_index": i,
                        "reason": "capability_not_live",
                        "outputs": [role for role, _leaf in outputs],
                        "optimal_roles": list(role_sets[i]),
                    }
                )
            continue
        if len(set(live)) != 1:
            unknown += 1
            disagreements += 1
            if len(unknown_examples) < 20:
                unknown_examples.append(
                    {
                        "state_index": i,
                        "reason": "qualified_capabilities_disagree",
                        "outputs": live,
                        "optimal_roles": list(role_sets[i]),
                    }
                )
            continue
        role = live[0]
        acted += 1
        predicted_roles[role] += 1
        if role in role_sets[i]:
            correct += 1
        else:
            wrong += 1
            if len(wrong_examples) < 20:
                wrong_examples.append(
                    {
                        "state_index": i,
                        "predicted_role": role,
                        "optimal_roles": list(role_sets[i]),
                    }
                )

    fold_summaries = []
    for cap in caps:
        ts = tree_summary(cap.model)
        ts["used_features"] = [
            feature_names[int(k)]
            for k in sorted(map(int, ts["used_feature_counts"].keys()))
        ]
        fold_summaries.append(
            {
                "name": cap.name,
                "train_files": [
                    chess.FILE_NAMES[x] for x in cap.train_files
                ],
                "validation_file": chess.FILE_NAMES[cap.validation_file],
                "validation_states": cap.validation_states,
                "validation_covered": cap.validation_covered,
                "validation_errors": cap.validation_errors,
                "validation_coverage_ratio": (
                    cap.validation_covered / cap.validation_states
                    if cap.validation_states else 0
                ),
                "trusted_leaves": len(cap.trusted_leaves),
                "tree": ts,
            }
        )

    result = {
        "schema": SCHEMA,
        "status": (
            "WARRANTED_PROSPECTIVE_GUARDED_TRANSFER"
            if wrong == 0 and acted > 0
            else "EXACT_RESIDUAL_GUARDED_TRANSFER"
        ),
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v2_authority": V2_AUTHORITY,
        "v3_authority": V3_AUTHORITY,
        "protected_interface": PROTECTED_INTERFACE,
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
        "method": {
            "capability_shape": "guarded exact move-role constructor",
            "qualification": (
                "train on two observed pawn files, qualify each tree leaf on "
                "the third unseen observed pawn file"
            ),
            "final_action_rule": (
                "act only when all three independently qualified capabilities "
                "are live and agree; otherwise UNKNOWN"
            ),
            "min_validation_support": args.min_validation_support,
        },
        "folds": fold_summaries,
        "prospective_d": {
            "states": len(heldout_d),
            "acted": acted,
            "correct": correct,
            "wrong": wrong,
            "unknown": unknown,
            "coverage_ratio": acted / len(heldout_d),
            "precision": correct / acted if acted else 0.0,
            "inactive": inactive,
            "disagreements": disagreements,
            "predicted_roles": dict(sorted(predicted_roles.items())),
            "wrong_examples": wrong_examples,
            "unknown_examples": unknown_examples,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                (
                    "without using any file-d labels in training or guard "
                    "qualification, every file-d state on which Crystal acts "
                    "receives an exact Syzygy-optimal move role"
                )
            ],
            "unknown": [
                "states where the guard abstains",
                "transfer to richer material",
                "general chess solution",
            ],
        },
        "cache": {"unique_wdl_positions": len(cache)},
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print("CRYSTAL_CHESS_GUARDED_TRANSFER_V4=PASS")
    print(
        f"heldout_d acted={acted}/{len(heldout_d)} "
        f"coverage={acted/len(heldout_d):.6f} "
        f"precision={correct/acted if acted else 0.0:.6f} wrong={wrong}"
    )
    for fold in fold_summaries:
        print(
            f"{fold['name']} validation="
            f"{fold['validation_covered']}/{fold['validation_states']} "
            f"trusted_leaves={fold['trusted_leaves']}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
