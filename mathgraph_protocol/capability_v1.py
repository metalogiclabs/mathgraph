"""Portable capability structure and conservative, local-only evaluation.

There are no admitted qualification profiles in this version of the evaluator.
Pinned references are descriptions, not fetched, executed, or authenticated.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from .json_strict import DuplicateKeyError, NonFiniteNumberError, strict_json_loads


CONTRACT_VERSION = "mathgraph.capability-contract.v1"
EVALUATION_VERSION = "mathgraph.capability-evaluation.v1"
REGISTRY_VERSION = "mathgraph.capability-registry.v1"
IDENTITY_FIELDS = ("id", "version", "profile")
CONTRACT_FIELDS = {"schema_version", *IDENTITY_FIELDS, "claim", "inputs", "outputs",
                   "preconditions", "guarantees", "assumptions", "boundary",
                   "implementation", "evidence", "limitations", "extensions"}
ARTIFACT_FIELDS = {"id", "locator", "sha256", "size_bytes", "media_type"}


class CapabilityValidationError(ValueError):
    """Structural rejection; never a refutation of the described claim."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise CapabilityValidationError(code)


def _object(value: Any, fields: set) -> None:
    _require(type(value) is dict, "INVALID_FIELD_TYPE")
    _require(fields <= value.keys(), "MISSING_FIELD")
    _require(value.keys() <= fields, "UNKNOWN_FIELD")


def _text(value: Any) -> None:
    _require(type(value) is str and bool(value.strip()), "INVALID_TEXT")


def _array(value: Any) -> None:
    _require(type(value) is list, "INVALID_FIELD_TYPE")


def _unique(value: Any, seen: set) -> None:
    _require(value not in seen, "DUPLICATE_ID")
    seen.add(value)


def _json_value(value: Any) -> None:
    """Apply JSON's type/finite-value contract to the direct Python API too."""
    if type(value) is dict:
        for key, child in value.items():
            _require(type(key) is str, "INVALID_FIELD_TYPE")
            _json_value(child)
    elif type(value) is list:
        for child in value:
            _json_value(child)
    elif type(value) is float:
        _require(math.isfinite(value), "INVALID_NUMBER")
    else:
        _require(value is None or type(value) in (str, int, bool), "INVALID_FIELD_TYPE")


def validate_artifact(artifact: Any) -> None:
    """Validate a pinned reference only; its locator conveys no access authority."""
    _object(artifact, ARTIFACT_FIELDS)
    for field in ("id", "locator", "media_type"):
        _text(artifact[field])
    _require(type(artifact["sha256"]) is str and
             re.fullmatch(r"[0-9a-f]{64}", artifact["sha256"]) is not None, "INVALID_DIGEST")
    _require(type(artifact["size_bytes"]) is int and artifact["size_bytes"] >= 0, "INVALID_SIZE")


def _identity(value: dict) -> None:
    for field in IDENTITY_FIELDS:
        _text(value[field])


def validate_contract(contract: Any) -> None:
    """Validate structure, exact references, and collection identifiers."""
    _json_value(contract)
    _object(contract, CONTRACT_FIELDS)
    _require(contract["schema_version"] == CONTRACT_VERSION, "UNSUPPORTED_VERSION")
    _identity(contract)
    _object(contract["claim"], {"id", "kind", "scope"})
    for field in ("id", "kind", "scope"):
        _text(contract["claim"][field])
    artifacts = []
    for field in ("inputs", "outputs"):
        _array(contract[field])
        _require(bool(contract[field]), "TYPES_REQUIRED")
        seen: set[str] = set()
        for typed in contract[field]:
            _object(typed, {"type_id", "schema"})
            _text(typed["type_id"])
            _unique(typed["type_id"], seen)
            artifacts.append(typed["schema"])
    for field in ("preconditions", "guarantees", "assumptions", "limitations"):
        _array(contract[field])
        if field in ("guarantees", "limitations"):
            _require(bool(contract[field]), field.upper() + "_REQUIRED")
        for statement in contract[field]:
            _text(statement)
    _array(contract["evidence"])
    seen = set()
    for artifact in contract["evidence"]:
        validate_artifact(artifact)
        _unique(artifact["id"], seen)
    artifacts.extend([contract["boundary"], contract["implementation"], *contract["evidence"]])
    by_id = {}
    for artifact in artifacts:
        validate_artifact(artifact)
        _require(artifact["id"] not in by_id or by_id[artifact["id"]] == artifact,
                 "CONFLICTING_ARTIFACT_ID")
        by_id[artifact["id"]] = artifact
    _array(contract["extensions"])
    seen = set()
    for extension in contract["extensions"]:
        _object(extension, {"id", "version", "critical", "payload"})
        _text(extension["id"])
        _text(extension["version"])
        _unique(extension["id"], seen)
        _require(type(extension["critical"]) is bool, "INVALID_FIELD_TYPE")
        _require(type(extension["payload"]) is dict, "INVALID_FIELD_TYPE")


def validate_registry(registry: Any) -> None:
    """Validate an index; this never admits or trusts the indexed evaluations.

    Each future qualified entry must pin a descriptor, evaluation, independently
    produced qualification receipt, and consumer trust policy. Authenticating
    those pins and replaying the named profile remains a separate operation.
    """
    _json_value(registry)
    _object(registry, {"schema_version", "id", "version", "qualified_entries", "experimental_candidates"})
    _require(registry["schema_version"] == REGISTRY_VERSION, "UNSUPPORTED_VERSION")
    _text(registry["id"])
    _text(registry["version"])
    seen: set[tuple[str, str]] = set()
    for field in ("qualified_entries", "experimental_candidates"):
        _array(registry[field])
        for row in registry[field]:
            references = ("contract", "evaluation", "qualification_receipt", "trust_policy") if field == "qualified_entries" else ("source",)
            fields = {*IDENTITY_FIELDS, *references}
            if field == "experimental_candidates":
                fields.update({"status", "description"})
            _object(row, fields)
            _identity(row)
            _unique((row["id"], row["version"]), seen)
            for reference in references:
                validate_artifact(row[reference])
            if field == "experimental_candidates":
                _require(row["status"] == "EXPERIMENTAL", "INVALID_CANDIDATE_STATUS")
                _text(row["description"])


def encode_result(result: dict) -> bytes:
    """Stable UTF-8 serialization for evaluations and direct Python inputs."""
    return (json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def error_result(code: str) -> dict:
    return {"schema_version": EVALUATION_VERSION, "contract": None,
            "contract_sha256": None, "contract_size_bytes": None,
            "validation": "INVALID", "qualification": "UNKNOWN",
            "qualification_receipt": None, "trust_policy": None,
            "freshness": "NOT_CHECKED", "revocation": "NOT_CHECKED", "supersession": "NOT_CHECKED",
            "current_applicability": "UNKNOWN", "action_authorization": "NONE", "reason_codes": [code]}


def _decode(document: Any) -> tuple[Any, bytes]:
    if isinstance(document, (str, bytes, bytearray)):
        raw = document.encode("utf-8") if isinstance(document, str) else bytes(document)
        return strict_json_loads(raw), raw
    _json_value(document)
    return document, encode_result(document)


def evaluate_contract(document: Any, *, expected_contract: Any = None) -> dict:
    """Inspect a descriptor without I/O, execution, admission, or mutation.

    expected_contract is an optional consumer-owned exact descriptor snapshot,
    not a trust policy. Matching it cannot qualify a capability. No profiles or
    critical extensions are admitted here; every valid descriptor stays UNKNOWN.
    """
    try:
        contract, raw = _decode(document)
        validate_contract(contract)
        reasons = ["UNSUPPORTED_PROFILE", "NO_ADMITTED_RECEIPT"]
        if any(extension["critical"] for extension in contract["extensions"]):
            reasons.append("UNSUPPORTED_CRITICAL_EXTENSION")
        if any(not extension["critical"] for extension in contract["extensions"]):
            reasons.append("NONCRITICAL_EXTENSION_IGNORED")
        if expected_contract is not None:
            expected, _ = _decode(expected_contract)
            validate_contract(expected)
            groups = [(("id", "version"), "IDENTITY_MISMATCH"),
                      (("profile",), "PROFILE_MISMATCH"), (("claim",), "CLAIM_SCOPE_MISMATCH"),
                      (("assumptions",), "ASSUMPTIONS_MISMATCH"),
                      (("implementation", "evidence"), "SOURCE_MISMATCH"),
                      (("boundary",), "BOUNDARY_MISMATCH"),
                      (("inputs", "outputs", "preconditions", "guarantees", "limitations", "extensions"), "CONTRACT_MISMATCH")]
            for fields, code in groups:
                if any(contract[field] != expected[field] for field in fields):
                    reasons.append(code)
        result = error_result("unused")
        result.update({"validation": "VALID", "contract": {field: contract[field] for field in IDENTITY_FIELDS},
                       "contract_sha256": hashlib.sha256(raw).hexdigest(), "contract_size_bytes": len(raw),
                       "reason_codes": reasons})
        return result
    except DuplicateKeyError:
        return error_result("DUPLICATE_KEY")
    except NonFiniteNumberError:
        return error_result("INVALID_NUMBER")
    except CapabilityValidationError as error:
        return error_result(error.code)
    except (ValueError, RecursionError, OverflowError):
        return error_result("INVALID_JSON")
