#!/usr/bin/env python3
"""Crystal Chess V40: exact coverage audit of frozen V37 on V39 fresh books.

No new rule is learned. The purpose is causal diagnosis only:

* Run the full frozen V37 1k -> TT-reused 4k semantic guard on every V39
  fresh position, ignoring the V39 sentinel compiler.
* Query 100k Stockfish only for positions V37 itself accepts.
* Distinguish three outcomes:
    A) V37 accepts none -> semantic coverage drift / absent opportunity.
    B) V37 accepts some, all correct -> V39 sentinel recall failure.
    C) V37 accepts some wrong -> V37 semantic transfer failure.

This audit decides what may legitimately change next.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import chess

from crystal_chess_search_sufficiency_v25 import (
    AUTHORITY_NODES,
    PROBE1_NODES,
    PROBE2_NODES,
    STOCKFISH_PIN,
    UCIStockfish,
)
from crystal_chess_search_confirmation_v26 import (
    V25_GUARD_SHA256,
    load_guard,
    read_epd,
)
from crystal_chess_adaptive_interface_compiler_v38 import exact_v37_accept

SCHEMA = "mathgraph.crystal-chess.v37-coverage-audit.v40"
V37_RUN = 36503878346
V39_RUN = 36505157227
EXPECTED_SEEDS = (20261019, 20261020)


def audit(
    engine: UCIStockfish,
    guard: dict[str, Any],
    boards: list[chess.Board],
) -> dict[str, Any]:
    accepted = wrong = 0
    examples: list[dict[str, Any]] = []
    for board in boards:
        fen = board.fen()
        p1 = engine.search(
            fen, PROBE1_NODES, multipv=2, clear=True
        )
        p2 = engine.search(
            fen, PROBE2_NODES, multipv=2, clear=False
        )
        ok_guard, iface, leaf = exact_v37_accept(
            guard, board, p1, p2
        )
        if not ok_guard:
            continue
        accepted += 1
        auth = engine.search(
            fen, AUTHORITY_NODES, multipv=1, clear=True
        )
        correct = str(p2["bestmove"]) == str(auth["bestmove"])
        wrong += int(not correct)
        if len(examples) < 40:
            examples.append({
                "fen": fen,
                "candidate": str(p2["bestmove"]),
                "authority": str(auth["bestmove"]),
                "match": correct,
                "v25_leaf": leaf,
                "iface": iface,
            })

    n = len(boards)
    return {
        "positions": n,
        "v37_accepted": accepted,
        "v37_wrong": wrong,
        "coverage_ratio": accepted / n if n else 0.0,
        "examples": examples,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--epd-a", type=Path, required=True)
    ap.add_argument("--manifest-a", type=Path, required=True)
    ap.add_argument("--epd-b", type=Path, required=True)
    ap.add_argument("--manifest-b", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    guard, sha = load_guard(args.guard)
    if sha != V25_GUARD_SHA256:
        raise AssertionError(("V25 guard drift", sha))

    manifests = [
        json.loads(args.manifest_a.read_text()),
        json.loads(args.manifest_b.read_text()),
    ]
    seeds = tuple(int(m["seed"]) for m in manifests)
    if seeds != EXPECTED_SEEDS:
        raise AssertionError(("V39 seed drift", seeds))

    sets = [read_epd(args.epd_a), read_epd(args.epd_b)]

    engine = UCIStockfish(args.stockfish)
    try:
        rows = [audit(engine, guard, boards) for boards in sets]
    finally:
        engine.quit()

    total_positions = sum(r["positions"] for r in rows)
    total_accepted = sum(r["v37_accepted"] for r in rows)
    total_wrong = sum(r["v37_wrong"] for r in rows)

    if total_accepted == 0:
        status = "V37_SEMANTIC_COVERAGE_ABSENT_ON_V39_TARGET"
    elif total_wrong == 0:
        status = "V39_SENTINEL_RECALL_FAILURE_V37_SEMANTICS_SURVIVE"
    else:
        status = "V37_SEMANTIC_TRANSFER_FAILURE"

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v37_run": V37_RUN,
        "v39_run": V39_RUN,
        "targets": [
            {
                "seed": EXPECTED_SEEDS[i],
                "book_sha256": manifests[i]["book_sha256"],
                **rows[i],
            }
            for i in range(2)
        ],
        "combined": {
            "positions": total_positions,
            "v37_accepted": total_accepted,
            "v37_wrong": total_wrong,
            "coverage_ratio": (
                total_accepted / total_positions if total_positions else 0.0
            ),
        },
        "interpretation": {
            "if_absent": (
                "V39 zero shortcuts were caused by lack of V37 semantic coverage "
                "on those books, not sentinel recall."
            ),
            "if_recall_failure": (
                "V37 still had correct shortcut opportunities; the 128-node "
                "sentinel missed them and is the only residual."
            ),
            "if_transfer_failure": (
                "V37 itself is not reusable on the V39 target distribution."
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print(f"CRYSTAL_CHESS_V37_COVERAGE_AUDIT_V40={status}")
    for seed, row in zip(EXPECTED_SEEDS, rows):
        print(
            f"seed={seed} positions={row['positions']} "
            f"accepted={row['v37_accepted']} wrong={row['v37_wrong']} "
            f"coverage={row['coverage_ratio']:.8f}"
        )
    print(
        f"combined accepted={total_accepted}/{total_positions} "
        f"wrong={total_wrong} "
        f"coverage={result['combined']['coverage_ratio']:.8f}"
    )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
