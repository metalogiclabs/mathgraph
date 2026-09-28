#!/usr/bin/env python3
"""Crystal Chess V32: residual-earned continuation stability.

V31 fused the V28/V29/V30 residual lineage into a compact candidate
continuation window:

    -175 < opponent reply score at 4k < 455
    reply depth at 4k != 6

It transferred cleanly on seed 20261004 but left exactly one false positive on
seed 20261003.  That residual has a precise structural separator: the
opponent's best reply changes from the 1k child probe to the TT-reused 4k child
probe.

V32 therefore adds exactly one condition:

    reply_best_stable == 1

No new score threshold, board feature, or learned tree is introduced.

The exposed V31 seeds are used only to verify that this single separator removes
the exact V31 residual with zero retained source errors.  The resulting
contract is frozen before two new normal-opening targets (20261005, 20261006)
are searched at 100k nodes.
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
from crystal_chess_search_continuation_window_v31 import (
    LOWER_EXCLUSIVE,
    UPPER_EXCLUSIVE,
    EXCLUDED_DEPTH,
)


SCHEMA = "mathgraph.crystal-chess.search-continuation-stability.v32"
V22_RUN = 36361812786
V25_RUN = 36362896141
V28_RUN = 36368371744
V29_RUN = 36368824668
V30_RUN = 36385064153
V31_RUN = 36385673166
FRESH_SEEDS = (20261005, 20261006)


def source_keys(
    v22_pgn: Path,
    exposed_epds: list[Path],
) -> set[tuple[str, bool, str, int | None]]:
    splits = extract_positions(v22_pgn, 220)
    keys = {
        position_key(board)
        for boards in splits.values()
        for board in boards
    }
    for path in exposed_epds:
        for board in read_epd(path):
            keys.add(position_key(board))
    return keys


def continuation_contract(
    names: list[str],
    feats: tuple[int, ...],
    *,
    require_stable: bool,
) -> bool:
    idx = {name: i for i, name in enumerate(names)}
    score = int(feats[idx["reply_score1_probe2"]])
    depth = int(feats[idx["reply_depth_probe2"]])
    stable = int(feats[idx["reply_best_stable"]])
    ok = (
        LOWER_EXCLUSIVE < score < UPPER_EXCLUSIVE
        and depth != EXCLUDED_DEPTH
    )
    if require_stable:
        ok = ok and stable == 1
    return ok


def evaluate(
    engine: UCIStockfish,
    guard: dict[str, Any],
    boards: list[chess.Board],
    *,
    authority: bool,
) -> dict[str, Any]:
    v25_fires = window_accepts = accepted = wrong = 0
    unstable_rejects = 0
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
        if not continuation_contract(
            names, feats, require_stable=False
        ):
            continue
        window_accepts += 1

        idx = {name: i for i, name in enumerate(names)}
        stable = int(feats[idx["reply_best_stable"]])
        if stable != 1:
            unstable_rejects += 1
            continue

        accepted += 1
        if not authority:
            continue

        auth = engine.search(
            fen, AUTHORITY_NODES, multipv=1, clear=True
        )
        ok = str(p2["bestmove"]) == str(auth["bestmove"])
        wrong += int(not ok)
        if len(examples) < 40:
            examples.append({
                "fen": fen,
                "leaf": leaf,
                "candidate": p2["bestmove"],
                "authority": auth["bestmove"],
                "match": ok,
                "reply_best_stable": stable,
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
    reduction = (
        1.0 - hybrid / baseline
        if baseline else 0.0
    )
    return {
        "positions": n,
        "v25_guard_fires": v25_fires,
        "window_accepts": window_accepts,
        "unstable_rejects": unstable_rejects,
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
    ap.add_argument("--v31-epd-a", type=Path, required=True)
    ap.add_argument("--v31-epd-b", type=Path, required=True)
    ap.add_argument("--fresh-epd-a", type=Path, required=True)
    ap.add_argument("--fresh-manifest-a", type=Path, required=True)
    ap.add_argument("--fresh-epd-b", type=Path, required=True)
    ap.add_argument("--fresh-manifest-b", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    guard, sha = load_guard(args.guard)
    if sha != V25_GUARD_SHA256:
        raise AssertionError(("V25 guard drift", sha))

    exposed = [
        args.v28_epd,
        args.v29_epd,
        args.v30_epd,
        args.v31_epd_a,
        args.v31_epd_b,
    ]
    prior = source_keys(args.v22_pgn, exposed)

    # Source causality check on the exact V31 exposed targets.
    v31_a = read_epd(args.v31_epd_a)
    v31_b = read_epd(args.v31_epd_b)

    manifests = [
        json.loads(args.fresh_manifest_a.read_text()),
        json.loads(args.fresh_manifest_b.read_text()),
    ]
    if tuple(int(m["seed"]) for m in manifests) != FRESH_SEEDS:
        raise AssertionError(
            ("fresh seed drift", [m["seed"] for m in manifests])
        )

    target_sets: list[list[chess.Board]] = []
    overlaps: list[int] = []
    target_keys: set[tuple[str, bool, str, int | None]] = set()
    for path in (args.fresh_epd_a, args.fresh_epd_b):
        boards_all = read_epd(path)
        overlap = {position_key(b) for b in boards_all} & prior
        boards = [
            b for b in boards_all
            if position_key(b) not in prior
        ]
        if len(boards) < 200:
            raise AssertionError(("fresh target too small", len(boards)))
        cross = {position_key(b) for b in boards} & target_keys
        if cross:
            raise AssertionError(("fresh targets overlap", len(cross)))
        target_keys.update(position_key(b) for b in boards)
        target_sets.append(boards)
        overlaps.append(len(overlap))

    engine = UCIStockfish(args.stockfish)
    try:
        source_a = evaluate(
            engine, guard, v31_a, authority=True
        )
        source_b = evaluate(
            engine, guard, v31_b, authority=True
        )

        # The exposed V31 source had exactly one wrong window decision total.
        source_wrong = source_a["wrong"] + source_b["wrong"]
        # With stability added, that residual must disappear.
        if source_wrong != 0:
            raise AssertionError(
                ("stability did not close V31 source residual", source_wrong)
            )
        if source_a["accepted"] + source_b["accepted"] < 20:
            raise AssertionError("stability guard collapsed source support")

        targets = [
            evaluate(engine, guard, boards, authority=True)
            for boards in target_sets
        ]
    finally:
        engine.quit()

    combined_positions = sum(r["positions"] for r in targets)
    combined_accepted = sum(r["accepted"] for r in targets)
    combined_wrong = sum(r["wrong"] for r in targets)
    combined_baseline = sum(r["baseline_nodes"] for r in targets)
    combined_hybrid = sum(r["hybrid_nodes"] for r in targets)
    combined_reduction = (
        1.0 - combined_hybrid / combined_baseline
        if combined_baseline else 0.0
    )

    green = (
        all(r["accepted"] > 0 for r in targets)
        and combined_wrong == 0
        and all(
            r["estimated_node_reduction_ratio"] > 0
            for r in targets
        )
        and combined_reduction > 0
    )
    status = (
        "WARRANTED_REPLICATED_NORMAL_SEARCH_CONTINUATION_STABILITY"
        if green else
        "FRESH_NORMAL_SEARCH_CONTINUATION_STABILITY_RESIDUAL"
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
            "v31": V31_RUN,
        },
        "frozen_contract": {
            "v25_guard_sha256": sha,
            "reply_score1_probe2_lower_exclusive": LOWER_EXCLUSIVE,
            "reply_score1_probe2_upper_exclusive": UPPER_EXCLUSIVE,
            "reply_depth_probe2_excluded": EXCLUDED_DEPTH,
            "reply_best_stable_required": True,
        },
        "source_reclosure": {
            "seed_20261003": source_a,
            "seed_20261004": source_b,
            "total_retained": source_a["accepted"] + source_b["accepted"],
            "total_wrong": source_wrong,
        },
        "targets": [
            {
                "seed": FRESH_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                "source_overlap_removed_before_search": overlaps[i],
                **targets[i],
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
                "reply stability is the only distinction added after V31",
                "the exact exposed V31 false positive is removed with zero retained V31 source errors",
                "both new target seeds are frozen and source-disjoint before 100k authority search",
                "every prospectively accepted shortcut on both targets equals pinned 100k Stockfish",
                "both targets retain positive net node reduction after charging the conditional continuation probe",
            ],
            "unknown": [
                "real UCI wall-clock gain",
                "self-play Elo gain",
                "transfer to unrelated opening generators",
                "chess-theoretic optimality of Stockfish authority",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print(f"CRYSTAL_CHESS_SEARCH_CONTINUATION_STABILITY_V32={status}")
    print(
        f"source retained={result['source_reclosure']['total_retained']} "
        f"wrong={source_wrong}"
    )
    for seed, row in zip(FRESH_SEEDS, targets):
        print(
            f"seed={seed} positions={row['positions']} "
            f"v25={row['v25_guard_fires']} window={row['window_accepts']} "
            f"unstable_rejects={row['unstable_rejects']} "
            f"accepted={row['accepted']} wrong={row['wrong']} "
            f"coverage={row['coverage_ratio']:.8f} "
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
