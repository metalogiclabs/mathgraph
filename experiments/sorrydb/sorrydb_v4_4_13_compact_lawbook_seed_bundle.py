from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSION = "v4.4.13"
IN_ROOT = Path("artifacts/sorrydb/accepted_certificate_dedup_v4_4_12")
OUT_ROOT = Path("artifacts/sorrydb/compact_lawbook_seed_v4_4_13")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    summary12 = load_json(IN_ROOT / "summary.json")
    classes = load_json(IN_ROOT / "dedup_classes.json")["classes"]
    cert_map = load_json(IN_ROOT / "certificate_to_class.json")["certificate_to_class"]

    if summary12["unique_repair_class_count"] != 2:
        raise SystemExit("expected exactly two v4.4.12 repair classes")

    seeds = []
    for cls in sorted(classes, key=lambda x: x["class_id"]):
        key = cls["dedup_key"]
        seed_id = cls["class_id"].replace("repair-class", "lawbook-seed")
        seeds.append({
            "seed_id": seed_id,
            "source_class_id": cls["class_id"],
            "status": "LAWBOOK_SEED_READY",
            "representative_certificate_id": cls["representative_certificate_id"],
            "certificate_ids": cls["certificate_ids"],
            "manifest_paths": cls["manifest_paths"],
            "repo_root": key.get("repo_root", ""),
            "repo_commit": key.get("repo_commit", ""),
            "file_path": key.get("file_path", ""),
            "line_span": key.get("line_span", ""),
            "source_snippet": cls["source_snippet"],
            "patch_snippet": cls["patch_snippet"],
            "source_snippet_sha256": key.get("source_snippet_sha256", ""),
            "patch_snippet_sha256": key.get("patch_snippet_sha256", ""),
            "replay_evidence": {
                "verdict": "PATCH_ACCEPTED",
                "baseline_verdict": "BASELINE_PASSED",
                "patch_apply_verdict": "PATCH_APPLIED",
                "patch_verdict": "PATCH_ACCEPTED",
            },
            "reuse_contract": {
                "requires_exact_source_or_verified_adapter": True,
                "requires_lean_replay_before_promotion": True,
                "portable_without_replay": False,
            },
        })

    seed_index = {
        "version": VERSION,
        "seed_count": len(seeds),
        "seeds": seeds,
    }

    replay_seed_queue = {
        "version": VERSION,
        "queue_type": "DEDUPED_ACCEPTED_REPAIR_SEED_QUEUE",
        "candidate_count": len(seeds),
        "candidates": [
            {
                "candidate_id": seed["seed_id"],
                "source_class_id": seed["source_class_id"],
                "representative_certificate_id": seed["representative_certificate_id"],
                "repo_root": seed["repo_root"],
                "repo_commit": seed["repo_commit"],
                "file_path": seed["file_path"],
                "source_snippet": seed["source_snippet"],
                "patch_snippet": seed["patch_snippet"],
                "expected_replay_verdict": "PATCH_ACCEPTED",
                "requires_replay": True,
            }
            for seed in seeds
        ],
    }

    summary = {
        "version": VERSION,
        "status": "COMPACT_LAWBOOK_SEED_BUNDLE_LEDGERED",
        "input_version": summary12["version"],
        "accepted_certificate_count": summary12["accepted_certificate_count"],
        "unique_repair_class_count": summary12["unique_repair_class_count"],
        "duplicate_certificate_count": summary12["duplicate_certificate_count"],
        "lawbook_seed_count": len(seeds),
        "mapped_certificate_count": len(cert_map),
        "bounded_claim": [
            "v4.4.13 promotes the two v4.4.12 deduplicated accepted repair classes into compact Lawbook seed entries",
            "each seed preserves accepted replay evidence and an explicit reuse contract",
            "the bundle is a replay seed bundle, not a new proof or portable theorem claim",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream submission",
            "that seeds are portable without exact-source replay or verified adapters",
        ],
        "next_frontier": "v4.4.14 run source-cleanliness and replay-restoration invariants against the hydrated checkout",
    }

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(OUT_ROOT / "summary.json", summary)
    write_json(OUT_ROOT / "lawbook_seed_index.json", seed_index)
    write_json(OUT_ROOT / "replay_seed_queue.json", replay_seed_queue)

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
