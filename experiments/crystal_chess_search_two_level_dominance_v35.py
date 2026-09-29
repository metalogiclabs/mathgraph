#!/usr/bin/env python3
"""Crystal Chess V35: two-level robust continuation dominance.

V34 proved that root-move + opponent-reply backed intervals are insufficient:
one exposed false positive survives even strict, pair-stable robust dominance.

V35 goes exactly one continuation layer deeper.  For both the candidate and
the root alternative:
  root move -> frozen cheap best reply -> cheap 1k/4k response search.
The candidate is admitted only if it robustly dominates the alternative at
BOTH levels.  No learned numeric threshold is introduced.

The weakest source-exact semantic variant is frozen before any 100k authority
query on fresh seeds 20261011 and 20261012.
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
    CHILD_PROBE1_NODES,
    CHILD_PROBE2_NODES,
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

SCHEMA = "mathgraph.crystal-chess.search-two-level-dominance.v35"
V22_RUN = 36361812786
V25_RUN = 36362896141
V28_RUN = 36368371744
V29_RUN = 36368824668
V30_RUN = 36385064153
V31_RUN = 36385673166
V32_RUN = 36386326389
V33_RUN = 36386803245
V34_RUN = 36501679711
FRESH_SEEDS = (20261011, 20261012)

VARIANTS = (
    "nested_interval_dominance",
    "nested_interval_dominance_response_stable",
    "strict_nested_interval_dominance_response_stable",
)


def first_level_values(row: dict[str, Any]) -> dict[str, int]:
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
        "gap": min(c1, c2) - max(a1, a2),
    }


def response_probe(
    engine: UCIStockfish,
    board: chess.Board,
    root_move_uci: str,
    continuation_meta: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        root_move = chess.Move.from_uci(root_move_uci)
    except ValueError:
        return None
    if root_move not in board.legal_moves:
        return None

    child = board.copy(stack=False)
    child.push(root_move)

    reply_uci = str(continuation_meta["probe2"]["bestmove"])
    try:
        reply = chess.Move.from_uci(reply_uci)
    except ValueError:
        return None
    if reply not in child.legal_moves:
        return None

    child.push(reply)
    fen = child.fen()
    p1 = engine.search(fen, CHILD_PROBE1_NODES, multipv=2, clear=True)
    p2 = engine.search(fen, CHILD_PROBE2_NODES, multipv=2, clear=False)

    return {
        "reply": reply_uci,
        "grandchild_fen": fen,
        "score_probe1": int(p1["score1"]),
        "score_probe2": int(p2["score1"]),
        "best_probe1": str(p1["bestmove"]),
        "best_probe2": str(p2["bestmove"]),
        "best_stable": str(p1["bestmove"]) == str(p2["bestmove"]),
        "depth_probe1": int(p1["depth"]),
        "depth_probe2": int(p2["depth"]),
        "seldepth_probe1": int(p1["seldepth"]),
        "seldepth_probe2": int(p2["seldepth"]),
        "pv1_probe1": list(p1["pv1"][:4]),
        "pv1_probe2": list(p2["pv1"][:4]),
    }


def add_second_level(
    engine: UCIStockfish,
    row: dict[str, Any],
) -> bool:
    board = chess.Board(str(row["fen"]))
    m = row["relation_meta"]
    c = response_probe(
        engine,
        board,
        str(row["candidate"]),
        dict(m["candidate_continuation"]),
    )
    a = response_probe(
        engine,
        board,
        str(row["alternative"]),
        dict(m["alternative_continuation"]),
    )
    if c is None or a is None:
        row["second_level"] = None
        return False

    clow = min(int(c["score_probe1"]), int(c["score_probe2"]))
    chigh = max(int(c["score_probe1"]), int(c["score_probe2"]))
    alow = min(int(a["score_probe1"]), int(a["score_probe2"]))
    ahigh = max(int(a["score_probe1"]), int(a["score_probe2"]))
    row["second_level"] = {
        "candidate": c,
        "alternative": a,
        "candidate_low": clow,
        "candidate_high": chigh,
        "alternative_low": alow,
        "alternative_high": ahigh,
        "gap": clow - ahigh,
    }
    return True


def variant_accepts(variant: str, row: dict[str, Any]) -> bool:
    s = row.get("second_level")
    if not isinstance(s, dict):
        return False
    f = first_level_values(row)
    first_ok = int(f["gap"]) >= 0
    second_ok = int(s["gap"]) >= 0
    stable = bool(s["candidate"]["best_stable"]) and bool(
        s["alternative"]["best_stable"]
    )

    if variant == "nested_interval_dominance":
        return first_ok and second_ok
    if variant == "nested_interval_dominance_response_stable":
        return first_ok and second_ok and stable
    if variant == "strict_nested_interval_dominance_response_stable":
        return int(f["gap"]) > 0 and int(s["gap"]) > 0 and stable
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
    v25_fires = parent = no_alt = relation_ready = accepted = wrong = 0
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
        }
        if not add_second_level(engine, row):
            continue
        relation_ready += 1

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
                "first_level": first_level_values(row),
                "second_level": row["second_level"],
                "candidate_parent": cmeta,
            })

    n = len(boards)
    baseline = n * AUTHORITY_NODES

    # Charged upper bound:
    # root 1k+4k for all;
    # candidate child 1k+4k when V25 fires;
    # relation_features recomputes candidate child and probes alternative:
    # charge 2 * child-probe cost for every parent-admitted state;
    # V35 then probes both grandchildren: another 2 * child-probe cost;
    # full 100k fallback everywhere not accepted.
    hybrid = (
        n * PROBE_TOTAL_NODES
        + v25_fires * CHILD_PROBE_TOTAL_NODES
        + parent * (4 * CHILD_PROBE_TOTAL_NODES)
        + (n - accepted) * AUTHORITY_NODES
    )
    reduction = 1.0 - hybrid / baseline if baseline else 0.0

    return {
        "positions": n,
        "v25_guard_fires": v25_fires,
        "parent_admitted": parent,
        "no_alternative": no_alt,
        "relation_ready": relation_ready,
        "accepted": accepted,
        "wrong": wrong,
        "coverage_ratio": accepted / n if n else 0.0,
        "baseline_nodes": baseline,
        "conservative_hybrid_nodes": hybrid,
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
                ("expected V33/V34 exposed residuals", len(rows), source_wrong)
            )

        second_ready = 0
        for row in rows:
            second_ready += int(add_second_level(engine, row))

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
                    "first_level": first_level_values(row),
                    "second_level": row.get("second_level"),
                })

        if variant is None:
            result = {
                "schema": SCHEMA,
                "status": "TWO_LEVEL_DOMINANCE_DOES_NOT_CLOSE_EXPOSED_RESIDUALS",
                "stockfish_pin": STOCKFISH_PIN,
                "source_states": len(rows),
                "source_wrong": source_wrong,
                "second_level_ready": second_ready,
                "diagnostics": diagnostics,
                "source_false_positives": source_bad,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, sort_keys=True, indent=2) + "\n"
            )
            print(
                "CRYSTAL_CHESS_SEARCH_TWO_LEVEL_DOMINANCE_V35="
                "TWO_LEVEL_DOMINANCE_DOES_NOT_CLOSE_EXPOSED_RESIDUALS"
            )
            print(
                f"source states={len(rows)} wrong={source_wrong} "
                f"second_ready={second_ready} diagnostics={diagnostics}"
            )
            print(f"artifact={args.output}")
            return 0

        # Frozen before any fresh authority query.
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
    combined_hybrid = sum(r["conservative_hybrid_nodes"] for r in targets)
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
        "WARRANTED_REPLICATED_NORMAL_SEARCH_TWO_LEVEL_DOMINANCE"
        if green else "FRESH_NORMAL_SEARCH_TWO_LEVEL_DOMINANCE_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "source_runs": {
            "v22": V22_RUN, "v25": V25_RUN, "v28": V28_RUN,
            "v29": V29_RUN, "v30": V30_RUN, "v31": V31_RUN,
            "v32": V32_RUN, "v33": V33_RUN, "v34": V34_RUN,
        },
        "source": {
            "states": len(rows),
            "wrong": source_wrong,
            "second_level_ready": second_ready,
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
            "coverage_ratio": combined_accepted / combined_positions,
            "baseline_nodes": combined_baseline,
            "conservative_hybrid_nodes": combined_hybrid,
            "estimated_node_reduction_ratio": combined_reduction,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "no threshold is fitted from V34 false positives",
                "candidate must dominate the root alternative robustly at two continuation levels",
                "weakest source-exact semantic variant is frozen before fresh 100k authority queries",
                "fresh seeds are disjoint from all exposed source states and from each other before authority search",
                "every accepted fresh shortcut equals pinned 100k Stockfish",
                "both fresh targets retain positive net node savings after charging all cheap probes conservatively",
            ],
            "unknown": [
                "real UCI wall-clock gain",
                "self-play Elo gain",
                "transfer to another opening generator",
                "chess-theoretic optimality of Stockfish authority",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_SEARCH_TWO_LEVEL_DOMINANCE_V35={status}")
    print(
        f"source states={len(rows)} wrong={source_wrong} "
        f"second_ready={second_ready} selected={variant} diagnostics={diagnostics}"
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
