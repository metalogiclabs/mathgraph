#!/usr/bin/env python3
"""Crystal Chess V6: discover source-only guards for KPvK -> KPPvK transfer.

Target KPPvK truth is used only to score candidate guards on a declared
DISCOVERY boundary. The guard vocabulary itself is restricted to facts
available from the frozen source capability:
  * exact KPvK WDL of each single-pawn projection,
  * the two projection policy roles,
  * side to move,
  * elementary relation between the two pawn squares.

The output is an exact census of signature -> (correct, wrong). A later run
must freeze selected zero-error signatures and qualify them on a disjoint
KPPvK boundary.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from itertools import combinations
import json
from pathlib import Path
import platform
import sys
import time

import chess
import chess.syzygy

from crystal_chess_kpvk_v0 import (
    BASE_CRYSTAL_AUTHORITY,
    PROTECTED_INTERFACE,
    make_kpvk,
    probe_wdl,
)
from crystal_chess_cross_material_v5 import (
    V3_AUTHORITY,
    V3_TREE_SHA256,
    make_kppvk,
    rebuild_frozen_v3,
    projection_role,
)
from crystal_chess_goal_certificate_v3 import file_sha256, move_role


SCHEMA = "mathgraph.crystal-chess.kppvk-source-guard-genesis.v6"


def parse_files(text: str) -> tuple[int, ...]:
    names = [x.strip() for x in text.split(",") if x.strip()]
    out = tuple(chess.FILE_NAMES.index(x) for x in names)
    if not out:
        raise ValueError("at least one pawn file required")
    return out


def signature(
    turn: bool,
    role: str,
    w1: int,
    w2: int,
    p1: int,
    p2: int,
) -> tuple:
    f1, f2 = chess.square_file(p1), chess.square_file(p2)
    r1, r2 = chess.square_rank(p1), chess.square_rank(p2)
    lo_w, hi_w = sorted((w1, w2))
    return (
        int(turn),
        role,
        lo_w,
        hi_w,
        int(f1 == f2),
        int(r1 == r2),
        abs(f1 - f2),
        abs(r1 - r2),
        min(r1, r2),
        max(r1, r2),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tablebase-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pawn-files", default="b,c")
    args = parser.parse_args()
    started = time.time()
    files = parse_files(args.pawn_files)

    tb_files = sorted(args.tablebase_dir.glob("*.rtbw"))
    manifest = [
        {"name": p.name, "size": p.stat().st_size, "sha256": file_sha256(p)}
        for p in tb_files
    ]
    cache: dict[tuple[str, bool], int] = {}

    census: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    legal_states = acted = correct = wrong = 0

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tablebase:
        clf, class_labels, feature_fns, _ = rebuild_frozen_v3(tablebase, cache)
        pawn_squares = [
            chess.square(file, rank)
            for file in files
            for rank in range(1, 6)
        ]

        for p1, p2 in combinations(pawn_squares, 2):
            for wk in chess.SQUARES:
                if wk in (p1, p2):
                    continue
                for bk in chess.SQUARES:
                    if bk in (p1, p2, wk):
                        continue
                    for turn in (chess.WHITE, chess.BLACK):
                        board = make_kppvk(wk, bk, p1, p2, turn)
                        if not board.is_valid():
                            continue
                        legal_states += 1
                        legal_moves = list(board.legal_moves)
                        if not legal_moves:
                            continue

                        r1 = projection_role(
                            clf, class_labels, feature_fns, wk, bk, p1, turn
                        )
                        r2 = projection_role(
                            clf, class_labels, feature_fns, wk, bk, p2, turn
                        )
                        if r1 is None or r2 is None or r1 != r2:
                            continue

                        realizers = [
                            move for move in legal_moves
                            if move_role(board, move) == r1
                        ]
                        if len(realizers) != 1:
                            continue

                        # Source-only guard coordinates.
                        v1 = make_kpvk(wk, bk, p1, turn)
                        v2 = make_kpvk(wk, bk, p2, turn)
                        w1 = probe_wdl(tablebase, v1, cache)
                        w2 = probe_wdl(tablebase, v2, cache)
                        sig = signature(turn, r1, w1, w2, p1, p2)

                        # Target truth is consulted only after the signature and
                        # action are fixed.
                        root = probe_wdl(tablebase, board, cache)
                        child = board.copy(stack=False)
                        child.push(realizers[0])
                        outcome = -probe_wdl(tablebase, child, cache)
                        ok = outcome == root

                        acted += 1
                        correct += int(ok)
                        wrong += int(not ok)
                        census[sig][0] += 1
                        census[sig][1] += int(not ok)

    rows = []
    for sig, (count, bad) in census.items():
        rows.append(
            {
                "turn": sig[0],
                "role": sig[1],
                "projection_wdl_min": sig[2],
                "projection_wdl_max": sig[3],
                "same_file": sig[4],
                "same_rank": sig[5],
                "file_gap": sig[6],
                "rank_gap": sig[7],
                "min_rank": sig[8],
                "max_rank": sig[9],
                "count": count,
                "wrong": bad,
                "correct": count - bad,
                "precision": (count - bad) / count,
            }
        )
    rows.sort(key=lambda x: (-x["count"], x["wrong"], json.dumps(x, sort_keys=True)))

    zero = [x for x in rows if x["wrong"] == 0]
    zero_coverage = sum(x["count"] for x in zero)
    result = {
        "schema": SCHEMA,
        "status": "EXACT_SOURCE_GUARD_CENSUS",
        "base_crystal_authority": BASE_CRYSTAL_AUTHORITY,
        "v3_authority": V3_AUTHORITY,
        "v3_tree_sha256": V3_TREE_SHA256,
        "protected_interface": PROTECTED_INTERFACE,
        "discovery_boundary": {
            "pawn_files": [chess.FILE_NAMES[x] for x in files],
            "pawn_ranks": [2, 3, 4, 5, 6],
        },
        "authority": {
            "kind": "Syzygy WDL",
            "tablebase_files": manifest,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "totals": {
            "legal_states": legal_states,
            "acted": acted,
            "correct": correct,
            "wrong": wrong,
            "raw_precision": correct / acted if acted else 0.0,
            "signature_classes": len(rows),
            "zero_error_signature_classes": len(zero),
            "zero_error_signature_coverage": zero_coverage,
            "zero_error_fraction_of_acted": zero_coverage / acted if acted else 0.0,
        },
        "signature_rows": rows,
        "epistemic_boundary": {
            "warranted": [
                "exact discovery-boundary census of source-only guard signatures"
            ],
            "candidate": [
                "zero-error signatures as transferable guards on a disjoint target boundary"
            ],
            "unknown": [
                "held-out a/d-involving KPPvK transfer",
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
    print("CRYSTAL_CHESS_GUARD_GENESIS_V6=PASS")
    print(
        f"legal={legal_states} acted={acted} precision={correct/acted:.6f} "
        f"signatures={len(rows)} zero={len(zero)} "
        f"zero_coverage={zero_coverage}/{acted} "
        f"fraction={zero_coverage/acted:.6f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
