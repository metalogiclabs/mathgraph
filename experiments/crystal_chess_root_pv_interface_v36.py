#!/usr/bin/env python3
"""Crystal Chess V36: compile earned continuation distinctions into root MultiPV.

V28-V35 showed that continuation structure matters, but child re-probing is too
expensive at current normal-game coverage.  V36 asks whether the same protected
distinction can be read from the already-paid 1k -> TT-reused 4k root MultiPV2
search.

No child search is performed.  The only new interface is:
* robust root score interval between PV1/PV2 across 1k and 4k;
* typed first opponent reply already present in the 4k PV1/PV2 lines.

The weakest predeclared source-exact relation is frozen before 100k authority
queries on untouched seeds 20261013 and 20261014.

This is a minimum-sufficient-interface compilation experiment: preserve the
earned semantic distinction while removing its redundant probe cost.
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
from crystal_chess_search_continuation_v28 import position_key

SCHEMA = "mathgraph.crystal-chess.root-pv-interface.v36"
FRESH_SEEDS = (20261013, 20261014)
V35_RUN = 36502300143

VARIANTS = (
    "root_interval_capture_equal",
    "root_interval_capture_equal_pair_stable",
    "root_interval_effect_equal",
    "root_interval_effect_equal_pair_stable",
)


def root_alternative(probe: dict[str, Any]) -> str | None:
    candidate = str(probe.get("bestmove") or "")
    pv1 = list(probe.get("pv1") or [])
    pv2 = list(probe.get("pv2") or [])
    if not candidate or not pv2:
        return None
    alt = str(pv2[0])
    if not alt or alt == candidate:
        return None
    if pv1 and str(pv1[0]) != candidate:
        return None
    return alt


def reply_effect(
    board: chess.Board,
    root_move_uci: str,
    reply_uci: str,
) -> dict[str, int]:
    root_move = chess.Move.from_uci(root_move_uci)
    if root_move not in board.legal_moves:
        raise AssertionError(("illegal root move", board.fen(), root_move_uci))
    child = board.copy(stack=False)
    child.push(root_move)
    reply = chess.Move.from_uci(reply_uci)
    if reply not in child.legal_moves:
        raise AssertionError(("illegal reply", child.fen(), reply_uci))
    mover = child.piece_at(reply.from_square)
    captured = child.piece_at(reply.to_square)
    return {
        "capture": int(child.is_capture(reply)),
        "check": int(child.gives_check(reply)),
        "zeroing": int(child.is_zeroing(reply)),
        "mover_type": int(mover.piece_type) if mover else 0,
        "captured_type": int(captured.piece_type) if captured else 0,
        "promotion": int(reply.promotion or 0),
    }


def root_interface(
    board: chess.Board,
    p1: dict[str, Any],
    p2: dict[str, Any],
) -> dict[str, Any] | None:
    if p1.get("score2") is None or p2.get("score2") is None:
        return None
    if len(p2.get("pv1") or []) < 2 or len(p2.get("pv2") or []) < 2:
        return None

    candidate = str(p2["bestmove"])
    alternative = root_alternative(p2)
    if alternative is None:
        return None

    p1_alt = root_alternative(p1)
    candidate_low = min(int(p1["score1"]), int(p2["score1"]))
    candidate_high = max(int(p1["score1"]), int(p2["score1"]))
    alternative_low = min(int(p1["score2"]), int(p2["score2"]))
    alternative_high = max(int(p1["score2"]), int(p2["score2"]))

    candidate_reply = str(p2["pv1"][1])
    alternative_reply = str(p2["pv2"][1])
    try:
        ce = reply_effect(board, candidate, candidate_reply)
        ae = reply_effect(board, alternative, alternative_reply)
    except (ValueError, AssertionError):
        return None

    return {
        "candidate": candidate,
        "alternative": alternative,
        "candidate_low": candidate_low,
        "candidate_high": candidate_high,
        "alternative_low": alternative_low,
        "alternative_high": alternative_high,
        "robust_gap": candidate_low - alternative_high,
        "root_best_stable": str(p1["bestmove"]) == candidate,
        "root_pair_stable": (
            str(p1["bestmove"]) == candidate
            and p1_alt is not None
            and p1_alt == alternative
        ),
        "candidate_reply": candidate_reply,
        "alternative_reply": alternative_reply,
        "candidate_reply_effect": ce,
        "alternative_reply_effect": ae,
    }


def variant_accepts(variant: str, iface: dict[str, Any]) -> bool:
    if int(iface["robust_gap"]) < 0:
        return False
    c = iface["candidate_reply_effect"]
    a = iface["alternative_reply_effect"]
    capture_equal = int(c["capture"]) == int(a["capture"])
    effect_equal = all(
        int(c[k]) == int(a[k]) for k in ("capture", "check", "zeroing")
    )
    if variant == "root_interval_capture_equal":
        return capture_equal
    if variant == "root_interval_capture_equal_pair_stable":
        return capture_equal and bool(iface["root_pair_stable"])
    if variant == "root_interval_effect_equal":
        return effect_equal
    if variant == "root_interval_effect_equal_pair_stable":
        return effect_equal and bool(iface["root_pair_stable"])
    raise ValueError(variant)


def source_rows(
    engine: UCIStockfish,
    guard: dict[str, Any],
    v22_pgn: Path,
    generations: list[tuple[str, Path]],
) -> tuple[list[dict[str, Any]], set[tuple[str, bool, str, int | None]]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, bool, str, int | None]] = set()

    splits = extract_positions(v22_pgn, 220)
    for split in ("train", "validation", "holdout"):
        records, _ = collect_records(engine, splits[split])
        for rec in records:
            board = chess.Board(rec["fen"])
            key = position_key(board)
            seen.add(key)
            fires, leaf = guard_fires(
                guard, board, rec["probe1"], rec["probe2"]
            )
            if not fires:
                continue
            iface = root_interface(board, rec["probe1"], rec["probe2"])
            if iface is None:
                continue
            rows.append({
                "generation": "v22",
                "fen": rec["fen"],
                "leaf": leaf,
                "iface": iface,
                "authority": str(rec["authority_bestmove"]),
                "match": str(rec["probe2"]["bestmove"]) == str(rec["authority_bestmove"]),
            })

    for generation, path in generations:
        for board in read_epd(path):
            key = position_key(board)
            if key in seen:
                continue
            seen.add(key)
            fen = board.fen()
            p1, p2 = base_probes(engine, fen)
            fires, leaf = guard_fires(guard, board, p1, p2)
            if not fires:
                continue
            iface = root_interface(board, p1, p2)
            if iface is None:
                continue
            auth = engine.search(fen, AUTHORITY_NODES, multipv=1, clear=True)
            rows.append({
                "generation": generation,
                "fen": fen,
                "leaf": leaf,
                "iface": iface,
                "authority": str(auth["bestmove"]),
                "match": str(p2["bestmove"]) == str(auth["bestmove"]),
            })
    return rows, seen


def choose_variant(rows: list[dict[str, Any]]) -> tuple[str | None, dict[str, Any]]:
    diagnostics: dict[str, Any] = {}
    for variant in VARIANTS:
        kept = [r for r in rows if variant_accepts(variant, r["iface"])]
        wrong = sum(not bool(r["match"]) for r in kept)
        support = Counter(str(r["generation"]) for r in kept)
        diagnostics[variant] = {
            "accepted": len(kept),
            "wrong": wrong,
            "support": dict(support),
            "coverage_of_source_guard_rows": len(kept) / len(rows) if rows else 0.0,
        }
        if len(kept) >= 30 and wrong == 0 and len(support) >= 4:
            return variant, diagnostics
    return None, diagnostics


def evaluate_target(
    engine: UCIStockfish,
    guard: dict[str, Any],
    boards: list[chess.Board],
    variant: str,
) -> dict[str, Any]:
    guard_fired = interface_available = accepted = wrong = 0
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
        interface_available += 1
        if not variant_accepts(variant, iface):
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
        "interface_available": interface_available,
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
        variant, diagnostics = choose_variant(rows)

        source_false = [
            {
                "generation": r["generation"],
                "fen": r["fen"],
                "authority": r["authority"],
                "candidate": r["iface"]["candidate"],
                "iface": r["iface"],
            }
            for r in rows if not bool(r["match"])
        ]

        if variant is None:
            result = {
                "schema": SCHEMA,
                "status": "ROOT_PV_INTERFACE_DOES_NOT_CLOSE_SOURCE",
                "stockfish_pin": STOCKFISH_PIN,
                "v35_run": V35_RUN,
                "source_states": len(rows),
                "source_wrong": len(source_false),
                "diagnostics": diagnostics,
                "source_false_positives": source_false,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
            print(
                "CRYSTAL_CHESS_ROOT_PV_INTERFACE_V36="
                "ROOT_PV_INTERFACE_DOES_NOT_CLOSE_SOURCE"
            )
            print(
                f"source={len(rows)} wrong={len(source_false)} "
                f"diagnostics={diagnostics}"
            )
            print(f"artifact={args.output}")
            return 0

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

        targets = [
            evaluate_target(engine, guard, boards, variant)
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
        "WARRANTED_REPLICATED_NORMAL_SEARCH_ROOT_PV_INTERFACE"
        if green else
        "FRESH_NORMAL_SEARCH_ROOT_PV_INTERFACE_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v35_run": V35_RUN,
        "source": {
            "states": len(rows),
            "wrong": len(source_false),
            "generation_counts": dict(Counter(str(r["generation"]) for r in rows)),
            "variant_diagnostics": diagnostics,
            "selected_variant": variant,
            "false_positives": source_false,
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
                "no child continuation probes are used",
                "only the already-paid 1k/4k root MultiPV output supplies the interface",
                "typed reply effects are the distinction earned by V35",
                "the weakest source-exact predeclared relation is frozen before fresh 100k labels",
                "both fresh targets have zero wrong substitutions and positive charged node reduction",
            ],
            "unknown": [
                "UCI wall-clock gain",
                "self-play Elo gain",
                "transfer to another opening generator",
                "chess-theoretic optimality",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_ROOT_PV_INTERFACE_V36={status}")
    print(
        f"source={len(rows)} wrong={len(source_false)} selected={variant} "
        f"diagnostics={diagnostics}"
    )
    for seed, row in zip(FRESH_SEEDS, targets):
        print(
            f"seed={seed} positions={row['positions']} "
            f"v25={row['v25_guard_fires']} iface={row['interface_available']} "
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
