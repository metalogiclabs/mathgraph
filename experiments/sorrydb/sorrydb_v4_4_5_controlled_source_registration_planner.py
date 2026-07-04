#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


VERSION = "v4.4.5"
STATUS = "CONTROLLED_SOURCE_REGISTRATION_PLANNED"

REGISTRATION_READY_FROM_EXISTING_CHECKOUT = "REGISTRATION_READY_FROM_EXISTING_CHECKOUT"
REGISTRATION_READY_FROM_CONTROLLED_SNIPPET_FIXTURE = "REGISTRATION_READY_FROM_CONTROLLED_SNIPPET_FIXTURE"
REGISTRATION_NEEDS_MANUAL_CHECKOUT = "REGISTRATION_NEEDS_MANUAL_CHECKOUT"
REGISTRATION_NEEDS_NETWORK_HYDRATION = "REGISTRATION_NEEDS_NETWORK_HYDRATION"
REGISTRATION_BLOCKED_INSUFFICIENT_REPO_IDENTITY = "REGISTRATION_BLOCKED_INSUFFICIENT_REPO_IDENTITY"
REGISTRATION_BLOCKED_INSUFFICIENT_FILE_IDENTITY = "REGISTRATION_BLOCKED_INSUFFICIENT_FILE_IDENTITY"
REGISTRATION_BLOCKED_MISSING_SNIPPET_HASH = "REGISTRATION_BLOCKED_MISSING_SNIPPET_HASH"
REGISTRATION_BLOCKED_POLICY_FULL_CHECKOUT = "REGISTRATION_BLOCKED_POLICY_FULL_CHECKOUT"
REGISTRATION_BLOCKED_UNCLASSIFIED = "REGISTRATION_BLOCKED_UNCLASSIFIED"

CATEGORIES = (
    REGISTRATION_READY_FROM_EXISTING_CHECKOUT,
    REGISTRATION_READY_FROM_CONTROLLED_SNIPPET_FIXTURE,
    REGISTRATION_NEEDS_MANUAL_CHECKOUT,
    REGISTRATION_NEEDS_NETWORK_HYDRATION,
    REGISTRATION_BLOCKED_INSUFFICIENT_REPO_IDENTITY,
    REGISTRATION_BLOCKED_INSUFFICIENT_FILE_IDENTITY,
    REGISTRATION_BLOCKED_MISSING_SNIPPET_HASH,
    REGISTRATION_BLOCKED_POLICY_FULL_CHECKOUT,
    REGISTRATION_BLOCKED_UNCLASSIFIED,
)

DEFAULT_LEDGER = Path("artifacts/sorrydb/source_inputs_v4_4_4/source_input_ledger.json")
DEFAULT_LEDGER_SUMMARY = Path("artifacts/sorrydb/source_inputs_v4_4_4/summary.json")
DEFAULT_SNIPPET_DIR = Path("artifacts/sorrydb/source_inputs_v4_4_4/source_snippets")
DEFAULT_REFERENCE_DIRS = (
    Path("artifacts/sorrydb/patch_certificates"),
    Path("artifacts/sorrydb/emitted_patch_certificates_v4_3_4"),
    Path("artifacts/sorrydb/enabled_queue_reality_v4_3_6"),
    Path("artifacts/sorrydb/streaming_reality_v4_3_8"),
    Path("artifacts/sorrydb/mined_queue_reality_v4_4_1"),
)
DEFAULT_CONTROLLED_SOURCE_DIRS = (
    Path("artifacts/sorrydb/controlled_sources"),
)
DEFAULT_OUTPUT_DIR = Path("artifacts/sorrydb/source_registration_v4_4_5")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value is not an object")
    return value


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def repo_url_from_project(project: str) -> str:
    value = project.strip().rstrip("/")
    if value.startswith("https://") or value.startswith("http://"):
        return value.removesuffix(".git")
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        return f"https://github.com/{value.removesuffix('.git')}"
    return ""


def within_roots(path: Path, roots: Iterable[Path]) -> bool:
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def is_certificate(value: dict[str, Any]) -> bool:
    return bool(value.get("certificate_id")) and any(
        key in value for key in ("project", "project_commit", "file_path")
    )


def scan_certificates(
    directories: Iterable[Path],
) -> tuple[dict[str, list[tuple[dict[str, Any], Path]]], list[str], list[str]]:
    certificates: dict[str, list[tuple[dict[str, Any], Path]]] = defaultdict(list)
    scanned_paths: list[str] = []
    notes: list[str] = []
    for directory in directories:
        if not directory.is_dir():
            notes.append(f"missing reference directory: {directory}")
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
    return certificates, scanned_paths, notes


def resolve_certificate(
    row: dict[str, Any],
    certificates: dict[str, list[tuple[dict[str, Any], Path]]],
) -> tuple[dict[str, Any] | None, Path | None]:
    certificate_id = str(row.get("certificate_id", row.get("row_id", "")))
    matches = certificates.get(certificate_id, [])
    if matches:
        return matches[0]
    return None, None


def resolve_snippet_record(
    row: dict[str, Any],
    ledger_path: Path,
    snippet_dir: Path,
) -> tuple[dict[str, Any] | None, Path | None]:
    relative = str(row.get("source_snippet_file", ""))
    candidates: list[Path] = []
    if relative:
        candidates.append(ledger_path.parent / relative)
        candidates.append(snippet_dir / Path(relative).name)
    for path in candidates:
        if not path.is_file():
            continue
        try:
            record = load_object(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if record.get("row_id") == row.get("row_id"):
            return record, path
    return None, None


def controlled_source_file(
    row: dict[str, Any],
    file_path: str,
    controlled_dirs: Iterable[Path],
) -> Path | None:
    candidates: list[Path] = []
    explicit = str(row.get("controlled_source_path", ""))
    if explicit:
        candidates.append(Path(explicit))
    historical = str(row.get("known_repo_root", ""))
    if historical:
        candidates.append(Path(historical) / file_path)
    for directory in controlled_dirs:
        candidates.append(directory / file_path)
    for path in candidates:
        if path.is_file() and within_roots(path, controlled_dirs):
            return path
    return None


def fixture_candidate(
    row: dict[str, Any],
    snippet: dict[str, Any] | None,
    snippet_path: Path | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    row_id = str(row.get("row_id", ""))
    if snippet is None:
        return None, {"row_id": row_id, "reason": "snippet record is missing or unreadable"}
    required = (
        "file_path",
        "source_snippet",
        "source_snippet_sha256",
        "patch_snippet",
        "patch_snippet_sha256",
    )
    missing = [key for key in required if not snippet.get(key)]
    if missing:
        return None, {"row_id": row_id, "reason": f"snippet record missing: {', '.join(missing)}"}
    if sha256_text(str(snippet["source_snippet"])) != snippet["source_snippet_sha256"]:
        return None, {"row_id": row_id, "reason": "source snippet hash mismatch"}
    if sha256_text(str(snippet["patch_snippet"])) != snippet["patch_snippet_sha256"]:
        return None, {"row_id": row_id, "reason": "patch snippet hash mismatch"}
    return {
        "fixture_id": f"v445-fixture-{row_id}",
        "row_id": row_id,
        "file_path": snippet["file_path"],
        "source_snippet_sha256": snippet["source_snippet_sha256"],
        "patch_snippet_sha256": snippet["patch_snippet_sha256"],
        "snippet_record": str(snippet_path or ""),
        "fixture_status": "CONTROLLED_SNIPPET_FIXTURE_PLANNED",
        "replay_ready": False,
        "boundary": "exact snippet context only; not a full source checkout or accepted replay",
    }, None


def classify_registration(
    row: dict[str, Any],
    certificate: dict[str, Any] | None,
    snippet: dict[str, Any] | None,
    *,
    controlled_dirs: Iterable[Path],
) -> dict[str, Any]:
    row_id = str(row.get("row_id", "registration-row"))
    file_path = str(row.get("file_path", "")).strip()
    source_hash = str(row.get("source_snippet_hash", "")).strip()
    patch_hash = str(row.get("patch_snippet_hash", "")).strip()
    historical_root = str(row.get("known_repo_root", ""))
    certificate_id = str(row.get("certificate_id", row_id))
    project = str((certificate or {}).get("project", row.get("project", "")))
    commit = str((certificate or {}).get("project_commit", row.get("commit", "")))
    repo_url = str((certificate or {}).get("repo_url", row.get("repo_url", "")))
    if not repo_url:
        repo_url = repo_url_from_project(project)

    result = {
        "row_id": row_id,
        "source_input_status": str(row.get("source_input_status", "")),
        "registration_status": REGISTRATION_BLOCKED_UNCLASSIFIED,
        "certificate_id": certificate_id,
        "file_path": file_path,
        "source_snippet_sha256": source_hash,
        "patch_snippet_sha256": patch_hash,
        "historical_repo_root": historical_root,
        "historical_repo_root_is_stable": bool(row.get("known_repo_root_is_stable", False)),
        "repo_url": repo_url,
        "commit": commit,
        "required_input": "",
        "reason": "",
    }
    if not file_path:
        result["registration_status"] = REGISTRATION_BLOCKED_INSUFFICIENT_FILE_IDENTITY
        result["reason"] = "file_path is missing"
        return result
    if not source_hash or not patch_hash:
        result["registration_status"] = REGISTRATION_BLOCKED_MISSING_SNIPPET_HASH
        result["reason"] = "source or patch snippet hash is missing"
        return result

    controlled = controlled_source_file(row, file_path, controlled_dirs)
    if controlled is not None and snippet is not None:
        source_snippet = str(snippet.get("source_snippet", ""))
        source_text = controlled.read_text(encoding="utf-8")
        if sha256_text(source_snippet) == source_hash and source_snippet in source_text:
            result["registration_status"] = REGISTRATION_READY_FROM_EXISTING_CHECKOUT
            result["required_input"] = str(controlled)
            result["reason"] = "controlled source file contains the expected source snippet hash"
            return result

    if not repo_url or not commit:
        result["registration_status"] = REGISTRATION_BLOCKED_INSUFFICIENT_REPO_IDENTITY
        result["required_input"] = "repository URL and immutable commit"
        result["reason"] = "repository URL or commit is not recoverable from checked-in evidence"
    elif row.get("source_input_status") == "SOURCE_CHECKOUT_NOT_CHECKED_IN_BY_POLICY":
        result["registration_status"] = REGISTRATION_BLOCKED_POLICY_FULL_CHECKOUT
        result["required_input"] = "approved controlled fixture or external checkout registration"
        result["reason"] = "policy blocks committing the full checkout; fixture or registered external source is required"
    elif repo_url.startswith("https://") or repo_url.startswith("http://"):
        result["registration_status"] = REGISTRATION_NEEDS_NETWORK_HYDRATION
        result["required_input"] = {
            "repo_url": repo_url,
            "commit": commit,
            "file_path": file_path,
            "expected_source_snippet_sha256": source_hash,
        }
        result["reason"] = "repository URL and commit are sufficient for a future controlled hydration; none was performed"
    else:
        result["registration_status"] = REGISTRATION_NEEDS_MANUAL_CHECKOUT
        result["required_input"] = {
            "repository_identity": project or repo_url,
            "commit": commit,
            "file_path": file_path,
        }
        result["reason"] = "repository identity is known but requires manual controlled checkout registration"
    return result


def build_registration_plan(
    ledger_path: Path,
    *,
    ledger_summary_path: Path | None = None,
    snippet_dir: Path,
    reference_dirs: Iterable[Path] = (),
    controlled_source_dirs: Iterable[Path] = (),
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    certificates, scanned_paths, notes = scan_certificates(reference_dirs)
    scanned_paths.append(str(ledger_path))
    ledger: dict[str, Any] = {}
    if ledger_path.exists():
        try:
            ledger = load_object(ledger_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            notes.append(f"malformed source input ledger: {exc}")
    else:
        notes.append(f"missing source input ledger: {ledger_path}")
    if ledger_summary_path is not None:
        scanned_paths.append(str(ledger_summary_path))
        if not ledger_summary_path.exists():
            notes.append(f"missing source input summary: {ledger_summary_path}")

    unstable_rows = [
        row for row in ledger.get("rows", [])
        if isinstance(row, dict) and row.get("source_input_status") == "SOURCE_CHECKOUT_PATH_UNSTABLE"
    ]
    rows: list[dict[str, Any]] = []
    fixture_candidates: list[dict[str, Any]] = []
    fixture_blockers: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    required_manual_inputs: list[dict[str, Any]] = []
    required_hydration_inputs: list[dict[str, Any]] = []

    for source_row in unstable_rows:
        certificate, certificate_path = resolve_certificate(source_row, certificates)
        snippet, snippet_path = resolve_snippet_record(source_row, ledger_path, snippet_dir)
        if certificate_path is not None:
            scanned_paths.append(str(certificate_path))
        if snippet_path is not None:
            scanned_paths.append(str(snippet_path))
        try:
            registration = classify_registration(
                source_row,
                certificate,
                snippet,
                controlled_dirs=controlled_source_dirs,
            )
        except Exception as exc:
            registration = {
                "row_id": str(source_row.get("row_id", "registration-row")),
                "source_input_status": str(source_row.get("source_input_status", "")),
                "registration_status": REGISTRATION_BLOCKED_UNCLASSIFIED,
                "certificate_id": str(source_row.get("certificate_id", "")),
                "file_path": str(source_row.get("file_path", "")),
                "source_snippet_sha256": str(source_row.get("source_snippet_hash", "")),
                "patch_snippet_sha256": str(source_row.get("patch_snippet_hash", "")),
                "historical_repo_root": str(source_row.get("known_repo_root", "")),
                "historical_repo_root_is_stable": bool(source_row.get("known_repo_root_is_stable", False)),
                "repo_url": "",
                "commit": "",
                "required_input": "",
                "reason": f"unexpected registration planning error: {exc}",
            }
        status = registration["registration_status"]
        counts[status] += 1
        rows.append(registration)
        if status == REGISTRATION_NEEDS_MANUAL_CHECKOUT:
            required_manual_inputs.append({
                "row_id": registration["row_id"],
                "required_input": registration["required_input"],
            })
        if status == REGISTRATION_NEEDS_NETWORK_HYDRATION:
            required_hydration_inputs.append({
                "row_id": registration["row_id"],
                "required_input": registration["required_input"],
            })
        fixture, blocker = fixture_candidate(source_row, snippet, snippet_path)
        if fixture is not None:
            fixture_candidates.append(fixture)
        if blocker is not None:
            fixture_blockers.append(blocker)

    rows.sort(key=lambda row: row["row_id"])
    fixture_candidates.sort(key=lambda row: row["row_id"])
    fixture_blockers.sort(key=lambda row: row["row_id"])
    stable_counts = {category: counts.get(category, 0) for category in CATEGORIES}
    ready_count = (
        stable_counts[REGISTRATION_READY_FROM_EXISTING_CHECKOUT]
        + stable_counts[REGISTRATION_READY_FROM_CONTROLLED_SNIPPET_FIXTURE]
    )
    blocked_statuses = (
        REGISTRATION_BLOCKED_INSUFFICIENT_REPO_IDENTITY,
        REGISTRATION_BLOCKED_INSUFFICIENT_FILE_IDENTITY,
        REGISTRATION_BLOCKED_MISSING_SNIPPET_HASH,
        REGISTRATION_BLOCKED_POLICY_FULL_CHECKOUT,
        REGISTRATION_BLOCKED_UNCLASSIFIED,
    )
    summary = {
        "version": VERSION,
        "status": STATUS,
        "unstable_source_row_count": len(unstable_rows),
        "registration_ready_count": ready_count,
        "manual_checkout_needed_count": stable_counts[REGISTRATION_NEEDS_MANUAL_CHECKOUT],
        "network_hydration_needed_count": stable_counts[REGISTRATION_NEEDS_NETWORK_HYDRATION],
        "blocked_count": sum(stable_counts[status] for status in blocked_statuses),
        "category_counts": stable_counts,
        "row_ids": [row["row_id"] for row in rows],
        "bounded_claim": "classifies unstable source rows into controlled source registration statuses and emits registration/fixture plans",
        "does_not_claim": [
            "source hydration",
            "Lean replay success",
            "new proof discovery",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream submission",
        ],
        "next_frontier": "v4.4.6 controlled source hydration/registration or a controlled snippet fixture experiment",
    }
    registration_plan = {
        "version": VERSION,
        "rows": rows,
        "category_counts": stable_counts,
        "source_input_ledger": str(ledger_path),
        "required_manual_inputs": required_manual_inputs,
        "required_hydration_inputs": required_hydration_inputs,
        "notes": notes + [
            "registration plans do not hydrate source or establish replay success",
            "historical temporary checkout paths are provenance only",
        ],
        "scanned_paths": sorted(dict.fromkeys(scanned_paths)),
    }
    fixture_plan = {
        "version": VERSION,
        "fixture_candidates": fixture_candidates,
        "fixture_blockers": fixture_blockers,
        "fixture_policy": {
            "actual_fixtures_created": False,
            "full_checkout_replacement": False,
            "replay_ready": False,
            "boundary": "small exact-context fixture plans are controlled evidence, not full source checkouts or accepted claims",
        },
        "notes": [
            "fixture candidates preserve exact snippet and patch hashes",
            "a separate experiment must define and verify any fixture replay semantics",
        ],
    }
    return summary, registration_plan, fixture_plan


def write_outputs(
    output_dir: Path,
    summary: dict[str, Any],
    registration_plan: dict[str, Any],
    fixture_plan: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("summary.json", summary),
        ("registration_plan.json", registration_plan),
        ("fixture_plan.json", fixture_plan),
    ):
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    summary, registration_plan, fixture_plan = build_registration_plan(
        DEFAULT_LEDGER,
        ledger_summary_path=DEFAULT_LEDGER_SUMMARY,
        snippet_dir=DEFAULT_SNIPPET_DIR,
        reference_dirs=DEFAULT_REFERENCE_DIRS,
        controlled_source_dirs=DEFAULT_CONTROLLED_SOURCE_DIRS,
    )
    write_outputs(DEFAULT_OUTPUT_DIR, summary, registration_plan, fixture_plan)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
