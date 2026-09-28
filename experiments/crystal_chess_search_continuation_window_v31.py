#!/usr/bin/env python3
"""Crystal Chess V31: fuse V28/V29/V30 into one continuation window.

V30 prospectively passed, but its selected "relative" feature was actually
candidate_backed_probe2 < 175, i.e. -reply_score1_probe2 < 175.  Combined with
the already-frozen V28 separator reply_score1_probe2 < 455 and V29 separator
reply_depth_probe2 != 6, the live consequence is simply:

    -175 < reply_score1_probe2 < 455
    and reply_depth_probe2 != 6.

The alternative-root continuation probe used in V30 is therefore not needed by
the selected consequence.  V31 fuses away that extra work and tests the compact
contract prospectively on two brand-new normal-opening seeds.

No target label is used to set either bound or the depth exclusion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import chess

from crystal_chess_search_sufficiency_v25 import (
    AUTHORITY_NODES,
    PROBE_TOTAL_NODES,
    STOCKFISH_PIN,
    UCIStockfish,
    extract_positions,
)
from crystal_chess_search_confirmation_v26 import (
    V25_GUARD_SHA256,
    base_probes,
    guard_fires,
    load_guard,
    read_epd,
)
from crystal_chess_search_continuation_v28 import (
    CHILD_PROBE_TOTAL_NODES,
    continuation_features,
    position_key,
)


SCHEMA = "mathgraph.crystal-chess.search-continuation-window.v31"
V22_RUN = 36361812786
V25_RUN = 36362896141
V28_RUN = 36368371744
V29_RUN = 36368824668
V30_RUN = 36385064153

LOWER_EXCLUSIVE = -175
UPPER_EXCLUSIVE = 455
EXCLUDED_DEPTH = 6
FRESH_SEEDS = (20261003, 20261004)


def source_keys(
    v22_pgn: Path,
    v28_epd: Path,
    v29_epd: Path,
    v30_epd: Path,
) -> set[tuple[str, bool, str, int | None]]:
    splits = extract_positions(v22_pgn, 220)
    keys = {
        position_key(board)
        for boards in splits.values()
        for board in boards
    }
    for path in (v28_epd, v29_epd, v30_epd):
        for board in read_epd(path):
            keys.add(position_key(board))
    return keys


def window_accepts(names: list[str], feats: tuple[int, ...]) -> bool:
    idx = {name: i for i, name in enumerate(names)}
    score = int(feats[idx["reply_score1_probe2"]])
    depth = int(feats[idx["reply_depth_probe2"]])
    return (
        LOWER_EXCLUSIVE < score < UPPER_EXCLUSIVE
        and depth != EXCLUDED_DEPTH
    )


def evaluate_target(
    engine: UCIStockfish,
    guard: dict[str, Any],
    boards: list[chess.Board],
) -> dict[str, Any]:
    v25_fires = 0
    accepted = 0
    wrong = 0
    examples: list[dict[str, Any]] = []

    for board in boards:
        fen = board.fen()
        p1, p2 = base_probes(engine, fen)
        fires, leaf = guard_fires(guard, board, p1, p2)
        if not fires:
            continue
        v25_fires += 1

        names, feats, meta = continuation_features(
            engine, board, str(p2["bestmove"])
        )
        if not window_accepts(names, feats):
            continue

        accepted += 1
        authority = engine.search(
            fen, AUTHORITY_NODES, multipv=1, clear=True
        )
        ok = str(p2["bestmove"]) == str(authority["bestmove"])
        wrong += int(not ok)
        if len(examples) < 30:
            idx = {name: i for i, name in enumerate(names)}
            examples.append({
                "fen": fen,
                "leaf": leaf,
                "candidate": p2["bestmove"],
                "authority": authority["bestmove"],
                "match": ok,
                "reply_score1_probe2": int(
                    feats[idx["reply_score1_probe2"]]
                ),
                "reply_depth_probe2": int(
                    feats[idx["reply_depth_probe2"]]
                ),
                "continuation": meta,
            })

    n = len(boards)
    baseline = n * AUTHORITY_NODES
    hybrid = (
        n * PROBE_TOTAL_NODES
        + v25_fires * CHILD_PROBE_TOTAL_NODES
        + (n - accepted) * AUTHORITY_NODES
    )
    reduction = 1.0 - hybrid / baseline
    return {
        "positions": n,
        "v25_guard_fires": v25_fires,
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
    ap.add_argument("--v28-epd", type=Path, required=True)
    ap.add_argument("--v29-epd", type=Path, required=True)
    ap.add_argument("--v30-epd", type=Path, required=True)
    ap.add_argument("--fresh-epd-a", type=Path, required=True)
    ap.add_argument("--fresh-manifest-a", type=Path, required=True)
    ap.add_argument("--fresh-epd-b", type=Path, required=True)
    ap.add_argument("--fresh-manifest-b", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    guard, sha = load_guard(args.guard)
    if sha != V25_GUARD_SHA256:
        raise AssertionError(("V25 guard drift", sha))

    manifests = [
        json.loads(args.fresh_manifest_a.read_text()),
        json.loads(args.fresh_manifest_b.read_text()),
    ]
    if tuple(int(m["seed"]) for m in manifests) != FRESH_SEEDS:
        raise AssertionError(
            ("fresh seed drift", [m["seed"] for m in manifests])
        )

    prior = source_keys(
        args.v22_pgn,
        args.v28_epd,
        args.v29_epd,
        args.v30_epd,
    )

    target_sets: list[list[chess.Board]] = []
    overlaps: list[int] = []
    all_target_keys: set[tuple[str, bool, str, int | None]] = set()
    for path in (args.fresh_epd_a, args.fresh_epd_b):
        boards_all = read_epd(path)
        overlap = {position_key(b) for b in boards_all} & prior
        boards = [
            b for b in boards_all
            if position_key(b) not in prior
        ]
        if len(boards) < 200:
            raise AssertionError(("fresh target too small", len(boards)))
        cross = {
            position_key(b) for b in boards
        } & all_target_keys
        if cross:
            raise AssertionError(("fresh targets overlap", len(cross)))
        all_target_keys.update(position_key(b) for b in boards)
        target_sets.append(boards)
        overlaps.append(len(overlap))

    engine = UCIStockfish(args.stockfish)
    try:
        rows = [
            evaluate_target(engine, guard, boards)
            for boards in target_sets
        ]
    finally:
        engine.quit()

    combined_positions = sum(r["positions"] for r in rows)
    combined_accepted = sum(r["accepted"] for r in rows)
    combined_wrong = sum(r["wrong"] for r in rows)
    combined_baseline = sum(r["baseline_nodes"] for r in rows)
    combined_hybrid = sum(r["hybrid_nodes"] for r in rows)
    combined_reduction = (
        1.0 - combined_hybrid / combined_baseline
        if combined_baseline else 0.0
    )

    green = (
        all(r["accepted"] > 0 for r in rows)
        and combined_wrong == 0
        and all(r["estimated_node_reduction_ratio"] > 0 for r in rows)
        and combined_reduction > 0
    )
    status = (
        "WARRANTED_REPLICATED_NORMAL_SEARCH_CONTINUATION_WINDOW"
        if green else
        "FRESH_NORMAL_SEARCH_CONTINUATION_WINDOW_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "source_runs": {
            "v22": V22_RUN,
            "v25": V25_RUN,
            "v28": V28_RUN,
            "v29": V29_RUN,
            "v30": V30_RUN,
        },
        "frozen_contract": {
            "v25_guard_sha256": sha,
            "reply_score1_probe2_lower_exclusive": LOWER_EXCLUSIVE,
            "reply_score1_probe2_upper_exclusive": UPPER_EXCLUSIVE,
            "reply_depth_probe2_excluded": EXCLUDED_DEPTH,
            "candidate_only_continuation": True,
            "alternative_probe_removed": True,
        },
        "targets": [
            {
                "seed": FRESH_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                "source_overlap_removed_before_search": overlaps[i],
                **rows[i],
            }
            for i in range(2)
        ],
        "combined": {
            "positions": combined_positions,
            "accepted": combined_accepted,
            "wrong": combined_wrong,
            "coverage_ratio": (
                combined_accepted / combined_positions
                if combined_positions else 0.0
            ),
            "baseline_nodes": combined_baseline,
            "hybrid_nodes": combined_hybrid,
            "estimated_node_reduction_ratio": combined_reduction,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "the compact continuation window is derived entirely from V28/V29/V30 exposed residual lineage",
                "no fresh target label changes either score bound or excluded depth",
                "both fresh target seeds are disjoint from all exposed V22/V28/V29/V30 source states before target authority search",
                "every accepted shortcut on both fresh seeds equals pinned 100k Stockfish",
                "the alternative-continuation probe has been removed and both individual targets retain positive net node savings",
            ],
            "unknown": [
                "real UCI wall-clock gain",
                "self-play Elo gain",
                "transfer to a different opening-generation protocol",
                "chess-theoretic optimality of Stockfish authority",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print(f"CRYSTAL_CHESS_SEARCH_CONTINUATION_WINDOW_V31={status}")
    for seed, row in zip(FRESH_SEEDS, rows):
        print(
            f"seed={seed} positions={row['positions']} "
            f"v25={row['v25_guard_fires']} accepted={row['accepted']} "
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
