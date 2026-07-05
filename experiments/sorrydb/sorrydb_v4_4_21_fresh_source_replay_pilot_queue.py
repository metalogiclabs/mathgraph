from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.21"
OUT = Path("artifacts/sorrydb/fresh_source_replay_pilot_queue_v4_4_21")

INPUTS = {
    "pilot_plan": Path("artifacts/sorrydb/post_outbound_fresh_source_pilot_plan_v4_4_20/summary.json"),
    "pilot_decision": Path("artifacts/sorrydb/post_outbound_fresh_source_pilot_plan_v4_4_20/decision.json"),
    "patch_bundle": Path("artifacts/sorrydb/upstream_patch_bundle_v4_4_17/upstream_patch_bundle.json"),
    "reviewer_checklist": Path("artifacts/sorrydb/reviewer_patch_note_v4_4_18/replay_checklist.json"),
    "lawbook_seed_index": Path("artifacts/sorrydb/compact_lawbook_seed_v4_4_13/lawbook_seed_index.json"),
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

    pilot_plan = load_json(INPUTS["pilot_plan"])
    pilot_decision = load_json(INPUTS["pilot_decision"])
    patch_bundle = load_json(INPUTS["patch_bundle"])
    checklist = load_json(INPUTS["reviewer_checklist"])
    seed_index = load_json(INPUTS["lawbook_seed_index"])

    constraints = pilot_decision.get("pilot_constraints", {})
    max_targets = constraints.get("max_candidate_targets")
    if max_targets != 5:
        raise SystemExit(f"expected max_candidate_targets == 5, got {max_targets}")

    patches = patch_bundle.get("patches", [])
    if len(patches) != 2:
        raise SystemExit(f"expected two seed patches, got {len(patches)}")

    candidates = [
        {
            "candidate_id": "fresh-pilot-001",
            "role": "control_exact_source_replay",
            "candidate_kind": "known_pinned_control",
            "target_repo": patch_bundle.get("target_repo"),
            "target_commit": patch_bundle.get("target_commit"),
            "target_file": patch_bundle.get("target_file"),
            "seed_patch_ids": [p["patch_id"] for p in patches],
            "selection_rule": "Use the already pinned MetaExamples/Fiddle.lean target as a control replay before testing fresh targets.",
            "freshness_status": "CONTROL_NOT_FRESH",
            "allowed_terminal_states": ["ACCEPTED_REPLAY", "FAILED_REPLAY", "OBSTRUCTED_ENVIRONMENT"],
            "requires_heavy_build": False,
        },
        {
            "candidate_id": "fresh-pilot-002",
            "role": "exact_source_snippet_search_eg1",
            "candidate_kind": "fresh_target_discovery_query",
            "source_snippet": patches[0]["source_snippet"],
            "replacement_snippet": patches[0]["replacement_snippet"],
            "selection_rule": "Search bounded local/source registries for an exact match to the eg1 source snippet before attempting replay.",
            "freshness_status": "UNRESOLVED_UNTIL_EXACT_MATCH_FOUND",
            "allowed_terminal_states": ["ACCEPTED_REPLAY", "FAILED_REPLAY", "OBSTRUCTED_EXACT_SOURCE_MISMATCH", "OBSTRUCTED_ENVIRONMENT"],
            "requires_exact_source_match_or_named_adapter": True,
            "requires_heavy_build": False,
        },
        {
            "candidate_id": "fresh-pilot-003",
            "role": "exact_source_snippet_search_eg2",
            "candidate_kind": "fresh_target_discovery_query",
            "source_snippet": patches[1]["source_snippet"],
            "replacement_snippet": patches[1]["replacement_snippet"],
            "selection_rule": "Search bounded local/source registries for an exact match to the eg2 source snippet before attempting replay.",
            "freshness_status": "UNRESOLVED_UNTIL_EXACT_MATCH_FOUND",
            "allowed_terminal_states": ["ACCEPTED_REPLAY", "FAILED_REPLAY", "OBSTRUCTED_EXACT_SOURCE_MISMATCH", "OBSTRUCTED_ENVIRONMENT"],
            "requires_exact_source_match_or_named_adapter": True,
            "requires_heavy_build": False,
        },
        {
            "candidate_id": "fresh-pilot-004",
            "role": "same_theorem_name_nearby_source_query",
            "candidate_kind": "fresh_target_discovery_query",
            "selector": {
                "query_terms": ["eg₁", "Nat.le_add_right", "extract_goal", "sorry"],
                "max_hits": 1,
            },
            "selection_rule": "Find at most one nearby source target with the same theorem/proof-shape vocabulary; require a named adapter before replay if the snippet is not exact.",
            "freshness_status": "UNRESOLVED_UNTIL_MATCH_OR_ADAPTER_FOUND",
            "allowed_terminal_states": ["ACCEPTED_REPLAY", "FAILED_REPLAY", "OBSTRUCTED_EXACT_SOURCE_MISMATCH", "OBSTRUCTED_NAMED_ADAPTER_REQUIRED", "OBSTRUCTED_ENVIRONMENT"],
            "requires_exact_source_match_or_named_adapter": True,
            "requires_heavy_build": False,
        },
        {
            "candidate_id": "fresh-pilot-005",
            "role": "same_successor_bound_shape_query",
            "candidate_kind": "fresh_target_discovery_query",
            "selector": {
                "query_terms": ["Nat.succ_le_succ", "Nat.le_add_right", "n + 1", "n + 2"],
                "max_hits": 1,
            },
            "selection_rule": "Find at most one fresh target with the same successor-bound repair shape; require exact source match or a named adapter before replay.",
            "freshness_status": "UNRESOLVED_UNTIL_MATCH_OR_ADAPTER_FOUND",
            "allowed_terminal_states": ["ACCEPTED_REPLAY", "FAILED_REPLAY", "OBSTRUCTED_EXACT_SOURCE_MISMATCH", "OBSTRUCTED_NAMED_ADAPTER_REQUIRED", "OBSTRUCTED_ENVIRONMENT"],
            "requires_exact_source_match_or_named_adapter": True,
            "requires_heavy_build": False,
        },
    ]

    if len(candidates) > max_targets:
        raise SystemExit("candidate queue exceeds max target constraint")

    queue = {
        "version": VERSION,
        "queue_type": "BOUNDED_FRESH_SOURCE_REPLAY_PILOT_QUEUE",
        "max_candidate_targets": max_targets,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "global_constraints": {
            "requires_exact_source_match_or_named_adapter": True,
            "no_heavy_lake_build_without_approval": True,
            "no_external_contact": True,
            "no_broad_source_world_mining": True,
            "terminal_states": constraints.get("allowed_terminal_states", []),
        },
        "seed_basis": {
            "lawbook_seed_count": seed_index.get("seed_count"),
            "patch_count": len(patches),
            "reviewer_checklist_command_count": len(checklist.get("commands", [])),
        },
    }

    summary = {
        "version": VERSION,
        "status": "FRESH_SOURCE_REPLAY_PILOT_QUEUE_LEDGERED",
        "input_version": pilot_plan.get("version"),
        "selected_followup_path": pilot_plan.get("selected_followup_path"),
        "candidate_count": len(candidates),
        "max_candidate_targets": max_targets,
        "control_candidate_count": sum(1 for c in candidates if c["freshness_status"] == "CONTROL_NOT_FRESH"),
        "fresh_discovery_candidate_count": sum(1 for c in candidates if c["freshness_status"] != "CONTROL_NOT_FRESH"),
        "requires_exact_source_match_or_named_adapter": True,
        "no_heavy_lake_build_without_approval": True,
        "bounded_claim": [
            "v4.4.21 creates a bounded fresh-source replay pilot candidate queue from the v4.4.20 plan",
            "the queue contains at most five candidates, including one pinned control and four fresh-target discovery queries",
            "each fresh candidate requires exact source match or a named adapter before replay",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches beyond v4.4.11 evidence",
            "that any fresh target currently exists",
            "automated external contact",
            "upstream acceptance",
            "general SorryDB mining",
            "semantic portability beyond exact-source replay or verified adapters",
            "permission to run heavy lake builds on low disk",
        ],
        "next_frontier": "v4.4.22 run only local bounded discovery over existing artifacts/source-cache for the five-candidate pilot queue",
    }

    report = f"""# SorryDB v4.4.21 — Fresh-Source Replay Pilot Candidate Queue

## Queue

- candidate count: {len(candidates)}
- max candidate targets: {max_targets}
- pinned control candidates: {summary["control_candidate_count"]}
- fresh discovery candidates: {summary["fresh_discovery_candidate_count"]}

## Boundary

This is a queue only. It does not run Lean, clone repositories, contact upstream, or claim that a fresh target exists.

## Bounded claim

- v4.4.21 creates a bounded fresh-source replay pilot candidate queue from the v4.4.20 plan.
- the queue contains at most five candidates, including one pinned control and four fresh-target discovery queries.
- each fresh candidate requires exact source match or a named adapter before replay.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- that any fresh target currently exists
- automated external contact
- upstream acceptance
- general SorryDB mining
- semantic portability beyond exact-source replay or verified adapters
- permission to run heavy lake builds on low disk

## Next frontier

v4.4.22 run only local bounded discovery over existing artifacts/source-cache for the five-candidate pilot queue.
"""

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "pilot_queue.json", queue)
    (OUT / "report.md").write_text(report, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
