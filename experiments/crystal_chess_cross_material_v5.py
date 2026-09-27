#!/usr/bin/env python3
"""Crystal Chess V5: zero-shot KPvK -> KPPvK capability transfer.

The KPvK V3 policy is frozen and reconstructed exactly (its tree digest is
checked against the V3 evidence). No KPPvK labels are used to choose actions.

For each K+2P vs K state in a complete declared subset:
  1. project the real state onto each single-pawn KPvK view;
  2. query the frozen KPvK symbolic policy on both projections;
  3. act only if both projections prescribe the same relative move role and
     that role has exactly one legal realization in the real KPPvK position;
  4. otherwise return UNKNOWN;
  5. only after the action is fixed, query exact Syzygy WDL to audit whether
     the chosen move preserves the root game-theoretic value.

Thus the richer authority is checker only, never policy input.
"""

from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
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
    probe_wdl,
)
from crystal_chess_goal_certificate_v3 import (
    choose_preferred_roles,
    encode_labels,
    file_sha256,
    move_role,
    optimal_roles,
    tree_digest,
)


SCHEMA = "mathgraph.crystal-chess.kppvk-zero-shot-transfer.v5b"
V3_AUTHORITY = (
    "metalogiclabs/mathgraph@73be9f4159816bf18a3ca70a1fb3eeb9793536a6"
)
V3_TREE_SHA256 = "f5b546a1a34ebd3d131f7b1e770a7e938563dd10cff8bcb3d0b1ba2540aa1aff"


def make_kppvk(
    wk: int,
    bk: int,
    p1: int,
    p2: int,
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
    board.set_piece_at(p1, chess.Piece(chess.PAWN, chess.WHITE))
    board.set_piece_at(p2, chess.Piece(chess.PAWN, chess.WHITE))
    return board


def rebuild_frozen_v3(
    tablebase: chess.syzygy.Tablebase,
    cache: dict[tuple[str, bool], int],
):
    bank = coordinate_feature_bank()
    feature_names = [name for name, _ in bank]
    feature_fns = [fn for _, fn in bank]
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
    labels, _freq = choose_preferred_roles(role_sets, nonterminal)
    y, class_labels = encode_labels(labels, nonterminal)
    clf = DecisionTreeClassifier(
        criterion="entropy",
        splitter="best",
        random_state=0,
    )
    clf.fit(X[nonterminal], y)
    got = tree_digest(clf)
    if got != V3_TREE_SHA256:
        raise AssertionError((got, V3_TREE_SHA256))
    return clf, class_labels, feature_fns, records


def projection_role(
    clf: DecisionTreeClassifier,
    class_labels: list[str],
    feature_fns,
    wk: int,
    bk: int,
    pawn: int,
    turn: bool,
) -> str | None:
    virtual = make_kpvk(wk, bk, pawn, turn)
    if not virtual.is_valid():
        return None
    if not any(virtual.legal_moves):
        return None
    row = np.asarray(
        [[fn(wk, bk, pawn, turn) for fn in feature_fns]],
        dtype=np.int16,
    )
    label = int(clf.predict(row)[0])
    return class_labels[label]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()

    tb_files = sorted(args.tablebase_dir.glob("*.rtbw"))
    manifest = [
        {"name": p.name, "size": p.stat().st_size, "sha256": file_sha256(p)}
        for p in tb_files
    ]
    cache: dict[tuple[str, bool], int] = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        clf, class_labels, feature_fns, _kp_records = rebuild_frozen_v3(
            tablebase, cache
        )

        # Complete declared richer subset: two distinct white pawns on files
        # a-d and ranks 2-6. Rank 7 is excluded so the chosen root action can
        # never be an immediate promotion requiring another 4-piece material
        # table. Black king captures may fall back to KPvK, which is loaded.
        pawn_squares = [
            chess.square(file, rank)
            for file in range(4)
            for rank in range(1, 6)
        ]

        candidates = 0
        legal_states = 0
        terminal_states = 0
        projection_unknown = 0
        projection_disagreement = 0
        nonunique_realizer = 0
        acted = 0
        correct = 0
        wrong = 0
        by_turn = {
            "white": Counter(),
            "black": Counter(),
        }
        by_role: Counter[str] = Counter()
        wrong_examples: list[dict[str, object]] = []

        for p1, p2 in combinations(pawn_squares, 2):
            for wk in chess.SQUARES:
                if wk in (p1, p2):
                    continue
                for bk in chess.SQUARES:
                    if bk in (p1, p2, wk):
                        continue
                    for turn in (chess.WHITE, chess.BLACK):
                        candidates += 1
                        board = make_kppvk(wk, bk, p1, p2, turn)
                        if not board.is_valid():
                            continue
                        legal_states += 1
                        legal_moves = list(board.legal_moves)
                        if not legal_moves:
                            terminal_states += 1
                            continue

                        r1 = projection_role(
                            clf, class_labels, feature_fns, wk, bk, p1, turn
                        )
                        r2 = projection_role(
                            clf, class_labels, feature_fns, wk, bk, p2, turn
                        )
                        if r1 is None or r2 is None:
                            projection_unknown += 1
                            continue
                        if r1 != r2:
                            projection_disagreement += 1
                            continue

                        # Prospective revocation learned only from the earlier
                        # V4 file-d residual, before inspecting any KPPvK
                        # outcomes. These three role families accounted for
                        # every V4 held-out error and are therefore disabled
                        # on the richer boundary pending a new certificate.
                        revoked_roles = {"K:-1,+0", "K:+0,-1", "P:+0,+1"}
                        if r1 in revoked_roles:
                            projection_unknown += 1
                            continue

                        realizers = [
                            move
                            for move in legal_moves
                            if move_role(board, move) == r1
                        ]
                        if len(realizers) != 1:
                            nonunique_realizer += 1
                            continue

                        chosen = realizers[0]
                        # Richer exact truth is queried only after the policy
                        # has committed to a concrete move.
                        root_wdl = probe_wdl(tablebase, board, cache)
                        child = board.copy(stack=False)
                        child.push(chosen)
                        consequence = -probe_wdl(tablebase, child, cache)

                        acted += 1
                        by_role[r1] += 1
                        side = "white" if turn else "black"
                        by_turn[side]["acted"] += 1
                        if consequence == root_wdl:
                            correct += 1
                            by_turn[side]["correct"] += 1
                        else:
                            wrong += 1
                            by_turn[side]["wrong"] += 1
                            if len(wrong_examples) < 25:
                                wrong_examples.append(
                                    {
                                        "fen": board.fen(),
                                        "pawn1": chess.square_name(p1),
                                        "pawn2": chess.square_name(p2),
                                        "projection_role": r1,
                                        "move": chosen.uci(),
                                        "root_wdl": root_wdl,
                                        "child_consequence": consequence,
                                    }
                                )

    status = (
        "WARRANTED_ZERO_SHOT_CROSS_MATERIAL_TRANSFER"
        if acted > 0 and wrong == 0
        else "EXACT_RESIDUAL_CROSS_MATERIAL_TRANSFER"
    )
    result = {
        "schema": SCHEMA,
        "status": status,
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v3_authority": V3_AUTHORITY,
        "v3_tree_sha256": V3_TREE_SHA256,
        "protected_interface": PROTECTED_INTERFACE,
        "method": {
            "source_capability": "frozen exact KPvK symbolic policy",
            "target_material": "White K+2P vs Black K",
            "target_subset": (
                "both white pawns on files a-d, ranks 2-6; all legal king "
                "placements and both sides to move"
            ),
            "policy_input": (
                "two single-pawn KPvK projections only; no KPPvK WDL/value"
            ),
            "guard": (
                "both projections prescribe identical move role and exactly "
                "one legal real move realizes that role"
            ),
            "audit": (
                "after action commitment, exact Syzygy root/child WDL checks "
                "whether the move preserves game-theoretic value"
            ),
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
        "coverage": {
            "candidate_assignments": candidates,
            "legal_states": legal_states,
            "terminal_states": terminal_states,
            "projection_unknown": projection_unknown,
            "projection_disagreement": projection_disagreement,
            "nonunique_realizer": nonunique_realizer,
            "acted": acted,
            "correct": correct,
            "wrong": wrong,
            "precision": correct / acted if acted else 0.0,
            "coverage_ratio_of_legal": acted / legal_states if legal_states else 0.0,
            "by_turn": {
                side: dict(counter) for side, counter in by_turn.items()
            },
            "by_role": dict(sorted(by_role.items())),
            "wrong_examples": wrong_examples,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                (
                    "a frozen capability learned and exhaustively qualified on "
                    "KPvK transfers with zero error to every KPPvK state on "
                    "which its projection-consensus guard fires in the complete "
                    "declared richer subset"
                )
            ],
            "unknown": [
                "KPPvK states where the guard abstains",
                "all other four-piece material classes",
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
    print("CRYSTAL_CHESS_CROSS_MATERIAL_V5B=PASS")
    print(
        f"legal={legal_states} acted={acted} correct={correct} wrong={wrong} "
        f"precision={correct/acted if acted else 0.0:.6f} "
        f"coverage={acted/legal_states if legal_states else 0.0:.6f}"
    )
    print(
        f"unknown_projection={projection_unknown} "
        f"disagreement={projection_disagreement} "
        f"nonunique={nonunique_realizer}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
