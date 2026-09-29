#!/usr/bin/env python3
"""Crystal Chess V34: robust backed-value interval dominance.

V33 rejects pointwise "candidate no worse than alternative" arbitration:
one exposed false positive survives both the 4k-only and both-probe variants.

V34 adds no learned threshold.  It tests a predeclared semantic family:
treat the two cheap backed evaluations of each root move as an uncertainty
interval, and admit a shortcut only when the candidate's worst observed
backed value is no worse than the alternative's best observed backed value.

Increasingly conservative variants additionally require the root best move,
then the whole root top-two ordering, to be stable across the 1k -> TT-reused
4k probes.  The weakest source-exact variant is frozen before any fresh 100k
authority query on seeds 20261009 and 20261010.

Pinned Stockfish remains the authority/fallback.  This is behavioral search
substitution, not a claim of chess-theoretic optimality.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

import chess

from crystal_chess_search_sufficiency_v25 import (
    AUTHORITY_NODES,
    PROBE_TOTAL_NODES,
    STOCKFISH_PIN,
    UCIStockfish,
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
from crystal_chess_search_relative_continuation_v30 import (
    relation_features,
    root_alternative,
)
from crystal_chess_search_backed_arbitration_v33 import (
    parent_accepts,
    source_keyset,
    source_rows,
)

SCHEMA = "mathgraph.crystal-chess.search-robust-dominance.v34"
V22_RUN = 36361812786
V25_RUN = 36362896141
V28_RUN = 36368371744
V29_RUN = 36368824668
V30_RUN = 36385064153
V31_RUN = 36385673166
V32_RUN = 36386326389
V33_RUN = 36386803245
FRESH_SEEDS = (20261009, 20261010)

VARIANTS = (
    "interval_nonoverlap",
    "interval_nonoverlap_root_best_stable",
    "interval_nonoverlap_root_pair_stable",
    "strict_interval_root_pair_stable",
)


def annotate_root_stability(
    engine: UCIStockfish,
    row: dict[str, Any],
) -> None:
    p1, p2 = base_probes(engine, str(row["fen"]))
    a1 = root_alternative(p1)
    a2 = root_alternative(p2)
    row["root_best_stable"] = str(p1["bestmove"]) == str(p2["bestmove"])
    row["root_pair_stable"] = (
        bool(row["root_best_stable"])
        and a1 is not None
        and a2 is not None
        and a1 == a2
    )


def robust_values(row: dict[str, Any]) -> dict[str, int]:
    m = row["relation_meta"]
    c1 = int(m["backed_candidate_probe1"])
    c2 = int(m["backed_candidate_probe2"])
    a1 = int(m["backed_alternative_probe1"])
    a2 = int(m["backed_alternative_probe2"])
    return {
        "candidate_low": min(c1, c2),
        "candidate_high": max(c1, c2),
        "alternative_low": min(a1, a2),
        "alternative_high": max(a1, a2),
        "robust_gap": min(c1, c2) - max(a1, a2),
    }


def variant_accepts(variant: str, row: dict[str, Any]) -> bool:
    v = robust_values(row)
    nonoverlap = v["candidate_low"] >= v["alternative_high"]
    strict = v["candidate_low"] > v["alternative_high"]
    if variant == "interval_nonoverlap":
        return nonoverlap
    if variant == "interval_nonoverlap_root_best_stable":
        return nonoverlap and bool(row["root_best_stable"])
    if variant == "interval_nonoverlap_root_pair_stable":
        return nonoverlap and bool(row["root_pair_stable"])
    if variant == "strict_interval_root_pair_stable":
        return strict and bool(row["root_pair_stable"])
    raise ValueError(variant)


def choose_variant(rows: list[dict[str, Any]]) -> tuple[str | None, dict[str, Any]]:
    diagnostics: dict[str, Any] = {}
    for variant in VARIANTS:
        kept = [r for r in rows if variant_accepts(variant, r)]
        wrong = sum(not bool(r["match"]) for r in kept)
        support = Counter(str(r["generation"]) for r in kept)
        diagnostics[variant] = {
            "accepted": len(kept),
            "wrong": wrong,
            "support": dict(support),
            "retention_ratio": len(kept) / len(rows) if rows else 0.0,
        }
        if len(kept) >= 20 and wrong == 0 and len(support) >= 3:
            return variant, diagnostics
    return None, diagnostics


def evaluate_target(
    engine: UCIStockfish,
    guard: dict[str, Any],
    boards: list[chess.Board],
    variant: str,
    relation_names_ref: list[str],
) -> dict[str, Any]:
    v25_fires = parent = no_alt = accepted = wrong = 0
    examples: list[dict[str, Any]] = []

    for board in boards:
        fen = board.fen()
        p1, p2 = base_probes(engine, fen)
        fires, leaf = guard_fires(guard, board, p1, p2)
        if not fires:
            continue
        v25_fires += 1

        cnames, cfeats, cmeta = continuation_features(
            engine, board, str(p2["bestmove"])
        )
        if not parent_accepts(cnames, cfeats):
            continue
        parent += 1

        alt = root_alternative(p2)
        if alt is None:
            no_alt += 1
            continue

        rnames, rfeats, rmeta = relation_features(
            engine, board, str(p2["bestmove"]), alt
        )
        if rnames != relation_names_ref:
            raise AssertionError("fresh relation feature drift")

        row = {
            "fen": fen,
            "candidate": str(p2["bestmove"]),
            "alternative": alt,
            "relation_features": rfeats,
            "relation_meta": rmeta,
            "root_best_stable": str(p1["bestmove"]) == str(p2["bestmove"]),
            "root_pair_stable": (
                str(p1["bestmove"]) == str(p2["bestmove"])
                and root_alternative(p1) is not None
                and root_alternative(p1) == alt
            ),
        }
        if not variant_accepts(variant, row):
            continue

        accepted += 1
        auth = engine.search(fen, AUTHORITY_NODES, multipv=1, clear=True)
        ok = str(p2["bestmove"]) == str(auth["bestmove"])
        wrong += int(not ok)
        if len(examples) < 30:
            examples.append({
                "fen": fen,
                "leaf": leaf,
                "candidate": str(p2["bestmove"]),
                "alternative": alt,
                "authority": str(auth["bestmove"]),
                "match": ok,
                "root_best_stable": row["root_best_stable"],
                "root_pair_stable": row["root_pair_stable"],
                **robust_values(row),
                "candidate_continuation": cmeta,
                "relation": rmeta,
            })

    n = len(boards)
    baseline = n * AUTHORITY_NODES
    hybrid = (
        n * PROBE_TOTAL_NODES
        + v25_fires * CHILD_PROBE_TOTAL_NODES
        + parent * CHILD_PROBE_TOTAL_NODES
        + (n - accepted) * AUTHORITY_NODES
    )
    reduction = 1.0 - hybrid / baseline if baseline else 0.0
    return {
        "positions": n,
        "v25_guard_fires": v25_fires,
        "parent_admitted": parent,
        "no_alternative": no_alt,
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

    if len(args.source_epd) != len(args.source_generation):
        raise AssertionError("source EPD/generation length mismatch")

    guard, sha = load_guard(args.guard)
    if sha != V25_GUARD_SHA256:
        raise AssertionError(("V25 guard drift", sha))

    source_generations = list(zip(args.source_generation, args.source_epd))

    engine = UCIStockfish(args.stockfish)
    try:
        rows, relation_names = source_rows(
            engine, guard, args.v22_pgn, source_generations
        )
        source_wrong = sum(not bool(r["match"]) for r in rows)
        if source_wrong != 3:
            raise AssertionError(
                ("expected V33 exposed residuals", len(rows), source_wrong)
            )
        for row in rows:
            annotate_root_stability(engine, row)

        variant, diagnostics = choose_variant(rows)
        source_bad = []
        for row in rows:
            if not bool(row["match"]):
                source_bad.append({
                    "generation": row["generation"],
                    "fen": row["fen"],
                    "candidate": row["candidate"],
                    "alternative": row["alternative"],
                    "authority": row["authority"],
                    "root_best_stable": row["root_best_stable"],
                    "root_pair_stable": row["root_pair_stable"],
                    **robust_values(row),
                    "relation_meta": row["relation_meta"],
                })

        if variant is None:
            result = {
                "schema": SCHEMA,
                "status": "ROBUST_DOMINANCE_DOES_NOT_CLOSE_EXPOSED_RESIDUALS",
                "stockfish_pin": STOCKFISH_PIN,
                "source_states": len(rows),
                "source_wrong": source_wrong,
                "diagnostics": diagnostics,
                "source_false_positives": source_bad,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, sort_keys=True, indent=2) + "\n"
            )
            print(
                "CRYSTAL_CHESS_SEARCH_ROBUST_DOMINANCE_V34="
                "ROBUST_DOMINANCE_DOES_NOT_CLOSE_EXPOSED_RESIDUALS"
            )
            print(
                f"source states={len(rows)} wrong={source_wrong} "
                f"diagnostics={diagnostics}"
            )
            print(f"artifact={args.output}")
            return 0

        # Variant is frozen before any fresh 100k authority search.
        prior_keys = source_keyset(args.v22_pgn, list(args.source_epd))
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
            source_overlap = {position_key(b) for b in all_boards} & prior_keys
            boards = [b for b in all_boards if position_key(b) not in prior_keys]
            cross = {position_key(b) for b in boards} & target_keys
            if cross:
                boards = [b for b in boards if position_key(b) not in target_keys]
            if len(boards) < 200:
                raise AssertionError(("fresh target too small", len(boards)))
            target_keys.update(position_key(b) for b in boards)
            target_sets.append(boards)
            source_overlaps.append(len(source_overlap))
            cross_overlaps.append(len(cross))

        targets = [
            evaluate_target(engine, guard, boards, variant, relation_names)
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
        and all(r["estimated_node_reduction_ratio"] > 0 for r in targets)
    )
    status = (
        "WARRANTED_REPLICATED_NORMAL_SEARCH_ROBUST_DOMINANCE"
        if green
        else "FRESH_NORMAL_SEARCH_ROBUST_DOMINANCE_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "source_runs": {
            "v22": V22_RUN, "v25": V25_RUN, "v28": V28_RUN,
            "v29": V29_RUN, "v30": V30_RUN, "v31": V31_RUN,
            "v32": V32_RUN, "v33": V33_RUN,
        },
        "source": {
            "states": len(rows),
            "wrong": source_wrong,
            "generation_counts": dict(Counter(str(r["generation"]) for r in rows)),
            "variant_diagnostics": diagnostics,
            "selected_variant": variant,
            "false_positives": source_bad,
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
                "no numerical threshold is learned from the false positives",
                "only the predeclared robust backed-value interval relations are considered",
                "the weakest source-exact relation is frozen before any fresh 100k authority query",
                "fresh seeds are disjoint from exposed source states and each other before authority search",
                "every fresh accepted shortcut equals pinned 100k Stockfish",
                "both fresh targets retain positive net node savings after all cheap probes are charged",
            ],
            "unknown": [
                "real UCI wall-clock gain on normal games",
                "self-play Elo gain",
                "transfer to another opening generator",
                "chess-theoretic optimality of Stockfish authority",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_SEARCH_ROBUST_DOMINANCE_V34={status}")
    print(
        f"source states={len(rows)} wrong={source_wrong} selected={variant} "
        f"diagnostics={diagnostics}"
    )
    for seed, row in zip(FRESH_SEEDS, targets):
        print(
            f"seed={seed} positions={row['positions']} "
            f"v25={row['v25_guard_fires']} parent={row['parent_admitted']} "
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

# workflow trigger: no semantic change
