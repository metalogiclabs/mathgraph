"""MathGraph Check v0: pinned, explicit-contract diagnostic.

This program does NOT formalize natural language, verify a Lean proof, certify
source-to-formal fidelity, or issue badges.  It detects differences between
explicitly supplied mathematical contract dimensions.  The author of those
contracts, their completeness and their interpretation remain unverified.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .contracts import (
    ArgumentStatus, ClaimContract, ContractStatus, compare_protected_contracts,
)

SCHEMA = "mathgraph.check.v0"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_TOP_FIELDS = {
    "schema", "title", "source", "formal", "protected_dimensions",
    "source_contract_origin",
}
_CONTRACT_FIELDS = {"anchor", "dimensions", "argument_route", "file", "sha256"}


class ManifestError(ValueError):
    """Fail-closed invalid manifest, missing local source or hash mismatch."""


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{name} must be an object")
    return value


def _contract(record: Any, name: str) -> ClaimContract:
    data = _mapping(record, name)
    unexpected = set(data) - _CONTRACT_FIELDS
    if unexpected:
        raise ManifestError(f"{name} has unsupported fields: {sorted(unexpected)}")
    anchor = data.get("anchor")
    if not isinstance(anchor, str) or not anchor.strip():
        raise ManifestError(f"{name}.anchor must be a non-empty source reference")
    dimensions = _mapping(data.get("dimensions"), f"{name}.dimensions")
    typed: dict[str, str | int | bool | tuple[str, ...]] = {}
    for key, value in dimensions.items():
        if not isinstance(key, str) or not key:
            raise ManifestError(f"{name}.dimensions has an invalid key")
        if type(value) in (str, int, bool):
            typed[key] = value
        elif isinstance(value, list) and all(type(v) is str for v in value):
            typed[key] = tuple(value)
        else:
            raise ManifestError(f"{name}.dimensions.{key} has unsupported value type")
    route = data.get("argument_route", "")
    if not isinstance(route, str):
        raise ManifestError(f"{name}.argument_route must be a string")
    return ClaimContract(anchor, typed, route)


def _pin(record: Mapping[str, Any], base: Path, name: str) -> dict[str, Any]:
    relative = record.get("file")
    expected = record.get("sha256")
    if expected is not None and (
        not isinstance(expected, str) or not _SHA256.fullmatch(expected)
    ):
        raise ManifestError(f"{name}.sha256 must be 64 lowercase hex digits")
    if relative is None:
        # An anchor and even a declared digest do not constitute replay.
        return {"status": "PIN_NOT_REPLAYED", "expected_sha256": expected}
    if not isinstance(relative, str) or not relative or not expected:
        raise ManifestError(f"{name}.file requires a relative path and sha256")
    requested = Path(relative)
    if requested.is_absolute():
        raise ManifestError(f"{name}.file must be relative to the manifest")
    root = base.resolve()
    target = (root / requested).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ManifestError(f"{name}.file escapes the manifest directory") from exc
    if not target.is_file():
        raise ManifestError(f"{name}.file does not exist")
    if target.stat().st_size > 128 * 1024 * 1024:
        raise ManifestError(f"{name}.file exceeds the 128 MiB v0 limit")
    h = hashlib.sha256()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    if h.hexdigest() != expected:
        raise ManifestError(f"{name}.file SHA256_MISMATCH")
    return {
        "status": "LOCAL_SHA256_CHECKED",
        "file": relative,
        "sha256": expected,
    }


def check_manifest(manifest: Any, *, base_dir: str | Path = ".") -> dict[str, Any]:
    """Produce a deterministic diagnostic, never a truth/statement-fidelity warrant."""
    data = _mapping(manifest, "manifest")
    unexpected = set(data) - _TOP_FIELDS
    if unexpected:
        raise ManifestError(f"unsupported top-level fields: {sorted(unexpected)}")
    if data.get("schema") != SCHEMA:
        raise ManifestError(f"schema must be {SCHEMA!r}")
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ManifestError("title must be non-empty")
    if data.get("source_contract_origin") != "MANUAL_UNREVIEWED":
        raise ManifestError("v0 accepts only MANUAL_UNREVIEWED source contracts")
    dimensions = data.get("protected_dimensions")
    if not isinstance(dimensions, list) or not dimensions or (
        any(not isinstance(k, str) or not k for k in dimensions)
    ) or len(set(dimensions)) != len(dimensions):
        raise ManifestError("protected_dimensions must be unique nonempty strings")
    source_data = _mapping(data.get("source"), "source")
    formal_data = _mapping(data.get("formal"), "formal")
    source = _contract(source_data, "source")
    formal = _contract(formal_data, "formal")
    pins = {
        "source": _pin(source_data, Path(base_dir), "source"),
        "formal": _pin(formal_data, Path(base_dir), "formal"),
    }
    audit = compare_protected_contracts(source, formal, tuple(dimensions))
    findings: list[dict[str, str]] = []
    for key in audit.mismatches:
        findings.append({"code": "DECLARED_DIMENSION_MISMATCH", "dimension": key})
    for key in audit.missing_dimensions:
        findings.append({"code": "MISSING_PROTECTED_DIMENSION", "dimension": key})
    if audit.argument_status is ArgumentStatus.DIFFERENT:
        findings.append({"code": "DECLARED_ARGUMENT_ROUTE_MISMATCH"})
    if audit.status is ContractStatus.DIVERGENT or (
        audit.argument_status is ArgumentStatus.DIFFERENT
    ):
        diagnostic = "CANDIDATE_CONTRACT_DIVERGENCE"
    elif audit.status is ContractStatus.UNKNOWN:
        diagnostic = "UNKNOWN_INCOMPLETE_CONTRACT"
    else:
        diagnostic = "NO_DECLARED_SEPARATOR_FOUND"
    encoded = json.dumps(data, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return {
        "schema": SCHEMA,
        "input_sha256": hashlib.sha256(encoded).hexdigest(),
        "title": title,
        "diagnostic": diagnostic,
        "source_anchor": source.anchor,
        "formal_anchor": formal.anchor,
        "protected_dimensions": dimensions,
        "comparison": {
            "status": audit.status.value,
            "argument_status": audit.argument_status.value,
            "mismatches": list(audit.mismatches),
            "missing_dimensions": list(audit.missing_dimensions),
        },
        "findings": findings,
        "source_pins": pins,
        "epistemic": {
            "source_contract_extraction": "MANUAL_UNREVIEWED",
            "informal_to_formal_fidelity": "UNKNOWN",
            "formal_kernel_verification": "UNKNOWN_NOT_RUN_BY_CHECK_V0",
            "truth_promotion": False,
            "verified_badge": "NOT_ISSUED",
        },
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    """Render the same non-promoting report as readable Markdown."""
    def safe(value: Any) -> str:
        return html.escape(str(value), quote=True).replace("|", "\\|").replace("\n", " ")
    rows = [
        ("Contract comparison", report["comparison"]["status"]),
        ("Argument route", report["comparison"]["argument_status"]),
        ("Informal-to-formal fidelity", report["epistemic"]["informal_to_formal_fidelity"]),
        ("Lean kernel verification", report["epistemic"]["formal_kernel_verification"]),
        ("Verified badge", report["epistemic"]["verified_badge"]),
    ]
    body = [
        "# MathGraph Check v0 — " + safe(report["title"]),
        "",
        "**Diagnostic only: no mathematical truth or statement-fidelity promotion.**",
        "",
        "Source: " + safe(report["source_anchor"]),
        "",
        "Formal: " + safe(report["formal_anchor"]),
        "",
        "Outcome: **" + safe(report["diagnostic"]) + "**",
        "",
        "| Dimension | Status |", "| --- | --- |",
    ] + ["| " + safe(k) + " | " + safe(v) + " |" for k, v in rows]
    body += ["", "## Findings", ""]
    if report["findings"]:
        body.extend(
            "- " + safe(f["code"]) + (
                " — " + safe(f["dimension"]) if "dimension" in f else ""
            ) for f in report["findings"]
        )
    else:
        body.append("No separator in the supplied dimensions; this does not certify equivalence.")
    body += [
        "", "## Reproducibility",
        "", "Manifest SHA256: " + safe(report["input_sha256"]),
        "",
        "Source pin: " + safe(report["source_pins"]["source"]["status"]),
        "",
        "Formal pin: " + safe(report["source_pins"]["formal"]["status"]),
        "",
        "Protected dimensions were manually supplied; source extraction remains unreviewed.",
        "",
    ]
    return "\n".join(body)
