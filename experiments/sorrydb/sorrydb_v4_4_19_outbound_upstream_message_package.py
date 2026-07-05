from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.19"
OUT = Path("artifacts/sorrydb/outbound_upstream_message_v4_4_19")

INPUTS = {
    "reviewer_summary": Path("artifacts/sorrydb/reviewer_patch_note_v4_4_18/summary.json"),
    "reviewer_patch_note": Path("artifacts/sorrydb/reviewer_patch_note_v4_4_18/reviewer_patch_note.md"),
    "replay_checklist": Path("artifacts/sorrydb/reviewer_patch_note_v4_4_18/replay_checklist.json"),
    "patch_bundle_summary": Path("artifacts/sorrydb/upstream_patch_bundle_v4_4_17/summary.json"),
    "patch_bundle": Path("artifacts/sorrydb/upstream_patch_bundle_v4_4_17/upstream_patch_bundle.json"),
}

TARGET_REPO = "siddhartha-gadgil/MetaExamples"
TARGET_COMMIT = "edbb75e784db19846a1c19841e182b797afc18bb"
TARGET_FILE = "MetaExamples/Fiddle.lean"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    missing = [str(path) for path in INPUTS.values() if not path.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    reviewer_summary = load_json(INPUTS["reviewer_summary"])
    checklist = load_json(INPUTS["replay_checklist"])
    bundle_summary = load_json(INPUTS["patch_bundle_summary"])
    bundle = load_json(INPUTS["patch_bundle"])
    reviewer_note_text = INPUTS["reviewer_patch_note"].read_text(encoding="utf-8")

    patches = bundle.get("patches", [])
    if len(patches) != 2:
        raise SystemExit(f"expected two patches, got {len(patches)}")

    outbound_subject = "Two exact-source Lean repairs for MetaExamples/Fiddle.lean with replay evidence"

    outbound_message = f"""Hi,

I found two small exact-source repairs for MetaExamples/Fiddle.lean at commit {TARGET_COMMIT}.

They replace two local sorry blocks with Lean terms that replayed successfully in my pinned checkout after cache hydration.

Patch 1:
{patches[0]["human_summary"]}

Patch 2:
{patches[1]["human_summary"]}

Evidence summary:

- target repo: {TARGET_REPO}
- pinned commit: {TARGET_COMMIT}
- target file: {TARGET_FILE}
- exact-source patch candidates: 2
- accepted replay certificates: {bundle_summary.get("accepted_replay_certificate_count")}
- deduplicated repair classes: {bundle_summary.get("unique_repair_class_count")}
- reviewer checklist artifact: artifacts/sorrydb/reviewer_patch_note_v4_4_18/reviewer_patch_note.md
- patch evidence bundle artifact: artifacts/sorrydb/upstream_patch_bundle_v4_4_17/upstream_patch_bundle.json

Important boundary:

This is not a claim of upstream acceptance, general proof repair, or portability. It is an exact-source evidence bundle: apply only if the source snippets match exactly, then rerun Lean in your checkout.

Suggested replay:

1. checkout {TARGET_REPO} at {TARGET_COMMIT}
2. run the baseline Lean check on {TARGET_FILE}
3. apply the two exact-source replacements
4. rerun Lean on {TARGET_FILE}
5. accept only if your checkout verifies

Thanks.
"""

    pr_body = f"""## Summary

This package prepares an outbound upstream-facing message for two exact-source Lean repair candidates in `{TARGET_FILE}` at commit `{TARGET_COMMIT}`.

## Evidence

- exact-source patch candidates: 2
- accepted replay certificates: {bundle_summary.get("accepted_replay_certificate_count")}
- deduplicated repair classes: {bundle_summary.get("unique_repair_class_count")}
- reviewer checklist: `artifacts/sorrydb/reviewer_patch_note_v4_4_18/reviewer_patch_note.md`
- patch evidence bundle: `artifacts/sorrydb/upstream_patch_bundle_v4_4_17/upstream_patch_bundle.json`

## Bounded claim

- v4.4.19 creates a minimal outbound upstream message package from the v4.4.18 reviewer patch note and replay checklist.
- the package contains a subject line, reviewer message, PR body draft, and artifact link map.
- the message is suitable for human review before any external contact.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- general SorryDB mining
- arbitrary proof repair
- upstream acceptance
- semantic portability beyond exact-source replay or verified adapters
- authority to contact or modify the upstream repository without human approval
"""

    artifact_links = {
        "version": VERSION,
        "links": [
            {
                "label": "reviewer_patch_note",
                "path": "artifacts/sorrydb/reviewer_patch_note_v4_4_18/reviewer_patch_note.md",
                "role": "human-readable exact replay note",
            },
            {
                "label": "replay_checklist",
                "path": "artifacts/sorrydb/reviewer_patch_note_v4_4_18/replay_checklist.json",
                "role": "machine-readable replay checklist",
            },
            {
                "label": "upstream_patch_bundle",
                "path": "artifacts/sorrydb/upstream_patch_bundle_v4_4_17/upstream_patch_bundle.json",
                "role": "patch evidence bundle",
            },
            {
                "label": "microflywheel_report",
                "path": "artifacts/sorrydb/microflywheel_report_v4_4_15/report.md",
                "role": "end-to-end obstruction-to-certificate report",
            },
        ],
    }

    package = {
        "version": VERSION,
        "package_type": "OUTBOUND_UPSTREAM_MESSAGE_PACKAGE",
        "target_repo": TARGET_REPO,
        "target_commit": TARGET_COMMIT,
        "target_file": TARGET_FILE,
        "subject": outbound_subject,
        "message_path": str(OUT / "outbound_message.md"),
        "pr_body_path": str(OUT / "upstream_pr_body.md"),
        "artifact_links_path": str(OUT / "artifact_links.json"),
        "patch_count": len(patches),
        "accepted_replay_certificate_count": bundle_summary.get("accepted_replay_certificate_count"),
        "unique_repair_class_count": bundle_summary.get("unique_repair_class_count"),
        "human_approval_required": True,
    }

    summary = {
        "version": VERSION,
        "status": "OUTBOUND_UPSTREAM_MESSAGE_PACKAGE_LEDGERED",
        "input_version": reviewer_summary.get("version"),
        "target_repo": TARGET_REPO,
        "target_commit": TARGET_COMMIT,
        "target_file": TARGET_FILE,
        "patch_count": len(patches),
        "accepted_replay_certificate_count": bundle_summary.get("accepted_replay_certificate_count"),
        "unique_repair_class_count": bundle_summary.get("unique_repair_class_count"),
        "human_approval_required": True,
        "bounded_claim": [
            "v4.4.19 creates a minimal outbound upstream message package from the v4.4.18 reviewer patch note and replay checklist",
            "the package contains a subject line, reviewer message, PR body draft, and artifact link map",
            "the message is suitable for human review before any external contact",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches beyond v4.4.11 evidence",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream acceptance",
            "semantic portability beyond exact-source replay or verified adapters",
            "authority to contact or modify the upstream repository without human approval",
        ],
        "next_frontier": "v4.4.20 either send/rework the outbound note manually, or build a fresh-source replay pilot",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "outbound_message_package.json", package)
    write_json(OUT / "artifact_links.json", artifact_links)
    (OUT / "outbound_message.md").write_text(outbound_message, encoding="utf-8")
    (OUT / "upstream_pr_body.md").write_text(pr_body, encoding="utf-8")
    snapshot_text = reviewer_note_text
    if "Replay checklist" not in snapshot_text:
        snapshot_text = snapshot_text + "\n\n## Replay checklist\n\nSee `replay_checklist.json` and the reviewer patch note above.\n"
    (OUT / "reviewer_patch_note_snapshot.md").write_text(snapshot_text, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
