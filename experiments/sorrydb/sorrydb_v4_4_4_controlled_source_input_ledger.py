#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


VERSION = "v4.4.4"
STATUS = "CONTROLLED_SOURCE_INPUTS_PROFILED"

SOURCE_CHECKOUT_AVAILABLE = "SOURCE_CHECKOUT_AVAILABLE"
SOURCE_CHECKOUT_UNAVAILABLE = "SOURCE_CHECKOUT_UNAVAILABLE"
SOURCE_CHECKOUT_NOT_CHECKED_IN_BY_POLICY = "SOURCE_CHECKOUT_NOT_CHECKED_IN_BY_POLICY"
SOURCE_CHECKOUT_PATH_UNSTABLE = "SOURCE_CHECKOUT_PATH_UNSTABLE"
SOURCE_SNIPPET_ONLY_AVAILABLE = "SOURCE_SNIPPET_ONLY_AVAILABLE"
SOURCE_INPUT_INSUFFICIENT = "SOURCE_INPUT_INSUFFICIENT"
SOURCE_INPUT_UNCLASSIFIED = "SOURCE_INPUT_UNCLASSIFIED"

CATEGORIES = (
    SOURCE_CHECKOUT_AVAILABLE,
    SOURCE_CHECKOUT_UNAVAILABLE,
    SOURCE_CHECKOUT_NOT_CHECKED_IN_BY_POLICY,
    SOURCE_CHECKOUT_PATH_UNSTABLE,
    SOURCE_SNIPPET_ONLY_AVAILABLE,
    SOURCE_INPUT_INSUFFICIENT,
    SOURCE_INPUT_UNCLASSIFIED,
)

DEFAULT_PLAN = Path("artifacts/sorrydb/backfill_plans_v4_4_3/backfill_plan.json")
DEFAULT_PLAN_SUMMARY = Path("artifacts/sorrydb/backfill_plans_v4_4_3/summary.json")
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
DEFAULT_OUTPUT_DIR = Path("artifacts/sorrydb/source_inputs_v4_4_4")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value is not an object")
    return value


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_row_id(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return slug or "source-row"


def path_is_unstable(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("/tmp/") or normalized == "/tmp":
        return True
    if re.match(r"^/Users/[^/]+/", normalized):
        return True
    if re.match(r"^/home/[^/]+/", normalized):
        return True
    return False


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
        key in value for key in ("file_path", "source_snippet", "patch_snippet")
    )


def is_repo_manifest(value: dict[str, Any]) -> bool:
    return bool(value.get("patch_certificate_id")) and bool(value.get("repo_root"))


def evidence_key(value: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(value.get("project", "")),
        str(value.get("project_commit", "")),
        str(value.get("file_path", "")),
        str(value.get("source_snippet", "")),
        str(value.get("patch_snippet", "")),
    )


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
            if is_repo_manifest(value):
                manifests.append((value, path))

    roots_by_evidence: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for manifest, manifest_path in manifests:
        certificate_id = str(manifest.get("patch_certificate_id", ""))
        for certificate, certificate_path in certificates.get(certificate_id, []):
            key = evidence_key(certificate)
            if all(key) and manifest.get("file_path") == certificate.get("file_path"):
                roots_by_evidence[key].append({
                    "repo_root": str(manifest["repo_root"]),
                    "manifest_path": str(manifest_path),
                    "certificate_path": str(certificate_path),
                })
    return certificates, dict(roots_by_evidence), scanned_paths, notes


def resolve_certificate(
    row: dict[str, Any],
    certificates: dict[str, list[tuple[dict[str, Any], Path]]],
) -> tuple[dict[str, Any] | None, Path | None]:
    certificate_id = str(row.get("evidence_id", row.get("certificate_id", "")))
    direct = str(row.get("certificate_path", ""))
    if direct:
        path = Path(direct)
        try:
            value = load_object(path)
        except (OSError, ValueError, json.JSONDecodeError):
            value = {}
        if value.get("certificate_id") == certificate_id:
            return value, path
    matches = certificates.get(certificate_id, [])
    if matches:
        return matches[0]
    return None, None


def controlled_source_path(
    certificate: dict[str, Any],
    known_repo_root: str,
    controlled_dirs: Iterable[Path],
) -> Path | None:
    file_path = str(certificate.get("file_path", ""))
    candidates: list[Path] = []
    explicit = str(certificate.get("controlled_source_path", ""))
    if explicit:
        candidates.append(Path(explicit))
    if known_repo_root:
        candidates.append(Path(known_repo_root) / file_path)
    for directory in controlled_dirs:
        candidates.append(directory / file_path)
    for candidate in candidates:
        if candidate.is_file() and within_roots(candidate, controlled_dirs):
            return candidate
    return None


def classify_source_input(
    row: dict[str, Any],
    certificate: dict[str, Any] | None,
    *,
    roots_by_evidence: dict[tuple[str, str, str, str, str], list[dict[str, Any]]],
    controlled_dirs: Iterable[Path],
) -> dict[str, Any]:
    row_id = str(row.get("evidence_id", row.get("row_id", "source-row")))
    base: dict[str, Any] = {
        "row_id": row_id,
        "prior_backfill_category": str(row.get("category", "")),
        "source_input_status": SOURCE_INPUT_UNCLASSIFIED,
        "file_path": "",
        "certificate_id": "",
        "known_repo_root": "",
        "known_repo_root_is_stable": False,
        "source_snippet_hash": "",
        "patch_snippet_hash": "",
        "source_snippet_file": "",
        "reason": "",
    }
    if certificate is None:
        base["source_input_status"] = SOURCE_INPUT_INSUFFICIENT
        base["reason"] = "no readable matching certificate"
        return base

    file_path = str(certificate.get("file_path", "")).strip()
    source_snippet = str(certificate.get("source_snippet", ""))
    patch_snippet = str(certificate.get("patch_snippet", ""))
    certificate_id = str(certificate.get("certificate_id", row_id))
    known_repo_root = str(certificate.get("repo_root", "")).strip()
    root_provenance: dict[str, Any] | None = None
    if not known_repo_root:
        recovered = roots_by_evidence.get(evidence_key(certificate), [])
        if recovered:
            root_provenance = recovered[0]
            known_repo_root = str(root_provenance["repo_root"])

    base.update({
        "file_path": file_path,
        "certificate_id": certificate_id,
        "known_repo_root": known_repo_root,
        "known_repo_root_is_stable": bool(known_repo_root and not path_is_unstable(known_repo_root)),
        "source_snippet_hash": sha256_text(source_snippet) if source_snippet else "",
        "patch_snippet_hash": sha256_text(patch_snippet) if patch_snippet else "",
    })
    if root_provenance is not None:
        base["repo_root_provenance"] = root_provenance

    controlled = controlled_source_path(certificate, known_repo_root, controlled_dirs)
    if controlled is not None:
        base["source_input_status"] = SOURCE_CHECKOUT_AVAILABLE
        base["controlled_source_path"] = str(controlled)
        base["known_repo_root_is_stable"] = True
        base["reason"] = "full source file exists inside a controlled checked-in source directory"
    elif not file_path or not source_snippet or not patch_snippet:
        base["source_input_status"] = SOURCE_INPUT_INSUFFICIENT
        base["reason"] = "file_path, source_snippet, or patch_snippet evidence is missing"
    elif known_repo_root and path_is_unstable(known_repo_root):
        base["source_input_status"] = SOURCE_CHECKOUT_PATH_UNSTABLE
        base["reason"] = "only a temporary or user-local checkout path is known; snippet/hash evidence is preserved"
    elif known_repo_root and Path(known_repo_root).is_absolute():
        base["source_input_status"] = SOURCE_CHECKOUT_NOT_CHECKED_IN_BY_POLICY
        base["reason"] = "external full checkout is not a controlled repository input; snippets and hashes are preferred"
    elif source_snippet:
        base["source_input_status"] = SOURCE_SNIPPET_ONLY_AVAILABLE
        base["reason"] = "exact snippet evidence exists but no controlled full source checkout is registered"
    else:
        base["source_input_status"] = SOURCE_CHECKOUT_UNAVAILABLE
        base["reason"] = "no controlled source checkout or safe source text is available"
    return base


def build_ledger(
    plan_path: Path,
    *,
    plan_summary_path: Path | None = None,
    reference_dirs: Iterable[Path] = (),
    controlled_source_dirs: Iterable[Path] = (),
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    controlled_dirs = list(controlled_source_dirs)
    certificates, roots_by_evidence, scanned_paths, notes = scan_reference_evidence(reference_dirs)
    scanned_paths.append(str(plan_path))
    plan: dict[str, Any] = {}
    if plan_path.exists():
        try:
            plan = load_object(plan_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            notes.append(f"malformed backfill plan: {exc}")
    else:
        notes.append(f"missing backfill plan: {plan_path}")
    if plan_summary_path is not None:
        scanned_paths.append(str(plan_summary_path))
        if not plan_summary_path.exists():
            notes.append(f"missing backfill summary: {plan_summary_path}")

    blocked_rows = [
        row for row in plan.get("blocked_rows", [])
        if isinstance(row, dict) and row.get("category") == "BACKFILL_BLOCKED_SOURCE_MISSING"
    ]
    rows: list[dict[str, Any]] = []
    snippet_payloads: dict[str, dict[str, Any]] = {}
    counts: Counter[str] = Counter()
    for blocked in blocked_rows:
        certificate, certificate_path = resolve_certificate(blocked, certificates)
        if certificate_path is not None:
            scanned_paths.append(str(certificate_path))
        try:
            ledger_row = classify_source_input(
                blocked,
                certificate,
                roots_by_evidence=roots_by_evidence,
                controlled_dirs=controlled_dirs,
            )
        except Exception as exc:
            ledger_row = {
                "row_id": str(blocked.get("evidence_id", "source-row")),
                "prior_backfill_category": str(blocked.get("category", "")),
                "source_input_status": SOURCE_INPUT_UNCLASSIFIED,
                "file_path": "",
                "certificate_id": "",
                "known_repo_root": "",
                "known_repo_root_is_stable": False,
                "source_snippet_hash": "",
                "patch_snippet_hash": "",
                "source_snippet_file": "",
                "reason": f"unexpected source accounting error: {exc}",
            }
        status = ledger_row["source_input_status"]
        counts[status] += 1
        if certificate is not None and certificate.get("source_snippet"):
            row_id = ledger_row["row_id"]
            filename = f"{safe_row_id(row_id)}.json"
            ledger_row["source_snippet_file"] = f"source_snippets/{filename}"
            source_snippet = str(certificate.get("source_snippet", ""))
            patch_snippet = str(certificate.get("patch_snippet", ""))
            snippet_payloads[filename] = {
                "row_id": row_id,
                "file_path": ledger_row["file_path"],
                "source_snippet": source_snippet,
                "source_snippet_sha256": sha256_text(source_snippet),
                "patch_snippet": patch_snippet,
                "patch_snippet_sha256": sha256_text(patch_snippet),
                "certificate_id": ledger_row["certificate_id"],
                "status": status,
            }
        rows.append(ledger_row)

    rows.sort(key=lambda row: row["row_id"])
    stable_counts = {category: counts.get(category, 0) for category in CATEGORIES}
    ledger = {
        "version": VERSION,
        "rows": rows,
        "category_counts": stable_counts,
        "controlled_source_dirs_scanned": [
            {"path": str(path), "exists": path.is_dir()} for path in controlled_dirs
        ],
        "source_snippet_files": [f"source_snippets/{name}" for name in sorted(snippet_payloads)],
        "notes": notes + [
            "snippet/hash records are controlled inputs but are not replay-ready full source checkouts",
            "temporary and user-local checkout paths are recorded as unstable, never silently trusted",
        ],
        "scanned_paths": sorted(dict.fromkeys(scanned_paths)),
    }
    summary = {
        "version": VERSION,
        "status": STATUS,
        "blocked_source_missing_count": len(blocked_rows),
        "source_checkout_available_count": stable_counts[SOURCE_CHECKOUT_AVAILABLE],
        "source_snippet_only_count": stable_counts[SOURCE_SNIPPET_ONLY_AVAILABLE],
        "source_input_insufficient_count": stable_counts[SOURCE_INPUT_INSUFFICIENT],
        "category_counts": stable_counts,
        "row_ids": [row["row_id"] for row in rows],
        "bounded_claim": "classifies missing-source backfill rows into controlled source-input statuses and emits snippet/hash evidence",
        "does_not_claim": [
            "new proof discovery",
            "Lean replay success",
            "source hydration",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream submission",
        ],
        "next_frontier": "v4.4.5 source hydration plan, a controlled small source fixture package, or manual source checkout registration",
    }
    return summary, ledger, snippet_payloads


def write_outputs(
    output_dir: Path,
    summary: dict[str, Any],
    ledger: dict[str, Any],
    snippet_payloads: dict[str, dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    snippet_dir = output_dir / "source_snippets"
    snippet_dir.mkdir(parents=True, exist_ok=True)
    for stale in snippet_dir.glob("*.json"):
        stale.unlink()
    for filename, payload in sorted(snippet_payloads.items()):
        (snippet_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "source_input_ledger.json").write_text(
        json.dumps(ledger, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    summary, ledger, snippet_payloads = build_ledger(
        DEFAULT_PLAN,
        plan_summary_path=DEFAULT_PLAN_SUMMARY,
        reference_dirs=DEFAULT_REFERENCE_DIRS,
        controlled_source_dirs=DEFAULT_CONTROLLED_SOURCE_DIRS,
    )
    write_outputs(DEFAULT_OUTPUT_DIR, summary, ledger, snippet_payloads)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
