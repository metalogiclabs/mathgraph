from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.24"
OUT = Path("artifacts/sorrydb/control_replay_approval_gate_v4_4_24")

INPUTS = {
    "replay_queue_summary": Path("artifacts/sorrydb/replay_or_obstruction_queue_v4_4_23/summary.json"),
    "replay_queue": Path("artifacts/sorrydb/replay_or_obstruction_queue_v4_4_23/replay_or_obstruction_queue.json"),
    "reviewer_checklist": Path("artifacts/sorrydb/reviewer_patch_note_v4_4_18/replay_checklist.json"),
    "outbound_message": Path("artifacts/sorrydb/outbound_upstream_message_v4_4_19/outbound_message.md"),
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

    summary23 = load_json(INPUTS["replay_queue_summary"])
    queue23 = load_json(INPUTS["replay_queue"])
    checklist = load_json(INPUTS["reviewer_checklist"])
    outbound_message = INPUTS["outbound_message"].read_text(encoding="utf-8")

    items = queue23.get("items", [])
    control_items = [x for x in items if x.get("queue_status") == "READY_FOR_CONTROL_REPLAY_IF_APPROVED"]
    exact_items = [x for x in items if x.get("queue_status") == "READY_FOR_EXACT_SOURCE_REPLAY_IF_APPROVED"]
    obstruction_items = [x for x in items if not x.get("replay_allowed_now")]

    approval_gate = {
        "version": VERSION,
        "gate_type": "CONTROL_REPLAY_APPROVAL_GATE",
        "input_version": summary23.get("version"),
        "approval_state": "NOT_APPROVED",
        "selected_action": "PARK_REPLAY_AND_RETURN_TO_MANUAL_OUTBOUND_REVIEW",
        "control_ready_count": len(control_items),
        "exact_source_ready_count": len(exact_items),
        "obstruction_count": len(obstruction_items),
        "replay_attempted": False,
        "human_approval_required_before_any_replay": True,
        "why_not_run_now": [
            "v4.4.23 marked replay candidates as approval-gated",
            "no explicit human approval token was provided in this run",
            "disk is limited and no heavy build should be started implicitly",
            "the current highest-trust external-facing artifact is the v4.4.19 outbound message package",
        ],
        "approval_token_required": "APPROVE_PINNED_CONTROL_REPLAY_V4_4_24",
        "if_approved_next_commands_are_packaged_not_executed": True,
    }

    packaged_commands = {
        "version": VERSION,
        "command_bundle_type": "PINNED_CONTROL_REPLAY_COMMANDS_NOT_EXECUTED",
        "approval_token_required": "APPROVE_PINNED_CONTROL_REPLAY_V4_4_24",
        "commands": checklist.get("commands", []),
        "notes": [
            "These commands are copied from the reviewer replay checklist.",
            "They are not executed by v4.4.24.",
            "Run only after explicit approval and after confirming disk budget.",
        ],
    }

    manual_review_packet = f"""# SorryDB v4.4.24 — Control Replay Approval Gate

## Decision

Replay is parked.

Reason: v4.4.23 produced approval-gated replay candidates, but no explicit approval token was provided here.

## Approval token required

APPROVE_PINNED_CONTROL_REPLAY_V4_4_24

## Ready counts

- control ready count: {len(control_items)}
- exact-source ready count: {len(exact_items)}
- obstruction count: {len(obstruction_items)}
- replay attempted: false

## Current outbound message

{outbound_message}

## If approved later

Use `pinned_control_replay_commands_not_executed.json`.

## Bounded claim

- v4.4.24 records the replay approval gate after the v4.4.23 replay-or-obstruction queue.
- because no explicit approval token is present, v4.4.24 parks replay and returns to manual outbound review.
- it packages the pinned control replay command list but does not execute it.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- that exact-source-ready local matches are fresh targets
- that any fresh target verifies
- automated external contact
- upstream acceptance
- permission to run heavy lake builds on low disk
"""

    summary = {
        "version": VERSION,
        "status": "CONTROL_REPLAY_APPROVAL_GATE_LEDGERED",
        "input_version": summary23.get("version"),
        "approval_state": "NOT_APPROVED",
        "selected_action": "PARK_REPLAY_AND_RETURN_TO_MANUAL_OUTBOUND_REVIEW",
        "control_ready_count": len(control_items),
        "exact_source_ready_count": len(exact_items),
        "obstruction_count": len(obstruction_items),
        "replay_attempted": False,
        "approval_token_required": "APPROVE_PINNED_CONTROL_REPLAY_V4_4_24",
        "bounded_claim": [
            "v4.4.24 records the replay approval gate after the v4.4.23 replay-or-obstruction queue",
            "because no explicit approval token is present, v4.4.24 parks replay and returns to manual outbound review",
            "it packages the pinned control replay command list but does not execute it",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches beyond v4.4.11 evidence",
            "that exact-source-ready local matches are fresh targets",
            "that any fresh target verifies",
            "automated external contact",
            "upstream acceptance",
            "permission to run heavy lake builds on low disk",
        ],
        "next_frontier": "v4.4.25 either manually send or rewrite the outbound upstream message; only run pinned control replay if the approval token is explicitly supplied",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "approval_gate.json", approval_gate)
    write_json(OUT / "pinned_control_replay_commands_not_executed.json", packaged_commands)
    (OUT / "manual_review_packet.md").write_text(manual_review_packet, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
