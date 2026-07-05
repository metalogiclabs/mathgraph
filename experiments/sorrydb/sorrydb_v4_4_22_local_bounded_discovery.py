from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.22"
OUT = Path("artifacts/sorrydb/local_bounded_discovery_v4_4_22")

INPUTS = {
    "pilot_queue": Path("artifacts/sorrydb/fresh_source_replay_pilot_queue_v4_4_21/pilot_queue.json"),
    "pilot_summary": Path("artifacts/sorrydb/fresh_source_replay_pilot_queue_v4_4_21/summary.json"),
    "source_cleanliness": Path("artifacts/sorrydb/source_cleanliness_v4_4_14/summary.json"),
    "patch_bundle": Path("artifacts/sorrydb/upstream_patch_bundle_v4_4_17/upstream_patch_bundle.json"),
}

SEARCH_ROOTS = [
    Path("artifacts"),
    Path("docs"),
    Path(".mathgraph_source_cache"),
]

MAX_READ_BYTES = 2_000_000
ALLOWED_SUFFIXES = {".lean", ".md", ".json", ".txt", ".py"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix not in ALLOWED_SUFFIXES:
            continue
        try:
            if p.stat().st_size > MAX_READ_BYTES:
                continue
        except OSError:
            continue
        out.append(p)
    return sorted(out)


def contains_text(path: Path, needle: str) -> bool:
    if not needle:
        return False
    try:
        return needle in path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def find_matches(needle: str, files: list[Path]) -> list[dict[str, Any]]:
    hits = []
    for path in files:
        if contains_text(path, needle):
            hits.append(
                {
                    "path": str(path),
                    "kind": "TEXT_MATCH",
                }
            )
    return hits


def main() -> None:
    missing = [str(path) for path in INPUTS.values() if not path.exists()]
    if missing:
        raise SystemExit("missing inputs: " + json.dumps(missing, indent=2))

    queue = load_json(INPUTS["pilot_queue"])
    summary21 = load_json(INPUTS["pilot_summary"])
    source_cleanliness = load_json(INPUTS["source_cleanliness"])
    patch_bundle = load_json(INPUTS["patch_bundle"])

    files = []
    for root in SEARCH_ROOTS:
        files.extend(iter_files(root))

    files = sorted(
        {
            path for path in files
            if "local_bounded_discovery_v4_4_22" not in str(path)
            and ".pytest_tmp" not in str(path)
        }
    )
    candidates = queue.get("candidates", [])

    observations = []
    for candidate in candidates:
        cid = candidate["candidate_id"]
        observation: dict[str, Any] = {
            "candidate_id": cid,
            "role": candidate.get("role"),
            "candidate_kind": candidate.get("candidate_kind"),
            "terminal_status": "OBSTRUCTED_NO_LOCAL_FRESH_TARGET_FOUND",
            "matches": [],
            "requires_replay": False,
            "replay_attempted": False,
        }

        if candidate.get("freshness_status") == "CONTROL_NOT_FRESH":
            target_file = patch_bundle.get("target_file")
            source_root = Path(source_cleanliness.get("source_root", ""))
            local_target = source_root / target_file if target_file else Path("")
            observation["terminal_status"] = "CONTROL_TARGET_LOCATED" if local_target.exists() else "OBSTRUCTED_CONTROL_TARGET_MISSING"
            observation["matches"] = [{"path": str(local_target), "kind": "PINNED_CONTROL_TARGET"}] if local_target.exists() else []
            observation["requires_replay"] = local_target.exists()
            observations.append(observation)
            continue

        source_snippet = candidate.get("source_snippet")
        if source_snippet:
            matches = find_matches(source_snippet, files)
            fresh_matches = [
                m for m in matches
                if "upstream_patch_bundle_v4_4_17" not in m["path"]
                and "fresh_source_replay_pilot_queue_v4_4_21" not in m["path"]
                and "local_bounded_discovery_v4_4_22" not in m["path"]
            ]
            observation["matches"] = fresh_matches[:5]
            if fresh_matches:
                observation["terminal_status"] = "LOCAL_EXACT_SOURCE_MATCH_FOUND_REPLAY_NOT_ATTEMPTED"
                observation["requires_replay"] = True
            else:
                observation["terminal_status"] = "OBSTRUCTED_NO_LOCAL_EXACT_SOURCE_MATCH"
            observations.append(observation)
            continue

        selector = candidate.get("selector", {})
        terms = selector.get("query_terms", [])
        term_hits = []
        for term in terms:
            term_hits.extend(find_matches(term, files))
        seen = set()
        dedup_hits = []
        for hit in term_hits:
            key = hit["path"]
            if key in seen:
                continue
            seen.add(key)
            dedup_hits.append(hit)
        filtered = [
            h for h in dedup_hits
            if "local_bounded_discovery_v4_4_22" not in h["path"]
        ][:5]
        observation["matches"] = filtered
        if filtered:
            observation["terminal_status"] = "LOCAL_SELECTOR_HITS_FOUND_NAMED_ADAPTER_REQUIRED"
            observation["requires_replay"] = False
        else:
            observation["terminal_status"] = "OBSTRUCTED_NO_LOCAL_SELECTOR_HITS"
        observations.append(observation)

    status_counts: dict[str, int] = {}
    for obs in observations:
        status_counts[obs["terminal_status"]] = status_counts.get(obs["terminal_status"], 0) + 1

    discovery = {
        "version": VERSION,
        "discovery_type": "LOCAL_BOUNDED_DISCOVERY_OVER_EXISTING_ARTIFACTS_AND_SOURCE_CACHE",
        "search_roots": [str(p) for p in SEARCH_ROOTS],
        "searched_file_count": len(files),
        "candidate_count": len(candidates),
        "observations": observations,
        "status_counts": status_counts,
        "constraints": {
            "no_clone": True,
            "no_network": True,
            "no_lean_replay": True,
            "no_heavy_lake_build": True,
            "existing_artifacts_and_source_cache_only": True,
        },
    }

    summary = {
        "version": VERSION,
        "status": "LOCAL_BOUNDED_DISCOVERY_LEDGERED",
        "input_version": summary21.get("version"),
        "candidate_count": len(candidates),
        "searched_file_count": len(files),
        "status_counts": status_counts,
        "control_targets_located": status_counts.get("CONTROL_TARGET_LOCATED", 0),
        "exact_source_matches_found": status_counts.get("LOCAL_EXACT_SOURCE_MATCH_FOUND_REPLAY_NOT_ATTEMPTED", 0),
        "selector_hits_found": status_counts.get("LOCAL_SELECTOR_HITS_FOUND_NAMED_ADAPTER_REQUIRED", 0),
        "replay_attempted": False,
        "bounded_claim": [
            "v4.4.22 runs local bounded discovery over existing artifacts and source-cache only",
            "the run searches the five-candidate v4.4.21 pilot queue without cloning, networking, Lean replay, or heavy builds",
            "outcomes are recorded as control located, exact-source match found, selector hit requiring adapter, or named obstruction",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches beyond v4.4.11 evidence",
            "that selector hits are valid replay targets",
            "that any fresh target verifies",
            "automated external contact",
            "upstream acceptance",
            "general SorryDB mining",
            "semantic portability beyond exact-source replay or verified adapters",
            "permission to run heavy lake builds on low disk",
        ],
        "next_frontier": "v4.4.23 convert any local exact-source matches into a replay-or-obstruction queue; if none, park the fresh-source pilot and return to manual outbound review",
    }

    report = f"""# SorryDB v4.4.22 — Local Bounded Discovery

## Result

- searched files: {len(files)}
- candidate count: {len(candidates)}
- replay attempted: false
- status counts: `{json.dumps(status_counts, sort_keys=True)}`

## Boundary

This run uses existing artifacts and source-cache only. It does not clone repositories, use network access, run Lean, run Lake, or perform external contact.

## Bounded claim

- v4.4.22 runs local bounded discovery over existing artifacts and source-cache only.
- the run searches the five-candidate v4.4.21 pilot queue without cloning, networking, Lean replay, or heavy builds.
- outcomes are recorded as control located, exact-source match found, selector hit requiring adapter, or named obstruction.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- that selector hits are valid replay targets
- that any fresh target verifies
- automated external contact
- upstream acceptance
- general SorryDB mining
- semantic portability beyond exact-source replay or verified adapters
- permission to run heavy lake builds on low disk

## Next frontier

v4.4.23 convert any local exact-source matches into a replay-or-obstruction queue; if none, park the fresh-source pilot and return to manual outbound review.
"""

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "discovery.json", discovery)
    (OUT / "report.md").write_text(report, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
