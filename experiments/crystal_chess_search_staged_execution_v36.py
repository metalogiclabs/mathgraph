#!/usr/bin/env python3
"""Crystal Chess V36: staged in-search execution of the frozen V35 rule.

V35 established a semantic two-level dominance rule that was source-exact and
prospectively zero-error on 21/501 fresh positions, but its front-end cost model
was negative because the universal 5k root probe was charged as extra work.

V36 changes no decision law.  It changes execution only:
* root Stockfish process performs 1k + 4k staged probes;
* if Crystal abstains, the SAME root process continues with 95k more nodes,
  preserving a 100k root budget;
* child/continuation probes run in a separate Stockfish process so they cannot
  contaminate root fallback TT;
* direct clean 100k Stockfish remains independent authority.

Promotion requires:
1. V35 frozen rule identity and zero-error source/fresh lineage;
2. every accepted shortcut equals clean 100k Stockfish;
3. every staged fallback equals clean 100k Stockfish;
4. total charged nodes are below direct 100k-per-position baseline.

No new threshold or learned representation is introduced.
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
    PROBE1_NODES,
    PROBE2_NODES,
    PROBE_TOTAL_NODES,
    STOCKFISH_PIN,
    UCIStockfish,
)
from crystal_chess_search_confirmation_v26 import (
    V25_GUARD_SHA256,
    guard_fires,
    load_guard,
    read_epd,
)
from crystal_chess_search_continuation_v28 import (
    CHILD_PROBE_TOTAL_NODES,
    continuation_features,
    position_key,
)
from crystal_chess_search_backed_arbitration_v33 import parent_accepts
from crystal_chess_search_relative_continuation_v30 import root_alternative
from crystal_chess_search_two_level_dominance_v35 import (
    add_second_level,
    variant_accepts,
)

SCHEMA = "mathgraph.crystal-chess.search-staged-execution.v36"
V35_RUN = 36513282542
V35_VARIANT = "nested_interval_dominance"
FRESH_SEEDS = (20261013, 20261014)
FALLBACK_REMAINING_NODES = AUTHORITY_NODES - PROBE_TOTAL_NODES


def staged_root_probes(
    engine: UCIStockfish,
    fen: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    p1 = engine.search(fen, PROBE1_NODES, multipv=2, clear=True)
    p2 = engine.search(fen, PROBE2_NODES, multipv=2, clear=False)
    return p1, p2


def relation_row(
    board: chess.Board,
    candidate: str,
    alternative: str,
    candidate_meta: dict[str, Any],
    alternative_meta: dict[str, Any],
) -> dict[str, Any]:
    c1 = -int(candidate_meta["probe1"]["score1"])
    c2 = -int(candidate_meta["probe2"]["score1"])
    a1 = -int(alternative_meta["probe1"]["score1"])
    a2 = -int(alternative_meta["probe2"]["score1"])
    return {
        "fen": board.fen(),
        "candidate": candidate,
        "alternative": alternative,
        "relation_meta": {
            "candidate": candidate,
            "alternative": alternative,
            "candidate_continuation": candidate_meta,
            "alternative_continuation": alternative_meta,
            "backed_candidate_probe1": c1,
            "backed_candidate_probe2": c2,
            "backed_alternative_probe1": a1,
            "backed_alternative_probe2": a2,
            "backed_delta_probe1": c1 - a1,
            "backed_delta_probe2": c2 - a2,
        },
    }


def validate_v35(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if data.get("schema") != "mathgraph.crystal-chess.search-two-level-dominance.v35":
        raise AssertionError(("V35 schema drift", data.get("schema")))
    source = data.get("source") or {}
    if source.get("selected_variant") != V35_VARIANT:
        raise AssertionError(("V35 variant drift", source.get("selected_variant")))
    if int(source.get("wrong", -1)) != 3:
        raise AssertionError(("V35 source residual drift", source.get("wrong")))
    targets = data.get("targets") or []
    if len(targets) != 2 or any(int(t.get("wrong", -1)) != 0 for t in targets):
        raise AssertionError("V35 fresh correctness lineage drift")
    if sum(int(t.get("accepted", 0)) for t in targets) != 21:
        raise AssertionError("V35 accepted-count lineage drift")
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--v35-result", type=Path, required=True)
    ap.add_argument("--prior-epd", type=Path, action="append", required=True)
    ap.add_argument("--fresh-epd-a", type=Path, required=True)
    ap.add_argument("--fresh-manifest-a", type=Path, required=True)
    ap.add_argument("--fresh-epd-b", type=Path, required=True)
    ap.add_argument("--fresh-manifest-b", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    validate_v35(args.v35_result)
    guard, sha = load_guard(args.guard)
    if sha != V25_GUARD_SHA256:
        raise AssertionError(("V25 guard drift", sha))

    prior_keys: set[tuple[str, bool, str, int | None]] = set()
    for path in args.prior_epd:
        prior_keys.update(position_key(b) for b in read_epd(path))

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
        overlap = {position_key(b) for b in all_boards} & prior_keys
        boards = [b for b in all_boards if position_key(b) not in prior_keys]
        cross = {position_key(b) for b in boards} & target_keys
        if cross:
            boards = [b for b in boards if position_key(b) not in target_keys]
        if len(boards) < 200:
            raise AssertionError(("fresh target too small", len(boards)))
        target_keys.update(position_key(b) for b in boards)
        target_sets.append(boards)
        source_overlaps.append(len(overlap))
        cross_overlaps.append(len(cross))

    authority = UCIStockfish(args.stockfish)
    root = UCIStockfish(args.stockfish)
    child = UCIStockfish(args.stockfish)

    results = []
    try:
        for boards in target_sets:
            c = Counter()
            examples: list[dict[str, Any]] = []

            for board in boards:
                fen = board.fen()
                c["positions"] += 1
                c["baseline_nodes"] += AUTHORITY_NODES

                auth = authority.search(
                    fen, AUTHORITY_NODES, multipv=1, clear=True
                )
                authority_move = str(auth["bestmove"])

                p1, p2 = staged_root_probes(root, fen)
                c["root_prefix_nodes"] += PROBE_TOTAL_NODES

                fires, leaf = guard_fires(guard, board, p1, p2)
                accepted = False
                candidate = str(p2["bestmove"])
                row: dict[str, Any] | None = None

                if fires:
                    c["v25_guard_fires"] += 1
                    cnames, cfeats, cmeta = continuation_features(
                        child, board, candidate
                    )
                    c["child_nodes"] += CHILD_PROBE_TOTAL_NODES
                    if parent_accepts(cnames, cfeats):
                        c["parent_admitted"] += 1
                        alt = root_alternative(p2)
                        if alt is not None:
                            ameta = continuation_features(child, board, alt)[2]
                            c["child_nodes"] += CHILD_PROBE_TOTAL_NODES
                            row = relation_row(
                                board, candidate, alt, cmeta, ameta
                            )
                            if add_second_level(child, row):
                                c["child_nodes"] += 2 * CHILD_PROBE_TOTAL_NODES
                                if variant_accepts(V35_VARIANT, row):
                                    accepted = True

                if accepted:
                    c["accepted"] += 1
                    ok = candidate == authority_move
                    c["shortcut_wrong"] += int(not ok)
                    if len(examples) < 20:
                        examples.append({
                            "fen": fen,
                            "leaf": leaf,
                            "candidate": candidate,
                            "authority": authority_move,
                            "shortcut": True,
                            "match": ok,
                        })
                else:
                    fallback = root.search(
                        fen,
                        FALLBACK_REMAINING_NODES,
                        multipv=1,
                        clear=False,
                    )
                    c["fallbacks"] += 1
                    c["fallback_nodes"] += FALLBACK_REMAINING_NODES
                    parity = str(fallback["bestmove"]) == authority_move
                    c["fallback_parity"] += int(parity)
                    if len(examples) < 20 and not parity:
                        examples.append({
                            "fen": fen,
                            "candidate": candidate,
                            "authority": authority_move,
                            "fallback": str(fallback["bestmove"]),
                            "shortcut": False,
                            "fallback_parity": False,
                        })

            n = int(c["positions"])
            charged = (
                int(c["root_prefix_nodes"])
                + int(c["child_nodes"])
                + int(c["fallback_nodes"])
            )
            baseline = int(c["baseline_nodes"])
            results.append({
                **dict(c),
                "charged_hybrid_nodes": charged,
                "node_reduction_ratio": (
                    1.0 - charged / baseline if baseline else 0.0
                ),
                "coverage_ratio": (
                    int(c["accepted"]) / n if n else 0.0
                ),
                "fallback_parity_ratio": (
                    int(c["fallback_parity"]) / int(c["fallbacks"])
                    if c["fallbacks"] else 1.0
                ),
                "examples": examples,
            })
    finally:
        authority.quit()
        root.quit()
        child.quit()

    combined = Counter()
    for r in results:
        for key in (
            "positions", "baseline_nodes", "root_prefix_nodes", "child_nodes",
            "fallback_nodes", "charged_hybrid_nodes", "v25_guard_fires",
            "parent_admitted", "accepted", "shortcut_wrong", "fallbacks",
            "fallback_parity",
        ):
            combined[key] += int(r.get(key, 0))

    baseline = int(combined["baseline_nodes"])
    charged = int(combined["charged_hybrid_nodes"])
    combined_reduction = 1.0 - charged / baseline if baseline else 0.0
    combined_coverage = (
        int(combined["accepted"]) / int(combined["positions"])
        if combined["positions"] else 0.0
    )
    parity_ratio = (
        int(combined["fallback_parity"]) / int(combined["fallbacks"])
        if combined["fallbacks"] else 1.0
    )

    green = (
        int(combined["accepted"]) > 0
        and int(combined["shortcut_wrong"]) == 0
        and parity_ratio == 1.0
        and combined_reduction > 0.0
        and all(r["node_reduction_ratio"] > 0.0 for r in results)
    )
    status = (
        "WARRANTED_REPLICATED_NORMAL_SEARCH_STAGED_EXECUTION_GAIN"
        if green else "FRESH_NORMAL_SEARCH_STAGED_EXECUTION_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v35_authority_run": V35_RUN,
        "frozen_v35_variant": V35_VARIANT,
        "execution": {
            "root_probe1_nodes": PROBE1_NODES,
            "root_probe2_nodes": PROBE2_NODES,
            "fallback_remaining_nodes": FALLBACK_REMAINING_NODES,
            "child_engine_isolated_from_root_tt": True,
        },
        "targets": [
            {
                "seed": FRESH_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                "prior_overlap_removed_before_search": source_overlaps[i],
                "earlier_target_overlap_removed_before_search": cross_overlaps[i],
                **results[i],
            }
            for i in range(2)
        ],
        "combined": {
            **dict(combined),
            "coverage_ratio": combined_coverage,
            "fallback_parity_ratio": parity_ratio,
            "node_reduction_ratio": combined_reduction,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "V35 semantic decision rule is unchanged",
                "fresh seeds are disjoint from V35 exposed fresh positions and from each other before authority search",
                "every accepted shortcut equals clean 100k Stockfish",
                "every staged fallback equals clean 100k Stockfish",
                "child probes run in a separate engine and cannot contaminate fallback TT",
                "charged root-prefix plus child plus fallback nodes are below direct 100k-per-position baseline on both fresh targets",
            ],
            "unknown": [
                "wall-clock gain in a production integrated Stockfish patch",
                "self-play Elo gain",
                "transfer to a different opening generator",
                "chess-theoretic optimality of Stockfish authority",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_SEARCH_STAGED_EXECUTION_V36={status}")
    for seed, r in zip(FRESH_SEEDS, results):
        print(
            f"seed={seed} positions={r['positions']} accepted={r['accepted']} "
            f"shortcut_wrong={r['shortcut_wrong']} "
            f"fallback_parity={r['fallback_parity']}/{r['fallbacks']} "
            f"coverage={r['coverage_ratio']:.8f} "
            f"reduction={r['node_reduction_ratio']:.8f}"
        )
    print(
        f"combined accepted={combined['accepted']}/{combined['positions']} "
        f"shortcut_wrong={combined['shortcut_wrong']} "
        f"fallback_parity={combined['fallback_parity']}/{combined['fallbacks']} "
        f"coverage={combined_coverage:.8f} reduction={combined_reduction:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
