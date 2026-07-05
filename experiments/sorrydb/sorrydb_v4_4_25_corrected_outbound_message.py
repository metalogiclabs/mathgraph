from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.25"
OUT = Path("artifacts/sorrydb/corrected_outbound_message_v4_4_25")

INPUTS = {
    "v4419_summary": Path("artifacts/sorrydb/outbound_upstream_message_v4_4_19/summary.json"),
    "v4419_message": Path("artifacts/sorrydb/outbound_upstream_message_v4_4_19/outbound_message.md"),
    "v4417_bundle": Path("artifacts/sorrydb/upstream_patch_bundle_v4_4_17/upstream_patch_bundle.json"),
    "v4418_note": Path("artifacts/sorrydb/reviewer_patch_note_v4_4_18/reviewer_patch_note.md"),
    "v4424_gate": Path("artifacts/sorrydb/control_replay_approval_gate_v4_4_24/summary.json"),
}

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def main() -> None:
    missing = [str(p) for p in INPUTS.values() if not p.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    old_summary = load_json(INPUTS["v4419_summary"])
    old_message = INPUTS["v4419_message"].read_text(encoding="utf-8")
    bundle = load_json(INPUTS["v4417_bundle"])
    gate = load_json(INPUTS["v4424_gate"])

    patches = bundle.get("patches", [])
    if len(patches) != 2:
        raise SystemExit(f"expected 2 patches, got {len(patches)}")

    patch_lines = []
    replacement_terms = []
    for idx, patch in enumerate(patches, start=1):
        replacement = patch.get("replacement_snippet", "").strip()
        source = patch.get("source_snippet", "").strip()
        if not replacement:
            raise SystemExit(f"patch {idx} missing replacement_snippet")
        replacement_terms.append(replacement)
        patch_lines.append(
            f"""Patch {idx}:
Source snippet:
{source}

Replacement:
{replacement}
"""
        )

    if len(set(replacement_terms)) != len(replacement_terms):
        raise SystemExit("replacement snippets are still duplicated; inspect upstream_patch_bundle.json")

    subject = "Two exact-source Lean repairs for MetaExamples/Fiddle.lean with replay evidence"

    corrected_message = f"""Hi,

I found two small exact-source repairs for MetaExamples/Fiddle.lean at commit {bundle["target_commit"]}.

They replace two local sorry blocks with Lean terms that replayed successfully in my pinned checkout after cache hydration.

{patch_lines[0]}
{patch_lines[1]}
Evidence summary:

- target repo: {bundle["target_repo"]}
- pinned commit: {bundle["target_commit"]}
- target file: {bundle["target_file"]}
- exact-source patch candidates: {len(patches)}
- accepted replay certificates: {old_summary["accepted_replay_certificate_count"]}
- deduplicated repair classes: {old_summary["unique_repair_class_count"]}
- reviewer checklist artifact: artifacts/sorrydb/reviewer_patch_note_v4_4_18/reviewer_patch_note.md
- patch evidence bundle artifact: artifacts/sorrydb/upstream_patch_bundle_v4_4_17/upstream_patch_bundle.json

Important boundary:

This is not a claim of upstream acceptance, general proof repair, or portability. It is an exact-source evidence bundle: apply only if the source snippets match exactly, then rerun Lean in your checkout.

Suggested replay:

1. checkout {bundle["target_repo"]} at {bundle["target_commit"]}
2. run the baseline Lean check on {bundle["target_file"]}
3. apply the two exact-source replacements above
4. rerun Lean on {bundle["target_file"]}
5. accept only if your checkout verifies

Thanks.
"""

    corrected_pr_body = f"""## Summary

This corrects the v4.4.19 outbound upstream message package.

The previous outbound message duplicated the Patch 1 summary in the Patch 2 slot. v4.4.25 regenerates the outbound text directly from the v4.4.17 patch bundle replacement snippets and records the correction before any manual upstream contact.

## Evidence

- target repo: `{bundle["target_repo"]}`
- target commit: `{bundle["target_commit"]}`
- target file: `{bundle["target_file"]}`
- exact-source patch candidates: {len(patches)}
- accepted replay certificates: {old_summary["accepted_replay_certificate_count"]}
- deduplicated repair classes: {old_summary["unique_repair_class_count"]}

## Bounded claim

- v4.4.25 corrects the human-facing outbound message by deriving both patch descriptions from the patch bundle.
- v4.4.25 detects and rejects duplicated replacement snippets.
- no upstream message is sent and no Lean replay is executed.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- upstream acceptance
- automated external contact
- that any fresh target verifies
- permission to run heavy lake builds on low disk
"""

    summary = {
        "version": VERSION,
        "status": "CORRECTED_OUTBOUND_MESSAGE_LEDGERED",
        "input_version": old_summary.get("version"),
        "approval_gate_version": gate.get("version"),
        "patch_count": len(patches),
        "accepted_replay_certificate_count": old_summary["accepted_replay_certificate_count"],
        "unique_repair_class_count": old_summary["unique_repair_class_count"],
        "detected_prior_message_duplicate": old_message.count("Replace the eg₁ sorry with exact Nat.le_add_right n 1.") >= 2,
        "corrected_replacement_terms": replacement_terms,
        "replacement_terms_unique": len(set(replacement_terms)) == len(replacement_terms),
        "upstream_contact_performed": False,
        "replay_attempted": False,
        "bounded_claim": [
            "v4.4.25 corrects the human-facing outbound message by deriving both patch descriptions from the patch bundle",
            "v4.4.25 detects and rejects duplicated replacement snippets",
            "no upstream message is sent and no Lean replay is executed",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches beyond v4.4.11 evidence",
            "upstream acceptance",
            "automated external contact",
            "that any fresh target verifies",
            "permission to run heavy lake builds on low disk",
        ],
        "next_frontier": "manually review corrected_outbound_message.md, then decide whether to send upstream",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    (OUT / "corrected_outbound_message.md").write_text(corrected_message, encoding="utf-8")
    (OUT / "corrected_upstream_pr_body.md").write_text(corrected_pr_body, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
