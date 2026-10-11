"""Deterministic unsigned in-toto correspondence for capability-contract v1.

Only exact bytes and explicit fields are checked. There is no I/O, signature
verification, profile replay, trust-policy admission, or action authorization.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .capability_v1 import (
    CONTRACT_VERSION,
    CapabilityValidationError,
    encode_result,
    validate_artifact,
    validate_contract,
)
from .json_strict import DuplicateKeyError, NonFiniteNumberError, strict_json_loads


STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = "https://mathgraph.org/attestation/external-binding/v1"
BINDING_VERSION = "mathgraph.external-binding.v1"
MEDIA_TYPE = "application/json"
ARTIFACT_FIELDS = {"name", "sha256", "size_bytes", "media_type", "object_schema"}


class ExternalBindingError(ValueError):
    """Correspondence or structure rejection; never a mathematical refutation."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ExternalBindingError(code)


def _fields(value: Any, fields: set[str]) -> None:
    _require(type(value) is dict, "INVALID_FIELD_TYPE")
    _require(fields <= value.keys(), "MISSING_FIELD")
    _require(value.keys() <= fields, "UNKNOWN_FIELD")


def _text(value: Any) -> None:
    _require(type(value) is str and bool(value.strip()), "INVALID_TEXT")


def _decode(raw: bytes) -> Any:
    _require(type(raw) is bytes, "EXACT_BYTES_REQUIRED")
    try:
        return strict_json_loads(raw.decode("utf-8"))
    except DuplicateKeyError as error:
        raise ExternalBindingError("DUPLICATE_KEY") from error
    except NonFiniteNumberError as error:
        raise ExternalBindingError("INVALID_NUMBER") from error
    except (ValueError, RecursionError, OverflowError) as error:
        raise ExternalBindingError("INVALID_JSON") from error


def _extensions(value: Any) -> None:
    _require(type(value) is list, "INVALID_FIELD_TYPE")
    seen: set[str] = set()
    for extension in value:
        _fields(extension, {"id", "version", "critical", "payload"})
        _text(extension["id"])
        _text(extension["version"])
        _require(extension["id"] not in seen, "DUPLICATE_EXTENSION_ID")
        seen.add(extension["id"])
        _require(type(extension["critical"]) is bool, "INVALID_FIELD_TYPE")
        _require(not extension["critical"], "UNSUPPORTED_CRITICAL_EXTENSION")
        _require(type(extension["payload"]) is dict, "INVALID_FIELD_TYPE")


def _artifact_pin(value: Any) -> None:
    _fields(value, ARTIFACT_FIELDS)
    _text(value["name"])
    _require(value["object_schema"] == CONTRACT_VERSION, "UNSUPPORTED_OBJECT_SCHEMA")
    _require(value["media_type"] == MEDIA_TYPE, "UNSUPPORTED_MEDIA_TYPE")
    try:
        validate_artifact({"id": value["name"], "locator": value["name"],
                           "sha256": value["sha256"], "size_bytes": value["size_bytes"],
                           "media_type": value["media_type"]})
    except CapabilityValidationError as error:
        raise ExternalBindingError(error.code) from error


def _contract(raw: bytes, name: str) -> tuple[dict, dict]:
    _text(name)
    contract = _decode(raw)
    try:
        validate_contract(contract)
    except CapabilityValidationError as error:
        raise ExternalBindingError(error.code) from error
    _extensions(contract["extensions"])
    return contract, {"name": name, "sha256": hashlib.sha256(raw).hexdigest(),
                      "size_bytes": len(raw), "media_type": MEDIA_TYPE,
                      "object_schema": CONTRACT_VERSION}


def export_statement(artifact_bytes: bytes, *, name: str) -> bytes:
    """Bind exact UTF-8 JSON bytes; the name is an opaque label, never a path/URL.

    Output uses sorted keys, two-space indentation, ASCII JSON escapes and one
    trailing LF. The artifact itself is never normalized. This is a local
    deterministic encoding, not a general JSON cryptographic canonicalization.
    No qualification is read from a registry or conferred by export.
    """
    contract, artifact = _contract(artifact_bytes, name)
    return encode_result({
        "_type": STATEMENT_TYPE,
        "subject": [{"name": name, "digest": {"sha256": artifact["sha256"]}}],
        "predicateType": PREDICATE_TYPE,
        "predicate": {"schema_version": BINDING_VERSION, "signature": "UNSIGNED",
                      "artifact": artifact, "claim": contract["claim"],
                      "assumptions": contract["assumptions"],
                      "evidence": contract["evidence"], "extensions": []},
    })


def import_statement(statement_bytes: bytes, artifact_bytes: bytes, *,
                     expected_artifact: dict) -> dict:
    """Check exact correspondence against a separately selected consumer pin.

    expected_artifact must contain name, sha256, size_bytes, media_type and
    object_schema. Taking this pin from the untrusted statement defeats the
    consumer's selection boundary. The pin alone does not authenticate a source.
    Invalid input raises ExternalBindingError; matching input returns only
    correspondence, with all authority outcomes explicitly unestablished.
    """
    _artifact_pin(expected_artifact)
    statement = _decode(statement_bytes)
    _fields(statement, {"_type", "subject", "predicateType", "predicate"})
    _require(statement["_type"] == STATEMENT_TYPE, "UNSUPPORTED_STATEMENT_TYPE")
    _require(statement["predicateType"] == PREDICATE_TYPE, "UNSUPPORTED_PREDICATE_TYPE")
    subjects = statement["subject"]
    _require(type(subjects) is list and len(subjects) == 1, "EXACTLY_ONE_SUBJECT_REQUIRED")
    _fields(subjects[0], {"name", "digest"})
    _fields(subjects[0]["digest"], {"sha256"})
    predicate = statement["predicate"]
    _fields(predicate, {"schema_version", "signature", "artifact", "claim",
                        "assumptions", "evidence", "extensions"})
    _require(predicate["schema_version"] == BINDING_VERSION, "UNSUPPORTED_BINDING_VERSION")
    _require(predicate["signature"] == "UNSIGNED", "UNSIGNED_REQUIRED")
    _artifact_pin(predicate["artifact"])
    _extensions(predicate["extensions"])
    contract, artifact = _contract(artifact_bytes, expected_artifact["name"])
    _require(artifact == expected_artifact, "ARTIFACT_PIN_MISMATCH")
    _require(predicate["artifact"] == artifact, "ARTIFACT_METADATA_MISMATCH")
    _require(subjects == [{"name": artifact["name"], "digest": {"sha256": artifact["sha256"]}}],
             "SUBJECT_MISMATCH")
    for field in ("claim", "assumptions", "evidence"):
        # Stable JSON distinguishes booleans, integers and floats, unlike ==.
        _require(encode_result(predicate[field]) == encode_result(contract[field]),
                 field.upper() + "_MISMATCH")
    return {"correspondence": "MATCH", "artifact": artifact, "claim": contract["claim"],
            "assumptions": contract["assumptions"], "evidence": contract["evidence"],
            "external_extensions": predicate["extensions"],
            "signature": "UNSIGNED", "authenticity": "NOT_CHECKED",
            "signer_policy": "NOT_CHECKED", "transparency": "NOT_CHECKED",
            "freshness": "NOT_CHECKED", "qualification": "UNKNOWN",
            "current_applicability": "UNKNOWN", "action_authorization": "NONE"}


__all__ = ["ExternalBindingError", "export_statement", "import_statement"]
