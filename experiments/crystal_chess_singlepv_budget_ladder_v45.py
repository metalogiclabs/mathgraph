#!/usr/bin/env python3
"""Crystal Chess V45: single-PV budget ladder on the exact V44 hard residual.

V44 shows the four positions unrecovered by 100k MultiPV16 are not rescued by
an equivalent top-16 consequence. At 400k forced evaluation the frozen V42
authority is consequence-maximal in all four.

V45 tests the one distinction V43/V44 earned: search mode.
For each of the four frozen positions, run independent clean single-PV searches
at increasing budgets below 100k and record the first budget whose bestmove
matches the frozen 100k authority.

No new feature, threshold, classifier, or target adaptation is introduced.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from crystal_chess_search_sufficiency_v25 import STOCKFISH_PIN, UCIStockfish

SCHEMA = "mathgraph.crystal-chess.singlepv-budget-ladder.v45"
V44_RUN = 36521246609
BUDGETS = (1000, 2000, 4000, 8000, 16000, 32000, 64000)


def residuals(v44: dict[str, Any]) -> list[dict[str, Any]]:
    if v44.get("schema") != "mathgraph.crystal-chess.forced-consequence-audit.v44":
        raise AssertionError(("V44 schema drift", v44.get("schema")))
    rows = list(v44.get("rows", []))
    if len(rows) != 4:
        raise AssertionError(("expected four exact V44 rows", len(rows)))
    if not all(bool(r["forced"]["400000"]["authority_is_max"]) for r in rows):
        raise AssertionError("V44 400k consequence authority drift")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stockfish", type=Path, required=True)
    ap.add_argument("--v44-result", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    v44 = json.loads(args.v44_result.read_text())
    rows = residuals(v44)

    engine = UCIStockfish(args.stockfish)
    out = []
    try:
        for src in rows:
            authority = str(src["authority"])
            ladder = []
            first = None
            for budget in BUDGETS:
                p = engine.search(
                    str(src["fen"]),
                    budget,
                    multipv=1,
                    clear=True,
                )
                best = str(p["bestmove"])
                hit = best == authority
                ladder.append({
                    "nodes": budget,
                    "bestmove": best,
                    "matches_authority": hit,
                    "score1": int(p["score1"]),
                    "depth": int(p["depth"]),
                    "seldepth": int(p["seldepth"]),
                    "pv1": list(p["pv1"][:10]),
                })
                if hit and first is None:
                    first = budget

            out.append({
                "generation": src.get("generation"),
                "fen": src["fen"],
                "authority": authority,
                "first_singlepv_recovery_budget": first,
                "recovered_below_100k": first is not None,
                "ladder": ladder,
            })
    finally:
        engine.quit()

    dist = Counter(
        "unrecovered" if r["first_singlepv_recovery_budget"] is None
        else str(r["first_singlepv_recovery_budget"])
        for r in out
    )
    recovered = sum(r["recovered_below_100k"] for r in out)
    cumulative = {
        str(b): sum(
            r["first_singlepv_recovery_budget"] is not None
            and int(r["first_singlepv_recovery_budget"]) <= b
            for r in out
        )
        for b in BUDGETS
    }

    if recovered == len(out):
        status = "V44_HARD_RESIDUAL_RECOVERED_BY_SUB100K_SINGLEPV"
    elif recovered > 0:
        status = "V44_HARD_RESIDUAL_PARTLY_RECOVERED_BY_SINGLEPV"
    else:
        status = "V44_HARD_RESIDUAL_REQUIRES_NEAR_AUTHORITY_BUDGET"

    result = {
        "schema": SCHEMA,
        "status": status,
        "stockfish_pin": STOCKFISH_PIN,
        "v44_run": V44_RUN,
        "budgets": list(BUDGETS),
        "residual_count": len(out),
        "recovered_count": recovered,
        "first_recovery_distribution": dict(dist),
        "cumulative_recovered": cumulative,
        "rows": out,
        "epistemic_boundary": {
            "warranted": [
                "only the exact four V44 hard source residuals are tested",
                "the V42 authority move is frozen before V45 searches",
                "all V45 probes use clean single-PV mode",
                "no learned threshold or feature is introduced",
            ],
            "unknown": [
                "a cheap runtime trigger for entering the single-PV ladder",
                "prospective recovery on fresh certificate-set misses",
                "net node or wall-clock gain",
                "self-play Elo gain",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(f"CRYSTAL_CHESS_SINGLEPV_BUDGET_LADDER_V45={status}")
    print(
        f"residual={len(out)} recovered={recovered} "
        f"distribution={dict(dist)} cumulative={cumulative}"
    )
    for r in out:
        print(
            f"authority={r['authority']} first={r['first_singlepv_recovery_budget']} "
            f"fen={r['fen']}"
        )
    print(f"artifact={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
