from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.16"
OUT = Path("artifacts/sorrydb/scale_path_selector_v4_4_16")

INPUTS = {
    "microflywheel": Path("artifacts/sorrydb/microflywheel_report_v4_4_15/summary.json"),
    "lawbook_seed_index": Path("artifacts/sorrydb/compact_lawbook_seed_v4_4_13/lawbook_seed_index.json"),
    "replay_seed_queue": Path("artifacts/sorrydb/compact_lawbook_seed_v4_4_13/replay_seed_queue.json"),
    "dedup_summary": Path("artifacts/sorrydb/accepted_certificate_dedup_v4_4_12/summary.json"),
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def score_option(option: dict[str, Any]) -> int:
    return (
        option["external_value"]
        + option["local_testability"]
        + option["artifact_readiness"]
        + option["feedback_speed"]
        + option["risk_reduction"]
        - option["execution_risk"]
    )


def main() -> None:
    missing = [str(path) for path in INPUTS.values() if not path.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    micro = load_json(INPUTS["microflywheel"])
    lawbook_seed_index = load_json(INPUTS["lawbook_seed_index"])
    replay_seed_queue = load_json(INPUTS["replay_seed_queue"])
    dedup = load_json(INPUTS["dedup_summary"])

    options = [
        {
            "path_id": "upstream_patch_package",
            "description": "Package the two deduplicated accepted MetaExamples/Fiddle repairs into a minimal upstream-facing patch evidence bundle.",
            "external_value": 5,
            "local_testability": 5,
            "artifact_readiness": 5,
            "feedback_speed": 4,
            "risk_reduction": 5,
            "execution_risk": 1,
            "why": [
                "already has four accepted replay certificates",
                "deduplicated to two repair classes",
                "best proof of external usefulness without claiming generality",
                "smallest next artifact with a real reviewer/judge boundary",
            ],
            "done_definition": [
                "produce upstream_patch_bundle.json",
                "include exact source file, line spans, source snippets, patch snippets, accepted replay evidence, and replay command",
                "include no portability claim beyond exact-source replay",
            ],
        },
        {
            "path_id": "replay_seed_reuse_on_fresh_targets",
            "description": "Try the two Lawbook replay seeds against fresh SorryDB targets or nearby source files.",
            "external_value": 4,
            "local_testability": 4,
            "artifact_readiness": 3,
            "feedback_speed": 3,
            "risk_reduction": 4,
            "execution_risk": 3,
            "why": [
                "tests whether seeds are useful beyond the exact cached source",
                "creates real adapter pressure",
                "higher upside but more ways to fail unclearly",
            ],
            "done_definition": [
                "choose a bounded fresh target set",
                "attempt exact-source or adapter-backed replay",
                "ledger accepted, failed, and obstructed outcomes separately",
            ],
        },
        {
            "path_id": "more_sorrydb_source_worlds",
            "description": "Hydrate and replay more SorryDB source worlds using the same obstruction-to-certificate microflywheel.",
            "external_value": 4,
            "local_testability": 3,
            "artifact_readiness": 3,
            "feedback_speed": 3,
            "risk_reduction": 5,
            "execution_risk": 4,
            "why": [
                "scales the engine",
                "improves coverage",
                "but risks returning to broad mining before packaging the win",
            ],
            "done_definition": [
                "select a small source-world batch",
                "run hydration, cache contact, replay, dedup, and seed packaging",
                "compare yield against v4.4.7 to v4.4.15",
            ],
        },
    ]

    for option in options:
        option["score"] = score_option(option)

    ranked = sorted(options, key=lambda x: (-x["score"], x["path_id"]))
    selected = ranked[0]

    summary = {
        "version": VERSION,
        "status": "SCALE_PATH_SELECTED",
        "selected_path_id": selected["path_id"],
        "selected_score": selected["score"],
        "ranked_path_ids": [x["path_id"] for x in ranked],
        "bounded_claim": [
            "v4.4.16 selects the next scale path after the completed v4.4.7 through v4.4.15 microflywheel",
            "selection is based on external value, local testability, artifact readiness, feedback speed, risk reduction, and execution risk",
            "the selected next path is an upstream-facing exact-source patch evidence bundle",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream acceptance",
            "semantic portability beyond exact-source replay or verified adapters",
        ],
        "evidence_inputs": {k: str(v) for k, v in INPUTS.items()},
        "microflywheel_headline": micro.get("headline", {}),
        "lawbook_seed_count": micro.get("headline", {}).get("lawbook_seed_count"),
        "unique_repair_classes": dedup.get("unique_repair_class_count"),
        "replay_seed_queue_type": type(replay_seed_queue).__name__,
        "lawbook_seed_index_type": type(lawbook_seed_index).__name__,
        "next_frontier": "v4.4.17 build the upstream-facing exact-source patch evidence bundle",
    }

    report = {
        "version": VERSION,
        "selected": selected,
        "ranked_options": ranked,
        "decision_rule": {
            "score": "external_value + local_testability + artifact_readiness + feedback_speed + risk_reduction - execution_risk",
            "tie_break": "lexicographic path_id after score",
        },
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "scale_path_report.json", report)

    md = f"""# SorryDB v4.4.16 — Scale Path Selector

## Selected path

{selected["path_id"]}

## Why

- highest score under the bounded decision rule
- packages the completed microflywheel before expanding the search space
- gives the work a clearer external reviewer boundary
- keeps the claim exact-source and evidence-backed

## Bounded claim

- v4.4.16 selects the next scale path after the completed v4.4.7 through v4.4.15 microflywheel.
- selection is based on external value, local testability, artifact readiness, feedback speed, risk reduction, and execution risk.
- the selected next path is an upstream-facing exact-source patch evidence bundle.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches
- general SorryDB mining
- arbitrary proof repair
- upstream acceptance
- semantic portability beyond exact-source replay or verified adapters

## Next frontier

v4.4.17 build the upstream-facing exact-source patch evidence bundle.
"""
    (OUT / "report.md").write_text(md, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
