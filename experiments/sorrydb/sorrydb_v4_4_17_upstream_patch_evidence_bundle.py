from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.17"
OUT = Path("artifacts/sorrydb/upstream_patch_bundle_v4_4_17")

INPUTS = {
    "scale_path": Path("artifacts/sorrydb/scale_path_selector_v4_4_16/summary.json"),
    "seed_index": Path("artifacts/sorrydb/compact_lawbook_seed_v4_4_13/lawbook_seed_index.json"),
    "replay_seed_queue": Path("artifacts/sorrydb/compact_lawbook_seed_v4_4_13/replay_seed_queue.json"),
    "dedup_classes": Path("artifacts/sorrydb/accepted_certificate_dedup_v4_4_12/dedup_classes.json"),
    "v4411_summary": Path("artifacts/sorrydb/hydrated_backfill_after_cache_v4_4_11/summary.json"),
    "v4410_summary": Path("artifacts/sorrydb/cache_hydration_reality_v4_4_10/summary.json"),
    "v4415_summary": Path("artifacts/sorrydb/microflywheel_report_v4_4_15/summary.json"),
}

EXPECTED_REPO = "siddhartha-gadgil/MetaExamples"
EXPECTED_COMMIT = "edbb75e784db19846a1c19841e182b797afc18bb"
TARGET_FILE = "MetaExamples/Fiddle.lean"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize_seed(seed: dict[str, Any], ordinal: int) -> dict[str, Any]:
    source = seed.get("source_snippet", "")
    patch = seed.get("patch_snippet", "")
    if "Nat.le_add_right" in patch:
        repair_name = "eg1_line97_nat_le_add_right"
        human_summary = "Replace the eg₁ sorry with exact Nat.le_add_right n 1."
    elif "Nat.succ_le_succ" in patch:
        repair_name = "eg2_line99_nat_succ_le_succ_nat_le_add_right"
        human_summary = "Replace the eg₂ sorry with exact Nat.succ_le_succ (Nat.le_add_right n 1)."
    else:
        repair_name = f"repair_{ordinal:03d}"
        human_summary = "Accepted exact-source repair seed."

    return {
        "patch_id": f"upstream-patch-{ordinal:03d}",
        "repair_name": repair_name,
        "human_summary": human_summary,
        "source_class_id": seed.get("source_class_id"),
        "source_seed_id": seed.get("seed_id"),
        "representative_certificate_id": seed.get("representative_certificate_id"),
        "certificate_ids": seed.get("certificate_ids", []),
        "manifest_paths": seed.get("manifest_paths", []),
        "target": {
            "repo": EXPECTED_REPO,
            "repo_root": seed.get("repo_root", ""),
            "repo_commit": seed.get("repo_commit") or EXPECTED_COMMIT,
            "file_path": seed.get("file_path") or TARGET_FILE,
            "line_span": seed.get("line_span", ""),
        },
        "source_snippet": source,
        "replacement_snippet": patch,
        "accepted_replay_evidence": seed.get("replay_evidence", {}),
        "reuse_contract": seed.get("reuse_contract", {}),
        "upstream_claim": {
            "claim_type": "exact_source_patch_candidate",
            "requires_upstream_review": True,
            "requires_fresh_replay_in_recipient_checkout": True,
            "portable_without_replay": False,
        },
    }


def main() -> None:
    missing = [str(path) for path in INPUTS.values() if not path.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    scale_path = load_json(INPUTS["scale_path"])
    seed_index = load_json(INPUTS["seed_index"])
    replay_seed_queue = load_json(INPUTS["replay_seed_queue"])
    dedup_classes = load_json(INPUTS["dedup_classes"])
    v4411 = load_json(INPUTS["v4411_summary"])
    v4410 = load_json(INPUTS["v4410_summary"])
    v4415 = load_json(INPUTS["v4415_summary"])

    selected = scale_path.get("selected_path_id")
    if selected != "upstream_patch_package":
        raise SystemExit(f"v4.4.16 did not select upstream_patch_package: {selected}")

    seeds = seed_index.get("seeds", [])
    if len(seeds) != 2:
        raise SystemExit(f"expected two lawbook seeds, got {len(seeds)}")

    patches = [normalize_seed(seed, idx + 1) for idx, seed in enumerate(seeds)]

    bundle = {
        "version": VERSION,
        "bundle_type": "UPSTREAM_EXACT_SOURCE_PATCH_EVIDENCE_BUNDLE",
        "target_repo": EXPECTED_REPO,
        "target_commit": EXPECTED_COMMIT,
        "target_file": TARGET_FILE,
        "patch_count": len(patches),
        "patches": patches,
        "evidence_chain": [
            {
                "version": "v4.4.10",
                "role": "cache_hydration_reality",
                "status": v4410.get("status"),
                "baseline_contact_passed": v4410.get("baseline_contact_passed"),
                "mathlib_olean_exists": v4410.get("mathlib_olean_exists"),
            },
            {
                "version": "v4.4.11",
                "role": "accepted_replay",
                "status": v4411.get("status"),
                "accepted_count": v4411.get("accepted_count"),
                "failed_count": v4411.get("failed_count"),
            },
            {
                "version": "v4.4.12",
                "role": "deduplication",
                "class_count": len(dedup_classes.get("classes", [])),
            },
            {
                "version": "v4.4.13",
                "role": "lawbook_seed_packaging",
                "seed_count": seed_index.get("seed_count"),
            },
            {
                "version": "v4.4.15",
                "role": "microflywheel_report",
                "headline": v4415.get("headline", {}),
            },
            {
                "version": "v4.4.16",
                "role": "scale_path_selection",
                "selected_path_id": scale_path.get("selected_path_id"),
            },
        ],
        "recipient_instructions": [
            "checkout the target repository at the pinned commit",
            "apply each replacement only to the exact matching source snippet",
            "run Lean in the recipient checkout before accepting the patch",
            "treat the bundle as evidence, not authority",
        ],
    }

    summary = {
        "version": VERSION,
        "status": "UPSTREAM_PATCH_EVIDENCE_BUNDLE_LEDGERED",
        "selected_path_id": selected,
        "target_repo": EXPECTED_REPO,
        "target_commit": EXPECTED_COMMIT,
        "target_file": TARGET_FILE,
        "patch_count": len(patches),
        "accepted_replay_certificate_count": v4411.get("accepted_count"),
        "unique_repair_class_count": len(dedup_classes.get("classes", [])),
        "lawbook_seed_count": seed_index.get("seed_count"),
        "bounded_claim": [
            "v4.4.17 packages the two deduplicated accepted repair seeds into an upstream-facing exact-source patch evidence bundle",
            "each patch candidate includes source snippet, replacement snippet, target repo, pinned commit, file path, certificate ids, and accepted replay evidence",
            "the bundle is evidence for review and replay, not an upstream acceptance claim",
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
        "next_frontier": "v4.4.18 generate a reviewer-facing patch note and exact replay checklist",
    }

    reviewer_note = f"""# SorryDB v4.4.17 — Upstream Patch Evidence Bundle

Target repository: {EXPECTED_REPO}
Pinned commit: {EXPECTED_COMMIT}
Target file: {TARGET_FILE}

This bundle contains {len(patches)} exact-source patch candidates.

## Candidate 1

{patches[0]["human_summary"]}

Source snippet:

{patches[0]["source_snippet"]}

Replacement snippet:

{patches[0]["replacement_snippet"]}

Evidence certificates:

{chr(10).join("- " + c for c in patches[0]["certificate_ids"])}

## Candidate 2

{patches[1]["human_summary"]}

Source snippet:

{patches[1]["source_snippet"]}

Replacement snippet:

{patches[1]["replacement_snippet"]}

Evidence certificates:

{chr(10).join("- " + c for c in patches[1]["certificate_ids"])}

## Bounded claim

- v4.4.17 packages the two deduplicated accepted repair seeds into an upstream-facing exact-source patch evidence bundle.
- each patch candidate includes source snippet, replacement snippet, target repo, pinned commit, file path, certificate ids, and accepted replay evidence.
- the bundle is evidence for review and replay, not an upstream acceptance claim.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- general SorryDB mining
- arbitrary proof repair
- upstream acceptance
- semantic portability beyond exact-source replay or verified adapters
- authority to modify the upstream repository

## Replay checklist

- checkout the target repository at the pinned commit
- apply each replacement only to the exact matching source snippet
- run Lean in the recipient checkout
- accept only if the recipient checkout verifies
"""

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "upstream_patch_bundle.json", bundle)
    (OUT / "reviewer_note.md").write_text(reviewer_note, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
