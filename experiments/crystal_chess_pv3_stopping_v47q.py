#!/usr/bin/env python3
"""Crystal Chess V47Q: hard-earned PV3 progressive stopping qualifier.

V47H isolates the strongest cheap semantic rule that survives all 19 known
hard candidate-generation residuals:

    stop when two consecutive clean single-PV checkpoints agree on
    (bestmove, first three PV moves).

On the adversarial 19-state residual this rule has 0 errors and 7.37% mean
budget reduction. V47Q now qualifies ONLY this earned rule on the full exposed
source corpus and two untouched normal-opening seeds.

Execution is optimized for qualification: once the rule fires, intermediate
budgets are skipped and a clean 100k authority search is run for verification.
If it never fires before 100k, authority is the decision.

This still measures the counterfactual minimum sufficient node budget, not yet
a production continuous-search implementation. A later UCI checkpoint gate
must prove the same rule inside one uninterrupted Stockfish search.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

import chess

from crystal_chess_search_sufficiency_v25 import STOCKFISH_PIN, UCIStockfish
from crystal_chess_normal_certificate_set_v41 import collect_boards
from crystal_chess_search_confirmation_v26 import read_epd
from crystal_chess_search_continuation_v28 import position_key

SCHEMA = "mathgraph.crystal-chess.pv3-stopping.v47q"
V47H_RUN = 36524410004
FRESH_SEEDS = (20261029, 20261030)
CHECKPOINTS = (8000, 16000, 32000, 64000, 96000)
AUTHORITY = 100000
MIN_REDUCTION = 0.05


def pv3(row: dict[str, Any]) -> tuple[str, ...] | None:
    pv = list(row.get("pv1") or [])
    if len(pv) < 3:
        return None
    return tuple(str(x) for x in pv[:3])


def probe(engine: UCIStockfish, fen: str, nodes: int) -> dict[str, Any]:
    r = engine.search(fen, nodes, multipv=1, clear=True)
    return {
        "nodes": nodes,
        "bestmove": str(r["bestmove"]),
        "pv1": list(r["pv1"][:8]),
        "score1": int(r["score1"]),
        "depth": int(r["depth"]),
        "seldepth": int(r["seldepth"]),
    }


def qualify_position(engine: UCIStockfish, board: chess.Board) -> dict[str, Any]:
    fen = board.fen()
    prev = None
    stopped = None
    trajectory = []

    for nodes in CHECKPOINTS:
        row = probe(engine, fen, nodes)
        trajectory.append(row)
        if prev is not None:
            pprev = pv3(prev)
            pnow = pv3(row)
            if (
                str(prev["bestmove"]) == str(row["bestmove"])
                and pprev is not None
                and pnow is not None
                and pprev == pnow
            ):
                stopped = row
                break
        prev = row

    authority = probe(engine, fen, AUTHORITY)

    if stopped is None:
        decision = authority
        stop_nodes = AUTHORITY
        stopped_early = False
    else:
        decision = stopped
        stop_nodes = int(stopped["nodes"])
        stopped_early = True

    return {
        "fen": fen,
        "decision": str(decision["bestmove"]),
        "authority": str(authority["bestmove"]),
        "match": str(decision["bestmove"]) == str(authority["bestmove"]),
        "stop_nodes": stop_nodes,
        "stopped_early": stopped_early,
        "trajectory": trajectory,
        "authority_probe": authority,
    }


def evaluate(
    engine: UCIStockfish,
    items: list[tuple[str, chess.Board]],
) -> dict[str, Any]:
    n = mismatch = early = nodes = 0
    support = Counter()
    mismatches = []
    stop_dist = Counter()

    for generation, board in items:
        row = qualify_position(engine, board)
        n += 1
        mismatch += int(not bool(row["match"]))
        early += int(bool(row["stopped_early"]))
        nodes += int(row["stop_nodes"])
        stop_dist[str(row["stop_nodes"])] += 1
        support[generation] += 1
        if not row["match"] and len(mismatches) < 40:
            mismatches.append({"generation": generation, **row})

    mean_nodes = nodes / n if n else AUTHORITY
    return {
        "positions": n,
        "mismatches": mismatch,
        "match_ratio": (n - mismatch) / n if n else 1.0,
        "early_stops": early,
        "early_stop_ratio": early / n if n else 0.0,
        "mean_nodes": mean_nodes,
        "node_reduction_ratio": 1.0 - mean_nodes / AUTHORITY,
        "stop_distribution": dict(stop_dist),
        "support": dict(support),
        "mismatch_examples": mismatches,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--v47h-result", type=Path, required=True)
    ap.add_argument("--v22-pgn", type=Path, required=True)
    ap.add_argument("--source-epd", type=Path, action="append", required=True)
    ap.add_argument("--source-generation", action="append", required=True)
    ap.add_argument("--fresh-epd-a", type=Path, required=True)
    ap.add_argument("--fresh-manifest-a", type=Path, required=True)
    ap.add_argument("--fresh-epd-b", type=Path, required=True)
    ap.add_argument("--fresh-manifest-b", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    v47h = json.loads(args.v47h_result.read_text())
    if v47h.get("schema") != "mathgraph.crystal-chess.progressive-hard-falsifier.v47h":
        raise AssertionError(("V47H schema drift", v47h.get("schema")))
    if "last2_move_pv3" not in set(v47h.get("surviving_zero_mismatch_rules", [])):
        raise AssertionError("earned PV3 rule no longer survives V47H")
    if int(v47h["rules"]["last2_move_pv3"]["mismatches"]) != 0:
        raise AssertionError("V47H PV3 mismatch drift")

    if len(args.source_epd) != len(args.source_generation):
        raise AssertionError("source EPD/generation mismatch")

    source_items = collect_boards(
        args.v22_pgn,
        list(zip(args.source_generation, args.source_epd)),
    )

    engine = UCIStockfish(args.stockfish)
    try:
        source = evaluate(engine, source_items)

        if (
            int(source["mismatches"]) != 0
            or float(source["node_reduction_ratio"]) < MIN_REDUCTION
        ):
            result = {
                "schema": SCHEMA,
                "status": "PV3_STOPPING_DOES_NOT_CLOSE_SOURCE",
                "stockfish_pin": STOCKFISH_PIN,
                "v47h_run": V47H_RUN,
                "source": source,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
            print("CRYSTAL_CHESS_PV3_STOPPING_V47Q=PV3_STOPPING_DOES_NOT_CLOSE_SOURCE")
            print(
                f"source positions={source['positions']} "
                f"mismatches={source['mismatches']} "
                f"early={source['early_stop_ratio']:.8f} "
                f"mean_nodes={source['mean_nodes']:.2f} "
                f"reduction={source['node_reduction_ratio']:.8f}"
            )
            print(f"artifact={args.output}")
            return 0

        # Freeze here before fresh search.
        manifests = [
            json.loads(args.fresh_manifest_a.read_text()),
            json.loads(args.fresh_manifest_b.read_text()),
        ]
        if tuple(int(m["seed"]) for m in manifests) != FRESH_SEEDS:
            raise AssertionError(("fresh seed drift", [m["seed"] for m in manifests]))

        source_keys = {position_key(b) for _, b in source_items}
        target_sets = []
        overlap = []
        target_keys: set[tuple[str, bool, str, int | None]] = set()
        for path in (args.fresh_epd_a, args.fresh_epd_b):
            all_boards = read_epd(path)
            src_overlap = {position_key(b) for b in all_boards} & source_keys
            boards = [b for b in all_boards if position_key(b) not in source_keys]
            cross = {position_key(b) for b in boards} & target_keys
            if cross:
                boards = [b for b in boards if position_key(b) not in target_keys]
            if len(boards) < 200:
                raise AssertionError(("fresh target too small", len(boards)))
            target_keys.update(position_key(b) for b in boards)
            target_sets.append(boards)
            overlap.append((len(src_overlap), len(cross)))

        fresh = [
            evaluate(engine, [("fresh", b) for b in boards])
            for boards in target_sets
        ]
    finally:
        engine.quit()

    total_n = sum(int(r["positions"]) for r in fresh)
    total_mismatch = sum(int(r["mismatches"]) for r in fresh)
    total_nodes = sum(float(r["mean_nodes"]) * int(r["positions"]) for r in fresh)
    total_early = sum(int(r["early_stops"]) for r in fresh)
    mean_nodes = total_nodes / total_n
    reduction = 1.0 - mean_nodes / AUTHORITY

    green = (
        total_mismatch == 0
        and all(int(r["mismatches"]) == 0 for r in fresh)
        and reduction >= MIN_REDUCTION
    )
    status = (
        "WARRANTED_REPLICATED_PV3_PROGRESSIVE_STOPPING"
        if green else
        "FRESH_PV3_PROGRESSIVE_STOPPING_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v47h_run": V47H_RUN,
        "rule": "last2_move_pv3",
        "checkpoints": list(CHECKPOINTS),
        "authority_budget": AUTHORITY,
        "source": source,
        "targets": [
            {
                "seed": FRESH_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                "source_overlap_removed_before_search": overlap[i][0],
                "earlier_target_overlap_removed_before_search": overlap[i][1],
                **fresh[i],
            }
            for i in range(2)
        ],
        "combined": {
            "positions": total_n,
            "mismatches": total_mismatch,
            "match_ratio": (total_n - total_mismatch) / total_n,
            "early_stops": total_early,
            "early_stop_ratio": total_early / total_n,
            "mean_nodes": mean_nodes,
            "node_reduction_ratio": reduction,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "rule is earned solely by zero-error survival on the exact V42 hard residual",
                "full exposed source replay has zero bestmove mismatches versus clean 100k authority",
                "rule is frozen before untouched seeds 20261029/30",
                "both fresh targets have zero mismatches and positive >=5% mean budget reduction",
            ],
            "unknown": [
                "equivalence of independent clean checkpoint searches to one continuous Stockfish search",
                "actual wall-clock savings under UCI stop control",
                "benefit from reallocating saved nodes to hard positions",
                "self-play Elo gain",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_PV3_STOPPING_V47Q={status}")
    print(
        f"source positions={source['positions']} mismatches={source['mismatches']} "
        f"early={source['early_stop_ratio']:.8f} "
        f"mean_nodes={source['mean_nodes']:.2f} "
        f"reduction={source['node_reduction_ratio']:.8f}"
    )
    for seed, row in zip(FRESH_SEEDS, fresh):
        print(
            f"seed={seed} positions={row['positions']} "
            f"mismatches={row['mismatches']} "
            f"early={row['early_stop_ratio']:.8f} "
            f"mean_nodes={row['mean_nodes']:.2f} "
            f"reduction={row['node_reduction_ratio']:.8f}"
        )
    print(
        f"combined mismatches={total_mismatch}/{total_n} "
        f"early={total_early/total_n:.8f} "
        f"mean_nodes={mean_nodes:.2f} reduction={reduction:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
