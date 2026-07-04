#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from typing import Any, Iterable


VERSION = "v4.4.3"
STATUS = "MISSING_MANIFEST_BACKFILL_PROFILED"
PATCH_ACCEPTED = "PATCH_ACCEPTED"
NAMED_OBSTRUCTION = "NAMED_OBSTRUCTION"

BACKFILL_REPLAY_READY = "BACKFILL_REPLAY_READY"
BACKFILL_BLOCKED_SOURCE_MISSING = "BACKFILL_BLOCKED_SOURCE_MISSING"
BACKFILL_BLOCKED_FILE_PATH_MISSING = "BACKFILL_BLOCKED_FILE_PATH_MISSING"
BACKFILL_BLOCKED_SOURCE_SNIPPET_MISSING = "BACKFILL_BLOCKED_SOURCE_SNIPPET_MISSING"
BACKFILL_BLOCKED_PATCH_SNIPPET_MISSING = "BACKFILL_BLOCKED_PATCH_SNIPPET_MISSING"
BACKFILL_BLOCKED_SOURCE_SNIPPET_NOT_FOUND = "BACKFILL_BLOCKED_SOURCE_SNIPPET_NOT_FOUND"
BACKFILL_BLOCKED_SOURCE_SNIPPET_AMBIGUOUS = "BACKFILL_BLOCKED_SOURCE_SNIPPET_AMBIGUOUS"
BACKFILL_BLOCKED_NO_SORRY_IN_SOURCE_SNIPPET = "BACKFILL_BLOCKED_NO_SORRY_IN_SOURCE_SNIPPET"
BACKFILL_BLOCKED_MULTIPLE_SORRIES_IN_SOURCE_SNIPPET = "BACKFILL_BLOCKED_MULTIPLE_SORRIES_IN_SOURCE_SNIPPET"
BACKFILL_BLOCKED_INSUFFICIENT_CERTIFICATE = "BACKFILL_BLOCKED_INSUFFICIENT_CERTIFICATE"
BACKFILL_BLOCKED_UNCLASSIFIED = "BACKFILL_BLOCKED_UNCLASSIFIED"

CATEGORIES = (
    BACKFILL_REPLAY_READY,
    BACKFILL_BLOCKED_SOURCE_MISSING,
    BACKFILL_BLOCKED_FILE_PATH_MISSING,
    BACKFILL_BLOCKED_SOURCE_SNIPPET_MISSING,
    BACKFILL_BLOCKED_PATCH_SNIPPET_MISSING,
    BACKFILL_BLOCKED_SOURCE_SNIPPET_NOT_FOUND,
    BACKFILL_BLOCKED_SOURCE_SNIPPET_AMBIGUOUS,
    BACKFILL_BLOCKED_NO_SORRY_IN_SOURCE_SNIPPET,
    BACKFILL_BLOCKED_MULTIPLE_SORRIES_IN_SOURCE_SNIPPET,
    BACKFILL_BLOCKED_INSUFFICIENT_CERTIFICATE,
    BACKFILL_BLOCKED_UNCLASSIFIED,
)

SORRY_RE = re.compile(r"\bsorry\b")

DEFAULT_PROFILE = Path("artifacts/sorrydb/miner_coverage_v4_4_2/profile.json")
DEFAULT_PROFILE_SUMMARY = Path("artifacts/sorrydb/miner_coverage_v4_4_2/summary.json")
DEFAULT_REFERENCE_DIRS = (
    Path("artifacts/sorrydb/patch_certificates"),
    Path("artifacts/sorrydb/emitted_patch_certificates_v4_3_4"),
    Path("artifacts/sorrydb/enabled_queue_reality_v4_3_6"),
    Path("artifacts/sorrydb/streaming_reality_v4_3_8"),
    Path("artifacts/sorrydb/mined_queue_reality_v4_4_1"),
)
DEFAULT_OUTPUT_DIR = Path("artifacts/sorrydb/backfill_plans_v4_4_3")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value is not an object")
    return value


def is_certificate(value: dict[str, Any]) -> bool:
    return bool(value.get("certificate_id")) and any(
        key in value for key in ("source_snippet", "patch_snippet", "file_path")
    )


def is_manifest(value: dict[str, Any]) -> bool:
    return bool(value.get("patch_certificate_id")) and bool(value.get("repo_root"))


def evidence_key(value: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(value.get("project", "")),
        str(value.get("project_commit", "")),
        str(value.get("file_path", "")),
        str(value.get("source_snippet", "")),
        str(value.get("patch_snippet", "")),
    )


def within_roots(path: Path, roots: Iterable[Path]) -> bool:
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def scan_reference_evidence(
    directories: Iterable[Path],
) -> tuple[
    dict[str, list[tuple[dict[str, Any], Path]]],
    dict[tuple[str, str, str, str, str], list[dict[str, Any]]],
    list[str],
    list[str],
]:
    certificates: dict[str, list[tuple[dict[str, Any], Path]]] = defaultdict(list)
    manifests: list[tuple[dict[str, Any], Path]] = []
    scanned_paths: list[str] = []
    notes: list[str] = []

    for directory in directories:
        if not directory.is_dir():
            notes.append(f"missing input directory: {directory}")
            continue
        for path in sorted(directory.rglob("*.json")):
            scanned_paths.append(str(path))
            try:
                value = load_object(path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                notes.append(f"ignored malformed JSON {path}: {exc}")
                continue
            if is_certificate(value):
                certificates[str(value["certificate_id"])].append((value, path))
            if is_manifest(value):
                manifests.append((value, path))

    repo_roots: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for manifest, manifest_path in manifests:
        certificate_id = str(manifest.get("patch_certificate_id", ""))
        for certificate, certificate_path in certificates.get(certificate_id, []):
            key = evidence_key(certificate)
            if all(key) and manifest.get("file_path") == certificate.get("file_path"):
                repo_roots[key].append({
                    "repo_root": str(manifest["repo_root"]),
                    "manifest_path": str(manifest_path),
                    "certificate_path": str(certificate_path),
                })
    return certificates, dict(repo_roots), scanned_paths, notes


def resolve_certificate(
    row: dict[str, Any],
    certificates: dict[str, list[tuple[dict[str, Any], Path]]],
) -> tuple[dict[str, Any] | None, Path | None, str]:
    evidence_id = str(row.get("evidence_id", ""))
    for raw_path in row.get("certificate_paths", []):
        path = Path(str(raw_path))
        try:
            value = load_object(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if value.get("certificate_id") == evidence_id:
            return value, path, "profile certificate path"
    matches = certificates.get(evidence_id, [])
    if matches:
        value, path = matches[0]
        return value, path, "recursive certificate scan"
    return None, None, ""


def blocked_row(
    row: dict[str, Any],
    category: str,
    *,
    certificate_path: Path | None = None,
    detail: str = "",
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "terminal_form": NAMED_OBSTRUCTION,
        "category": category,
        "evidence_id": str(row.get("evidence_id", "")),
        "source_profile_row": row,
    }
    if certificate_path is not None:
        result["certificate_path"] = str(certificate_path)
    if detail:
        result["detail"] = detail
    return result


def classify_missing_manifest_row(
    row: dict[str, Any],
    certificate: dict[str, Any] | None,
    certificate_path: Path | None,
    *,
    repo_root_index: dict[tuple[str, str, str, str, str], list[dict[str, Any]]],
    source_roots: Iterable[Path],
) -> tuple[str, dict[str, Any]]:
    if certificate is None:
        return BACKFILL_BLOCKED_INSUFFICIENT_CERTIFICATE, blocked_row(
            row,
            BACKFILL_BLOCKED_INSUFFICIENT_CERTIFICATE,
            detail="no readable matching certificate",
        )
    if (
        certificate.get("final_verdict") != PATCH_ACCEPTED
        or certificate.get("lean_returncode") != 0
    ):
        return BACKFILL_BLOCKED_INSUFFICIENT_CERTIFICATE, blocked_row(
            row,
            BACKFILL_BLOCKED_INSUFFICIENT_CERTIFICATE,
            certificate_path=certificate_path,
            detail="certificate is not accepted replay evidence",
        )

    file_path = str(certificate.get("file_path", "")).strip()
    if not file_path:
        return BACKFILL_BLOCKED_FILE_PATH_MISSING, blocked_row(
            row, BACKFILL_BLOCKED_FILE_PATH_MISSING, certificate_path=certificate_path
        )
    source_snippet = str(certificate.get("source_snippet", ""))
    if not source_snippet:
        return BACKFILL_BLOCKED_SOURCE_SNIPPET_MISSING, blocked_row(
            row, BACKFILL_BLOCKED_SOURCE_SNIPPET_MISSING, certificate_path=certificate_path
        )
    patch_snippet = str(certificate.get("patch_snippet", ""))
    if not patch_snippet:
        return BACKFILL_BLOCKED_PATCH_SNIPPET_MISSING, blocked_row(
            row, BACKFILL_BLOCKED_PATCH_SNIPPET_MISSING, certificate_path=certificate_path
        )

    sorry_count = len(SORRY_RE.findall(source_snippet))
    if sorry_count == 0:
        return BACKFILL_BLOCKED_NO_SORRY_IN_SOURCE_SNIPPET, blocked_row(
            row, BACKFILL_BLOCKED_NO_SORRY_IN_SOURCE_SNIPPET, certificate_path=certificate_path
        )
    if sorry_count > 1:
        return BACKFILL_BLOCKED_MULTIPLE_SORRIES_IN_SOURCE_SNIPPET, blocked_row(
            row, BACKFILL_BLOCKED_MULTIPLE_SORRIES_IN_SOURCE_SNIPPET, certificate_path=certificate_path
        )

    repo_root = str(certificate.get("repo_root", "")).strip()
    recovery: dict[str, Any] | None = None
    if not repo_root:
        recovered = repo_root_index.get(evidence_key(certificate), [])
        if recovered:
            recovery = recovered[0]
            repo_root = str(recovery["repo_root"])
    if not repo_root:
        return BACKFILL_BLOCKED_INSUFFICIENT_CERTIFICATE, blocked_row(
            row,
            BACKFILL_BLOCKED_INSUFFICIENT_CERTIFICATE,
            certificate_path=certificate_path,
            detail="repo_root is absent and not recoverable from checked-in evidence",
        )

    source_path = Path(repo_root) / file_path
    if not source_path.is_file() or not within_roots(source_path, source_roots):
        return BACKFILL_BLOCKED_SOURCE_MISSING, blocked_row(
            row,
            BACKFILL_BLOCKED_SOURCE_MISSING,
            certificate_path=certificate_path,
            detail=f"source is unavailable as a checked-in input: {source_path}",
        )

    source_text = source_path.read_text(encoding="utf-8")
    occurrence_count = source_text.count(source_snippet)
    if occurrence_count == 0:
        return BACKFILL_BLOCKED_SOURCE_SNIPPET_NOT_FOUND, blocked_row(
            row, BACKFILL_BLOCKED_SOURCE_SNIPPET_NOT_FOUND, certificate_path=certificate_path
        )
    if occurrence_count > 1:
        return BACKFILL_BLOCKED_SOURCE_SNIPPET_AMBIGUOUS, blocked_row(
            row, BACKFILL_BLOCKED_SOURCE_SNIPPET_AMBIGUOUS, certificate_path=certificate_path
        )

    certificate_id = str(certificate.get("certificate_id", row.get("evidence_id", "")))
    candidate = {
        "candidate_id": f"v443-backfill-{certificate_id}",
        "repo_root": repo_root,
        "file_path": file_path,
        "source_snippet": source_snippet,
        "patch_snippet": patch_snippet,
        "timeout_seconds": 120,
        "queue_timeout_seconds": 240,
        "project": certificate.get("project", ""),
        "project_commit": certificate.get("project_commit", ""),
        "certificate_id": certificate_id,
        "certificate_version": certificate.get("certificate_version", ""),
        "restore_check": certificate.get("restore_check", "original source restored after replay"),
        "provenance": {
            "source_profile_evidence_id": row.get("evidence_id", ""),
            "certificate_path": str(certificate_path or ""),
            "repo_root_recovery": recovery or "certificate field",
            "planner_version": VERSION,
        },
    }
    return BACKFILL_REPLAY_READY, candidate


def plan_backfills(
    profile_path: Path,
    *,
    profile_summary_path: Path | None = None,
    reference_dirs: Iterable[Path] = (),
    source_roots: Iterable[Path] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    profile = load_object(profile_path)
    certificates, repo_root_index, scanned_paths, notes = scan_reference_evidence(reference_dirs)
    scanned_paths.append(str(profile_path))
    if profile_summary_path is not None:
        scanned_paths.append(str(profile_summary_path))
        if profile_summary_path.exists():
            try:
                load_object(profile_summary_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                notes.append(f"malformed source profile summary: {exc}")
        else:
            notes.append(f"missing source profile summary: {profile_summary_path}")

    missing_rows = [
        row
        for row in profile.get("obstructions", [])
        if isinstance(row, dict) and row.get("category") == "MISSING_MANIFEST"
    ]
    ready_candidates: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()

    for row in missing_rows:
        certificate, certificate_path, resolution = resolve_certificate(row, certificates)
        if certificate_path is not None:
            scanned_paths.append(str(certificate_path))
        try:
            category, result = classify_missing_manifest_row(
                row,
                certificate,
                certificate_path,
                repo_root_index=repo_root_index,
                source_roots=source_roots,
            )
        except Exception as exc:
            category = BACKFILL_BLOCKED_UNCLASSIFIED
            result = blocked_row(
                row,
                category,
                certificate_path=certificate_path,
                detail=f"unexpected planning error: {exc}",
            )
        counts[category] += 1
        if category == BACKFILL_REPLAY_READY:
            result["provenance"]["certificate_resolution"] = resolution
            ready_candidates.append(result)
        else:
            result["certificate_resolution"] = resolution
            blocked_rows.append(result)

    ready_candidates.sort(key=lambda row: row["candidate_id"])
    blocked_rows.sort(key=lambda row: (row["category"], row["evidence_id"]))
    stable_counts = {category: counts.get(category, 0) for category in CATEGORIES}
    plan = {
        "version": VERSION,
        "ready_candidates": ready_candidates,
        "blocked_rows": blocked_rows,
        "category_counts": stable_counts,
        "source_profile": str(profile_path),
        "scanned_paths": sorted(dict.fromkeys(scanned_paths)),
        "notes": notes + [
            "ready candidates are replay plans, not accepted claims",
            "blocked rows remain NAMED_OBSTRUCTION records",
        ],
    }
    summary = {
        "version": VERSION,
        "status": STATUS,
        "missing_manifest_count": len(missing_rows),
        "backfill_ready_count": len(ready_candidates),
        "blocked_count": len(blocked_rows),
        "category_counts": stable_counts,
        "ready_candidate_ids": [row["candidate_id"] for row in ready_candidates],
        "bounded_claim": "classifies missing-manifest evidence rows into replay-ready candidates or named backfill obstructions",
        "does_not_claim": [
            "new proof discovery",
            "Lean replay success",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream submission",
        ],
        "next_frontier": "v4.4.4: run any BACKFILL_REPLAY_READY queue through streaming Lean replay",
    }
    return summary, plan


def write_outputs(output_dir: Path, summary: dict[str, Any], plan: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "backfill_plan.json").write_text(
        json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    queue_path = output_dir / "backfill_queue.json"
    if plan["ready_candidates"]:
        queue = {
            "version": VERSION,
            "status": "BACKFILL_REPLAY_QUEUE_PLANNED",
            "bounded_claim": "contains replay candidates only; no replay acceptance is claimed",
            "candidates": plan["ready_candidates"],
        }
        queue_path.write_text(
            json.dumps(queue, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    elif queue_path.exists():
        queue_path.unlink()


def main() -> int:
    summary, plan = plan_backfills(
        DEFAULT_PROFILE,
        profile_summary_path=DEFAULT_PROFILE_SUMMARY,
        reference_dirs=DEFAULT_REFERENCE_DIRS,
        source_roots=[Path.cwd()],
    )
    write_outputs(DEFAULT_OUTPUT_DIR, summary, plan)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
