#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable


MINER_VERSION = "v4.4.0"
MINED_CANDIDATE_QUEUE = "MINED_CANDIDATE_QUEUE"
PATCH_ACCEPTED = "PATCH_ACCEPTED"
NAMED_OBSTRUCTION = "NAMED_OBSTRUCTION"
SORRY_RE = re.compile(r"\bsorry\b")


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def parse_known_spans(values: Iterable[str]) -> list[dict[str, int]]:
    spans: list[dict[str, int]] = []
    for raw in values:
        value = raw.strip()
        if not value:
            continue
        parts = value.split(":", 1)
        start = int(parts[0])
        end = int(parts[1]) if len(parts) == 2 else start
        if start < 1 or end < start:
            raise ValueError(f"invalid known sorry span: {raw}")
        spans.append({"start_line": start, "end_line": end})
    return spans


def span_contains(spans: list[dict[str, int]], line: int) -> bool:
    return any(span["start_line"] <= line <= span["end_line"] for span in spans)


def unique_snippet_span(
    source_text: str,
    snippet: str,
) -> tuple[dict[str, int] | None, str]:
    count = source_text.count(snippet)
    if count == 0:
        return None, "EXACT_SOURCE_SNIPPET_MISSING"
    if count > 1:
        return None, "EXACT_SOURCE_SNIPPET_AMBIGUOUS"

    sorry_matches = list(SORRY_RE.finditer(snippet))
    if len(sorry_matches) != 1:
        return None, "SOURCE_SNIPPET_REQUIRES_ONE_SORRY"

    offset = source_text.index(snippet)
    start_line = source_text.count("\n", 0, offset) + 1
    end_line = start_line + snippet.count("\n")
    sorry_line = start_line + snippet.count("\n", 0, sorry_matches[0].start())
    return {
        "start_line": start_line,
        "end_line": end_line,
        "sorry_start_line": sorry_line,
        "sorry_end_line": sorry_line,
    }, ""


def obstruction(
    reason: str,
    manifest_path: Path,
    certificate_path: Path | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "terminal_form": NAMED_OBSTRUCTION,
        "reason": reason,
        "manifest_path": str(manifest_path),
    }
    if certificate_path is not None:
        row["certificate_path"] = str(certificate_path)
    return row


def validate_evidence_pair(
    manifest: dict[str, Any],
    certificate: dict[str, Any],
) -> str:
    if manifest.get("verdict") != PATCH_ACCEPTED:
        return "MANIFEST_NOT_PATCH_ACCEPTED"
    if manifest.get("patch_verdict") != PATCH_ACCEPTED:
        return "MANIFEST_PATCH_VERDICT_NOT_ACCEPTED"
    if (manifest.get("patch_result") or {}).get("returncode") != 0:
        return "MANIFEST_LEAN_RETURNCODE_NOT_ZERO"
    if certificate.get("final_verdict") != PATCH_ACCEPTED:
        return "CERTIFICATE_NOT_PATCH_ACCEPTED"
    if certificate.get("lean_returncode") != 0:
        return "CERTIFICATE_LEAN_RETURNCODE_NOT_ZERO"
    if manifest.get("patch_certificate_id") != certificate.get("certificate_id"):
        return "CERTIFICATE_ID_MISMATCH"

    matching_fields = ("file_path", "source_snippet", "patch_snippet")
    for field in matching_fields:
        if not manifest.get(field) or manifest.get(field) != certificate.get(field):
            return f"EVIDENCE_FIELD_MISMATCH:{field}"
    if manifest["source_snippet"] == manifest["patch_snippet"]:
        return "PATCH_DOES_NOT_CHANGE_SOURCE"
    if SORRY_RE.search(str(manifest["patch_snippet"])):
        return "PATCH_SNIPPET_STILL_CONTAINS_SORRY"
    return ""


def candidate_from_pair(
    manifest: dict[str, Any],
    certificate: dict[str, Any],
    source_file: Path,
    source_text: str,
    known_spans: list[dict[str, int]],
    manifest_path: Path,
    certificate_path: Path,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    evidence_error = validate_evidence_pair(manifest, certificate)
    if evidence_error:
        return None, obstruction(evidence_error, manifest_path, certificate_path)

    file_path = str(certificate["file_path"])
    if not str(source_file).replace("\\", "/").endswith(file_path.replace("\\", "/")):
        return None, obstruction("TARGET_SOURCE_PATH_MISMATCH", manifest_path, certificate_path)

    exact_span, span_error = unique_snippet_span(source_text, str(certificate["source_snippet"]))
    if span_error:
        return None, obstruction(span_error, manifest_path, certificate_path)
    assert exact_span is not None
    if not span_contains(known_spans, exact_span["sorry_start_line"]):
        return None, obstruction("SORRY_OUTSIDE_KNOWN_SPANS", manifest_path, certificate_path)

    certificate_id = str(certificate["certificate_id"])
    candidate = {
        "candidate_id": f"v440-{certificate_id}",
        "repo_root": str(manifest.get("repo_root", source_file.parent)),
        "file_path": file_path,
        "source_snippet": certificate["source_snippet"],
        "patch_snippet": certificate["patch_snippet"],
        "project": certificate.get("project", ""),
        "project_commit": certificate.get("project_commit", ""),
        "certificate_id": certificate_id,
        "certificate_version": certificate.get("certificate_version", ""),
        "restore_check": certificate.get("restore_check", ""),
        "timeout_seconds": manifest.get("timeout_seconds", 120),
        "run_baseline_first": 1,
        "min_free_gb": manifest.get("required_gb", 5),
        "source_span": {
            "start_line": exact_span["start_line"],
            "end_line": exact_span["end_line"],
        },
        "sorry_span": {
            "start_line": exact_span["sorry_start_line"],
            "end_line": exact_span["sorry_end_line"],
        },
        "mined_from": {
            "manifest_path": str(manifest_path),
            "certificate_path": str(certificate_path),
            "source_file": str(source_file),
        },
    }
    return candidate, None


def mine_queue(
    manifest_dir: Path,
    certificate_dir: Path,
    source_file: Path,
    known_spans: list[dict[str, int]],
) -> dict[str, Any]:
    if not source_file.exists():
        raise FileNotFoundError(source_file)
    if not known_spans:
        raise ValueError("at least one known sorry span is required")

    source_text = source_file.read_text(encoding="utf-8")
    certificate_paths = sorted(certificate_dir.glob("*.json"))
    certificates: dict[str, tuple[dict[str, Any], Path]] = {}
    for path in certificate_paths:
        certificate = load_object(path)
        certificate_id = str(certificate.get("certificate_id", ""))
        if certificate_id:
            certificates[certificate_id] = (certificate, path)

    candidates: list[dict[str, Any]] = []
    obstructions: list[dict[str, Any]] = []
    for manifest_path in sorted(manifest_dir.glob("*.json")):
        manifest = load_object(manifest_path)
        certificate_id = str(manifest.get("patch_certificate_id", ""))
        evidence = certificates.get(certificate_id)
        if evidence is None:
            obstructions.append(obstruction("MATCHING_CERTIFICATE_MISSING", manifest_path))
            continue
        certificate, certificate_path = evidence
        candidate, blocked = candidate_from_pair(
            manifest,
            certificate,
            source_file,
            source_text,
            known_spans,
            manifest_path,
            certificate_path,
        )
        if candidate is not None:
            candidates.append(candidate)
        if blocked is not None:
            obstructions.append(blocked)

    candidates.sort(key=lambda row: (row["file_path"], row["sorry_span"]["start_line"], row["candidate_id"]))
    return {
        "version": MINER_VERSION,
        "status": MINED_CANDIDATE_QUEUE,
        "bounded_claim": "generates valid queue entries from exact source, patch, and certificate rows",
        "does_not_claim": [
            "new proof discovery",
            "general SorryDB mining",
            "upstream automation",
        ],
        "source_file": str(source_file),
        "known_sorry_spans": known_spans,
        "manifest_count": len(list(manifest_dir.glob("*.json"))),
        "certificate_count": len(certificate_paths),
        "candidate_count": len(candidates),
        "obstruction_count": len(obstructions),
        "candidates": candidates,
        "obstructions": obstructions,
    }


def default_source_file(manifest_dir: Path) -> Path:
    configured = os.getenv("SORRYDB_V440_SOURCE_FILE", "").strip()
    if configured:
        return Path(configured)
    manifests = sorted(manifest_dir.glob("*.json"))
    if not manifests:
        return Path("")
    return Path(str(load_object(manifests[0]).get("source", "")))


def main() -> int:
    parser = argparse.ArgumentParser(description="Mine exact-source queue candidates from accepted replay evidence.")
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=Path("artifacts/sorrydb/streaming_reality_v4_3_8/manifests"),
    )
    parser.add_argument(
        "--certificate-dir",
        type=Path,
        default=Path("artifacts/sorrydb/streaming_reality_v4_3_8/certificates"),
    )
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--known-span", action="append", default=[])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/sorrydb/mined_queues/sorrydb_v4_4_0_exact_source_candidates.json"),
    )
    args = parser.parse_args()

    source_file = args.source_file or default_source_file(args.manifest_dir)
    span_values = args.known_span or [
        value
        for value in os.getenv("SORRYDB_V440_KNOWN_SORRY_SPANS", "").split(",")
        if value.strip()
    ]
    queue = mine_queue(
        args.manifest_dir,
        args.certificate_dir,
        source_file,
        parse_known_spans(span_values),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(queue, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(queue, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
