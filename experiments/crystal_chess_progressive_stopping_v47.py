#!/usr/bin/env python3
"""Crystal Chess V47: progressive single-PV stopping.

V46 rejects any economically useful zero-miss *pre-search* escalation guard
built from the existing shallow V25 feature vocabulary.

V43-V45 independently show why: the hard cases are distinguished by the
search trajectory itself. 18/19 V42 candidate-generation misses recover below
100k under deeper/native search, and the last case appears at 96k single-PV.

V47 therefore tests a stateful controller:
    observe clean single-PV trajectories at 8k,16k,32k,64k,96k;
    stop early only when a predeclared stability condition is satisfied;
    otherwise continue to the frozen 100k authority.

No learned chess feature, score threshold, classifier, or move-set width is
introduced. Rules are purely about move/PV stability across budgets.

This is a diagnostic for an *inside-Stockfish* controller. Independent clean
searches approximate the checkpoint trajectory; a later integrated gate must
verify that observing checkpoints inside one continuous search preserves the
same decisions and compute accounting.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

import chess

from crystal_chess_search_sufficiency_v25 import (
    STOCKFISH_PIN,
    UCIStockfish,
)
from crystal_chess_normal_certificate_set_v41 import collect_boards
from crystal_chess_search_confirmation_v26 import read_epd
from crystal_chess_search_continuation_v28 import position_key

SCHEMA = "mathgraph.crystal-chess.progressive-stopping.v47"
FRESH_SEEDS = (20261027, 20261028)
BUDGETS = (8000, 16000, 32000, 64000, 96000, 100000)
AUTHORITY_BUDGET = 100000
MIN_SOURCE_REDUCTION = 0.05

RULES = (
    "last2_move",
    "last3_move",
    "all_move",
    "last2_move_pv2",
    "last3_move_pv2",
    "all_move_pv2",
    "last2_move_pv3",
    "last3_move_pv3",
    "all_move_pv3",
)


def prefix(pv: list[str], k: int) -> tuple[str, ...] | None:
    if len(pv) < k:
        return None
    return tuple(str(x) for x in pv[:k])


def stable_rule(rule: str, history: list[dict[str, Any]]) -> bool:
    if not history:
        return False

    if rule.startswith("last2_"):
        n = 2
    elif rule.startswith("last3_"):
        n = 3
    elif rule.startswith("all_"):
        n = len(history)
        if n < 2:
            return False
    else:
        raise ValueError(rule)

    if len(history) < n:
        return False
    rows = history[-n:] if not rule.startswith("all_") else history

    moves = [str(r["bestmove"]) for r in rows]
    if len(set(moves)) != 1:
        return False

    if rule.endswith("_move"):
        return True
    if rule.endswith("_move_pv2"):
        k = 2
    elif rule.endswith("_move_pv3"):
        k = 3
    else:
        raise ValueError(rule)

    pfx = [prefix(list(r["pv1"]), k) for r in rows]
    return all(x is not None for x in pfx) and len(set(pfx)) == 1


def trajectory(engine: UCIStockfish, fen: str) -> list[dict[str, Any]]:
    out = []
    for budget in BUDGETS:
        r = engine.search(fen, budget, multipv=1, clear=True)
        out.append({
            "nodes": budget,
            "bestmove": str(r["bestmove"]),
            "score1": int(r["score1"]),
            "depth": int(r["depth"]),
            "seldepth": int(r["seldepth"]),
            "pv1": list(r["pv1"][:10]),
        })
    return out


def simulate(rule: str, traj: list[dict[str, Any]]) -> dict[str, Any]:
    authority = str(traj[-1]["bestmove"])
    history: list[dict[str, Any]] = []
    stop = traj[-1]
    stopped_early = False

    for row in traj[:-1]:
        history.append(row)
        if stable_rule(rule, history):
            stop = row
            stopped_early = True
            break

    return {
        "stop_nodes": int(stop["nodes"]),
        "stop_bestmove": str(stop["bestmove"]),
        "authority_bestmove": authority,
        "match": str(stop["bestmove"]) == authority,
        "stopped_early": stopped_early,
    }


def evaluate_rule(
    rule: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    mismatch = 0
    node_sum = 0
    early = 0
    support = Counter()
    examples = []

    for row in rows:
        sim = simulate(rule, row["trajectory"])
        mismatch += int(not sim["match"])
        node_sum += int(sim["stop_nodes"])
        early += int(sim["stopped_early"])
        support[str(row["generation"])] += 1
        if not sim["match"] and len(examples) < 30:
            examples.append({
                "generation": row["generation"],
                "fen": row["fen"],
                **sim,
                "trajectory": row["trajectory"],
            })

    n = len(rows)
    mean_nodes = node_sum / n if n else AUTHORITY_BUDGET
    return {
        "positions": n,
        "mismatches": mismatch,
        "match_ratio": (n - mismatch) / n if n else 1.0,
        "early_stops": early,
        "early_stop_ratio": early / n if n else 0.0,
        "mean_nodes": mean_nodes,
        "node_reduction_ratio": 1.0 - mean_nodes / AUTHORITY_BUDGET,
        "support": dict(support),
        "mismatch_examples": examples,
    }


def choose_rule(stats: dict[str, Any]) -> str | None:
    candidates = []
    order = {name: i for i, name in enumerate(RULES)}
    for rule, st in stats.items():
        if int(st["mismatches"]) != 0:
            continue
        if float(st["node_reduction_ratio"]) < MIN_SOURCE_REDUCTION:
            continue
        candidates.append((
            float(st["mean_nodes"]),
            -float(st["early_stop_ratio"]),
            order[rule],
            rule,
        ))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][3]


def collect_trajectories(
    engine: UCIStockfish,
    items: list[tuple[str, chess.Board]],
) -> list[dict[str, Any]]:
    rows = []
    for generation, board in items:
        rows.append({
            "generation": generation,
            "fen": board.fen(),
            "trajectory": trajectory(engine, board.fen()),
        })
    return rows


def fresh_eval(
    engine: UCIStockfish,
    boards: list[chess.Board],
    rule: str,
) -> dict[str, Any]:
    rows = [
        {
            "generation": "fresh",
            "fen": b.fen(),
            "trajectory": trajectory(engine, b.fen()),
        }
        for b in boards
    ]
    st = evaluate_rule(rule, rows)
    st["examples"] = [
        {
            "fen": r["fen"],
            **simulate(rule, r["trajectory"]),
            "trajectory": r["trajectory"],
        }
        for r in rows[:30]
    ]
    return st


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--v22-pgn", type=Path, required=True)
    ap.add_argument("--source-epd", type=Path, action="append", required=True)
    ap.add_argument("--source-generation", action="append", required=True)
    ap.add_argument("--fresh-epd-a", type=Path, required=True)
    ap.add_argument("--fresh-manifest-a", type=Path, required=True)
    ap.add_argument("--fresh-epd-b", type=Path, required=True)
    ap.add_argument("--fresh-manifest-b", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    if len(args.source_epd) != len(args.source_generation):
        raise AssertionError("source EPD/generation mismatch")

    source_items = collect_boards(
        args.v22_pgn,
        list(zip(args.source_generation, args.source_epd)),
    )

    engine = UCIStockfish(args.stockfish)
    try:
        source_rows = collect_trajectories(engine, source_items)
        source_stats = {
            rule: evaluate_rule(rule, source_rows)
            for rule in RULES
        }
        selected = choose_rule(source_stats)

        if selected is None:
            result = {
                "schema": SCHEMA,
                "status": "NO_ZERO_MISS_PROGRESSIVE_STOP_RULE",
                "stockfish_pin": STOCKFISH_PIN,
                "budgets": list(BUDGETS),
                "source": {
                    "positions": len(source_rows),
                    "generation_counts": dict(
                        Counter(str(r["generation"]) for r in source_rows)
                    ),
                    "rules": source_stats,
                },
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, sort_keys=True, indent=2) + "\n"
            )
            print(
                "CRYSTAL_CHESS_PROGRESSIVE_STOPPING_V47="
                "NO_ZERO_MISS_PROGRESSIVE_STOP_RULE"
            )
            for rule, st in source_stats.items():
                print(
                    f"{rule}: mismatches={st['mismatches']} "
                    f"early={st['early_stop_ratio']:.8f} "
                    f"mean_nodes={st['mean_nodes']:.2f} "
                    f"reduction={st['node_reduction_ratio']:.8f}"
                )
            print(f"artifact={args.output}")
            return 0

        # Freeze selected rule before fresh trajectories are queried.
        manifests = [
            json.loads(args.fresh_manifest_a.read_text()),
            json.loads(args.fresh_manifest_b.read_text()),
        ]
        if tuple(int(m["seed"]) for m in manifests) != FRESH_SEEDS:
            raise AssertionError(
                ("fresh seed drift", [m["seed"] for m in manifests])
            )

        source_keys = {position_key(b) for _, b in source_items}
        targets = []
        overlap = []
        target_keys: set[tuple[str, bool, str, int | None]] = set()

        for path in (args.fresh_epd_a, args.fresh_epd_b):
            all_boards = read_epd(path)
            src_overlap = {position_key(b) for b in all_boards} & source_keys
            boards = [
                b for b in all_boards
                if position_key(b) not in source_keys
            ]
            cross = {position_key(b) for b in boards} & target_keys
            if cross:
                boards = [
                    b for b in boards
                    if position_key(b) not in target_keys
                ]
            if len(boards) < 200:
                raise AssertionError(("fresh target too small", len(boards)))
            target_keys.update(position_key(b) for b in boards)
            targets.append(fresh_eval(engine, boards, selected))
            overlap.append((len(src_overlap), len(cross)))
    finally:
        engine.quit()

    total_n = sum(int(r["positions"]) for r in targets)
    total_mismatch = sum(int(r["mismatches"]) for r in targets)
    total_nodes = sum(float(r["mean_nodes"]) * int(r["positions"]) for r in targets)
    total_early = sum(int(r["early_stops"]) for r in targets)
    mean_nodes = total_nodes / total_n if total_n else AUTHORITY_BUDGET
    reduction = 1.0 - mean_nodes / AUTHORITY_BUDGET

    green = (
        total_mismatch == 0
        and all(int(r["mismatches"]) == 0 for r in targets)
        and reduction >= MIN_SOURCE_REDUCTION
    )
    status = (
        "WARRANTED_REPLICATED_PROGRESSIVE_STOPPING_RULE"
        if green else
        "FRESH_PROGRESSIVE_STOPPING_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "budgets": list(BUDGETS),
        "authority_budget": AUTHORITY_BUDGET,
        "selected_rule": selected,
        "source": {
            "positions": len(source_rows),
            "generation_counts": dict(
                Counter(str(r["generation"]) for r in source_rows)
            ),
            "rules": source_stats,
        },
        "targets": [
            {
                "seed": FRESH_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                "source_overlap_removed_before_search": overlap[i][0],
                "earlier_target_overlap_removed_before_search": overlap[i][1],
                **targets[i],
            }
            for i in range(2)
        ],
        "combined": {
            "positions": total_n,
            "mismatches": total_mismatch,
            "match_ratio": (
                (total_n - total_mismatch) / total_n
                if total_n else 1.0
            ),
            "early_stops": total_early,
            "early_stop_ratio": (
                total_early / total_n if total_n else 0.0
            ),
            "mean_nodes": mean_nodes,
            "node_reduction_ratio": reduction,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "rule selected only from predeclared move/PV stability semantics",
                "no score threshold, classifier, or chess feature is fitted",
                "source mismatch count is zero",
                "selected rule is frozen before fresh trajectories are queried",
                "fresh stopping move equals clean 100k Stockfish on both untouched seeds",
                "mean selected clean-search budget is at least 5% below 100k",
            ],
            "unknown": [
                "whether the same checkpoint rule is valid inside one continuous Stockfish search",
                "wall-clock gain of integrated checkpointing",
                "whether saved nodes reallocated to residual positions improve Elo",
                "chess-theoretic optimality of 100k Stockfish",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print(f"CRYSTAL_CHESS_PROGRESSIVE_STOPPING_V47={status}")
    print(
        f"source positions={len(source_rows)} selected={selected} "
        f"source_mean_nodes={source_stats[selected]['mean_nodes']:.2f} "
        f"source_reduction={source_stats[selected]['node_reduction_ratio']:.8f}"
    )
    for seed, row in zip(FRESH_SEEDS, targets):
        print(
            f"seed={seed} positions={row['positions']} "
            f"mismatches={row['mismatches']} "
            f"early={row['early_stop_ratio']:.8f} "
            f"mean_nodes={row['mean_nodes']:.2f} "
            f"reduction={row['node_reduction_ratio']:.8f}"
        )
    print(
        f"combined mismatches={total_mismatch}/{total_n} "
        f"early={result['combined']['early_stop_ratio']:.8f} "
        f"mean_nodes={mean_nodes:.2f} reduction={reduction:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
