#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any


VERSION = "v4.4.7"
STATUS = "HYDRATED_BACKFILL_QUEUE_PLANNED"
QUEUE_STATUS = "HYDRATED_BACKFILL_QUEUE_READY"

HYDRATED_BACKFILL_READY = "HYDRATED_BACKFILL_READY"
HYDRATED_BACKFILL_BLOCKED_NOT_VERIFIED = "HYDRATED_BACKFILL_BLOCKED_NOT_VERIFIED"
HYDRATED_BACKFILL_BLOCKED_FILE_MISSING = "HYDRATED_BACKFILL_BLOCKED_FILE_MISSING"
HYDRATED_BACKFILL_BLOCKED_SNIPPET_AMBIGUOUS = "HYDRATED_BACKFILL_BLOCKED_SNIPPET_AMBIGUOUS"
HYDRATED_BACKFILL_BLOCKED_SNIPPET_HASH_MISMATCH = "HYDRATED_BACKFILL_BLOCKED_SNIPPET_HASH_MISMATCH"
HYDRATED_BACKFILL_BLOCKED_PATCH_HASH_MISMATCH = "HYDRATED_BACKFILL_BLOCKED_PATCH_HASH_MISMATCH"
HYDRATED_BACKFILL_BLOCKED_NO_SORRY = "HYDRATED_BACKFILL_BLOCKED_NO_SORRY"
HYDRATED_BACKFILL_BLOCKED_MULTIPLE_SORRIES = "HYDRATED_BACKFILL_BLOCKED_MULTIPLE_SORRIES"
HYDRATED_BACKFILL_BLOCKED_PATCH_CONTAINS_SORRY = "HYDRATED_BACKFILL_BLOCKED_PATCH_CONTAINS_SORRY"
HYDRATED_BACKFILL_BLOCKED_MISSING_PATCH = "HYDRATED_BACKFILL_BLOCKED_MISSING_PATCH"
HYDRATED_BACKFILL_BLOCKED_UNCLASSIFIED = "HYDRATED_BACKFILL_BLOCKED_UNCLASSIFIED"

CATEGORIES = (
    HYDRATED_BACKFILL_READY,
    HYDRATED_BACKFILL_BLOCKED_NOT_VERIFIED,
    HYDRATED_BACKFILL_BLOCKED_FILE_MISSING,
    HYDRATED_BACKFILL_BLOCKED_SNIPPET_AMBIGUOUS,
    HYDRATED_BACKFILL_BLOCKED_SNIPPET_HASH_MISMATCH,
    HYDRATED_BACKFILL_BLOCKED_PATCH_HASH_MISMATCH,
    HYDRATED_BACKFILL_BLOCKED_NO_SORRY,
    HYDRATED_BACKFILL_BLOCKED_MULTIPLE_SORRIES,
    HYDRATED_BACKFILL_BLOCKED_PATCH_CONTAINS_SORRY,
    HYDRATED_BACKFILL_BLOCKED_MISSING_PATCH,
    HYDRATED_BACKFILL_BLOCKED_UNCLASSIFIED,
)

SORRY_RE = re.compile(r"\bsorry\b")

DEFAULT_HYDRATION_SUMMARY = Path("artifacts/sorrydb/source_hydration_v4_4_6/summary.json")
DEFAULT_HYDRATION_LEDGER = Path("artifacts/sorrydb/source_hydration_v4_4_6/source_hydration_ledger.json")
DEFAULT_FILE_HASHES = Path("artifacts/sorrydb/source_hydration_v4_4_6/file_hashes.json")
DEFAULT_VERIFIED_SNIPPETS = Path("artifacts/sorrydb/source_hydration_v4_4_6/verified_snippets.json")
DEFAULT_REGISTRATION_PLAN = Path("artifacts/sorrydb/source_registration_v4_4_5/registration_plan.json")
DEFAULT_SNIPPET_DIR = Path("artifacts/sorrydb/source_inputs_v4_4_4/source_snippets")
DEFAULT_PRIOR_BACKFILL_PLAN = Path("artifacts/sorrydb/backfill_plans_v4_4_3/backfill_plan.json")
DEFAULT_OUTPUT_DIR = Path("artifacts/sorrydb/hydrated_backfill_queue_v4_4_7")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_object(path: Path) -> dict[str, Any]:
    value = load_json(path)
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value is not an object")
    return value


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def certificate_version_from_id(certificate_id: str) -> str:
    match = re.search(r"sorrydb-v(\d+)-(\d+)-(\d+)", certificate_id)
    if not match:
        return ""
    return f"v{match.group(1)}.{match.group(2)}.{match.group(3)}"


def rows_by_id(rows: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        return {}
    return {
        str(row["row_id"]): row
        for row in rows
        if isinstance(row, dict) and row.get("row_id")
    }


def load_snippet_records(directory: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    records: dict[str, dict[str, Any]] = {}
    scanned: list[str] = []
    if not directory.is_dir():
        return records, scanned
    for path in sorted(directory.glob("*.json")):
        scanned.append(str(path))
        try:
            value = load_object(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if value.get("row_id"):
            value["_path"] = str(path)
            records[str(value["row_id"])] = value
    return records, scanned


def blocked(row_id: str, category: str, reason: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "terminal_form": "NAMED_OBSTRUCTION",
        "row_id": row_id,
        "category": category,
        "reason": reason,
        "evidence": evidence,
    }


def classify_row(
    hydration_row: dict[str, Any],
    verified: dict[str, Any] | None,
    registration: dict[str, Any] | None,
    snippet: dict[str, Any] | None,
    cache_root: Path,
) -> tuple[str, dict[str, Any]]:
    row_id = str(hydration_row.get("row_id", ""))
    evidence = {
        "hydration_status": hydration_row.get("status", ""),
        "verified_snippet": verified or {},
        "registration_row": registration or {},
        "snippet_record": (snippet or {}).get("_path", ""),
    }
    if hydration_row.get("status") != "SOURCE_HYDRATED_VERIFIED":
        category = HYDRATED_BACKFILL_BLOCKED_NOT_VERIFIED
        return category, blocked(row_id, category, "hydration row is not SOURCE_HYDRATED_VERIFIED", evidence)
    if verified is None or registration is None or snippet is None:
        category = HYDRATED_BACKFILL_BLOCKED_UNCLASSIFIED
        return category, blocked(row_id, category, "required joined evidence is missing", evidence)

    occurrence_count = int(verified.get("source_snippet_occurrence_count", 0))
    if occurrence_count != 1:
        category = (
            HYDRATED_BACKFILL_BLOCKED_SNIPPET_AMBIGUOUS
            if occurrence_count > 1
            else HYDRATED_BACKFILL_BLOCKED_UNCLASSIFIED
        )
        return category, blocked(row_id, category, f"source snippet occurrence count is {occurrence_count}", evidence)

    file_path = str(hydration_row.get("file_path", registration.get("file_path", "")))
    source_file = cache_root / file_path
    if not source_file.is_file():
        category = HYDRATED_BACKFILL_BLOCKED_FILE_MISSING
        return category, blocked(row_id, category, "hydrated source file is missing", evidence)

    source_snippet = str(snippet.get("source_snippet", ""))
    patch_snippet = str(snippet.get("patch_snippet", ""))
    expected_source_hash = str(registration.get("source_snippet_sha256", ""))
    expected_patch_hash = str(registration.get("patch_snippet_sha256", ""))
    if (
        not source_snippet
        or sha256_text(source_snippet) != expected_source_hash
        or str(verified.get("source_snippet_sha256", "")) != expected_source_hash
        or str(snippet.get("source_snippet_sha256", "")) != expected_source_hash
    ):
        category = HYDRATED_BACKFILL_BLOCKED_SNIPPET_HASH_MISMATCH
        return category, blocked(row_id, category, "source snippet hash evidence does not agree", evidence)
    if not patch_snippet:
        category = HYDRATED_BACKFILL_BLOCKED_MISSING_PATCH
        return category, blocked(row_id, category, "patch snippet is missing", evidence)
    if (
        sha256_text(patch_snippet) != expected_patch_hash
        or str(verified.get("patch_snippet_sha256", "")) != expected_patch_hash
        or str(snippet.get("patch_snippet_sha256", "")) != expected_patch_hash
    ):
        category = HYDRATED_BACKFILL_BLOCKED_PATCH_HASH_MISMATCH
        return category, blocked(row_id, category, "patch snippet hash evidence does not agree", evidence)

    sorry_count = len(SORRY_RE.findall(source_snippet))
    if sorry_count == 0:
        category = HYDRATED_BACKFILL_BLOCKED_NO_SORRY
        return category, blocked(row_id, category, "source snippet contains no sorry", evidence)
    if sorry_count > 1:
        category = HYDRATED_BACKFILL_BLOCKED_MULTIPLE_SORRIES
        return category, blocked(row_id, category, "source snippet contains multiple sorries", evidence)
    if SORRY_RE.search(patch_snippet):
        category = HYDRATED_BACKFILL_BLOCKED_PATCH_CONTAINS_SORRY
        return category, blocked(row_id, category, "patch snippet still contains sorry", evidence)
    if verified.get("source_snippet_line_start") is None or verified.get("source_snippet_line_end") is None:
        category = HYDRATED_BACKFILL_BLOCKED_UNCLASSIFIED
        return category, blocked(row_id, category, "unique source snippet line span is missing", evidence)
    if source_file.read_text(encoding="utf-8").count(source_snippet) != 1:
        category = HYDRATED_BACKFILL_BLOCKED_SNIPPET_AMBIGUOUS
        return category, blocked(row_id, category, "live controlled source no longer has one exact snippet occurrence", evidence)

    certificate_id = str(registration.get("certificate_id", ""))
    if not certificate_id:
        category = HYDRATED_BACKFILL_BLOCKED_UNCLASSIFIED
        return category, blocked(row_id, category, "certificate id is missing", evidence)

    candidate = {
        "candidate_id": f"v447-backfill-{certificate_id}",
        "repo_root": str(cache_root.resolve()),
        "file_path": file_path,
        "source_snippet": source_snippet,
        "patch_snippet": patch_snippet,
        "timeout_seconds": 240,
        "queue_timeout_seconds": 600,
        "required_gb": 5.0,
        "min_free_gb": 5.0,
        "run_baseline_first": True,
        "project": registration.get("repo_url", ""),
        "project_commit": registration.get("commit", ""),
        "certificate_id": certificate_id,
        "certificate_version": certificate_version_from_id(certificate_id),
        "restore_check": f"restore exact source snippet at lines {verified['source_snippet_line_start']}-{verified['source_snippet_line_end']}",
        "provenance": {
            "hydration_row_id": row_id,
            "hydration_status": hydration_row.get("status", ""),
            "controlled_cache_root": str(cache_root.resolve()),
            "source_snippet_sha256": expected_source_hash,
            "patch_snippet_sha256": expected_patch_hash,
            "source_snippet_line_start": verified["source_snippet_line_start"],
            "source_snippet_line_end": verified["source_snippet_line_end"],
            "planner_version": VERSION,
        },
    }
    return HYDRATED_BACKFILL_READY, candidate


def plan_queue(
    hydration_summary_path: Path,
    hydration_ledger_path: Path,
    file_hashes_path: Path,
    verified_snippets_path: Path,
    registration_plan_path: Path,
    snippet_dir: Path,
    prior_backfill_plan_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    input_paths = [
        hydration_summary_path,
        hydration_ledger_path,
        file_hashes_path,
        verified_snippets_path,
        registration_plan_path,
        prior_backfill_plan_path,
    ]
    notes: list[str] = []
    try:
        hydration_summary = load_object(hydration_summary_path)
        hydration_ledger = load_object(hydration_ledger_path)
        file_hashes = load_json(file_hashes_path)
        verified_rows = load_json(verified_snippets_path)
        registration_plan = load_object(registration_plan_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        hydration_summary = {}
        hydration_ledger = {"rows": []}
        file_hashes = []
        verified_rows = []
        registration_plan = {"rows": []}
        notes.append(f"required input missing or malformed: {exc}")

    cache_root = Path(str(hydration_summary.get("controlled_cache_path", "")))
    hydration_rows = rows_by_id(hydration_ledger.get("rows", []))
    verified_by_id = rows_by_id(verified_rows)
    registration_by_id = rows_by_id(registration_plan.get("rows", []))
    snippets_by_id, snippet_paths = load_snippet_records(snippet_dir)

    ready: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for row_id, hydration_row in sorted(hydration_rows.items()):
        try:
            category, result = classify_row(
                hydration_row,
                verified_by_id.get(row_id),
                registration_by_id.get(row_id),
                snippets_by_id.get(row_id),
                cache_root,
            )
        except Exception as exc:
            category = HYDRATED_BACKFILL_BLOCKED_UNCLASSIFIED
            result = blocked(row_id, category, f"unexpected planner error: {exc}", {})
        counts[category] += 1
        if category == HYDRATED_BACKFILL_READY:
            ready.append(result)
        else:
            blocked_rows.append(result)

    ready.sort(key=lambda row: row["candidate_id"])
    blocked_rows.sort(key=lambda row: row["row_id"])
    stable_counts = {category: counts.get(category, 0) for category in CATEGORIES}
    candidate_ids = [row["candidate_id"] for row in ready]
    summary = {
        "version": VERSION,
        "status": STATUS,
        "hydrated_row_count": len(hydration_rows),
        "backfill_ready_count": len(ready),
        "blocked_count": len(blocked_rows),
        "category_counts": stable_counts,
        "ready_candidate_ids": candidate_ids,
        "bounded_claim": "verified hydrated source rows can be converted into replay-ready queue candidates",
        "does_not_claim": [
            "Lean replay success",
            "proof checking",
            "new proof discovery",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream submission",
        ],
        "next_frontier": "v4.4.8 run the hydrated backfill queue through streaming Lean replay and ledger outcomes",
    }
    plan = {
        "version": VERSION,
        "ready_candidates": ready,
        "blocked_rows": blocked_rows,
        "category_counts": stable_counts,
        "source_hydration_summary": str(hydration_summary_path),
        "notes": notes + [
            "ready rows are replay candidates, not accepted claims",
            f"checked {len(file_hashes) if isinstance(file_hashes, list) else 0} hydrated file hash records",
        ],
        "scanned_paths": sorted(str(path) for path in input_paths) + snippet_paths,
    }
    queue = {
        "version": VERSION,
        "status": QUEUE_STATUS,
        "candidates": ready,
        "provenance": {
            "source_hydration_summary": str(hydration_summary_path),
            "source_hydration_ledger": str(hydration_ledger_path),
            "verified_snippets": str(verified_snippets_path),
            "registration_plan": str(registration_plan_path),
        },
        "bounded_claim": "contains replay candidates derived from verified hydrated source evidence",
        "does_not_claim": summary["does_not_claim"],
    }
    return summary, plan, queue


def write_outputs(
    output_dir: Path,
    summary: dict[str, Any],
    plan: dict[str, Any],
    queue: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("summary.json", summary),
        ("backfill_plan.json", plan),
        ("backfill_queue.json", queue),
    ):
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    summary, plan, queue = plan_queue(
        DEFAULT_HYDRATION_SUMMARY,
        DEFAULT_HYDRATION_LEDGER,
        DEFAULT_FILE_HASHES,
        DEFAULT_VERIFIED_SNIPPETS,
        DEFAULT_REGISTRATION_PLAN,
        DEFAULT_SNIPPET_DIR,
        DEFAULT_PRIOR_BACKFILL_PLAN,
    )
    write_outputs(DEFAULT_OUTPUT_DIR, summary, plan, queue)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
