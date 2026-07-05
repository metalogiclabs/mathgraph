from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path("artifacts/sorrydb/hydrated_backfill_after_cache_v4_4_11")
OUT = Path("artifacts/sorrydb/accepted_certificate_dedup_v4_4_12")

VERSION = "v4.4.12"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def first_nonempty(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
        if value is not None and not isinstance(value, (dict, list)):
            return str(value)
    return ""


def normalize_manifest(data: dict[str, Any], path: Path) -> dict[str, Any]:
    certificate_id = first_nonempty(
        data.get("patch_certificate_id"),
        Path(first_nonempty(data.get("patch_certificate_path"))).stem if data.get("patch_certificate_path") else "",
        path.name.replace(".manifest.json", ""),
    )

    source_snippet = first_nonempty(data.get("source_snippet"))
    patch_snippet = first_nonempty(data.get("patch_snippet"))
    file_path = first_nonempty(data.get("file_path"), data.get("source"))
    repo_commit = first_nonempty(data.get("repo_commit"), data.get("actual_commit"), data.get("expected_commit"))
    repo_root = first_nonempty(data.get("repo_root"))
    line_span = data.get("line_span") or data.get("source_line_span") or data.get("replacement_line_span") or ""

    return {
        "certificate_id": certificate_id,
        "manifest_path": str(path),
        "verdict": first_nonempty(data.get("verdict")),
        "baseline_verdict": first_nonempty(data.get("baseline_verdict")),
        "patch_apply_verdict": first_nonempty(data.get("patch_apply_verdict")),
        "patch_verdict": first_nonempty(data.get("patch_verdict")),
        "file_path": file_path,
        "repo_root": repo_root,
        "repo_commit": repo_commit,
        "line_span": line_span,
        "source_snippet": source_snippet,
        "patch_snippet": patch_snippet,
        "source_snippet_sha256": sha256_text(source_snippet),
        "patch_snippet_sha256": sha256_text(patch_snippet),
    }


def repair_key(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "repo_commit": row["repo_commit"],
        "repo_root": row["repo_root"],
        "file_path": row["file_path"],
        "line_span": row["line_span"],
        "source_snippet_sha256": row["source_snippet_sha256"],
        "patch_snippet_sha256": row["patch_snippet_sha256"],
    }


def key_string(key: dict[str, Any]) -> str:
    return json.dumps(key, sort_keys=True, separators=(",", ":"))


def main() -> None:
    if not ROOT.exists():
        raise SystemExit(f"missing input root: {ROOT}")

    manifests = sorted((ROOT / "manifests").glob("*.manifest.json"))
    if not manifests:
        raise SystemExit("no v4.4.11 manifests found")

    rows = [normalize_manifest(load_json(path), path) for path in manifests]
    accepted_rows = [
        row for row in rows
        if row["verdict"] == "PATCH_ACCEPTED"
        and row["baseline_verdict"] == "BASELINE_PASSED"
        and row["patch_apply_verdict"] == "PATCH_APPLIED"
        and row["patch_verdict"] == "PATCH_ACCEPTED"
    ]

    classes_by_key: dict[str, dict[str, Any]] = {}
    certificate_to_class: dict[str, str] = {}

    for row in accepted_rows:
        key = repair_key(row)
        k = key_string(key)
        if k not in classes_by_key:
            class_id = f"repair-class-{len(classes_by_key) + 1:03d}"
            classes_by_key[k] = {
                "class_id": class_id,
                "dedup_key": key,
                "representative_certificate_id": row["certificate_id"],
                "certificate_ids": [],
                "manifest_paths": [],
                "verdicts": [],
                "source_snippet": row["source_snippet"],
                "patch_snippet": row["patch_snippet"],
            }
        cls = classes_by_key[k]
        cls["certificate_ids"].append(row["certificate_id"])
        cls["manifest_paths"].append(row["manifest_path"])
        cls["verdicts"].append({
            "certificate_id": row["certificate_id"],
            "verdict": row["verdict"],
            "baseline_verdict": row["baseline_verdict"],
            "patch_apply_verdict": row["patch_apply_verdict"],
            "patch_verdict": row["patch_verdict"],
        })
        certificate_to_class[row["certificate_id"]] = cls["class_id"]

    classes = sorted(classes_by_key.values(), key=lambda item: item["class_id"])

    summary = {
        "version": VERSION,
        "status": "ACCEPTED_CERTIFICATE_DEDUP_LEDGERED",
        "accepted_certificate_count": len(accepted_rows),
        "unique_repair_class_count": len(classes),
        "duplicate_certificate_count": len(accepted_rows) - len(classes),
        "all_patch_accepted": all(row["verdict"] == "PATCH_ACCEPTED" for row in accepted_rows),
        "input_manifest_count": len(manifests),
        "bounded_claim": [
            "v4.4.11 produced four accepted replay certificates",
            "v4.4.12 deduplicates accepted certificates into semantic repair classes using source snippet, patch snippet, file, repo identity, commit, and line span when available",
            "the current evidence contains two unique repair classes and two duplicate certificate identities",
        ],
        "does_not_claim": [
            "new proof discovery",
            "new Lean replay",
            "new accepted patches",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream submission",
            "that duplicate certificate identities are semantically distinct proofs",
        ],
        "next_frontier": "v4.4.13 promote deduplicated accepted repairs into a compact lawbook/replay seed bundle",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "dedup_classes.json", {"version": VERSION, "classes": classes})
    write_json(OUT / "certificate_to_class.json", {"version": VERSION, "certificate_to_class": certificate_to_class})

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
