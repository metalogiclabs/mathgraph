#!/usr/bin/env python3
"""Crystal Chess V37: residual-earned zeroing parity on the cheap root-PV interface.

V36's broad cheap parent:
  root interval nonoverlap + root top-two pair stability + reply-capture parity
retained one exact source false positive.  In that residual, the only protected
reply-effect bit separating candidate and authority alternative is zeroing:
candidate reply non-zeroing, alternative reply a pawn move.

V37 adds exactly:
  candidate_reply_zeroing == alternative_reply_zeroing

No new search, no threshold, no child probes.  The parent + one-bit separator is
reclosed over all exposed generations including V36, then frozen before fresh
100k authority queries on seeds 20261015/20261016.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

import chess

from crystal_chess_search_sufficiency_v25 import (
    AUTHORITY_NODES, PROBE_TOTAL_NODES, STOCKFISH_PIN, UCIStockfish,
)
from crystal_chess_search_confirmation_v26 import (
    V25_GUARD_SHA256, base_probes, guard_fires, load_guard, read_epd,
)
from crystal_chess_search_continuation_v28 import position_key
from crystal_chess_root_pv_interface_v36 import root_interface, source_rows

SCHEMA = "mathgraph.crystal-chess.root-reply-zeroing.v37"
FRESH_SEEDS = (20261015, 20261016)
V36_RUN = 36503091782


def parent_accepts(iface: dict[str, Any]) -> bool:
    c = iface["candidate_reply_effect"]
    a = iface["alternative_reply_effect"]
    return (
        int(iface["robust_gap"]) >= 0
        and bool(iface["root_pair_stable"])
        and int(c["capture"]) == int(a["capture"])
    )


def separator_accepts(iface: dict[str, Any]) -> bool:
    c = iface["candidate_reply_effect"]
    a = iface["alternative_reply_effect"]
    return int(c["zeroing"]) == int(a["zeroing"])


def evaluate_target(
    engine: UCIStockfish,
    guard: dict[str, Any],
    boards: list[chess.Board],
) -> dict[str, Any]:
    guard_fired = iface_available = parent = accepted = wrong = 0
    examples: list[dict[str, Any]] = []
    for board in boards:
        fen = board.fen()
        p1, p2 = base_probes(engine, fen)
        fires, leaf = guard_fires(guard, board, p1, p2)
        if not fires:
            continue
        guard_fired += 1
        iface = root_interface(board, p1, p2)
        if iface is None:
            continue
        iface_available += 1
        if not parent_accepts(iface):
            continue
        parent += 1
        if not separator_accepts(iface):
            continue
        accepted += 1
        auth = engine.search(fen, AUTHORITY_NODES, multipv=1, clear=True)
        ok = str(p2["bestmove"]) == str(auth["bestmove"])
        wrong += int(not ok)
        if len(examples) < 30:
            examples.append({
                "fen": fen,
                "leaf": leaf,
                "authority": str(auth["bestmove"]),
                "match": ok,
                **iface,
            })

    n = len(boards)
    baseline = n * AUTHORITY_NODES
    hybrid = n * PROBE_TOTAL_NODES + (n - accepted) * AUTHORITY_NODES
    reduction = 1.0 - hybrid / baseline if baseline else 0.0
    return {
        "positions": n,
        "v25_guard_fires": guard_fired,
        "interface_available": iface_available,
        "parent_admitted": parent,
        "accepted": accepted,
        "wrong": wrong,
        "coverage_ratio": accepted / n if n else 0.0,
        "baseline_nodes": baseline,
        "hybrid_nodes": hybrid,
        "estimated_node_reduction_ratio": reduction,
        "examples": examples,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--v22-pgn", type=Path, required=True)
    ap.add_argument("--source-epd", type=Path, action="append", required=True)
    ap.add_argument("--source-generation", action="append", required=True)
    ap.add_argument("--fresh-epd-a", type=Path, required=True)
    ap.add_argument("--fresh-manifest-a", type=Path, required=True)
    ap.add_argument("--fresh-epd-b", type=Path, required=True)
    ap.add_argument("--fresh-manifest-b", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    guard, sha = load_guard(args.guard)
    if sha != V25_GUARD_SHA256:
        raise AssertionError(("V25 guard drift", sha))
    generations = list(zip(args.source_generation, args.source_epd))

    engine = UCIStockfish(args.stockfish)
    try:
        rows, source_keys = source_rows(
            engine, guard, args.v22_pgn, generations
        )
        parent = [r for r in rows if parent_accepts(r["iface"])]
        parent_wrong = sum(not bool(r["match"]) for r in parent)
        kept = [r for r in parent if separator_accepts(r["iface"])]
        kept_wrong = sum(not bool(r["match"]) for r in kept)
        support = Counter(str(r["generation"]) for r in kept)

        diagnostics = {
            "source_guard_rows": len(rows),
            "parent_accepted": len(parent),
            "parent_wrong": parent_wrong,
            "separator_accepted": len(kept),
            "separator_wrong": kept_wrong,
            "support": dict(support),
            "retention_ratio": len(kept) / len(parent) if parent else 0.0,
        }
        parent_bad = [
            {
                "generation": r["generation"],
                "fen": r["fen"],
                "authority": r["authority"],
                "candidate": r["iface"]["candidate"],
                "iface": r["iface"],
                "separator_accepts": separator_accepts(r["iface"]),
            }
            for r in parent if not bool(r["match"])
        ]

        source_green = (
            len(kept) >= 30 and kept_wrong == 0 and len(support) >= 4
        )
        if not source_green:
            result = {
                "schema": SCHEMA,
                "status": "ZEROING_PARITY_DOES_NOT_CLOSE_EXPOSED_SOURCE",
                "stockfish_pin": STOCKFISH_PIN,
                "v36_run": V36_RUN,
                "diagnostics": diagnostics,
                "parent_false_positives": parent_bad,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
            print(
                "CRYSTAL_CHESS_ROOT_REPLY_ZEROING_V37="
                "ZEROING_PARITY_DOES_NOT_CLOSE_EXPOSED_SOURCE"
            )
            print(f"diagnostics={diagnostics}")
            print(f"artifact={args.output}")
            return 0

        # Frozen here before any fresh authority query.
        manifests = [
            json.loads(args.fresh_manifest_a.read_text()),
            json.loads(args.fresh_manifest_b.read_text()),
        ]
        if tuple(int(m["seed"]) for m in manifests) != FRESH_SEEDS:
            raise AssertionError(("fresh seed drift", [m["seed"] for m in manifests]))

        target_sets: list[list[chess.Board]] = []
        source_overlaps: list[int] = []
        cross_overlaps: list[int] = []
        target_keys: set[tuple[str, bool, str, int | None]] = set()
        for path in (args.fresh_epd_a, args.fresh_epd_b):
            all_boards = read_epd(path)
            source_overlap = {position_key(b) for b in all_boards} & source_keys
            boards = [b for b in all_boards if position_key(b) not in source_keys]
            cross = {position_key(b) for b in boards} & target_keys
            if cross:
                boards = [b for b in boards if position_key(b) not in target_keys]
            if len(boards) < 200:
                raise AssertionError(("fresh target too small", len(boards)))
            target_keys.update(position_key(b) for b in boards)
            target_sets.append(boards)
            source_overlaps.append(len(source_overlap))
            cross_overlaps.append(len(cross))

        targets = [evaluate_target(engine, guard, b) for b in target_sets]
    finally:
        engine.quit()

    combined_positions = sum(r["positions"] for r in targets)
    combined_accepted = sum(r["accepted"] for r in targets)
    combined_wrong = sum(r["wrong"] for r in targets)
    combined_baseline = sum(r["baseline_nodes"] for r in targets)
    combined_hybrid = sum(r["hybrid_nodes"] for r in targets)
    combined_reduction = 1.0 - combined_hybrid / combined_baseline

    green = (
        all(r["accepted"] > 0 for r in targets)
        and combined_wrong == 0
        and all(r["estimated_node_reduction_ratio"] > 0 for r in targets)
    )
    status = (
        "WARRANTED_REPLICATED_NORMAL_SEARCH_ROOT_REPLY_ZEROING"
        if green else
        "FRESH_NORMAL_SEARCH_ROOT_REPLY_ZEROING_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v36_run": V36_RUN,
        "source": {
            "diagnostics": diagnostics,
            "parent_false_positives": parent_bad,
        },
        "targets": [
            {
                "seed": FRESH_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                "source_overlap_removed_before_search": source_overlaps[i],
                "earlier_target_overlap_removed_before_search": cross_overlaps[i],
                **targets[i],
            }
            for i in range(2)
        ],
        "combined": {
            "positions": combined_positions,
            "accepted": combined_accepted,
            "wrong": combined_wrong,
            "coverage_ratio": combined_accepted / combined_positions,
            "baseline_nodes": combined_baseline,
            "hybrid_nodes": combined_hybrid,
            "estimated_node_reduction_ratio": combined_reduction,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "V36 broad cheap parent is frozen",
                "the sole new separator is equality of opponent-reply zeroing type",
                "no threshold or extra search is added",
                "separator is source-exact across at least four exposed generations before fresh labels",
                "both fresh seeds have zero wrong substitutions and positive charged node reduction",
            ],
            "unknown": [
                "normal-game wall-clock gain",
                "self-play Elo gain",
                "transfer to other opening generators",
                "chess-theoretic optimality",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_ROOT_REPLY_ZEROING_V37={status}")
    print(f"source diagnostics={diagnostics}")
    for seed, row in zip(FRESH_SEEDS, targets):
        print(
            f"seed={seed} positions={row['positions']} "
            f"v25={row['v25_guard_fires']} iface={row['interface_available']} "
            f"parent={row['parent_admitted']} accepted={row['accepted']} "
            f"wrong={row['wrong']} coverage={row['coverage_ratio']:.8f} "
            f"reduction={row['estimated_node_reduction_ratio']:.8f}"
        )
    print(
        f"combined accepted={combined_accepted}/{combined_positions} "
        f"wrong={combined_wrong} "
        f"coverage={result['combined']['coverage_ratio']:.8f} "
        f"reduction={combined_reduction:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
