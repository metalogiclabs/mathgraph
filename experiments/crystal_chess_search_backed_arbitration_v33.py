#!/usr/bin/env python3
"""Crystal Chess V33: semantic backed-up capability arbitration.

V32 proves that a stable single candidate continuation is not sufficient.
V33 tests the programme's intended arbitration object directly:

    candidate continuation value >= nearest root alternative continuation value

where both values are independently backed up through the opponent's cheap
1k -> TT-reused 4k continuation.

No threshold is learned.  Two semantic variants are declared before source
replay:
  A. candidate is no worse at the 4k backed-up comparison;
  B. candidate is no worse at both 1k and 4k comparisons.

The weakest variant that closes all already-exposed parent false positives with
nontrivial retained support is frozen before two new normal-opening seeds are
queried at 100k nodes.

Parent contract is frozen V32:
* frozen V25 root guard;
* -175 < reply_score1_probe2 < 455;
* reply_depth_probe2 != 6;
* reply_best_stable == 1.

This is behavioral substitution relative to pinned Stockfish, not a proof of
chess-theoretic optimality.
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
    collect_records,
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
from crystal_chess_search_relative_continuation_v30 import (
    root_alternative,
    relation_features,
)


SCHEMA = "mathgraph.crystal-chess.search-backed-arbitration.v33"
V22_RUN = 36361812786
V25_RUN = 36362896141
V28_RUN = 36368371744
V29_RUN = 36368824668
V30_RUN = 36385064153
V31_RUN = 36385673166
V32_RUN = 36386326389
FRESH_SEEDS = (20261007, 20261008)

SEMANTIC_VARIANTS = (
    "probe2_nonworse",
    "both_nonworse",
)


def parent_accepts(
    names: list[str],
    feats: tuple[int, ...],
) -> bool:
    idx = {name: i for i, name in enumerate(names)}
    score = int(feats[idx["reply_score1_probe2"]])
    depth = int(feats[idx["reply_depth_probe2"]])
    stable = int(feats[idx["reply_best_stable"]])
    return (
        LOWER_EXCLUSIVE < score < UPPER_EXCLUSIVE
        and depth != EXCLUDED_DEPTH
        and stable == 1
    )


def relation_accepts(
    variant: str,
    names: list[str],
    feats: tuple[int, ...],
) -> bool:
    idx = {name: i for i, name in enumerate(names)}
    d1 = int(feats[idx["backed_delta_probe1"]])
    d2 = int(feats[idx["backed_delta_probe2"]])
    if variant == "probe2_nonworse":
        return d2 >= 0
    if variant == "both_nonworse":
        return d1 >= 0 and d2 >= 0
    raise ValueError(variant)


def source_keyset(
    v22_pgn: Path,
    epds: list[Path],
) -> set[tuple[str, bool, str, int | None]]:
    splits = extract_positions(v22_pgn, 220)
    keys = {
        position_key(board)
        for boards in splits.values()
        for board in boards
    }
    for path in epds:
        keys.update(position_key(b) for b in read_epd(path))
    return keys


def source_rows(
    engine: UCIStockfish,
    guard: dict[str, Any],
    v22_pgn: Path,
    generations: list[tuple[str, Path]],
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    relation_names: list[str] | None = None

    # V22 keeps its already-protected 100k labels.
    splits = extract_positions(v22_pgn, 220)
    for split in ("train", "validation", "holdout"):
        records, _ = collect_records(engine, splits[split])
        for rec in records:
            board = chess.Board(rec["fen"])
            p1, p2 = rec["probe1"], rec["probe2"]
            fires, _ = guard_fires(guard, board, p1, p2)
            if not fires:
                continue
            cnames, cfeats, _ = continuation_features(
                engine, board, str(p2["bestmove"])
            )
            if not parent_accepts(cnames, cfeats):
                continue
            alt = root_alternative(p2)
            if alt is None:
                continue
            rnames, rfeats, rmeta = relation_features(
                engine, board, str(p2["bestmove"]), alt
            )
            if relation_names is None:
                relation_names = rnames
            elif relation_names != rnames:
                raise AssertionError("source relation feature drift")
            rows.append({
                "generation": "v22",
                "fen": rec["fen"],
                "candidate": str(p2["bestmove"]),
                "alternative": alt,
                "relation_features": rfeats,
                "relation_meta": rmeta,
                "authority": str(rec["authority_bestmove"]),
                "match": bool(rec["match"]),
            })

    # All later exposed targets are now source evidence.
    for generation, path in generations:
        for board in read_epd(path):
            fen = board.fen()
            p1, p2 = base_probes(engine, fen)
            fires, _ = guard_fires(guard, board, p1, p2)
            if not fires:
                continue
            cnames, cfeats, _ = continuation_features(
                engine, board, str(p2["bestmove"])
            )
            if not parent_accepts(cnames, cfeats):
                continue
            alt = root_alternative(p2)
            if alt is None:
                continue
            rnames, rfeats, rmeta = relation_features(
                engine, board, str(p2["bestmove"]), alt
            )
            if relation_names is None:
                relation_names = rnames
            elif relation_names != rnames:
                raise AssertionError("source relation feature drift")
            auth = engine.search(
                fen, AUTHORITY_NODES, multipv=1, clear=True
            )
            rows.append({
                "generation": generation,
                "fen": fen,
                "candidate": str(p2["bestmove"]),
                "alternative": alt,
                "relation_features": rfeats,
                "relation_meta": rmeta,
                "authority": str(auth["bestmove"]),
                "match": str(p2["bestmove"]) == str(auth["bestmove"]),
            })

    return rows, relation_names or []


def choose_semantic_variant(
    rows: list[dict[str, Any]],
    names: list[str],
) -> tuple[str | None, dict[str, Any]]:
    diagnostics: dict[str, Any] = {}
    for variant in SEMANTIC_VARIANTS:
        kept = [
            row for row in rows
            if relation_accepts(
                variant, names, tuple(row["relation_features"])
            )
        ]
        wrong = sum(not bool(row["match"]) for row in kept)
        support = Counter(str(r["generation"]) for r in kept)
        diagnostics[variant] = {
            "accepted": len(kept),
            "wrong": wrong,
            "support": dict(support),
            "retention_ratio": len(kept) / len(rows) if rows else 0.0,
        }
        if (
            len(kept) >= 20
            and wrong == 0
            and len(support) >= 3
        ):
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
        if not relation_accepts(variant, rnames, rfeats):
            continue

        accepted += 1
        auth = engine.search(
            fen, AUTHORITY_NODES, multipv=1, clear=True
        )
        ok = str(p2["bestmove"]) == str(auth["bestmove"])
        wrong += int(not ok)
        if len(examples) < 30:
            idx = {name: i for i, name in enumerate(rnames)}
            examples.append({
                "fen": fen,
                "leaf": leaf,
                "candidate": str(p2["bestmove"]),
                "alternative": alt,
                "authority": str(auth["bestmove"]),
                "match": ok,
                "backed_delta_probe1": int(
                    rfeats[idx["backed_delta_probe1"]]
                ),
                "backed_delta_probe2": int(
                    rfeats[idx["backed_delta_probe2"]]
                ),
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

    source_generations = list(
        zip(args.source_generation, args.source_epd)
    )
    prior_keys = source_keyset(
        args.v22_pgn,
        list(args.source_epd),
    )

    manifests = [
        json.loads(args.fresh_manifest_a.read_text()),
        json.loads(args.fresh_manifest_b.read_text()),
    ]
    if tuple(int(m["seed"]) for m in manifests) != FRESH_SEEDS:
        raise AssertionError(
            ("fresh seed drift", [m["seed"] for m in manifests])
        )

    target_sets: list[list[chess.Board]] = []
    source_overlaps: list[int] = []
    cross_overlaps: list[int] = []
    target_keys: set[tuple[str, bool, str, int | None]] = set()
    for path in (args.fresh_epd_a, args.fresh_epd_b):
        all_boards = read_epd(path)
        source_overlap = {
            position_key(b) for b in all_boards
        } & prior_keys
        boards = [
            b for b in all_boards
            if position_key(b) not in prior_keys
        ]
        cross = {
            position_key(b) for b in boards
        } & target_keys
        if cross:
            boards = [
                b for b in boards
                if position_key(b) not in target_keys
            ]
        if len(boards) < 200:
            raise AssertionError(("fresh target too small", len(boards)))
        target_keys.update(position_key(b) for b in boards)
        target_sets.append(boards)
        source_overlaps.append(len(source_overlap))
        cross_overlaps.append(len(cross))

    engine = UCIStockfish(args.stockfish)
    try:
        rows, relation_names = source_rows(
            engine,
            guard,
            args.v22_pgn,
            source_generations,
        )
        source_wrong = sum(not bool(r["match"]) for r in rows)
        if source_wrong < 1:
            raise AssertionError(
                ("expected exposed parent residuals", len(rows), source_wrong)
            )

        variant, diagnostics = choose_semantic_variant(
            rows, relation_names
        )
        if variant is None:
            result = {
                "schema": SCHEMA,
                "status": "BACKED_ARBITRATION_DOES_NOT_CLOSE_EXPOSED_RESIDUALS",
                "source_states": len(rows),
                "source_wrong": source_wrong,
                "diagnostics": diagnostics,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, sort_keys=True, indent=2) + "\n"
            )
            print(
                "CRYSTAL_CHESS_SEARCH_BACKED_ARBITRATION_V33="
                "BACKED_ARBITRATION_DOES_NOT_CLOSE_EXPOSED_RESIDUALS"
            )
            print(
                f"source states={len(rows)} wrong={source_wrong} "
                f"diagnostics={diagnostics}"
            )
            print(f"artifact={args.output}")
            return 0

        targets = [
            evaluate_target(
                engine,
                guard,
                boards,
                variant,
                relation_names,
            )
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
    )
    status = (
        "WARRANTED_REPLICATED_NORMAL_SEARCH_BACKED_ARBITRATION"
        if green else
        "FRESH_NORMAL_SEARCH_BACKED_ARBITRATION_RESIDUAL"
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
            "v32": V32_RUN,
        },
        "frozen_parent": {
            "v25_guard_sha256": sha,
            "reply_score_window": [
                LOWER_EXCLUSIVE,
                UPPER_EXCLUSIVE,
            ],
            "reply_depth_excluded": EXCLUDED_DEPTH,
            "reply_best_stable": True,
        },
        "source": {
            "states": len(rows),
            "wrong": source_wrong,
            "generation_counts": dict(
                Counter(str(r["generation"]) for r in rows)
            ),
            "semantic_variant_diagnostics": diagnostics,
            "selected_variant": variant,
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
                "only two predeclared backed-up capability-arbitration relations are considered",
                "the weakest relation that closes every exposed parent false positive with nontrivial multi-generation support is frozen before fresh authority search",
                "fresh seeds are disjoint from all exposed source states and from each other before authority search",
                "every fresh accepted shortcut equals pinned 100k Stockfish",
                "both fresh targets retain positive node savings after charging root and both child continuation probes",
            ],
            "unknown": [
                "real UCI wall-clock gain",
                "self-play Elo gain",
                "transfer across another opening-generation protocol",
                "chess-theoretic optimality of Stockfish authority",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print(f"CRYSTAL_CHESS_SEARCH_BACKED_ARBITRATION_V33={status}")
    print(
        f"source states={len(rows)} wrong={source_wrong} "
        f"selected={variant} diagnostics={diagnostics}"
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
