#!/usr/bin/env python3
"""Crystal Chess V27: one-feature residual separator for normal search sufficiency.

Parent V25 found a zero-error validation guard but exactly one false positive on
its prospective holdout. V26 showed that simply extending search to 8k/16k/32k
does not recover the 100k authority move.

V27 therefore follows the Crystal rule literally:

1. freeze the V25 guard unchanged;
2. reopen ONLY the states inside its safe leaf on the now-exposed V22/V25
   source corpus;
3. let the single exact false positive earn the smallest one-feature
   structural separator using only existing V25 observables;
4. freeze that separator;
5. open the untouched fresh V26 normal-book target (seed 20260929), where no
   100k authority search has yet been run;
6. promote only if every accepted fresh shortcut matches pinned 100k
   Stockfish and the 5k-probe hybrid has positive net node reduction.

This is behavioral search substitution relative to pinned Stockfish, not a
proof of chess-theoretic optimality.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

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
    FRESH_SEED,
    V25_GUARD_SHA256,
    base_probes,
    guard_fires,
    load_guard,
    read_epd,
)


SCHEMA = "mathgraph.crystal-chess.search-residual-separator.v27"
V25_RUN = 36362896141
V26_RUN = 36367418497
V22_RUN = 36361812786
V26_BOOK_SHA256 = "6968d92eb607df0bba90f6b4c4890237629afdf574c419487900205e030b7106"
MIN_SOURCE_SUPPORT = 12
MIN_SOURCE_SPLITS = 2


def position_key(board: chess.Board) -> tuple[str, bool, str, int | None]:
    return (
        board.board_fen(),
        board.turn,
        board.castling_xfen(),
        board.ep_square,
    )


def predicate_eval(spec: dict[str, Any], value: int) -> bool:
    op = spec["op"]
    ref = int(spec["value"])
    if op == "lt":
        return value < ref
    if op == "gt":
        return value > ref
    if op == "ne":
        return value != ref
    raise ValueError(op)


def find_separator(
    covered: list[dict[str, Any]],
    feature_names: list[str],
) -> dict[str, Any] | None:
    failures = [row for row in covered if not row["match"]]
    if len(failures) != 1:
        raise AssertionError(("expected exactly one parent residual", len(failures)))
    fail = failures[0]
    fvals = tuple(int(x) for x in fail["features"])

    candidates: list[dict[str, Any]] = []
    for j, name in enumerate(feature_names):
        vals = [int(row["features"][j]) for row in covered]
        fv = fvals[j]

        specs: list[dict[str, Any]] = [
            {"feature": j, "feature_name": name, "op": "lt", "value": fv},
            {"feature": j, "feature_name": name, "op": "gt", "value": fv},
        ]
        # Exact inequality is permitted only for genuinely low-cardinality
        # structural coordinates, not scores/depth-like quasi-continuous data.
        unique = sorted(set(vals))
        if len(unique) <= 8:
            specs.append(
                {"feature": j, "feature_name": name, "op": "ne", "value": fv}
            )

        for spec in specs:
            kept = [
                row
                for row in covered
                if predicate_eval(spec, int(row["features"][j]))
            ]
            if not kept:
                continue
            wrong = sum(not row["match"] for row in kept)
            splits = sorted({str(row["split"]) for row in kept})
            support = len(kept)
            if wrong != 0:
                continue
            if support < MIN_SOURCE_SUPPORT or len(splits) < MIN_SOURCE_SPLITS:
                continue
            candidates.append(
                {
                    **spec,
                    "source_support": support,
                    "source_split_count": len(splits),
                    "source_splits": splits,
                    "source_retention_ratio": support / len(covered),
                }
            )

    if not candidates:
        return None

    # Maximize retained proven-correct parent coverage. Then prefer a separator
    # supported in more historical splits, then threshold predicates over
    # exact inequality, then stable lexical feature identity.
    op_rank = {"lt": 0, "gt": 0, "ne": 1}
    candidates.sort(
        key=lambda c: (
            -int(c["source_support"]),
            -int(c["source_split_count"]),
            op_rank[str(c["op"])],
            str(c["feature_name"]),
            int(c["value"]),
        )
    )
    return candidates[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--source-pgn", type=Path, required=True)
    ap.add_argument("--fresh-epd", type=Path, required=True)
    ap.add_argument("--fresh-manifest", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    guard, guard_sha = load_guard(args.guard)
    if guard_sha != V25_GUARD_SHA256:
        raise AssertionError(("V25 guard digest drift", guard_sha))

    manifest = json.loads(args.fresh_manifest.read_text(encoding="utf-8"))
    if int(manifest["seed"]) != FRESH_SEED:
        raise AssertionError(("fresh seed drift", manifest["seed"]))
    if manifest["book_sha256"] != V26_BOOK_SHA256:
        raise AssertionError(("fresh book authority drift", manifest["book_sha256"]))

    source_splits = extract_positions(args.source_pgn, 220)
    engine = UCIStockfish(args.stockfish)
    try:
        source_records: list[dict[str, Any]] = []
        feature_names: list[str] | None = None
        for split in ("train", "validation", "holdout"):
            recs, names = collect_records(engine, source_splits[split])
            if feature_names is None:
                feature_names = names
            elif feature_names != names:
                raise AssertionError("source feature order drift")
            for rec in recs:
                rec = dict(rec)
                rec["split"] = split
                source_records.append(rec)

        covered: list[dict[str, Any]] = []
        for rec in source_records:
            board = chess.Board(rec["fen"])
            fires, leaf = guard_fires(
                guard, board, rec["probe1"], rec["probe2"]
            )
            if fires:
                row = dict(rec)
                row["leaf"] = leaf
                covered.append(row)

        parent_wrong = sum(not row["match"] for row in covered)
        if parent_wrong != 1:
            raise AssertionError(
                ("V25 parent residual count drift", len(covered), parent_wrong)
            )

        separator = find_separator(covered, feature_names or [])
        if separator is None:
            result = {
                "schema": SCHEMA,
                "status": "NO_ONE_FEATURE_SOURCE_RESIDUAL_SEPARATOR",
                "stockfish_pin": STOCKFISH_PIN,
                "v25_run": V25_RUN,
                "v26_run": V26_RUN,
                "source_parent_covered": len(covered),
                "source_parent_wrong": parent_wrong,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, sort_keys=True, indent=2) + "\n"
            )
            print(
                "CRYSTAL_CHESS_SEARCH_RESIDUAL_SEPARATOR_V27="
                "NO_ONE_FEATURE_SOURCE_RESIDUAL_SEPARATOR"
            )
            print(f"artifact={args.output}")
            return 0

        # Freeze separator before opening fresh target authority.
        fresh = read_epd(args.fresh_epd)
        source_keys = {
            position_key(board)
            for boards in source_splits.values()
            for board in boards
        }
        fresh_keys = {position_key(board) for board in fresh}
        overlap = source_keys & fresh_keys
        if overlap:
            raise AssertionError(("fresh/source position overlap", len(overlap)))

        parent_guard_fires = 0
        separator_rejects = 0
        accepted = 0
        accepted_wrong = 0
        examples: list[dict[str, Any]] = []

        j = int(separator["feature"])
        for board in fresh:
            fen = board.fen()
            p1, p2 = base_probes(engine, fen)
            fires, leaf = guard_fires(guard, board, p1, p2)
            if not fires:
                continue
            parent_guard_fires += 1

            from crystal_chess_search_sufficiency_v25 import feature_row
            names, features = feature_row(board, p1, p2)
            if list(names) != list(feature_names):
                raise AssertionError("fresh feature order drift")

            if not predicate_eval(separator, int(features[j])):
                separator_rejects += 1
                continue

            # Commitment is complete here. Deep authority starts only now.
            accepted += 1
            authority = engine.search(
                fen, AUTHORITY_NODES, multipv=1, clear=True
            )
            ok = p2["bestmove"] == authority["bestmove"]
            accepted_wrong += int(not ok)
            if len(examples) < 30:
                examples.append(
                    {
                        "fen": fen,
                        "leaf": leaf,
                        "feature_name": separator["feature_name"],
                        "feature_value": int(features[j]),
                        "probe_move": p2["bestmove"],
                        "authority_move": authority["bestmove"],
                        "match": ok,
                    }
                )
    finally:
        engine.quit()

    n = len(fresh)
    baseline_nodes = n * AUTHORITY_NODES
    hybrid_nodes = n * PROBE_TOTAL_NODES + (n - accepted) * AUTHORITY_NODES
    reduction = 1.0 - hybrid_nodes / baseline_nodes
    green = accepted > 0 and accepted_wrong == 0 and reduction > 0.0
    status = (
        "WARRANTED_PROSPECTIVE_NORMAL_SEARCH_RESIDUAL_SEPARATOR"
        if green
        else "FRESH_NORMAL_SEARCH_SEPARATOR_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v22_run": V22_RUN,
        "v25_run": V25_RUN,
        "v26_run": V26_RUN,
        "v25_guard_sha256": guard_sha,
        "source": {
            "positions": len(source_records),
            "parent_guard_covered": len(covered),
            "parent_guard_wrong": parent_wrong,
            "separator": separator,
            "retained_source_states": int(separator["source_support"]),
        },
        "fresh_target": {
            "seed": FRESH_SEED,
            "book_sha256": manifest["book_sha256"],
            "positions": n,
            "source_position_overlap": len(overlap),
            "parent_guard_fires": parent_guard_fires,
            "separator_rejects": separator_rejects,
            "accepted_shortcuts": accepted,
            "accepted_coverage_ratio": accepted / n,
            "accepted_wrong": accepted_wrong,
            "baseline_node_budget": baseline_nodes,
            "expected_hybrid_node_budget": hybrid_nodes,
            "estimated_node_reduction_ratio": reduction,
            "examples": examples,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "the V25 parent guard is unchanged",
                "exactly one exposed V25 source failure earns one separator using only pre-existing V25 observables",
                "separator selection sees no V26 fresh-target authority",
                "fresh corpus is position-disjoint from the V22/V25 selected source corpus",
                "every fresh accepted shortcut matches pinned 100k Stockfish and total expected node work is reduced",
            ],
            "unknown": [
                "replication on another fresh normal-opening seed",
                "wall-clock UCI benefit",
                "self-play Elo benefit",
                "chess-theoretic optimality of the pinned Stockfish authority",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )
    print(f"CRYSTAL_CHESS_SEARCH_RESIDUAL_SEPARATOR_V27={status}")
    print(
        f"source parent={len(covered)} wrong={parent_wrong} "
        f"separator={separator}"
    )
    print(
        f"fresh positions={n} parent_guard={parent_guard_fires} "
        f"separator_rejects={separator_rejects}"
    )
    print(
        f"accepted={accepted} wrong={accepted_wrong} "
        f"coverage={accepted/n:.8f} reduction={reduction:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
