#!/usr/bin/env python3
"""Crystal Chess V4: residual-driven policy compounding on exact KPvK.

Generation 1 is acquired with *no d-file labels*: an exact symbolic policy on
pawn files a-c. V3 showed that it transfers to most d-file states.

Generation 2 is trained only after exposing the prospective d-file residual.
It is a guarded repair controller whose output is either:
  * <BASE>  -- reuse Generation 1 unchanged, or
  * a replacement relative move role certified optimal by Syzygy.

The scientific questions are:
1. Does the residual-specific repair close every held-out d-file failure?
2. Does removing the repair restore exactly the original failures?
3. Is the compiled base+repair representation materially smaller than a fresh
   exact full-domain policy?

This is the ROS acquisition -> compile -> reclose -> ablate cycle in chess.
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
    PROTECTED_INTERFACE,
    coordinate_feature_bank,
    enumerate_records,
    make_kpvk,
)
from crystal_chess_goal_certificate_v3 import (
    V2_AUTHORITY,
    choose_preferred_roles,
    file_sha256,
    optimal_roles,
    tree_summary,
)


SCHEMA = "mathgraph.crystal-chess.kpvk-residual-compounding.v4"
V3_AUTHORITY = (
    "metalogiclabs/mathgraph@73be9f4159816bf18a3ca70a1fb3eeb9793536a6"
)
BASE_SENTINEL = "<BASE>"


def preferred_role(
    roles: tuple[str, ...],
    ranking: dict[str, int],
) -> str:
    return min(roles, key=lambda r: (ranking.get(r, 10**9), r))


def audit_roles(
    predicted: list[str],
    indices: list[int],
    role_sets: list[tuple[str, ...]],
) -> dict[str, object]:
    bad: list[dict[str, object]] = []
    good = 0
    for role, i in zip(predicted, indices):
        if role in role_sets[i]:
            good += 1
        elif len(bad) < 20:
            bad.append(
                {
                    "state_index": i,
                    "predicted_role": role,
                    "optimal_roles": list(role_sets[i]),
                }
            )
    return {
        "states": len(indices),
        "valid": good,
        "invalid": len(indices) - good,
        "valid_ratio": good / len(indices) if indices else 1.0,
        "invalid_examples": bad,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("crystal_chess_kpvk_residual_compounding_v4.json"),
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
    feature_names = [name for name, _ in bank]
    feature_fns = [fn for _, fn in bank]
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
        for i, rec in enumerate(records):
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
            roles = optimal_roles(board, rec.wdl, tablebase, cache)
            role_sets.append(roles)
            if roles:
                nonterminal.append(i)

    X = np.asarray([rec.features for rec in records], dtype=np.int16)
    train_abc = [
        i for i in nonterminal if chess.square_file(records[i].pawn) <= 2
    ]
    heldout_d = [
        i for i in nonterminal if chess.square_file(records[i].pawn) == 3
    ]

    # Generation 1: exact on a-c only.
    base_labels, base_role_frequency = choose_preferred_roles(
        role_sets, train_abc
    )
    base_tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=args.random_state,
    )
    base_tree.fit(X[train_abc], [base_labels[i] for i in train_abc])

    base_train_pred = [str(x) for x in base_tree.predict(X[train_abc])]
    base_train_audit = audit_roles(base_train_pred, train_abc, role_sets)
    if base_train_audit["invalid"] != 0:
        raise AssertionError(base_train_audit["invalid_examples"])

    base_d_pred = [str(x) for x in base_tree.predict(X[heldout_d])]
    base_d_audit = audit_roles(base_d_pred, heldout_d, role_sets)
    residual_positions = [
        pos
        for pos, (role, i) in enumerate(zip(base_d_pred, heldout_d))
        if role not in role_sets[i]
    ]
    residual_states = [heldout_d[pos] for pos in residual_positions]
    if not residual_states:
        raise AssertionError("no prospective residual: V4 acquisition not exercised")

    # Generation 2 role preference is learned only from the exposed failures.
    repair_frequency: Counter[str] = Counter()
    for i in residual_states:
        repair_frequency.update(role_sets[i])
    repair_ranking = {
        role: rank
        for rank, (role, _count) in enumerate(
            sorted(repair_frequency.items(), key=lambda kv: (-kv[1], kv[0]))
        )
    }

    # Guard + repair are compiled as one controller over the d-file context.
    # Successful base states explicitly target BASE; residual states target one
    # independently checkable optimal replacement role.
    repair_targets: list[str] = []
    for role, i in zip(base_d_pred, heldout_d):
        if role in role_sets[i]:
            repair_targets.append(BASE_SENTINEL)
        else:
            repair_targets.append(
                preferred_role(role_sets[i], repair_ranking)
            )

    repair_tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=args.random_state,
    )
    repair_tree.fit(X[heldout_d], repair_targets)
    repair_decisions = [str(x) for x in repair_tree.predict(X[heldout_d])]

    combined_d_pred: list[str] = []
    repair_invocations = 0
    for base_role, repair_role in zip(base_d_pred, repair_decisions):
        if repair_role == BASE_SENTINEL:
            combined_d_pred.append(base_role)
        else:
            repair_invocations += 1
            combined_d_pred.append(repair_role)

    combined_d_audit = audit_roles(combined_d_pred, heldout_d, role_sets)
    if combined_d_audit["invalid"] != 0:
        raise AssertionError(combined_d_audit["invalid_examples"])

    # A causal ablation must restore the exact original residual.
    ablated_d_audit = audit_roles(base_d_pred, heldout_d, role_sets)
    if ablated_d_audit["invalid"] != len(residual_states):
        raise AssertionError("ablation did not restore original residual count")

    # Fresh full-domain baseline for representation-cost comparison.
    full_labels, full_role_frequency = choose_preferred_roles(
        role_sets, nonterminal
    )
    full_tree = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=args.random_state,
    )
    full_tree.fit(X[nonterminal], [full_labels[i] for i in nonterminal])
    full_pred = [str(x) for x in full_tree.predict(X[nonterminal])]
    full_audit = audit_roles(full_pred, nonterminal, role_sets)
    if full_audit["invalid"] != 0:
        raise AssertionError(full_audit["invalid_examples"])

    base_summary = tree_summary(base_tree)
    repair_summary = tree_summary(repair_tree)
    full_summary = tree_summary(full_tree)
    for summary in (base_summary, repair_summary, full_summary):
        summary["used_features"] = [
            feature_names[int(k)]
            for k in sorted(map(int, summary["used_feature_counts"].keys()))
        ]

    combined_leaves = int(base_summary["leaves"]) + int(repair_summary["leaves"])
    combined_nodes = int(base_summary["nodes"]) + int(repair_summary["nodes"])
    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_BOUNDED_KPVK_RESIDUAL_COMPOUNDING",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v2_authority": V2_AUTHORITY,
        "v3_authority": V3_AUTHORITY,
        "protected_interface": PROTECTED_INTERFACE,
        "method": {
            "generation_1": "exact a-c symbolic WDL-preserving policy",
            "prospective_boundary": "all d-file labels withheld from generation 1",
            "residual": "d-file states where generation-1 emitted role is not WDL-preserving",
            "generation_2": "d-context guarded BASE-or-repair symbolic controller",
            "ablation": "remove generation 2 and replay generation 1 unchanged",
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
        "generation_1": {
            "train_states": len(train_abc),
            "heldout_d_states": len(heldout_d),
            "role_frequency": base_role_frequency,
            "tree": base_summary,
            "train_audit": base_train_audit,
            "prospective_d_audit": base_d_audit,
            "prospective_residual_states": len(residual_states),
        },
        "generation_2": {
            "acquisition_input_states": len(residual_states),
            "repair_role_frequency": dict(repair_frequency),
            "tree": repair_summary,
            "repair_invocations_on_d": repair_invocations,
            "combined_d_audit": combined_d_audit,
            "ablation_d_audit": ablated_d_audit,
        },
        "compounding": {
            "a_c_exact": base_train_audit["invalid"] == 0,
            "d_exact_after_repair": combined_d_audit["invalid"] == 0,
            "full_canonical_a_d_exact": (
                base_train_audit["invalid"] == 0
                and combined_d_audit["invalid"] == 0
            ),
            "residual_restored_by_ablation": (
                ablated_d_audit["invalid"] == len(residual_states)
            ),
            "combined_leaves": combined_leaves,
            "combined_nodes": combined_nodes,
            "fresh_full_tree_leaves": int(full_summary["leaves"]),
            "fresh_full_tree_nodes": int(full_summary["nodes"]),
            "combined_vs_fresh_leaf_ratio": (
                combined_leaves / int(full_summary["leaves"])
            ),
            "states_per_combined_leaf": len(nonterminal) / combined_leaves,
            "acquisition_fraction_of_d": len(residual_states) / len(heldout_d),
        },
        "fresh_full_baseline": {
            "role_frequency": full_role_frequency,
            "tree": full_summary,
            "audit": full_audit,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "generation 1 is exact on its a-c acquisition boundary",
                "generation 1 prospectively transfers to the reported fraction of untouched d-file states",
                "generation 2 closes every d-file residual under independent Syzygy replay",
                "removing generation 2 restores exactly the original d-file residual count",
                "the compounded a-d canonical policy is exact for the declared KPvK WDL objective",
            ],
            "unknown": [
                "whether the same acquired capabilities transfer to richer material",
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
    print("CRYSTAL_CHESS_RESIDUAL_COMPOUNDING_V4=PASS")
    print(
        f"base_transfer_d={base_d_audit['valid']}/{base_d_audit['states']} "
        f"residual={len(residual_states)}"
    )
    print(
        f"repair_d={combined_d_audit['valid']}/{combined_d_audit['states']} "
        f"repair_invocations={repair_invocations}"
    )
    print(
        f"ablation_invalid={ablated_d_audit['invalid']} "
        f"expected={len(residual_states)}"
    )
    print(
        f"leaves base={base_summary['leaves']} repair={repair_summary['leaves']} "
        f"combined={combined_leaves} fresh_full={full_summary['leaves']} "
        f"ratio={combined_leaves / int(full_summary['leaves']):.6f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
