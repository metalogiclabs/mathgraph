#!/usr/bin/env python3
"""Crystal Chess V26: residual-earned continuation confirmation.

V25 exposed exactly one prospective false positive in its untouched normal-game
holdout.  The learned 5k search-sufficiency guard itself is frozen unchanged.

The only new distinction V26 is allowed to add is *continued search stability*
after that frozen guard fires:

    1k probe -> 4k probe -> frozen V25 guard
                           |
                           +-> if guarded, one confirmation search

The already-exposed V25 residual is used only to choose the smallest
confirmation budget from {8k, 16k, 32k} that separates the false positive from
its 100k authority move.  That budget is then frozen before any new target is
opened.

Prospective target:
* a fresh deterministic normal-opening corpus generated with a new seed,
* exact overlap with the V22/V25 selected source positions is rejected,
* the 100k pinned Stockfish authority is consulted only after the
  guard+confirmation decision is fixed for a position.

This is a behavioral search-substitution capability relative to the pinned
Stockfish budget, not a chess-theoretic proof of the chosen move.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import chess
import numpy as np

from crystal_chess_search_sufficiency_v25 import (
    AUTHORITY_NODES,
    PROBE1_NODES,
    PROBE2_NODES,
    PROBE_TOTAL_NODES,
    STOCKFISH_PIN,
    UCIStockfish,
    extract_positions,
    feature_row,
)


SCHEMA = "mathgraph.crystal-chess.search-confirmation.v26"
V25_RUN = 36362896141
V22_RUN = 36361812786
V25_GUARD_SHA256 = "8ae05aba08f65154163cbd9cdd63aed8d4fbb7d3a790ebc4dae72437e1fdf7bd"
FRESH_SEED = 20260929
CONFIRMATION_BUDGETS = (8000, 16000, 32000)

# Exact V25 holdout separator, frozen from artifact 10946720077.
RESIDUAL_FEN = "2kr1br1/pp3p2/1n3p2/2p4p/1P1p1q2/P1P2BP1/5P1P/1R1QR1K1 w - - 1 13"
RESIDUAL_PROBE_MOVE = "e1e4"
RESIDUAL_AUTHORITY_MOVE = "c3d4"


def load_guard(path: Path) -> tuple[dict[str, Any], str]:
    with gzip.open(path, "rb") as handle:
        raw = handle.read()
    digest = hashlib.sha256(raw).hexdigest()
    payload = json.loads(raw)
    if payload.get("schema") != "mathgraph.crystal-chess.search-sufficiency.v25.guard":
        raise AssertionError(("unexpected guard schema", payload.get("schema")))
    if payload.get("stockfish_pin") != STOCKFISH_PIN:
        raise AssertionError(("stockfish pin drift", payload.get("stockfish_pin")))
    return payload, digest


def guard_leaf(payload: dict[str, Any], row: tuple[int, ...]) -> int:
    tree = payload["tree"]
    node = 0
    while True:
        feature = int(tree["feature"][node])
        if feature < 0:
            return node
        threshold = float(tree["threshold"][node])
        node = (
            int(tree["children_left"][node])
            if row[feature] <= threshold
            else int(tree["children_right"][node])
        )


def guard_fires(
    payload: dict[str, Any],
    board: chess.Board,
    p1: dict[str, Any],
    p2: dict[str, Any],
) -> tuple[bool, int]:
    names, row = feature_row(board, p1, p2)
    if list(names) != list(payload["feature_names"]):
        raise AssertionError("V25 feature order drift")
    leaf = guard_leaf(payload, row)
    return leaf in set(int(x) for x in payload["safe_leaves"]), leaf


def read_epd(path: Path) -> list[chess.Board]:
    boards: list[chess.Board] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            board, _ops = chess.Board.from_epd(line)
            fen = board.fen()
            if fen in seen:
                continue
            seen.add(fen)
            boards.append(board)
    return boards


def source_selected_fens(source_pgn: Path) -> set[str]:
    splits = extract_positions(source_pgn, 10000)
    return {board.fen() for boards in splits.values() for board in boards}


def base_probes(engine: UCIStockfish, fen: str) -> tuple[dict[str, Any], dict[str, Any]]:
    p1 = engine.search(fen, PROBE1_NODES, multipv=2, clear=True)
    p2 = engine.search(fen, PROBE2_NODES, multipv=2, clear=False)
    return p1, p2


def select_confirmation_budget(
    engine: UCIStockfish,
    guard: dict[str, Any],
) -> dict[str, Any]:
    board = chess.Board(RESIDUAL_FEN)

    # Re-verify the exact parent residual under the pinned engine.
    p1, p2 = base_probes(engine, RESIDUAL_FEN)
    fires, leaf = guard_fires(guard, board, p1, p2)
    authority = engine.search(
        RESIDUAL_FEN, AUTHORITY_NODES, multipv=1, clear=True
    )
    if not fires:
        raise AssertionError("V25 residual no longer enters frozen safe leaf")
    if p2["bestmove"] != RESIDUAL_PROBE_MOVE:
        raise AssertionError(
            ("V25 residual probe drift", p2["bestmove"], RESIDUAL_PROBE_MOVE)
        )
    if authority["bestmove"] != RESIDUAL_AUTHORITY_MOVE:
        raise AssertionError(
            (
                "V25 residual authority drift",
                authority["bestmove"],
                RESIDUAL_AUTHORITY_MOVE,
            )
        )

    trials = []
    selected = None
    for budget in CONFIRMATION_BUDGETS:
        # Recreate exactly the parent probe state before each confirmation
        # budget so the budgets are not nested/contaminated by prior trials.
        q1, q2 = base_probes(engine, RESIDUAL_FEN)
        confirm = engine.search(
            RESIDUAL_FEN, budget, multipv=1, clear=False
        )
        trial = {
            "budget": budget,
            "probe_move": q2["bestmove"],
            "confirmation_move": confirm["bestmove"],
            "authority_move": authority["bestmove"],
            "separates_parent_false_positive": (
                confirm["bestmove"] != q2["bestmove"]
            ),
            "confirmation_matches_authority": (
                confirm["bestmove"] == authority["bestmove"]
            ),
        }
        trials.append(trial)
        if (
            selected is None
            and trial["separates_parent_false_positive"]
            and trial["confirmation_matches_authority"]
        ):
            selected = budget

    return {
        "guard_leaf": leaf,
        "probe1": p1["bestmove"],
        "probe2": p2["bestmove"],
        "authority": authority["bestmove"],
        "trials": trials,
        "selected_budget": selected,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--fresh-epd", type=Path, required=True)
    ap.add_argument("--source-pgn", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    guard, guard_sha = load_guard(args.guard)
    if guard_sha != V25_GUARD_SHA256:
        raise AssertionError(("V25 guard digest drift", guard_sha))

    fresh = read_epd(args.fresh_epd)
    if len(fresh) < 100:
        raise AssertionError(("fresh corpus too small", len(fresh)))

    source_fens = source_selected_fens(args.source_pgn)
    overlap = sorted({board.fen() for board in fresh} & source_fens)
    if overlap:
        raise AssertionError(("fresh/source overlap", len(overlap), overlap[:5]))

    engine = UCIStockfish(args.stockfish)
    try:
        separator = select_confirmation_budget(engine, guard)
        selected_budget = separator["selected_budget"]

        if selected_budget is None:
            result = {
                "schema": SCHEMA,
                "status": "NO_CONTINUATION_CONFIRMATION_SEPARATOR",
                "stockfish_pin": STOCKFISH_PIN,
                "v25_run": V25_RUN,
                "v22_run": V22_RUN,
                "v25_guard_sha256": guard_sha,
                "parent_residual": separator,
                "fresh_positions": len(fresh),
                "fresh_seed": FRESH_SEED,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, sort_keys=True, indent=2) + "\n"
            )
            print(
                "CRYSTAL_CHESS_SEARCH_CONFIRMATION_V26="
                "NO_CONTINUATION_CONFIRMATION_SEPARATOR"
            )
            print(f"artifact={args.output}")
            return 0

        guard_fires_count = 0
        confirmation_rejects = 0
        accepted = 0
        base_guard_wrong = 0
        accepted_wrong = 0
        base_examples = []
        accepted_examples = []

        for board in fresh:
            fen = board.fen()
            p1, p2 = base_probes(engine, fen)
            fires, leaf = guard_fires(guard, board, p1, p2)
            if not fires:
                continue

            guard_fires_count += 1
            confirmation = engine.search(
                fen, selected_budget, multipv=1, clear=False
            )
            confirmed = confirmation["bestmove"] == p2["bestmove"]
            confirmation_rejects += int(not confirmed)

            # Authority begins only after the base guard and confirmation
            # decision are both fixed.
            authority = engine.search(
                fen, AUTHORITY_NODES, multipv=1, clear=True
            )
            base_ok = p2["bestmove"] == authority["bestmove"]
            base_guard_wrong += int(not base_ok)

            if len(base_examples) < 30:
                base_examples.append(
                    {
                        "fen": fen,
                        "leaf": leaf,
                        "probe_move": p2["bestmove"],
                        "confirmation_move": confirmation["bestmove"],
                        "authority_move": authority["bestmove"],
                        "base_match": base_ok,
                        "confirmed": confirmed,
                    }
                )

            if not confirmed:
                continue

            accepted += 1
            ok = p2["bestmove"] == authority["bestmove"]
            accepted_wrong += int(not ok)
            if len(accepted_examples) < 30:
                accepted_examples.append(
                    {
                        "fen": fen,
                        "leaf": leaf,
                        "move": p2["bestmove"],
                        "authority_move": authority["bestmove"],
                        "match": ok,
                    }
                )
    finally:
        engine.quit()

    n = len(fresh)
    baseline_nodes = n * AUTHORITY_NODES
    # Runtime protocol: 5k probes on all positions; confirmation only if V25
    # guard fires; 100k fallback on every position not accepted.
    expected_nodes = (
        n * PROBE_TOTAL_NODES
        + guard_fires_count * int(selected_budget)
        + (n - accepted) * AUTHORITY_NODES
    )
    reduction = 1.0 - expected_nodes / baseline_nodes

    green = accepted > 0 and accepted_wrong == 0 and reduction > 0.0
    status = (
        "WARRANTED_PROSPECTIVE_NORMAL_SEARCH_CONFIRMATION_GUARD"
        if green
        else "FRESH_NORMAL_SEARCH_CONFIRMATION_RESIDUAL"
    )

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v25_run": V25_RUN,
        "v22_run": V22_RUN,
        "v25_guard_sha256": guard_sha,
        "source_residual": separator,
        "fresh_target": {
            "seed": FRESH_SEED,
            "positions": n,
            "source_selected_fen_overlap": len(overlap),
        },
        "protocol": {
            "probe1_nodes": PROBE1_NODES,
            "probe2_nodes": PROBE2_NODES,
            "confirmation_nodes": selected_budget,
            "authority_nodes": AUTHORITY_NODES,
            "confirmation_runs_only_when_v25_guard_fires": True,
            "fallback": "unchanged pinned 100k Stockfish search",
        },
        "prospective": {
            "base_guard_fires": guard_fires_count,
            "base_guard_coverage_ratio": guard_fires_count / n,
            "base_guard_wrong": base_guard_wrong,
            "confirmation_rejects": confirmation_rejects,
            "accepted_shortcuts": accepted,
            "accepted_coverage_ratio": accepted / n,
            "accepted_wrong": accepted_wrong,
            "baseline_node_budget": baseline_nodes,
            "expected_hybrid_node_budget": expected_nodes,
            "estimated_node_reduction_ratio": reduction,
            "base_examples": base_examples,
            "accepted_examples": accepted_examples,
        },
        "epistemic_boundary": {
            "warranted_if_green": [
                "the V25 guard is frozen byte-for-byte and deep authority is never a feature",
                "confirmation depth is selected only from the already-exposed V25 source residual",
                "fresh target uses a new deterministic opening seed and no selected source FEN overlaps it",
                "fresh 100k Stockfish authority is consulted only after guard+confirmation commitment",
                "every prospectively accepted shortcut matches pinned 100k Stockfish and the total node budget is lower than 100k-per-position baseline",
            ],
            "unknown": [
                "transfer to another fresh opening distribution",
                "wall-clock UCI gain",
                "self-play Elo gain",
                "chess-theoretic optimality of the Stockfish authority move",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print(f"CRYSTAL_CHESS_SEARCH_CONFIRMATION_V26={status}")
    print(
        f"source_separator selected={selected_budget} "
        f"trials={separator['trials']}"
    )
    print(
        f"fresh positions={n} guard={guard_fires_count} "
        f"base_wrong={base_guard_wrong} confirmation_rejects={confirmation_rejects}"
    )
    print(
        f"accepted={accepted} wrong={accepted_wrong} "
        f"coverage={accepted/n:.8f} reduction={reduction:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
