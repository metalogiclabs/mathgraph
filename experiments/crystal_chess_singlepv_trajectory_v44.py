#!/usr/bin/env python3
"""Crystal Chess V44: single-PV trajectory on the exact V43 search-mode residual.

V43 leaves four positions where the frozen 100k single-PV authority move is
absent even from clean 100k MultiPV16.  V44 therefore changes only search mode.

For those four positions, run clean single-PV Stockfish at a fixed node ladder
and record the earliest budget at which the frozen 100k authority move becomes
the selected bestmove.

No new feature, threshold, classifier, or candidate-set rule is introduced.
This is a diagnostic of search-mode/horizon behavior.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from crystal_chess_search_sufficiency_v25 import STOCKFISH_PIN, UCIStockfish

SCHEMA = "mathgraph.crystal-chess.singlepv-trajectory.v44"
V43_RUN = 36520938383
BUDGETS = (1000, 4000, 8000, 16000, 32000, 64000, 96000, 100000)


def residuals(v43: dict) -> list[dict]:
    if v43.get("schema") != "mathgraph.crystal-chess.residual-budget-ladder.v43":
        raise AssertionError(("V43 schema drift", v43.get("schema")))
    rows = [r for r in v43["rows"] if r["first_recovered_budget"] is None]
    if len(rows) != 4:
        raise AssertionError(("expected four V43 search-mode residuals", len(rows)))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--v43-result", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    v43 = json.loads(args.v43_result.read_text())
    rows = residuals(v43)

    engine = UCIStockfish(args.stockfish)
    out = []
    try:
        for src in rows:
            authority = str(src["authority"])
            ladder = []
            first = None
            distinct = []
            seen = set()
            for budget in BUDGETS:
                p = engine.search(
                    str(src["fen"]), budget, multipv=1, clear=True
                )
                best = str(p["bestmove"])
                if best not in seen:
                    seen.add(best)
                    distinct.append(best)
                is_authority = best == authority
                if is_authority and first is None:
                    first = budget
                ladder.append({
                    "nodes": budget,
                    "bestmove": best,
                    "score1": int(p["score1"]),
                    "depth": int(p["depth"]),
                    "seldepth": int(p["seldepth"]),
                    "is_frozen_authority": is_authority,
                    "pv1": list(p["pv1"][:8]),
                })
            out.append({
                "generation": src["generation"],
                "fen": src["fen"],
                "authority": authority,
                "first_singlepv_authority_budget": first,
                "distinct_bestmoves": distinct,
                "distinct_bestmove_count": len(distinct),
                "ladder": ladder,
            })
    finally:
        engine.quit()

    dist = Counter(str(r["first_singlepv_authority_budget"]) for r in out)
    before_100k = sum(
        r["first_singlepv_authority_budget"] is not None
        and int(r["first_singlepv_authority_budget"]) < 100000
        for r in out
    )
    by_64k = sum(
        r["first_singlepv_authority_budget"] is not None
        and int(r["first_singlepv_authority_budget"]) <= 64000
        for r in out
    )

    if by_64k == len(out):
        status = "SEARCH_MODE_RESIDUAL_RECOVERS_CHEAPLY_IN_SINGLEPV"
    elif before_100k == len(out):
        status = "SEARCH_MODE_RESIDUAL_RECOVERS_ONLY_LATE_IN_SINGLEPV"
    else:
        status = "SEARCH_MODE_RESIDUAL_REQUIRES_FULL_100K_SINGLEPV"

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v43_run": V43_RUN,
        "budgets": list(BUDGETS),
        "residual_count": len(out),
        "recovered_by_64k": by_64k,
        "recovered_before_100k": before_100k,
        "first_recovery_distribution": dict(dist),
        "rows": out,
        "epistemic_boundary": {
            "warranted": [
                "only V43's four search-mode residuals are tested",
                "the 100k authority move is frozen before V44 probes",
                "each budget uses a clean independent single-PV search",
                "no learned decision rule is produced",
            ],
            "unknown": [
                "runtime trigger for search-mode escalation",
                "economic value of any trajectory certificate",
                "transfer outside these four residuals",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_SINGLEPV_TRAJECTORY_V44={status}")
    print(
        f"residual={len(out)} by64k={by_64k} before100k={before_100k} "
        f"distribution={dict(dist)}"
    )
    for row in out:
        print(
            f"authority={row['authority']} first={row['first_singlepv_authority_budget']} "
            f"distinct={row['distinct_bestmove_count']} moves={row['distinct_bestmoves']} "
            f"fen={row['fen']}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
