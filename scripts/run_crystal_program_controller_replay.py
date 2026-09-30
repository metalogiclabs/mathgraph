#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from mathgraph.research_controller import (
    ActionMode,
    candidate_from_dict,
    campaign_state_from_dict,
    decide_campaign,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        default="experiments/crystal_program_controller_v1/frozen_ros_replay.json",
    )
    parser.add_argument(
        "--output",
        default="artifacts/crystal_program_controller_v1/replay_result.json",
    )
    args = parser.parse_args()

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    rows = []
    localization_holds = 0
    negative_memory_changes = 0
    refinement_separator_checks = 0
    refinement_separator_blocks = 0

    for case in fixture["cases"]:
        state = campaign_state_from_dict(case["state"])
        candidates = [candidate_from_dict(x) for x in case["candidates"]]
        decision = decide_campaign(state, candidates)
        selected_ok = (
            decision.status == "ACT"
            and decision.selected_candidate_id == case["expected_selected"]
        )

        localization = decide_campaign(
            replace(state, compressed_state_ref=""),
            candidates,
        )
        if localization.status == "HOLD":
            localization_holds += 1

        negative_ablation = decide_campaign(
            replace(state, retained_negative_tags=()),
            candidates,
        )
        if negative_ablation.selected_candidate_id != decision.selected_candidate_id:
            negative_memory_changes += 1

        selected = next(
            c for c in candidates if c.candidate_id == case["expected_selected"]
        )
        separator_ablation_status = "NOT_APPLICABLE"
        if selected.mode == ActionMode.REFINE:
            refinement_separator_checks += 1
            mutated = [
                replace(c, separator_refs=())
                if c.candidate_id == selected.candidate_id
                else c
                for c in candidates
            ]
            sep_decision = decide_campaign(state, mutated)
            blocked = sep_decision.selected_candidate_id != selected.candidate_id
            if blocked:
                refinement_separator_blocks += 1
            separator_ablation_status = "BLOCKED" if blocked else "FAILED_TO_BLOCK"

        rows.append(
            {
                "case_id": case["case_id"],
                "expected_selected": case["expected_selected"],
                "outcome_ref": case.get("outcome_ref"),
                "selected_ok": selected_ok,
                "decision": decision.to_dict(),
                "decision_id": decision.id,
                "localization_ablation": localization.to_dict(),
                "negative_memory_ablation": negative_ablation.to_dict(),
                "separator_ablation_status": separator_ablation_status,
            }
        )

    total = len(rows)
    passed = sum(1 for row in rows if row["selected_ok"])
    result = {
        "schema": "mathgraph.crystal-program-controller-replay-result.v1",
        "boundary": fixture["boundary"],
        "case_count": total,
        "normal_replay_passed": passed,
        "residual_localization_ablation_holds": localization_holds,
        "negative_memory_ablation_changes_selection": negative_memory_changes,
        "refinement_separator_checks": refinement_separator_checks,
        "refinement_separator_ablation_blocks": refinement_separator_blocks,
        "portfolio_selection_qualified": False,
        "portfolio_selection_note": (
            "Historical cases are from different times and domains; their replay "
            "scores are not a normalized live portfolio forecast. Programme-wide "
            "selection is valid only when inputs use a shared declared cost/"
            "contraction scale."
        ),
        "rows": rows,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    assert passed == total, (passed, total)
    assert localization_holds == total, (localization_holds, total)
    assert negative_memory_changes == total, (negative_memory_changes, total)
    assert refinement_separator_checks >= 5, refinement_separator_checks
    assert refinement_separator_blocks == refinement_separator_checks, (
        refinement_separator_blocks,
        refinement_separator_checks,
    )

    print(
        "CRYSTAL_PROGRAM_CONTROLLER_REPLAY=PASS "
        f"cases={passed}/{total} "
        f"localization_hold={localization_holds}/{total} "
        f"negative_memory_causal={negative_memory_changes}/{total} "
        f"separator_blocks={refinement_separator_blocks}/"
        f"{refinement_separator_checks}"
    )
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
