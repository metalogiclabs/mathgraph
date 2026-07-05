from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

VERSION = "v4.4.26"
OUT = Path("artifacts/sorrydb/upstream_repair_flywheel_tracker_v4_4_26")

INPUTS = {
    "corrected_summary": Path("artifacts/sorrydb/corrected_outbound_message_v4_4_25/summary.json"),
    "corrected_message": Path("artifacts/sorrydb/corrected_outbound_message_v4_4_25/corrected_outbound_message.md"),
    "patch_bundle": Path("artifacts/sorrydb/upstream_patch_bundle_v4_4_17/upstream_patch_bundle.json"),
}

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def normalize_contact(raw: str) -> tuple[str, str]:
    raw = raw.strip()
    if raw == "NOT_SENT":
        return "NOT_SENT", ""
    if raw.startswith("https://github.com/"):
        return "SENT_AWAITING_RESPONSE", raw
    return "UNVERIFIED_CONTACT_REFERENCE", raw

def main() -> None:
    missing = [str(p) for p in INPUTS.values() if not p.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    raw_contact = os.environ.get("UPSTREAM_CONTACT_URL", "NOT_SENT")
    upstream_status, upstream_url = normalize_contact(raw_contact)

    corrected = load_json(INPUTS["corrected_summary"])
    bundle = load_json(INPUTS["patch_bundle"])
    message = INPUTS["corrected_message"].read_text(encoding="utf-8")

    attempt = {
        "attempt_id": "sorry-pr-001",
        "version": VERSION,
        "target_repo": bundle["target_repo"],
        "target_commit": bundle["target_commit"],
        "target_file": bundle["target_file"],
        "patch_count": corrected["patch_count"],
        "accepted_replay_certificate_count": corrected["accepted_replay_certificate_count"],
        "unique_repair_class_count": corrected["unique_repair_class_count"],
        "local_replay_status": "ACCEPTED_IN_PINNED_CHECKOUT",
        "outbound_message_artifact": "artifacts/sorrydb/corrected_outbound_message_v4_4_25/corrected_outbound_message.md",
        "upstream_contact_status": upstream_status,
        "upstream_contact_url": upstream_url,
        "external_outcome": "PENDING" if upstream_status.startswith("SENT") else "NOT_SENT",
        "maintainer_feedback": "",
        "obstruction_if_rejected": "",
        "lawbook_seed_if_accepted": "",
        "next_action": "wait for upstream response" if upstream_status.startswith("SENT") else "send corrected outbound message manually",
    }

    tracker = {
        "version": VERSION,
        "tracker_type": "SORRY_TO_PR_FLYWHEEL",
        "goal": "10 upstream-visible Lean repair attempts; at least 1 accepted upstream repair",
        "attempt_count": 1,
        "sent_count": 1 if upstream_status.startswith("SENT") else 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "pending_count": 1 if upstream_status.startswith("SENT") else 0,
        "not_sent_count": 1 if upstream_status == "NOT_SENT" else 0,
        "attempts": [attempt],
        "score": {
            "internal_evidence_chain": 9,
            "trust_boundary_discipline": 9,
            "external_impact": 4 if upstream_status == "NOT_SENT" else 5,
            "overall": 7.8 if upstream_status == "NOT_SENT" else 8.0,
        },
        "next_frontier": [
            "record upstream response when it arrives",
            "find 9 more small exact-source Lean sorry repair attempts",
            "prefer boring accepted micro-repairs over hard theorem attempts",
        ],
        "bounded_claim": [
            "v4.4.26 starts the Sorry-to-PR flywheel tracker with the MetaExamples exact-source repair attempt",
            "it records whether the corrected outbound message has been sent manually",
            "it defines the external outcome fields needed to score accepted, rejected, ignored, or obstructed repairs",
        ],
        "does_not_claim": [
            "upstream acceptance",
            "new proof discovery",
            "new Lean replay",
            "automated external contact",
            "that the maintainer has responded",
            "that local replay implies portability",
        ],
    }

    csv_rows = [
        {
            "attempt_id": attempt["attempt_id"],
            "target_repo": attempt["target_repo"],
            "target_commit": attempt["target_commit"],
            "target_file": attempt["target_file"],
            "patch_count": attempt["patch_count"],
            "local_replay_status": attempt["local_replay_status"],
            "upstream_contact_status": attempt["upstream_contact_status"],
            "upstream_contact_url": attempt["upstream_contact_url"],
            "external_outcome": attempt["external_outcome"],
            "next_action": attempt["next_action"],
        }
    ]

    report = f"""# SorryDB v4.4.26 — Upstream Repair Flywheel Tracker

## Goal

10 upstream-visible Lean repair attempts, with at least 1 accepted upstream repair.

## Current attempt

- attempt id: {attempt["attempt_id"]}
- target repo: {attempt["target_repo"]}
- target commit: {attempt["target_commit"]}
- target file: {attempt["target_file"]}
- patch count: {attempt["patch_count"]}
- local replay status: {attempt["local_replay_status"]}
- upstream contact status: {attempt["upstream_contact_status"]}
- upstream contact url: {attempt["upstream_contact_url"] or "(none)"}
- external outcome: {attempt["external_outcome"]}

## Next action

{attempt["next_action"]}

## Bounded claim

- v4.4.26 starts the Sorry-to-PR flywheel tracker with the MetaExamples exact-source repair attempt.
- it records whether the corrected outbound message has been sent manually.
- it defines the external outcome fields needed to score accepted, rejected, ignored, or obstructed repairs.

## Does not claim

- upstream acceptance
- new proof discovery
- new Lean replay
- automated external contact
- that the maintainer has responded
- that local replay implies portability
"""

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", tracker)
    write_json(OUT / "attempt_001.json", attempt)
    (OUT / "report.md").write_text(report, encoding="utf-8")

    with (OUT / "attempts.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

    print(json.dumps(tracker, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
