#!/usr/bin/env python3
"""Crystal Chess V6: acquire only the KPPvK transfer residual, then hold out again.

Generation 0 is the frozen exact KPvK goal-certificate capability.
V5 prospectively transferred it to 48,724 / 49,999 nonterminal KPPvK states
using either pawn as the single-pawn anchor, leaving exactly 1,275 failures.

V6 uses the original V5 slice (seed 20260928) as an acquisition environment:
* BASE-labelled states keep the frozen transported capability;
* only residual states contribute new replacement move-role targets;
* a symbolic BASE-or-repair controller learns the applicability guard.

The combined controller is then frozen and evaluated on an independent 50,000
state KPPvK slice (seed 20260929).  No labels from that second slice enter
acquisition.
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
from typing import Any

import chess
import chess.syzygy
import numpy as np
from sklearn.tree import DecisionTreeClassifier

from crystal_chess_kpvk_v0 import (
    coordinate_feature_bank,
    enumerate_records,
    make_kpvk,
    probe_wdl,
)
from crystal_chess_goal_certificate_v3 import (
    choose_preferred_roles,
    move_role,
    optimal_roles,
    tree_summary,
)
from crystal_chess_richer_transfer_v5 import (
    canonical_feature_row,
    exact_optimal_moves,
    make_kppvk,
    reflect_role,
    role_is_optimal_for_anchor,
    sample_kppvk,
)


SCHEMA = "mathgraph.crystal-chess.kppvk-residual-compounding.v6"
V5_AUTHORITY = (
    "metalogiclabs/mathgraph@0b8da1aee8ffecfb351c0211dc8513631fd106cd"
)
BASE = "<BASE>"


def cheb(a: int, b: int) -> int:
    return max(
        abs(chess.square_file(a) - chess.square_file(b)),
        abs(chess.square_rank(a) - chess.square_rank(b)),
    )


def edge_distance(square: int) -> int:
    f = chess.square_file(square)
    r = chess.square_rank(square)
    return min(f, 7 - f, r, 7 - r)


def frozen_kpvk_policy(tablebase, cache, feature_fns):
    records, _ = enumerate_records(tablebase, cache, feature_fns)
    role_sets: list[tuple[str, ...]] = []
    nonterminal: list[int] = []
    for i, rec in enumerate(records):
        board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
        roles = optimal_roles(board, rec.wdl, tablebase, cache)
        role_sets.append(roles)
        if roles:
            nonterminal.append(i)
    labels, role_frequency = choose_preferred_roles(role_sets, nonterminal)
    X = np.asarray([rec.features for rec in records], dtype=np.int16)
    policy = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    policy.fit(X[nonterminal], [labels[i] for i in nonterminal])
    return policy, role_frequency, tree_summary(policy)


def base_predictions(sample, policy, feature_fns):
    rows = []
    reflected = []
    for wk, bk, p1, p2, turn in sample:
        for anchor in (p1, p2):
            row, flag = canonical_feature_row(
                wk, bk, anchor, turn, feature_fns
            )
            rows.append(row)
            reflected.append(flag)
    raw = [str(x) for x in policy.predict(np.asarray(rows, dtype=np.int16))]
    roles = [
        reflect_role(role) if flag else role
        for role, flag in zip(raw, reflected)
    ]
    return roles


def repair_label_for_move(
    board: chess.Board,
    move: chess.Move,
    p1: int,
    p2: int,
) -> str:
    role = move_role(board, move)
    piece = board.piece_at(move.from_square)
    if piece is None:
        raise AssertionError("optimal move lacks mover")
    if piece.piece_type == chess.KING:
        return "K|" + role
    if piece.piece_type == chess.PAWN:
        if move.from_square == p1:
            return "A0|" + role
        if move.from_square == p2:
            return "A1|" + role
        raise AssertionError("optimal pawn move not from an anchor")
    raise AssertionError(f"unexpected KPPvK mover: {piece}")


def repair_label_is_optimal(
    label: str,
    board: chess.Board,
    p1: int,
    p2: int,
    optimal: list[chess.Move],
) -> bool:
    if label == BASE:
        raise ValueError("BASE is handled separately")
    prefix, role = label.split("|", 1)
    for move in optimal:
        if move_role(board, move) != role:
            continue
        piece = board.piece_at(move.from_square)
        if piece is None:
            continue
        if prefix == "K" and piece.piece_type == chess.KING:
            return True
        if prefix == "A0" and move.from_square == p1:
            return True
        if prefix == "A1" and move.from_square == p2:
            return True
    return False


def state_feature_vector(
    state: tuple[int, int, int, int, bool],
    feature_fns,
    base_roles: tuple[str, str],
    role_ids: dict[str, int],
) -> tuple[int, ...]:
    wk, bk, p1, p2, turn = state
    r1, f1 = canonical_feature_row(wk, bk, p1, turn, feature_fns)
    r2, f2 = canonical_feature_row(wk, bk, p2, turn, feature_fns)

    # Relational pair features, plus raw finite coordinates as a last-resort
    # separator. The tree is free to ignore them; the held-out slice tells us
    # whether any acquired distinction transfers.
    extras = (
        role_ids[base_roles[0]],
        role_ids[base_roles[1]],
        int(f1),
        int(f2),
        abs(chess.square_file(p1) - chess.square_file(p2)),
        abs(chess.square_rank(p1) - chess.square_rank(p2)),
        cheb(p1, p2),
        int(chess.square_file(p1) == chess.square_file(p2)),
        int(chess.square_rank(p1) == chess.square_rank(p2)),
        edge_distance(p1),
        edge_distance(p2),
        chess.square_file(wk),
        chess.square_rank(wk),
        chess.square_file(bk),
        chess.square_rank(bk),
        chess.square_file(p1),
        chess.square_rank(p1),
        chess.square_file(p2),
        chess.square_rank(p2),
        int(turn),
    )
    return tuple(int(x) for x in r1 + r2 + extras)


def feature_names(base_names: list[str]) -> list[str]:
    names = [f"a0:{n}" for n in base_names] + [f"a1:{n}" for n in base_names]
    names += [
        "base_role_0",
        "base_role_1",
        "anchor0_reflected",
        "anchor1_reflected",
        "pawn_file_gap",
        "pawn_rank_gap",
        "pawn_cheb",
        "pawns_same_file",
        "pawns_same_rank",
        "pawn0_edge",
        "pawn1_edge",
        "wk_file_raw",
        "wk_rank_raw",
        "bk_file_raw",
        "bk_rank_raw",
        "pawn0_file_raw",
        "pawn0_rank_raw",
        "pawn1_file_raw",
        "pawn1_rank_raw",
        "turn_raw",
    ]
    return names


def exact_dataset(
    sample,
    tablebase,
    cache,
    policy,
    feature_fns,
    base_names,
    *,
    collect_targets: bool,
    repair_ranking: dict[str, int] | None = None,
):
    predicted = base_predictions(sample, policy, feature_fns)
    all_roles = sorted(set(predicted))
    role_ids = {role: i for i, role in enumerate(all_roles)}

    rows = []
    base_success = []
    available_repairs: list[tuple[str, ...]] = []
    roots = []
    terminals = 0

    # First pass establishes exact optimal sets.
    for i, state in enumerate(sample):
        wk, bk, p1, p2, turn = state
        board = make_kppvk(wk, bk, p1, p2, turn)
        root_wdl = probe_wdl(tablebase, board, cache)
        optimal = exact_optimal_moves(board, root_wdl, tablebase, cache)
        if not optimal:
            terminals += 1
            continue

        role_pair = (predicted[2 * i], predicted[2 * i + 1])
        base_ok = (
            role_is_optimal_for_anchor(role_pair[0], p1, optimal, board)
            or role_is_optimal_for_anchor(role_pair[1], p2, optimal, board)
        )
        labels = sorted(
            {
                repair_label_for_move(board, move, p1, p2)
                for move in optimal
            }
        )
        rows.append(
            state_feature_vector(
                state, feature_fns, role_pair, role_ids
            )
        )
        base_success.append(base_ok)
        available_repairs.append(tuple(labels))
        roots.append(
            {
                "state": state,
                "fen": board.fen(),
                "root_wdl": root_wdl,
                "optimal": optimal,
                "base_roles": role_pair,
                "p1": p1,
                "p2": p2,
            }
        )

    targets = None
    ranking = repair_ranking
    if collect_targets:
        freq = Counter()
        for ok, labels in zip(base_success, available_repairs):
            if not ok:
                freq.update(labels)
        ranking = {
            label: rank
            for rank, (label, _count) in enumerate(
                sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
            )
        }
        targets = []
        for ok, labels in zip(base_success, available_repairs):
            if ok:
                targets.append(BASE)
            else:
                targets.append(
                    min(labels, key=lambda x: (ranking.get(x, 10**9), x))
                )

    return {
        "X": np.asarray(rows, dtype=np.int16),
        "base_success": base_success,
        "available_repairs": available_repairs,
        "roots": roots,
        "targets": targets,
        "repair_ranking": ranking,
        "terminals": terminals,
        "base_role_ids": role_ids,
        "feature_names": feature_names(base_names),
    }


def evaluate_controller(dataset, controller) -> dict[str, object]:
    predictions = [str(x) for x in controller.predict(dataset["X"])]
    valid = 0
    base_valid = sum(dataset["base_success"])
    repair_invocations = 0
    repair_success = 0
    unsafe_override = 0
    residual_examples = []

    for pred, base_ok, root in zip(
        predictions, dataset["base_success"], dataset["roots"]
    ):
        if pred == BASE:
            ok = base_ok
        else:
            repair_invocations += 1
            board = chess.Board(root["fen"])
            ok = repair_label_is_optimal(
                pred,
                board,
                int(root["p1"]),
                int(root["p2"]),
                root["optimal"],
            )
            repair_success += int(ok)
            if base_ok and not ok:
                unsafe_override += 1
        valid += int(ok)
        if not ok and len(residual_examples) < 30:
            residual_examples.append(
                {
                    "fen": root["fen"],
                    "root_wdl": root["root_wdl"],
                    "base_roles": list(root["base_roles"]),
                    "controller": pred,
                    "optimal_roles": [
                        move_role(chess.Board(root["fen"]), m)
                        for m in root["optimal"]
                    ],
                }
            )

    n = len(predictions)
    return {
        "states": n,
        "base_success": base_valid,
        "base_ratio": base_valid / n if n else 1.0,
        "combined_success": valid,
        "combined_ratio": valid / n if n else 1.0,
        "residual": n - valid,
        "repair_invocations": repair_invocations,
        "repair_success": repair_success,
        "unsafe_override": unsafe_override,
        "residual_examples": residual_examples,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--sample-size", type=int, default=50000)
    ap.add_argument("--acquisition-seed", type=int, default=20260928)
    ap.add_argument("--heldout-seed", type=int, default=20260929)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    started = time.time()

    bank = coordinate_feature_bank()
    base_names = [n for n, _ in bank]
    feature_fns = [fn for _, fn in bank]
    cache: dict[tuple[str, bool], int] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        policy, role_frequency, policy_summary = frozen_kpvk_policy(
            tablebase, cache, feature_fns
        )

        acquisition_sample = sample_kppvk(
            args.sample_size, args.acquisition_seed
        )
        acquisition = exact_dataset(
            acquisition_sample,
            tablebase,
            cache,
            policy,
            feature_fns,
            base_names,
            collect_targets=True,
        )
        acquisition_residual = (
            len(acquisition["base_success"])
            - sum(acquisition["base_success"])
        )
        # Reproduce the durable V5 acquisition boundary exactly.
        if (
            args.sample_size == 50000
            and args.acquisition_seed == 20260928
            and acquisition_residual != 1275
        ):
            raise AssertionError(
                f"V5 residual drift: expected 1275 got {acquisition_residual}"
            )

        controller = DecisionTreeClassifier(
            criterion="entropy",
            splitter="best",
            random_state=0,
        )
        controller.fit(acquisition["X"], acquisition["targets"])
        acquisition_eval = evaluate_controller(acquisition, controller)

        heldout_sample = sample_kppvk(
            args.sample_size, args.heldout_seed
        )
        heldout = exact_dataset(
            heldout_sample,
            tablebase,
            cache,
            policy,
            feature_fns,
            base_names,
            collect_targets=False,
            repair_ranking=acquisition["repair_ranking"],
        )
        # Role IDs are local categorical codes. The state vector needs the same
        # source-role coding on both slices, so rebuild heldout role coordinates
        # with acquisition coding if the observed role set differs.
        if heldout["base_role_ids"] != acquisition["base_role_ids"]:
            # The frozen KPvK tree has a fixed role vocabulary, so differing
            # maps can only be order/subset drift. Recompute deterministically
            # using the union and rebuild both datasets.
            all_roles = sorted(
                set(acquisition["base_role_ids"]) | set(heldout["base_role_ids"])
            )
            # This case is not expected with the complete frozen KPvK policy.
            raise AssertionError(
                f"base role coding drift across slices: {all_roles}"
            )

        heldout_eval = evaluate_controller(heldout, controller)

    acq_states = acquisition_eval["states"]
    # Causal ablation is exactly the frozen BASE result on the acquisition
    # slice; it must restore the original V5 residual.
    ablation_residual = acq_states - acquisition_eval["base_success"]

    status = (
        "WARRANTED_HELDOUT_KPPVK_RESIDUAL_COMPOUNDING"
        if acquisition_eval["residual"] == 0
        and acquisition_eval["unsafe_override"] == 0
        and heldout_eval["residual"] == 0
        and heldout_eval["unsafe_override"] == 0
        else "CANDIDATE_WITH_HELDOUT_KPPVK_RESIDUAL"
    )
    summary = tree_summary(controller)
    used = sorted(
        {
            int(x)
            for x in controller.tree_.feature
            if int(x) >= 0
        }
    )
    summary["used_features"] = [
        acquisition["feature_names"][i] for i in used
    ]

    result = {
        "schema": SCHEMA,
        "status": status,
        "v5_authority": V5_AUTHORITY,
        "method": {
            "generation_0": "frozen complete KPvK goal certificate",
            "generation_1_acquisition": (
                "only V5 KPPvK residual states provide new replacement roles; "
                "base-success states provide guard negatives via BASE target"
            ),
            "heldout": (
                "independent KPPvK deterministic sample; zero heldout labels in acquisition"
            ),
        },
        "seeds": {
            "acquisition": args.acquisition_seed,
            "heldout": args.heldout_seed,
        },
        "sample_size_each": args.sample_size,
        "kpvk_source": {
            "role_frequency": role_frequency,
            "tree": policy_summary,
        },
        "acquisition": {
            **{k:v for k,v in acquisition_eval.items() if k!="residual_examples"},
            "original_v5_residual": acquisition_residual,
            "ablation_residual": ablation_residual,
            "repair_role_vocabulary": sorted(acquisition["repair_ranking"]),
        },
        "controller": {
            "tree": summary,
            "feature_count": len(acquisition["feature_names"]),
            "used_feature_count": len(summary["used_features"]),
            "used_features": summary["used_features"],
        },
        "heldout": heldout_eval,
        "epistemic_boundary": {
            "warranted_if_green": [
                "the residual-acquired controller exactly recloses the V5 acquisition slice",
                "ablation restores the original V5 residual",
                "the frozen two-generation controller has zero error on an independent KPPvK slice",
            ],
            "unknown": [
                "complete KPPvK coverage outside the sampled boundaries",
                "transfer to further material classes",
                "general chess solution",
            ],
        },
        "cache": {
            "unique_wdl_positions_probed_or_certified": len(cache)
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
        },
        "elapsed_seconds": time.time() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2)+"\n")

    print(f"CRYSTAL_CHESS_RICHER_RESIDUAL_V6={status}")
    print(
        f"acquisition base={acquisition_eval['base_success']}/{acq_states} "
        f"combined={acquisition_eval['combined_success']}/{acq_states} "
        f"ablation_residual={ablation_residual}"
    )
    print(
        f"heldout base={heldout_eval['base_success']}/{heldout_eval['states']} "
        f"combined={heldout_eval['combined_success']}/{heldout_eval['states']} "
        f"residual={heldout_eval['residual']} "
        f"unsafe_override={heldout_eval['unsafe_override']}"
    )
    print(
        f"repair_tree leaves={summary['leaves']} depth={summary['max_depth']} "
        f"used_features={len(summary['used_features'])}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
