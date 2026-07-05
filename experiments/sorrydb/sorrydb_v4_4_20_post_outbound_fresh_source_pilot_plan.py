from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.20"
OUT = Path("artifacts/sorrydb/post_outbound_fresh_source_pilot_plan_v4_4_20")

INPUTS = {
    "outbound_summary": Path("artifacts/sorrydb/outbound_upstream_message_v4_4_19/summary.json"),
    "outbound_package": Path("artifacts/sorrydb/outbound_upstream_message_v4_4_19/outbound_message_package.json"),
    "artifact_links": Path("artifacts/sorrydb/outbound_upstream_message_v4_4_19/artifact_links.json"),
    "reviewer_message": Path("artifacts/sorrydb/outbound_upstream_message_v4_4_19/outbound_message.md"),
    "microflywheel_summary": Path("artifacts/sorrydb/microflywheel_report_v4_4_15/summary.json"),
}

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def main() -> None:
    missing = [str(path) for path in INPUTS.values() if not path.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    outbound_summary = load_json(INPUTS["outbound_summary"])
    outbound_package = load_json(INPUTS["outbound_package"])
    links = load_json(INPUTS["artifact_links"])
    micro = load_json(INPUTS["microflywheel_summary"])
    reviewer_message = INPUTS["reviewer_message"].read_text(encoding="utf-8")

    if outbound_summary.get("human_approval_required") is not True:
        raise SystemExit("expected v4.4.19 human_approval_required == true")

    options = [
        {
            "path_id": "manual_outbound_review",
            "description": "Stop automation and have a human review or rewrite the outbound upstream message before any external contact.",
            "priority": 1,
            "why": [
                "v4.4.19 explicitly requires human approval",
                "external contact should not be automated",
                "this preserves the trust boundary",
            ],
            "done_definition": [
                "human reads outbound_message.md",
                "human either sends, rewrites, or parks it",
                "decision is recorded before further external action",
            ],
        },
        {
            "path_id": "fresh_source_replay_pilot",
            "description": "After manual outbound review is parked or completed, run a tiny fresh-source replay pilot to test whether the two Lawbook seeds transfer under exact-source or verified-adapter constraints.",
            "priority": 2,
            "why": [
                "tests the next real scaling question",
                "keeps batch size tiny",
                "preserves exact-source and obstruction-ledger discipline",
            ],
            "done_definition": [
                "choose at most five candidate fresh targets",
                "require exact source snippet match or named adapter",
                "record accepted, failed, and obstructed outcomes separately",
            ],
        },
        {
            "path_id": "more_source_world_mining",
            "description": "Expand SorryDB source-world mining only after the outbound package and fresh-source pilot produce a clear next constraint.",
            "priority": 3,
            "why": [
                "larger mining is premature while the first upstream-facing package is unsent or unreviewed",
                "disk is limited",
                "the next bottleneck is transfer/reviewer contact, not breadth",
            ],
            "done_definition": [
                "only run after manual review and pilot decision",
                "small bounded source-world batch",
                "no heavy lake build unless explicitly approved",
            ],
        },
    ]

    pilot_constraints = {
        "max_candidate_targets": 5,
        "requires_exact_source_match_or_named_adapter": True,
        "requires_no_heavy_lake_build_without_approval": True,
        "allowed_terminal_states": ["ACCEPTED_REPLAY", "FAILED_REPLAY", "OBSTRUCTED_EXACT_SOURCE_MISMATCH", "OBSTRUCTED_ENVIRONMENT"],
        "disk_note": "root filesystem has low free space; avoid broad clone/build runs",
    }

    decision = {
        "version": VERSION,
        "decision_type": "POST_OUTBOUND_NEXT_STEP_PLAN",
        "selected_immediate_path": "manual_outbound_review",
        "selected_followup_path": "fresh_source_replay_pilot",
        "blocked_paths": ["automated_external_contact", "broad_source_world_mining"],
        "options": options,
        "pilot_constraints": pilot_constraints,
        "artifact_links": links.get("links", []),
    }

    summary = {
        "version": VERSION,
        "status": "POST_OUTBOUND_FRESH_SOURCE_PILOT_PLAN_LEDGERED",
        "input_version": outbound_summary.get("version"),
        "selected_immediate_path": "manual_outbound_review",
        "selected_followup_path": "fresh_source_replay_pilot",
        "human_approval_required": True,
        "patch_count": outbound_summary.get("patch_count"),
        "accepted_replay_certificate_count": outbound_summary.get("accepted_replay_certificate_count"),
        "microflywheel_status": micro.get("status"),
        "outbound_subject": outbound_package.get("subject"),
        "bounded_claim": [
            "v4.4.20 records that the immediate next step after v4.4.19 is manual human review of the outbound upstream message",
            "v4.4.20 selects a tiny fresh-source replay pilot as the next technical follow-up after the human-review boundary",
            "the pilot is constrained to at most five targets and exact-source match or named adapter outcomes",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches beyond v4.4.11 evidence",
            "automated external contact",
            "upstream acceptance",
            "general SorryDB mining",
            "semantic portability beyond exact-source replay or verified adapters",
            "permission to run broad clone/build jobs on low disk",
        ],
        "next_frontier": "v4.4.21 create the bounded fresh-source replay pilot candidate queue",
    }

    human_review_note = f"""# SorryDB v4.4.20 — Human Review Boundary and Fresh-Source Pilot Plan

## Immediate path

Manual outbound review.

The v4.4.19 outbound message package is ready, but human approval is required before any external contact.

## Follow-up technical path

Tiny fresh-source replay pilot.

Constraints:

- at most five candidate targets
- exact-source match or named adapter required
- no broad mining
- no heavy lake build without explicit approval
- terminal states must be accepted, failed, or named obstruction

## Current outbound subject

{outbound_package.get("subject")}

## Current outbound message snapshot

{reviewer_message}

## Bounded claim

- v4.4.20 records that the immediate next step after v4.4.19 is manual human review of the outbound upstream message.
- v4.4.20 selects a tiny fresh-source replay pilot as the next technical follow-up after the human-review boundary.
- the pilot is constrained to at most five targets and exact-source match or named adapter outcomes.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- automated external contact
- upstream acceptance
- general SorryDB mining
- semantic portability beyond exact-source replay or verified adapters
- permission to run broad clone/build jobs on low disk
"""

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "decision.json", decision)
    (OUT / "human_review_and_pilot_plan.md").write_text(human_review_note, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
