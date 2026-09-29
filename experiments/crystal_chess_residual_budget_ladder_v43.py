#!/usr/bin/env python3
"""Crystal Chess V43: budget ladder on the exact V42 width residual.

V42 proves width alone does not close the normal certificate-set problem:
19/2385 source positions have the pinned 100k Stockfish move absent from both
the 1k and TT-reused 4k MultiPV16 lists.

V43 touches only those 19 residuals.  It asks the cheapest next question:
does deeper clean MultiPV16 search recover the same 100k single-PV authority
move, and at what budget?

No new feature, threshold, classifier, or applicability rule is introduced.
This is a diagnostic, not a deployment rule.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from crystal_chess_search_sufficiency_v25 import (
    STOCKFISH_PIN,
    UCIStockfish,
)
from crystal_chess_normal_certificate_set_v41 import search_multi

SCHEMA = "mathgraph.crystal-chess.residual-budget-ladder.v43"
V42_RUN = 36519656689
MULTIPV = 16
BUDGETS = (8000, 16000, 32000, 64000, 100000)


def rank_of(move: str, probe: dict[str, Any]) -> int | None:
    for row in probe["ranked"]:
        if str(row["move"]) == move:
            return int(row["rank"])
    return None


def residuals(v42: dict[str, Any]) -> list[dict[str, Any]]:
    if v42.get("schema") != "mathgraph.crystal-chess.normal-certificate-width.v42":
        raise AssertionError(("V42 schema drift", v42.get("schema")))
    rows = list(
        v42["source"]["variants"]["union_top16"].get("miss_examples", [])
    )
    if len(rows) != int(v42["source"]["authority_absent_both_top16"]):
        raise AssertionError(
            (
                "V42 residual example count drift",
                len(rows),
                v42["source"]["authority_absent_both_top16"],
            )
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--v42-result", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    v42 = json.loads(args.v42_result.read_text())
    rows = residuals(v42)
    if len(rows) != 19:
        raise AssertionError(("expected exact V42 residual of 19", len(rows)))

    engine = UCIStockfish(args.stockfish)
    out = []
    try:
        for src in rows:
            authority = str(src["authority"])
            ladder = []
            first_budget = None
            first_rank = None
            for budget in BUDGETS:
                p = search_multi(
                    engine,
                    str(src["fen"]),
                    budget,
                    multipv=MULTIPV,
                    clear=True,
                )
                rank = rank_of(authority, p)
                ladder.append(
                    {
                        "nodes": budget,
                        "bestmove": str(p["bestmove"]),
                        "authority_rank": rank,
                        "authority_present": rank is not None,
                        "top16": [
                            {
                                "rank": int(r["rank"]),
                                "move": str(r["move"]),
                                "score": int(r["score"]),
                                "depth": int(r["depth"]),
                                "seldepth": int(r["seldepth"]),
                            }
                            for r in p["ranked"][:16]
                        ],
                    }
                )
                if rank is not None and first_budget is None:
                    first_budget = budget
                    first_rank = rank

            out.append(
                {
                    "generation": src["generation"],
                    "fen": src["fen"],
                    "authority": authority,
                    "first_recovered_budget": first_budget,
                    "first_recovered_rank": first_rank,
                    "recovered_by_100k_multipv16": first_budget is not None,
                    "ladder": ladder,
                }
            )
    finally:
        engine.quit()

    dist = Counter(
        "unrecovered" if r["first_recovered_budget"] is None
        else str(r["first_recovered_budget"])
        for r in out
    )
    recovered = sum(r["first_recovered_budget"] is not None for r in out)
    by_budget = {
        str(b): sum(
            any(
                int(step["nodes"]) <= b and bool(step["authority_present"])
                for step in r["ladder"]
            )
            for r in out
        )
        for b in BUDGETS
    }

    if recovered == len(out):
        status = "V42_RESIDUAL_IS_BUDGET_HORIZON_ONLY"
    elif recovered > 0:
        status = "V42_RESIDUAL_MIXES_BUDGET_AND_SEARCH_MODE"
    else:
        status = "V42_RESIDUAL_NOT_RECOVERED_BY_100K_MULTIPV16"

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v42_run": V42_RUN,
        "multipv": MULTIPV,
        "budgets": list(BUDGETS),
        "residual_count": len(out),
        "recovered_count": recovered,
        "first_recovery_distribution": dict(dist),
        "cumulative_recovered_by_budget": by_budget,
        "rows": out,
        "epistemic_boundary": {
            "warranted": [
                "only V42's 19 exact width residuals are tested",
                "the authority move is frozen from V42 before all V43 probes",
                "no threshold or learned feature is introduced",
            ],
            "unknown": [
                "a cheap runtime trigger for deeper search",
                "economic benefit of adaptive budget escalation",
                "fresh transfer of any resulting escalation policy",
                "chess-theoretic optimality of Stockfish authority",
            ],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_RESIDUAL_BUDGET_LADDER_V43={status}")
    print(
        f"residual={len(out)} recovered={recovered} "
        f"distribution={dict(dist)} cumulative={by_budget}"
    )
    for r in out:
        print(
            f"authority={r['authority']} first={r['first_recovered_budget']} "
            f"rank={r['first_recovered_rank']} fen={r['fen']}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
