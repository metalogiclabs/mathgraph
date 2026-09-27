#!/usr/bin/env python3
"""Crystal Chess V6B: prospective relative guard transfer across pawn files.

Acquire a KPPvK capability only from TWO independent same-file discovery
worlds:
  * both pawns on file b
  * both pawns on file c

A source-only signature is admitted iff:
  * it appears with at least MIN_SUPPORT states in BOTH discovery worlds, and
  * the frozen KPvK-projection action is exact Syzygy-optimal on every such
    state in BOTH worlds.

The admitted guard contains no absolute pawn-file coordinate.

Freeze that guard bank, then prospectively test it on two disjoint complete
same-file worlds:
  * both pawns on file a
  * both pawns on file d

Target WDL is queried only after the guard and concrete move are fixed.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from itertools import combinations
import hashlib
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
from crystal_chess_guard_genesis_v6 import signature
from crystal_chess_goal_certificate_v3 import file_sha256, move_role


SCHEMA = "mathgraph.crystal-chess.kppvk-relative-guard-transfer.v6b"


def same_file_states(file: int):
    squares = [chess.square(file, rank) for rank in range(1, 6)]
    for p1, p2 in combinations(squares, 2):
        for wk in chess.SQUARES:
            if wk in (p1, p2):
                continue
            for bk in chess.SQUARES:
                if bk in (p1, p2, wk):
                    continue
                for turn in (chess.WHITE, chess.BLACK):
                    board = make_kppvk(wk, bk, p1, p2, turn)
                    if board.is_valid():
                        yield wk, bk, p1, p2, turn, board


def candidate(
    clf,
    class_labels,
    feature_fns,
    tb,
    cache,
    wk,
    bk,
    p1,
    p2,
    turn,
    board,
):
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return None
    r1 = projection_role(clf, class_labels, feature_fns, wk, bk, p1, turn)
    r2 = projection_role(clf, class_labels, feature_fns, wk, bk, p2, turn)
    if r1 is None or r2 is None or r1 != r2:
        return None
    realizers = [m for m in legal_moves if move_role(board, m) == r1]
    if len(realizers) != 1:
        return None
    w1 = probe_wdl(tb, make_kpvk(wk, bk, p1, turn), cache)
    w2 = probe_wdl(tb, make_kpvk(wk, bk, p2, turn), cache)
    sig = signature(turn, r1, w1, w2, p1, p2)
    return sig, r1, realizers[0]


def audit_move(tb, cache, board, move):
    root = probe_wdl(tb, board, cache)
    child = board.copy(stack=False)
    child.push(move)
    outcome = -probe_wdl(tb, child, cache)
    return outcome == root, root, outcome


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablebase-dir", type=Path, required=True)
    ap.add_argument("--min-support", type=int, default=8)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    started = time.time()

    tb_files = sorted(args.tablebase_dir.glob("*.rtbw"))
    manifest = [
        {"name": p.name, "size": p.stat().st_size, "sha256": file_sha256(p)}
        for p in tb_files
    ]
    cache = {}

    with chess.syzygy.open_tablebase(
        str(args.tablebase_dir), load_wdl=True, load_dtz=False
    ) as tb:
        clf, class_labels, feature_fns, _ = rebuild_frozen_v3(tb, cache)

        discovery = {}
        for file in (1, 2):  # b, c
            counts = defaultdict(lambda: [0, 0])
            legal = candidates = correct = wrong = 0
            for wk, bk, p1, p2, turn, board in same_file_states(file):
                legal += 1
                cand = candidate(
                    clf, class_labels, feature_fns, tb, cache,
                    wk, bk, p1, p2, turn, board
                )
                if cand is None:
                    continue
                candidates += 1
                sig, role, move = cand
                ok, _root, _outcome = audit_move(tb, cache, board, move)
                correct += int(ok)
                wrong += int(not ok)
                counts[sig][0] += 1
                counts[sig][1] += int(not ok)
            discovery[file] = {
                "counts": counts,
                "legal": legal,
                "candidates": candidates,
                "correct": correct,
                "wrong": wrong,
            }

        # Relative admission: same source-only signature must be supported and
        # perfect in both independent discovery files.
        guards = set()
        common = set(discovery[1]["counts"]) & set(discovery[2]["counts"])
        for sig in common:
            b_count, b_wrong = discovery[1]["counts"][sig]
            c_count, c_wrong = discovery[2]["counts"][sig]
            if (
                b_count >= args.min_support
                and c_count >= args.min_support
                and b_wrong == 0
                and c_wrong == 0
            ):
                guards.add(sig)

        guard_payload = sorted([list(x) for x in guards], key=repr)
        guard_digest = hashlib.sha256(
            json.dumps(guard_payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

        heldouts = {}
        for file in (0, 3):  # a, d
            legal = candidate_states = acted = correct = wrong = 0
            failures = []
            roles = defaultdict(int)
            for wk, bk, p1, p2, turn, board in same_file_states(file):
                legal += 1
                cand = candidate(
                    clf, class_labels, feature_fns, tb, cache,
                    wk, bk, p1, p2, turn, board
                )
                if cand is None:
                    continue
                candidate_states += 1
                sig, role, move = cand
                if sig not in guards:
                    continue
                acted += 1
                roles[role] += 1
                ok, root, outcome = audit_move(tb, cache, board, move)
                correct += int(ok)
                wrong += int(not ok)
                if not ok and len(failures) < 25:
                    failures.append({
                        "fen": board.fen(),
                        "role": role,
                        "move": move.uci(),
                        "root_wdl": root,
                        "child_consequence": outcome,
                        "signature": list(sig),
                    })
            heldouts[file] = {
                "legal": legal,
                "candidate_states": candidate_states,
                "acted": acted,
                "correct": correct,
                "wrong": wrong,
                "precision": correct / acted if acted else 1.0,
                "coverage_of_legal": acted / legal if legal else 0.0,
                "coverage_of_candidate": acted / candidate_states if candidate_states else 0.0,
                "roles": dict(sorted(roles.items())),
                "failures": failures,
            }

    total_acted = sum(heldouts[f]["acted"] for f in (0, 3))
    total_wrong = sum(heldouts[f]["wrong"] for f in (0, 3))
    total_correct = sum(heldouts[f]["correct"] for f in (0, 3))
    status = (
        "WARRANTED_PROSPECTIVE_RELATIVE_CROSS_MATERIAL_GUARD"
        if total_acted > 0 and total_wrong == 0
        else "EXACT_RESIDUAL_RELATIVE_GUARD"
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
            "discovery_worlds": ["KPPvK both pawns file b", "KPPvK both pawns file c"],
            "heldout_worlds": ["KPPvK both pawns file a", "KPPvK both pawns file d"],
            "guard_vocabulary": (
                "side-to-move, predicted relative role, two KPvK projection WDLs, "
                "and relative pawn-pair rank/file geometry; no absolute file"
            ),
            "admission": (
                "same signature perfect with >= min_support in both independent "
                "discovery worlds"
            ),
            "min_support_each_discovery_world": args.min_support,
        },
        "authority": {
            "kind": "Syzygy WDL",
            "tablebase_files": manifest,
        },
        "guard_bank": {
            "count": len(guards),
            "sha256": guard_digest,
        },
        "discovery": {
            chess.FILE_NAMES[f]: {
                k: v for k, v in discovery[f].items() if k != "counts"
            }
            for f in (1, 2)
        },
        "heldout": {
            chess.FILE_NAMES[f]: heldouts[f] for f in (0, 3)
        },
        "combined_heldout": {
            "acted": total_acted,
            "correct": total_correct,
            "wrong": total_wrong,
            "precision": total_correct / total_acted if total_acted else 1.0,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                (
                    "relative source-only guards acquired on b/c transfer without "
                    "error to every a/d state on which they fire"
                ),
                "heldout labels do not enter guard admission",
            ],
            "unknown": [
                "KPPvK states outside admitted guards",
                "more general pair geometries",
                "general chess solution",
            ],
        },
        "cache": {"wdl_positions": len(cache)},
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "elapsed_seconds": time.time() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print("CRYSTAL_CHESS_RELATIVE_GUARD_V6B=PASS")
    print(
        f"guards={len(guards)} heldout_acted={total_acted} "
        f"correct={total_correct} wrong={total_wrong} "
        f"precision={total_correct/total_acted if total_acted else 1.0:.6f}"
    )
    for f in (0, 3):
        x = heldouts[f]
        print(
            f"file={chess.FILE_NAMES[f]} acted={x['acted']} "
            f"wrong={x['wrong']} precision={x['precision']:.6f} "
            f"coverage={x['coverage_of_legal']:.6f}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
