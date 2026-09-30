#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mathgraph.research_controller import (
    campaign_state_from_dict,
    candidate_from_dict,
    decide_campaign,
    decide_portfolio,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--snapshot",
        default="experiments/crystal_program_controller_v1/live_ros_snapshot_20260930.json",
    )
    parser.add_argument(
        "--output",
        default="artifacts/crystal_program_controller_v1/live_decision.json",
    )
    args = parser.parse_args()

    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    states = []
    candidates = []
    expected = {}
    campaign_rows = []

    for row in snapshot["campaigns"]:
        state = campaign_state_from_dict(row["state"])
        local = [candidate_from_dict(x) for x in row.get("candidates", [])]
        states.append(state)
        candidates.extend(local)
        expected[state.campaign_id] = row["expected_status"]
        decision = decide_campaign(state, local)
        campaign_rows.append(decision.to_dict())
        assert decision.status == row["expected_status"], (
            state.campaign_id,
            decision.to_dict(),
            row["expected_status"],
        )

    portfolio = decide_portfolio(states, candidates)
    assert portfolio.status == snapshot["expected_portfolio_status"], portfolio.to_dict()
    assert portfolio.selected_campaign_id is None
    assert portfolio.selected_candidate_id is None

    actionable = [
        row["campaign_id"]
        for row in campaign_rows
        if row["status"] == "ACT"
    ]
    held = [
        row["campaign_id"]
        for row in campaign_rows
        if row["status"] == "HOLD"
    ]

    result = {
        "schema": "mathgraph.crystal-live-program-decision.v1",
        "snapshot_time_utc": snapshot["snapshot_time_utc"],
        "source_boundary": snapshot["boundary"],
        "campaign_count": len(states),
        "actionable_campaigns": actionable,
        "held_campaigns": held,
        "campaign_decisions": campaign_rows,
        "portfolio_decision": portfolio.to_dict(),
        "portfolio_decision_id": portfolio.id,
        "interpretation": (
            "Campaign-local residual-first actions are admitted where current durable "
            "state supports them. Cross-campaign selection is deliberately withheld "
            "because the live actions use distinct campaign-local measurement bases."
        ),
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        "CRYSTAL_LIVE_PROGRAM_SNAPSHOT=PASS "
        f"campaigns={len(states)} "
        f"act={len(actionable)} "
        f"hold={len(held)} "
        f"portfolio={portfolio.status}"
    )
    print("ACTIONABLE=" + ",".join(actionable))
    print("HELD=" + ",".join(held))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
