from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.18"
OUT = Path("artifacts/sorrydb/reviewer_patch_note_v4_4_18")

INPUTS = {
    "summary": Path("artifacts/sorrydb/upstream_patch_bundle_v4_4_17/summary.json"),
    "bundle": Path("artifacts/sorrydb/upstream_patch_bundle_v4_4_17/upstream_patch_bundle.json"),
    "reviewer_note": Path("artifacts/sorrydb/upstream_patch_bundle_v4_4_17/reviewer_note.md"),
}

REPLAY_COMMANDS = [
    "git clone https://github.com/siddhartha-gadgil/MetaExamples.git MetaExamples-sorrydb-v4418-review",
    "cd MetaExamples-sorrydb-v4418-review",
    "git checkout edbb75e784db19846a1c19841e182b797afc18bb",
    "lake exe cache get",
    "lake env lean MetaExamples/Fiddle.lean",
    "apply the two exact-source replacements from the patch note",
    "lake env lean MetaExamples/Fiddle.lean",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def patch_block(patch: dict[str, Any]) -> str:
    certs = "\n".join(f"- {cert}" for cert in patch.get("certificate_ids", []))
    return f"""## {patch["patch_id"]}: {patch["repair_name"]}

Summary: {patch["human_summary"]}

Target:
- repo: {patch["target"]["repo"]}
- commit: {patch["target"]["repo_commit"]}
- file: {patch["target"]["file_path"]}
- line span: {patch["target"].get("line_span", "")}

Source snippet:

{patch["source_snippet"]}

Replacement snippet:

{patch["replacement_snippet"]}

Evidence certificates:

{certs}

Review requirement:

- apply only if the source snippet matches exactly
- rerun Lean in the recipient checkout
- accept only if the recipient checkout verifies
"""


def main() -> None:
    missing = [str(path) for path in INPUTS.values() if not path.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    summary17 = load_json(INPUTS["summary"])
    bundle = load_json(INPUTS["bundle"])
    patches = bundle.get("patches", [])

    if summary17.get("patch_count") != 2:
        raise SystemExit("expected v4.4.17 patch_count == 2")
    if len(patches) != 2:
        raise SystemExit("expected exactly two patches in v4.4.17 bundle")

    checklist = {
        "version": VERSION,
        "checklist_type": "REVIEWER_EXACT_SOURCE_REPLAY_CHECKLIST",
        "target_repo": bundle.get("target_repo"),
        "target_commit": bundle.get("target_commit"),
        "target_file": bundle.get("target_file"),
        "commands": REPLAY_COMMANDS,
        "acceptance_criteria": [
            "target repository checks out at the pinned commit",
            "baseline Lean run succeeds before patching",
            "each source snippet matches exactly before replacement",
            "patched Lean run succeeds after replacement",
            "reviewer accepts the patch on its own merits",
        ],
        "rejection_criteria": [
            "source snippet does not match exactly",
            "baseline Lean run fails in reviewer checkout",
            "patched Lean run fails in reviewer checkout",
            "reviewer rejects the repair",
        ],
    }

    note = f"""# SorryDB v4.4.18 — Reviewer Patch Note and Exact Replay Checklist

This note converts the v4.4.17 upstream patch evidence bundle into a reviewer-facing patch note.

Target repository: {bundle.get("target_repo")}
Pinned commit: {bundle.get("target_commit")}
Target file: {bundle.get("target_file")}

Patch candidates: {len(patches)}

{patch_block(patches[0])}

{patch_block(patches[1])}

## Exact replay checklist

1. Clone the target repository.
2. Checkout the pinned commit.
3. Hydrate the Lean cache if needed.
4. Run the baseline Lean check before applying patches.
5. Apply only exact-source replacements.
6. Run the patched Lean check.
7. Accept only if the recipient checkout verifies.

## Replay commands

{chr(10).join("- " + cmd for cmd in REPLAY_COMMANDS)}

## Bounded claim

- v4.4.18 turns the v4.4.17 upstream patch evidence bundle into a reviewer-facing patch note and exact replay checklist.
- the note contains two exact-source patch candidates backed by four accepted replay certificates from v4.4.11.
- the checklist describes how a reviewer can independently replay the candidate patches.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- general SorryDB mining
- arbitrary proof repair
- upstream acceptance
- semantic portability beyond exact-source replay or verified adapters
- authority to modify the upstream repository
"""

    summary = {
        "version": VERSION,
        "status": "REVIEWER_PATCH_NOTE_REPLAY_CHECKLIST_LEDGERED",
        "input_version": summary17.get("version"),
        "target_repo": bundle.get("target_repo"),
        "target_commit": bundle.get("target_commit"),
        "target_file": bundle.get("target_file"),
        "patch_count": len(patches),
        "checklist_command_count": len(REPLAY_COMMANDS),
        "accepted_replay_certificate_count": summary17.get("accepted_replay_certificate_count"),
        "unique_repair_class_count": summary17.get("unique_repair_class_count"),
        "bounded_claim": [
            "v4.4.18 turns the v4.4.17 upstream patch evidence bundle into a reviewer-facing patch note and exact replay checklist",
            "the note contains two exact-source patch candidates backed by four accepted replay certificates from v4.4.11",
            "the checklist describes how a reviewer can independently replay the candidate patches",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches beyond v4.4.11 evidence",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream acceptance",
            "semantic portability beyond exact-source replay or verified adapters",
            "authority to modify the upstream repository",
        ],
        "next_frontier": "v4.4.19 create a minimal outbound upstream PR/message package with links to the evidence bundle and reviewer checklist",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "replay_checklist.json", checklist)
    (OUT / "reviewer_patch_note.md").write_text(note, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
