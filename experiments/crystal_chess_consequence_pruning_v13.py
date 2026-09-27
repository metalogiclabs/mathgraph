#!/usr/bin/env python3
"""Crystal Chess V13: consequence-pruned exact DTZ certificate trees.

Earlier exact trees choose one preferred optimal role per state and then learn
that arbitrary labeling. This over-retains distinctions whenever a region of
states shares some other certified role.

V13 first trains the exact preferred-label tree as a complete scaffold. It then
prunes any node whose entire state set has a nonempty intersection of exact
DTZ-valid roles. The node becomes one leaf using any common certified role.

This is lossless consequence compression: distinctions needed only to imitate
an arbitrary choice disappear.
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
from crystal_chess_goal_certificate_v3 import (
    choose_preferred_roles,
    file_sha256,
    tree_summary,
)
from crystal_chess_dtz_certificate_v6 import (
    probe_dtz_safe,
    dtz_optimal_roles,
)
from crystal_chess_piece_family_v10 import (
    PIECE_MAP,
    make_board,
    features as piece_features,
    optimal_roles as piece_optimal_roles,
)


SCHEMA = "mathgraph.crystal-chess.consequence-pruned-dtz.v13"


def role_ranking(role_sets):
    freq = Counter()
    for rs in role_sets:
        freq.update(rs)
    ordered = [r for r, _n in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))]
    return ordered, dict(freq)


def build_family(piece: str, tb):
    wcache = {}
    dcache = {}
    rows = []
    roles = []

    if piece == "P":
        bank = coordinate_feature_bank()
        feature_names = [name for name, _fn in bank]
        recs, _enum = enumerate_records(
            tb, wcache, [fn for _name, fn in bank]
        )
        for rec in recs:
            board = make_kpvk(rec.wk, rec.bk, rec.pawn, rec.turn)
            if not list(board.legal_moves):
                continue
            rd = probe_dtz_safe(tb, board, dcache)
            rs = dtz_optimal_roles(
                board, rec.wdl, rd, tb, wcache, dcache
            )
            rows.append(rec.features)
            roles.append(rs)
        return np.asarray(rows, dtype=np.int16), roles, feature_names, wcache, dcache

    piece_type = PIECE_MAP[piece]
    feature_names = [
        "turn","wk_file","wk_rank","bk_file","bk_rank","x_file","x_rank",
        "wk_dx_x","wk_dy_x","bk_dx_x","bk_dy_x",
        "abs_wk_dx_x","abs_wk_dy_x","abs_bk_dx_x","abs_bk_dy_x",
        "wk_bk_dx","wk_bk_dy","abs_wk_bk_dx","abs_wk_bk_dy",
        "cheb_wk_x","cheb_bk_x","cheb_kings",
        "man_wk_x","man_bk_x","man_kings",
        "wk_edge","bk_edge","x_edge",
        "same_file_wk_x","same_file_bk_x","same_rank_wk_x","same_rank_bk_x",
        "same_file_kings","same_rank_kings",
    ]
    for x in chess.SQUARES:
        for wk in chess.SQUARES:
            if wk == x:
                continue
            for bk in chess.SQUARES:
                if bk in (wk, x):
                    continue
                for turn in (False, True):
                    board = make_board(wk, bk, x, turn, piece_type)
                    if not board.is_valid() or not list(board.legal_moves):
                        continue
                    rw = int(tb.probe_wdl(board))
                    rd = probe_dtz_safe(tb, board, dcache)
                    rs = piece_optimal_roles(
                        board, rw, rd, tb, wcache, dcache, piece
                    )
                    rows.append(piece_features(wk, bk, x, turn))
                    roles.append(rs)
    return np.asarray(rows, dtype=np.int16), roles, feature_names, wcache, dcache


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--piece", choices=["P","Q","R","B","N"], required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    started = time.time()

    files = sorted(args.tablebase_dir.glob("*.rtb*"))
    manifest = [
        {"name": p.name, "size": p.stat().st_size, "sha256": file_sha256(p)}
        for p in files
    ]

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=True
    ) as tb:
        X, role_sets, feature_names, wcache, dcache = build_family(
            args.piece, tb
        )

    n = len(role_sets)
    if not n:
        raise AssertionError("empty family")
    ordered_roles, role_freq = role_ranking(role_sets)
    rank = {r: i for i, r in enumerate(ordered_roles)}
    preferred = [min(rs, key=lambda r: (rank[r], r)) for rs in role_sets]

    scaffold = DecisionTreeClassifier(
        criterion="entropy", splitter="best", random_state=0
    )
    scaffold.fit(X, preferred)
    scaffold_pred = [str(x) for x in scaffold.predict(X)]
    invalid = [
        i for i, (p, rs) in enumerate(zip(scaffold_pred, role_sets))
        if p not in rs
    ]
    if invalid:
        raise AssertionError(f"scaffold invalid: {invalid[:20]}")

    role_to_bit = {r: 1 << i for i, r in enumerate(ordered_roles)}
    allowed_masks = [
        sum(role_to_bit[r] for r in rs)
        for rs in role_sets
    ]
    all_mask = (1 << len(ordered_roles)) - 1

    t = scaffold.tree_
    nodes = []

    def choose_common(mask: int) -> str:
        for r in ordered_roles:
            if mask & role_to_bit[r]:
                return r
        raise AssertionError("empty common role mask")

    def recurse(tree_node: int, ids: np.ndarray, depth: int) -> tuple[int, int, int]:
        common = all_mask
        for i in ids:
            common &= allowed_masks[int(i)]
            if common == 0:
                break

        out_id = len(nodes)
        nodes.append(None)

        if common:
            label = choose_common(common)
            nodes[out_id] = {
                "leaf": label,
                "support": int(len(ids)),
            }
            return out_id, 1, depth

        feat = int(t.feature[tree_node])
        if feat < 0:
            raise AssertionError("original exact leaf lacks a common valid role")
        threshold = float(t.threshold[tree_node])
        vals = X[ids, feat]
        left_ids = ids[vals <= threshold]
        right_ids = ids[vals > threshold]
        if not len(left_ids) or not len(right_ids):
            raise AssertionError("degenerate scaffold split")

        left, ll, ld = recurse(int(t.children_left[tree_node]), left_ids, depth + 1)
        right, rl, rd = recurse(int(t.children_right[tree_node]), right_ids, depth + 1)
        nodes[out_id] = {
            "feature": feat,
            "threshold": threshold,
            "left": left,
            "right": right,
            "support": int(len(ids)),
        }
        return out_id, ll + rl, max(ld, rd)

    root, pruned_leaves, pruned_depth = recurse(
        0, np.arange(n, dtype=np.int32), 0
    )
    assert root == 0

    def predict_row(row) -> str:
        node = 0
        while True:
            item = nodes[node]
            if "leaf" in item:
                return item["leaf"]
            node = item["left"] if row[item["feature"]] <= item["threshold"] else item["right"]

    pruned_invalid = []
    for i in range(n):
        label = predict_row(X[i])
        if label not in role_sets[i]:
            if len(pruned_invalid) < 20:
                pruned_invalid.append((i, label, role_sets[i]))
    if pruned_invalid:
        raise AssertionError(pruned_invalid)

    pruned_nodes = len(nodes)
    raw = json.dumps(nodes, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    scaffold_summary = tree_summary(scaffold)

    result = {
        "schema": SCHEMA,
        "status": "WARRANTED_BOUNDED_CONSEQUENCE_PRUNED_DTZ_CERTIFICATE",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "piece": args.piece,
        "authority": {
            "kind": "Syzygy WDL+DTZ",
            "tablebase_files": manifest,
        },
        "coverage": {
            "nonterminal_states": n,
            "distinct_valid_roles": len(ordered_roles),
        },
        "scaffold": {
            "tree": scaffold_summary,
            "compression_vs_state_table": n / int(scaffold_summary["leaves"]),
        },
        "consequence_pruned": {
            "nodes": pruned_nodes,
            "leaves": pruned_leaves,
            "max_depth": pruned_depth,
            "sha256": digest,
            "audit_invalid": 0,
            "compression_vs_state_table": n / pruned_leaves,
            "leaf_reduction_vs_scaffold": 1 - pruned_leaves / int(scaffold_summary["leaves"]),
        },
        "role_frequency": role_freq,
        "feature_names": feature_names,
        "cache": {"wdl": len(wcache), "dtz": len(dcache)},
        "epistemic_boundary": {
            "warranted_if_green": [
                "every pruned leaf emits one role that is exact DTZ-valid for every state in that leaf",
                "pruning removes only distinctions between arbitrarily different valid certificate choices",
            ],
            "unknown": [
                "global minimum certificate tree",
                "transfer of the pruned tree to richer material",
                "general chess solution",
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
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("CRYSTAL_CHESS_CONSEQUENCE_PRUNING_V13=PASS")
    print(
        f"piece={args.piece} states={n} "
        f"scaffold_leaves={scaffold_summary['leaves']} "
        f"pruned_leaves={pruned_leaves}"
    )
    print(
        f"compression={n/pruned_leaves:.3f}x "
        f"leaf_reduction={1-pruned_leaves/int(scaffold_summary['leaves']):.6f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
