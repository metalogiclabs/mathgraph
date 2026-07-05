from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.15"
OUT = Path("artifacts/sorrydb/microflywheel_report_v4_4_15")

INPUTS = {
    "v4.4.7": Path("artifacts/sorrydb/hydrated_backfill_queue_v4_4_7/backfill_queue.json"),
    "v4.4.8": Path("artifacts/sorrydb/hydrated_backfill_reality_v4_4_8/summary.json"),
    "v4.4.9": Path("artifacts/sorrydb/cache_hydration_plan_v4_4_9/summary.json"),
    "v4.4.10": Path("artifacts/sorrydb/cache_hydration_reality_v4_4_10/summary.json"),
    "v4.4.11": Path("artifacts/sorrydb/hydrated_backfill_after_cache_v4_4_11/summary.json"),
    "v4.4.12": Path("artifacts/sorrydb/accepted_certificate_dedup_v4_4_12/summary.json"),
    "v4.4.13": Path("artifacts/sorrydb/compact_lawbook_seed_v4_4_13/summary.json"),
    "v4.4.14": Path("artifacts/sorrydb/source_cleanliness_v4_4_14/summary.json"),
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

    loaded = {version: load_json(path) for version, path in INPUTS.items()}

    stages = [
        {
            "version": "v4.4.7",
            "stage": "hydrated_source_backfill_queue_planned",
            "terminal_observation": "four hydrated source rows became queue-compatible candidates",
            "input_path": str(INPUTS["v4.4.7"]),
            "claim_type": "planner",
        },
        {
            "version": "v4.4.8",
            "stage": "hydrated_backfill_reality_before_cache",
            "terminal_observation": loaded["v4.4.8"].get("verdict", loaded["v4.4.8"].get("status", "")),
            "accepted_count": loaded["v4.4.8"].get("accepted_count"),
            "failed_count": loaded["v4.4.8"].get("failed_count"),
            "claim_type": "obstruction",
        },
        {
            "version": "v4.4.9",
            "stage": "cache_dependency_hydration_planned",
            "terminal_observation": loaded["v4.4.9"].get("cache_hydration_status"),
            "recommended_command": loaded["v4.4.9"].get("recommended_command"),
            "claim_type": "planner",
        },
        {
            "version": "v4.4.10",
            "stage": "cache_hydration_reality",
            "terminal_observation": loaded["v4.4.10"].get("status"),
            "mathlib_olean_exists": loaded["v4.4.10"].get("mathlib_olean_exists"),
            "baseline_contact_passed": loaded["v4.4.10"].get("baseline_contact_passed"),
            "claim_type": "environment_contact",
        },
        {
            "version": "v4.4.11",
            "stage": "hydrated_backfill_after_cache_accepted",
            "terminal_observation": loaded["v4.4.11"].get("status"),
            "candidate_count": loaded["v4.4.11"].get("candidate_count"),
            "accepted_count": loaded["v4.4.11"].get("accepted_count"),
            "failed_count": loaded["v4.4.11"].get("failed_count"),
            "claim_type": "accepted_replay",
        },
        {
            "version": "v4.4.12",
            "stage": "accepted_certificate_dedup",
            "terminal_observation": loaded["v4.4.12"].get("status"),
            "accepted_certificate_count": loaded["v4.4.12"].get("accepted_certificate_count"),
            "unique_repair_class_count": loaded["v4.4.12"].get("unique_repair_class_count"),
            "duplicate_certificate_count": loaded["v4.4.12"].get("duplicate_certificate_count"),
            "claim_type": "deduplication",
        },
        {
            "version": "v4.4.13",
            "stage": "compact_lawbook_seed_bundle",
            "terminal_observation": loaded["v4.4.13"].get("status"),
            "lawbook_seed_count": loaded["v4.4.13"].get("lawbook_seed_count"),
            "claim_type": "seed_packaging",
        },
        {
            "version": "v4.4.14",
            "stage": "source_cleanliness_replay_restoration",
            "terminal_observation": loaded["v4.4.14"].get("status"),
            "restoration_invariant_passed": loaded["v4.4.14"].get("restoration_invariant_passed"),
            "source_tracked_changes_clean": loaded["v4.4.14"].get("source_tracked_changes_clean"),
            "source_has_untracked_paths": loaded["v4.4.14"].get("source_has_untracked_paths"),
            "claim_type": "restoration_invariant",
        },
    ]

    flywheel = {
        "version": VERSION,
        "name": "SorryDB minimal end-to-end microflywheel",
        "loop": [
            "hydrated source candidates",
            "controlled replay obstruction",
            "cache hydration plan",
            "authorized cache hydration reality",
            "accepted replay",
            "deduplication",
            "compact Lawbook seed packaging",
            "source restoration invariant",
        ],
        "stages": stages,
    }

    scoreboard = {
        "version": VERSION,
        "before_cache": {
            "accepted_count": loaded["v4.4.8"].get("accepted_count"),
            "failed_count": loaded["v4.4.8"].get("failed_count"),
        },
        "after_cache": {
            "candidate_count": loaded["v4.4.11"].get("candidate_count"),
            "accepted_count": loaded["v4.4.11"].get("accepted_count"),
            "failed_count": loaded["v4.4.11"].get("failed_count"),
        },
        "deduplicated": {
            "accepted_certificate_count": loaded["v4.4.12"].get("accepted_certificate_count"),
            "unique_repair_class_count": loaded["v4.4.12"].get("unique_repair_class_count"),
            "duplicate_certificate_count": loaded["v4.4.12"].get("duplicate_certificate_count"),
            "lawbook_seed_count": loaded["v4.4.13"].get("lawbook_seed_count"),
        },
        "restoration": {
            "restoration_invariant_passed": loaded["v4.4.14"].get("restoration_invariant_passed"),
            "source_tracked_changes_clean": loaded["v4.4.14"].get("source_tracked_changes_clean"),
            "target_diff_clean": loaded["v4.4.14"].get("target_diff_clean"),
        },
    }

    summary = {
        "version": VERSION,
        "status": "MICROFLYWHEEL_REPORT_LEDGERED",
        "bounded_claim": [
            "v4.4.15 packages the minimal end-to-end SorryDB microflywheel from v4.4.7 through v4.4.14",
            "the report shows one obstruction-to-certificate chain crossing cache/build failure into accepted replay",
            "the final compact artifact contains two deduplicated Lawbook replay seeds backed by four accepted replay certificates",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream submission",
            "production readiness",
            "semantic portability beyond exact-source replay or verified adapters",
        ],
        "headline": {
            "accepted_after_cache": loaded["v4.4.11"].get("accepted_count"),
            "unique_repair_classes": loaded["v4.4.12"].get("unique_repair_class_count"),
            "lawbook_seed_count": loaded["v4.4.13"].get("lawbook_seed_count"),
            "restoration_invariant_passed": loaded["v4.4.14"].get("restoration_invariant_passed"),
        },
        "next_frontier": "v4.4.16 choose one scale path: more SorryDB source worlds, upstream patch package, or replay-seed reuse on fresh targets",
    }

    report_md = """# SorryDB v4.4.15 — Minimal End-to-End Microflywheel Report

## Headline

The v4.4.7–v4.4.14 chain demonstrates a complete bounded MathGraph loop:

hydrated source candidates
to controlled replay obstruction
to cache hydration plan
to authorized cache hydration reality
to accepted replay
to deduplication
to compact Lawbook seed packaging
to source restoration invariant

## Scoreboard

- before cache: {before_accepted} accepted, {before_failed} failed
- after cache: {after_accepted} accepted, {after_failed} failed
- accepted replay certificates: {certs}
- unique repair classes: {classes}
- duplicate certificate identities: {dupes}
- compact Lawbook seeds: {seeds}
- restoration invariant passed: {restored}

## Bounded claim

- v4.4.15 packages the minimal end-to-end SorryDB microflywheel from v4.4.7 through v4.4.14.
- the report shows one obstruction-to-certificate chain crossing cache/build failure into accepted replay.
- the final compact artifact contains two deduplicated Lawbook replay seeds backed by four accepted replay certificates.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches
- general SorryDB mining
- arbitrary proof repair
- upstream submission
- production readiness
- semantic portability beyond exact-source replay or verified adapters

## Next frontier

v4.4.16 should choose one scale path: more SorryDB source worlds, upstream patch package, or replay-seed reuse on fresh targets.
""".format(
        before_accepted=scoreboard["before_cache"]["accepted_count"],
        before_failed=scoreboard["before_cache"]["failed_count"],
        after_accepted=scoreboard["after_cache"]["accepted_count"],
        after_failed=scoreboard["after_cache"]["failed_count"],
        certs=scoreboard["deduplicated"]["accepted_certificate_count"],
        classes=scoreboard["deduplicated"]["unique_repair_class_count"],
        dupes=scoreboard["deduplicated"]["duplicate_certificate_count"],
        seeds=scoreboard["deduplicated"]["lawbook_seed_count"],
        restored=scoreboard["restoration"]["restoration_invariant_passed"],
    )

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "flywheel.json", flywheel)
    write_json(OUT / "scoreboard.json", scoreboard)
    (OUT / "report.md").write_text(report_md, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
