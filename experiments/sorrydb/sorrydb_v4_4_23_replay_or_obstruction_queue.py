from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.23"
OUT = Path("artifacts/sorrydb/replay_or_obstruction_queue_v4_4_23")

INPUTS = {
    "local_discovery_summary": Path("artifacts/sorrydb/local_bounded_discovery_v4_4_22/summary.json"),
    "local_discovery": Path("artifacts/sorrydb/local_bounded_discovery_v4_4_22/discovery.json"),
    "pilot_queue": Path("artifacts/sorrydb/fresh_source_replay_pilot_queue_v4_4_21/pilot_queue.json"),
    "patch_bundle": Path("artifacts/sorrydb/upstream_patch_bundle_v4_4_17/upstream_patch_bundle.json"),
}

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def classify_match(path: str) -> str:
    if ".mathgraph_source_cache/" in path:
        return "PINNED_SOURCE_CACHE"
    if "artifacts/sorrydb/" in path:
        return "INTERNAL_ARTIFACT"
    if path.startswith("docs/"):
        return "INTERNAL_DOC"
    if path.startswith("experiments/") or path.startswith("tests/"):
        return "INTERNAL_CODE"
    return "UNKNOWN_LOCAL"

def main() -> None:
    missing = [str(path) for path in INPUTS.values() if not path.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    summary22 = load_json(INPUTS["local_discovery_summary"])
    discovery = load_json(INPUTS["local_discovery"])
    pilot_queue = load_json(INPUTS["pilot_queue"])
    patch_bundle = load_json(INPUTS["patch_bundle"])

    observations = discovery.get("observations", [])
    pilot_by_id = {c["candidate_id"]: c for c in pilot_queue.get("candidates", [])}

    replay_or_obstruction_items = []

    for obs in observations:
        cid = obs["candidate_id"]
        candidate = pilot_by_id.get(cid, {})
        matches = obs.get("matches", [])
        match_classes = sorted({classify_match(m.get("path", "")) for m in matches})

        if obs["terminal_status"] == "CONTROL_TARGET_LOCATED":
            queue_status = "READY_FOR_CONTROL_REPLAY_IF_APPROVED"
            reason = "Pinned source-cache control target exists; replay can be rerun only if approved."
        elif obs["terminal_status"] == "LOCAL_EXACT_SOURCE_MATCH_FOUND_REPLAY_NOT_ATTEMPTED":
            if all(cls in {"INTERNAL_ARTIFACT", "INTERNAL_DOC", "INTERNAL_CODE"} for cls in match_classes):
                queue_status = "OBSTRUCTED_INTERNAL_EVIDENCE_MATCH_ONLY"
                reason = "Exact text match was found only inside MathGraph-owned artifacts/docs/code, not a fresh source target."
            elif "PINNED_SOURCE_CACHE" in match_classes:
                queue_status = "READY_FOR_EXACT_SOURCE_REPLAY_IF_APPROVED"
                reason = "Exact source match appears in pinned source cache; replay requires approval and source classification."
            else:
                queue_status = "OBSTRUCTED_UNCLASSIFIED_LOCAL_MATCH"
                reason = "Local exact match exists but is not yet classified as a valid source target."
        elif obs["terminal_status"] == "LOCAL_SELECTOR_HITS_FOUND_NAMED_ADAPTER_REQUIRED":
            queue_status = "OBSTRUCTED_NAMED_ADAPTER_REQUIRED"
            reason = "Selector hits are not exact-source replay targets; a named adapter is required before replay."
        else:
            queue_status = obs["terminal_status"]
            reason = "No replayable local target was produced by bounded discovery."

        replay_or_obstruction_items.append(
            {
                "candidate_id": cid,
                "source_role": candidate.get("role"),
                "discovery_terminal_status": obs["terminal_status"],
                "queue_status": queue_status,
                "reason": reason,
                "match_count": len(matches),
                "match_classes": match_classes,
                "matches": matches[:5],
                "replay_allowed_now": queue_status in {
                    "READY_FOR_CONTROL_REPLAY_IF_APPROVED",
                    "READY_FOR_EXACT_SOURCE_REPLAY_IF_APPROVED",
                },
                "requires_human_approval": True,
                "requires_heavy_build": False,
            }
        )

    status_counts: dict[str, int] = {}
    for item in replay_or_obstruction_items:
        status_counts[item["queue_status"]] = status_counts.get(item["queue_status"], 0) + 1

    ready_count = sum(1 for item in replay_or_obstruction_items if item["replay_allowed_now"])
    obstruction_count = len(replay_or_obstruction_items) - ready_count

    queue = {
        "version": VERSION,
        "queue_type": "REPLAY_OR_OBSTRUCTION_QUEUE_FROM_LOCAL_BOUNDED_DISCOVERY",
        "input_version": summary22.get("version"),
        "target_repo": patch_bundle.get("target_repo"),
        "target_commit": patch_bundle.get("target_commit"),
        "target_file": patch_bundle.get("target_file"),
        "item_count": len(replay_or_obstruction_items),
        "ready_count": ready_count,
        "obstruction_count": obstruction_count,
        "status_counts": status_counts,
        "items": replay_or_obstruction_items,
        "global_constraints": {
            "no_replay_executed": True,
            "human_approval_required_before_replay": True,
            "no_heavy_lake_build_without_approval": True,
            "selector_hits_are_not_replay_targets_without_adapter": True,
        },
    }

    summary = {
        "version": VERSION,
        "status": "REPLAY_OR_OBSTRUCTION_QUEUE_LEDGERED",
        "input_version": summary22.get("version"),
        "item_count": len(replay_or_obstruction_items),
        "ready_count": ready_count,
        "obstruction_count": obstruction_count,
        "status_counts": status_counts,
        "replay_attempted": False,
        "bounded_claim": [
            "v4.4.23 converts the v4.4.22 local discovery observations into a replay-or-obstruction queue",
            "the queue separates approval-gated replay candidates from internal evidence matches and selector-hit obstructions",
            "no Lean replay, clone, network access, or heavy build is executed",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches beyond v4.4.11 evidence",
            "that internal artifact matches are fresh targets",
            "that selector hits are valid replay targets",
            "that any fresh target verifies",
            "automated external contact",
            "upstream acceptance",
            "semantic portability beyond exact-source replay or verified adapters",
            "permission to run heavy lake builds on low disk",
        ],
        "next_frontier": "v4.4.24 either run the pinned control replay with explicit approval, or park fresh-source replay and return to manual outbound review",
    }

    report = f"""# SorryDB v4.4.23 — Replay-or-Obstruction Queue

## Result

- item count: {len(replay_or_obstruction_items)}
- ready count: {ready_count}
- obstruction count: {obstruction_count}
- replay attempted: false
- status counts: `{json.dumps(status_counts, sort_keys=True)}`

## Boundary

This converts discovery observations into queue states only. It does not run Lean, clone repositories, use network access, or contact upstream.

## Bounded claim

- v4.4.23 converts the v4.4.22 local discovery observations into a replay-or-obstruction queue.
- the queue separates approval-gated replay candidates from internal evidence matches and selector-hit obstructions.
- no Lean replay, clone, network access, or heavy build is executed.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- that internal artifact matches are fresh targets
- that selector hits are valid replay targets
- that any fresh target verifies
- automated external contact
- upstream acceptance
- semantic portability beyond exact-source replay or verified adapters
- permission to run heavy lake builds on low disk

## Next frontier

v4.4.24 either run the pinned control replay with explicit approval, or park fresh-source replay and return to manual outbound review.
"""

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "replay_or_obstruction_queue.json", queue)
    (OUT / "report.md").write_text(report, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
