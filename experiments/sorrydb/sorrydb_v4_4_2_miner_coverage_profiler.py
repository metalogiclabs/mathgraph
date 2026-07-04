#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
from typing import Any, Iterable


VERSION = "v4.4.2"
STATUS = "MINER_COVERAGE_PROFILED"
PATCH_ACCEPTED = "PATCH_ACCEPTED"
NAMED_OBSTRUCTION = "NAMED_OBSTRUCTION"

MINED_CANDIDATE = "MINED_CANDIDATE"
MISSING_MANIFEST = "MISSING_MANIFEST"
MISSING_CERTIFICATE = "MISSING_CERTIFICATE"
MANIFEST_NOT_ACCEPTED = "MANIFEST_NOT_ACCEPTED"
CERTIFICATE_NOT_ACCEPTED = "CERTIFICATE_NOT_ACCEPTED"
MANIFEST_CERTIFICATE_ID_MISMATCH = "MANIFEST_CERTIFICATE_ID_MISMATCH"
FILE_PATH_MISMATCH = "FILE_PATH_MISMATCH"
SOURCE_SNIPPET_MISMATCH = "SOURCE_SNIPPET_MISMATCH"
PATCH_SNIPPET_MISMATCH = "PATCH_SNIPPET_MISMATCH"
SOURCE_FILE_MISSING = "SOURCE_FILE_MISSING"
SOURCE_SNIPPET_NOT_FOUND = "SOURCE_SNIPPET_NOT_FOUND"
SOURCE_SNIPPET_AMBIGUOUS = "SOURCE_SNIPPET_AMBIGUOUS"
NO_SORRY_IN_SOURCE_SNIPPET = "NO_SORRY_IN_SOURCE_SNIPPET"
MULTIPLE_SORRIES_IN_SOURCE_SNIPPET = "MULTIPLE_SORRIES_IN_SOURCE_SNIPPET"
SORRY_OUTSIDE_KNOWN_SPAN = "SORRY_OUTSIDE_KNOWN_SPAN"
UNCLASSIFIED_OBSTRUCTION = "UNCLASSIFIED_OBSTRUCTION"

CATEGORIES = (
    MINED_CANDIDATE,
    MISSING_MANIFEST,
    MISSING_CERTIFICATE,
    MANIFEST_NOT_ACCEPTED,
    CERTIFICATE_NOT_ACCEPTED,
    MANIFEST_CERTIFICATE_ID_MISMATCH,
    FILE_PATH_MISMATCH,
    SOURCE_SNIPPET_MISMATCH,
    PATCH_SNIPPET_MISMATCH,
    SOURCE_FILE_MISSING,
    SOURCE_SNIPPET_NOT_FOUND,
    SOURCE_SNIPPET_AMBIGUOUS,
    NO_SORRY_IN_SOURCE_SNIPPET,
    MULTIPLE_SORRIES_IN_SOURCE_SNIPPET,
    SORRY_OUTSIDE_KNOWN_SPAN,
    UNCLASSIFIED_OBSTRUCTION,
)

SORRY_RE = re.compile(r"\bsorry\b")

DEFAULT_INPUT_DIRS = (
    Path("artifacts/sorrydb/streaming_reality_v4_3_8"),
    Path("artifacts/sorrydb/mined_queue_reality_v4_4_1"),
    Path("artifacts/sorrydb/emitted_patch_certificates_v4_3_4"),
    Path("artifacts/sorrydb/patch_certificates"),
    Path("artifacts/sorrydb/enabled_queue_reality_v4_3_6"),
)
DEFAULT_MINED_QUEUE = Path(
    "artifacts/sorrydb/mined_queues/sorrydb_v4_4_0_exact_source_candidates.json"
)
DEFAULT_OUTPUT_DIR = Path("artifacts/sorrydb/miner_coverage_v4_4_2")


def load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("top-level JSON value is not an object")
    return value


def is_manifest(value: dict[str, Any]) -> bool:
    return bool(value.get("patch_certificate_id")) and (
        "patch_result" in value or "patch_verdict" in value
    )


def is_certificate(value: dict[str, Any]) -> bool:
    return bool(value.get("certificate_id")) and all(
        key in value for key in ("file_path", "source_snippet", "patch_snippet")
    )


def accepted_manifest(value: dict[str, Any]) -> bool:
    patch_result = value.get("patch_result") or {}
    return (
        value.get("verdict") == PATCH_ACCEPTED
        and value.get("patch_verdict") == PATCH_ACCEPTED
        and patch_result.get("returncode") == 0
    )


def accepted_certificate(value: dict[str, Any]) -> bool:
    return (
        value.get("final_verdict") == PATCH_ACCEPTED
        and value.get("lean_returncode") == 0
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


def source_path_for(manifest: dict[str, Any], certificate: dict[str, Any]) -> Path:
    source = str(manifest.get("source", ""))
    if source:
        return Path(source)
    repo_root = Path(str(manifest.get("repo_root", "")))
    return repo_root / str(certificate.get("file_path", ""))


def known_span_contains(spans: list[dict[str, int]], line: int) -> bool:
    return any(
        int(span.get("start_line", 0)) <= line <= int(span.get("end_line", 0))
        for span in spans
    )


def classify_pair(
    manifest: dict[str, Any],
    certificate: dict[str, Any],
    *,
    source_roots: Iterable[Path],
    known_spans: list[dict[str, int]],
    already_mined: bool = False,
) -> tuple[str, dict[str, Any]]:
    manifest_id = str(manifest.get("patch_certificate_id", ""))
    certificate_id = str(certificate.get("certificate_id", ""))
    detail: dict[str, Any] = {
        "manifest_certificate_id": manifest_id,
        "certificate_id": certificate_id,
    }

    if not accepted_manifest(manifest):
        return MANIFEST_NOT_ACCEPTED, detail
    if not accepted_certificate(certificate):
        return CERTIFICATE_NOT_ACCEPTED, detail
    if manifest_id != certificate_id:
        return MANIFEST_CERTIFICATE_ID_MISMATCH, detail
    if manifest.get("file_path") != certificate.get("file_path"):
        return FILE_PATH_MISMATCH, detail
    if manifest.get("source_snippet") != certificate.get("source_snippet"):
        return SOURCE_SNIPPET_MISMATCH, detail
    if manifest.get("patch_snippet") != certificate.get("patch_snippet"):
        return PATCH_SNIPPET_MISMATCH, detail

    snippet = str(certificate.get("source_snippet", ""))
    sorry_matches = list(SORRY_RE.finditer(snippet))
    if not sorry_matches:
        return NO_SORRY_IN_SOURCE_SNIPPET, detail
    if len(sorry_matches) > 1:
        return MULTIPLE_SORRIES_IN_SOURCE_SNIPPET, detail

    if already_mined:
        detail["classification_basis"] = "checked-in v4.4.0 mined queue"
        return MINED_CANDIDATE, detail

    source_path = source_path_for(manifest, certificate)
    detail["source_path"] = str(source_path)
    if (
        not source_path.is_file()
        or not within_roots(source_path, source_roots)
    ):
        return SOURCE_FILE_MISSING, detail

    source_text = source_path.read_text(encoding="utf-8")
    occurrence_count = source_text.count(snippet)
    detail["source_snippet_occurrence_count"] = occurrence_count
    if occurrence_count == 0:
        return SOURCE_SNIPPET_NOT_FOUND, detail
    if occurrence_count > 1:
        return SOURCE_SNIPPET_AMBIGUOUS, detail

    offset = source_text.index(snippet)
    start_line = source_text.count("\n", 0, offset) + 1
    sorry_line = start_line + snippet.count("\n", 0, sorry_matches[0].start())
    detail["sorry_line"] = sorry_line
    if not known_span_contains(known_spans, sorry_line):
        return SORRY_OUTSIDE_KNOWN_SPAN, detail
    return MINED_CANDIDATE, detail


def load_mined_queue(
    path: Path | None,
) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, int]]], list[dict[str, Any]]]:
    if path is None or not path.exists():
        return {}, {}, []
    try:
        queue = load_json_object(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {}, {}, [{
            "terminal_form": NAMED_OBSTRUCTION,
            "category": UNCLASSIFIED_OBSTRUCTION,
            "path": str(path),
            "detail": f"malformed mined queue: {exc}",
        }]

    mined: dict[str, dict[str, Any]] = {}
    spans_by_file: dict[str, list[dict[str, int]]] = defaultdict(list)
    for candidate in queue.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        certificate_id = str(candidate.get("certificate_id", ""))
        if certificate_id:
            mined[certificate_id] = candidate
        file_path = str(candidate.get("file_path", ""))
        span = candidate.get("sorry_span")
        if file_path and isinstance(span, dict):
            spans_by_file[file_path].append(span)
    return mined, dict(spans_by_file), []


def profile_evidence(
    input_dirs: Iterable[Path],
    *,
    mined_queue_path: Path | None = None,
    source_roots: Iterable[Path] = (),
    known_spans_by_file: dict[str, list[dict[str, int]]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_groups: dict[str, list[tuple[dict[str, Any], Path]]] = defaultdict(list)
    certificate_groups: dict[str, list[tuple[dict[str, Any], Path]]] = defaultdict(list)
    scanned_paths: list[str] = []
    missing_input_dirs: list[str] = []
    malformed: list[dict[str, Any]] = []

    for directory in input_dirs:
        if not directory.is_dir():
            missing_input_dirs.append(str(directory))
            continue
        for path in sorted(directory.rglob("*.json")):
            scanned_paths.append(str(path))
            try:
                value = load_json_object(path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                malformed.append({
                    "terminal_form": NAMED_OBSTRUCTION,
                    "category": UNCLASSIFIED_OBSTRUCTION,
                    "path": str(path),
                    "detail": f"malformed JSON: {exc}",
                })
                continue
            if is_manifest(value):
                manifest_groups[str(value["patch_certificate_id"])].append((value, path))
            elif is_certificate(value):
                certificate_groups[str(value["certificate_id"])].append((value, path))

    mined_by_id, queue_spans, queue_obstructions = load_mined_queue(mined_queue_path)
    if mined_queue_path is not None:
        scanned_paths.append(str(mined_queue_path))
    spans_by_file = dict(queue_spans)
    for file_path, spans in (known_spans_by_file or {}).items():
        spans_by_file.setdefault(file_path, []).extend(spans)

    duplicate_groups: list[dict[str, Any]] = []
    for kind, groups in (("manifest", manifest_groups), ("certificate", certificate_groups)):
        for evidence_id, rows in sorted(groups.items()):
            if len(rows) > 1:
                duplicate_groups.append({
                    "kind": kind,
                    "evidence_id": evidence_id,
                    "count": len(rows),
                    "paths": [str(path) for _, path in rows],
                })

    candidates: list[dict[str, Any]] = []
    obstructions: list[dict[str, Any]] = malformed + queue_obstructions
    category_counts: Counter[str] = Counter(
        obstruction["category"] for obstruction in obstructions
    )

    evidence_ids = sorted(set(manifest_groups) | set(certificate_groups))
    for evidence_id in evidence_ids:
        manifests = manifest_groups.get(evidence_id, [])
        certificates = certificate_groups.get(evidence_id, [])
        base = {
            "evidence_id": evidence_id,
            "manifest_paths": [str(path) for _, path in manifests],
            "certificate_paths": [str(path) for _, path in certificates],
        }
        if not manifests:
            category = MISSING_MANIFEST
            detail: dict[str, Any] = {}
        elif not certificates:
            category = MISSING_CERTIFICATE
            detail = {}
        else:
            manifest = next((row for row, _ in manifests if accepted_manifest(row)), manifests[0][0])
            certificate = next((row for row, _ in certificates if accepted_certificate(row)), certificates[0][0])
            file_path = str(certificate.get("file_path", manifest.get("file_path", "")))
            category, detail = classify_pair(
                manifest,
                certificate,
                source_roots=source_roots,
                known_spans=spans_by_file.get(file_path, []),
                already_mined=evidence_id in mined_by_id,
            )

        category_counts[category] += 1
        row = {**base, "category": category, **detail}
        if category == MINED_CANDIDATE:
            mined = mined_by_id.get(evidence_id, {})
            row["candidate_id"] = mined.get("candidate_id", evidence_id)
            candidates.append(row)
        else:
            obstructions.append({
                **row,
                "terminal_form": NAMED_OBSTRUCTION,
            })

    stable_counts = {category: category_counts.get(category, 0) for category in CATEGORIES}
    candidate_ids = sorted(str(row["candidate_id"]) for row in candidates)
    profile = {
        "version": VERSION,
        "candidates": candidates,
        "obstructions": obstructions,
        "duplicate_groups": duplicate_groups,
        "scanned_paths": sorted(dict.fromkeys(scanned_paths)),
        "missing_input_dirs": sorted(missing_input_dirs),
    }
    summary = {
        "version": VERSION,
        "status": STATUS,
        "scanned_manifest_count": sum(len(rows) for rows in manifest_groups.values()),
        "scanned_certificate_count": sum(len(rows) for rows in certificate_groups.values()),
        "mined_candidate_count": len(candidates),
        "obstruction_count": len(obstructions),
        "category_counts": stable_counts,
        "candidate_ids": candidate_ids,
        "bounded_claim": "identifies which evidence rows are mineable and which are blocked by named obstruction categories",
        "does_not_claim": [
            "new proof discovery",
            "Lean replay success",
            "general SorryDB mining",
            "arbitrary proof repair",
            "upstream submission",
        ],
        "next_frontier": "broader evidence ingestion or a 10–20 row queue generated from profiled candidates",
    }
    return summary, profile


def main() -> int:
    summary, profile = profile_evidence(
        DEFAULT_INPUT_DIRS,
        mined_queue_path=DEFAULT_MINED_QUEUE,
        source_roots=[Path.cwd()],
    )
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (DEFAULT_OUTPUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (DEFAULT_OUTPUT_DIR / "profile.json").write_text(
        json.dumps(profile, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
