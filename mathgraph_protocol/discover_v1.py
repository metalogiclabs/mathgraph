"""Strict local advisory ranking; never executes routes or checks mathematical truth."""

from __future__ import annotations

from copy import deepcopy
import json
import math
import re
from typing import Any

from .discovery_ranking import default_weights, rank_candidates
from .json_strict import DuplicateKeyError, NonFiniteNumberError, strict_json_loads


REQUEST_VERSION = "mathgraph.discover-request.v1"
RESULT_VERSION = "mathgraph.discover-result.v1"
DESCENSION_TARGETS = frozenset({
    "finite_countermodel_attempt", "lean_verifier_contact_candidate", "lean_digest_repair",
    "obstruction_naming_attempt", "obstruction_naming", "constructor_synthesis_attempt",
    "constructor_synthesis", "projection_test", "representation_repair", "evidence_replay",
    "replay_validation", "lawbook_ingestion", "reason_atlas_route_test", "trust_audit",
})
NUMERIC_FIELDS = frozenset({
    "expected_certificate_value", "expected_obstruction_value", "expected_residual_compression",
    "expected_projection_gain", "expected_reuse", "expected_constructor_reuse",
    "expected_bridge_value", "novelty_score", "verification_cost", "duplicate_risk",
    "overfit_risk", "foreign_moisture_risk",
})
CANDIDATE_FIELDS = frozenset({
    "candidate_id", "candidate_type", "source_ids", "title", "suggested_route",
    "descension_target", "advisory_only", "can_promote_truth",
})
SOURCE_FIELDS = frozenset({
    "source_id", "locator", "repo_path", "bundle", "bundle_relative_path", "sha256",
    "size_bytes", "availability", "integrity_check", "required_for_full_replay",
})


class DiscoverValidationError(ValueError):
    """Structural request rejection with a stable machine-readable code."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str = "INVALID_FIELD") -> None:
    if not condition:
        raise DiscoverValidationError(code)


def _object(value: Any, required: set | frozenset, optional: set | frozenset = frozenset()) -> None:
    _require(type(value) is dict, "INVALID_FIELD_TYPE")
    _require(required <= value.keys(), "MISSING_FIELD")
    _require(value.keys() <= required | optional, "UNKNOWN_FIELD")


def _text(value: Any) -> None:
    _require(type(value) is str and bool(value.strip()), "INVALID_FIELD_TYPE")


def _number(value: Any) -> None:
    _require(type(value) in (int, float), "INVALID_FIELD_TYPE")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    _require(finite and value >= 0, "INVALID_NUMBER")


def _array(value: Any) -> None:
    _require(type(value) is list, "INVALID_FIELD_TYPE")


def _unique(identifier: str, seen: set[str]) -> None:
    _require(identifier not in seen, "DUPLICATE_ID")
    seen.add(identifier)


def validate_request(request: Any) -> None:
    """Check structural fields and references; eligibility is evaluated separately."""
    _object(request, {"schema_version", "request_id", "policy", "top_k", "candidates",
                      "sources", "source_diagnostics", "reported_metrics"})
    _require(request["schema_version"] == REQUEST_VERSION, "UNSUPPORTED_VERSION")
    _text(request["request_id"])
    policy = request["policy"]
    _object(policy, {"mode", "beta"})
    _text(policy["mode"])
    _require(policy["mode"] in {"balanced", "harvest", "frontier", "architectonic"}, "INVALID_POLICY")
    _number(policy["beta"])
    _require(type(request["top_k"]) is int and request["top_k"] >= 0, "INVALID_TOP_K")
    for field in ("candidates", "sources", "source_diagnostics", "reported_metrics"):
        _array(request[field])
    for diagnostic in request["source_diagnostics"]:
        _text(diagnostic)
    source_ids: set[str] = set()
    for source in request["sources"]:
        _object(source, SOURCE_FIELDS)
        for field in ("source_id", "locator", "sha256", "availability", "integrity_check"):
            _text(source[field])
        _unique(source["source_id"], source_ids)
        _require(re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is not None, "INVALID_DIGEST")
        _require(type(source["size_bytes"]) is int and source["size_bytes"] >= 0, "INVALID_SIZE")
        _require(type(source["required_for_full_replay"]) is bool, "INVALID_FIELD_TYPE")
        for field in ("repo_path", "bundle", "bundle_relative_path"):
            if source[field] is not None:
                _text(source[field])
        _require(source["availability"] in {"PRESENT", "MISSING"})
        _require(source["integrity_check"] in {"MATCHED", "NOT_CHECKED"})
        _require(source["availability"] != "MISSING" or source["integrity_check"] == "NOT_CHECKED")
    metric_ids: set[str] = set()
    for metric in request["reported_metrics"]:
        _object(metric, {"name", "value", "source_id"})
        _text(metric["name"])
        _text(metric["source_id"])
        _unique(metric["name"], metric_ids)
        _require(metric["source_id"] in source_ids, "UNKNOWN_SOURCE_ID")
        if type(metric["value"]) is not bool:
            _number(metric["value"])
    candidate_ids: set[str] = set()
    for candidate in request["candidates"]:
        _object(candidate, CANDIDATE_FIELDS, NUMERIC_FIELDS | {"notes", "description"})
        for field in ("candidate_id", "candidate_type", "title", "suggested_route", "descension_target"):
            _text(candidate[field])
        _unique(candidate["candidate_id"], candidate_ids)
        for field in ("advisory_only", "can_promote_truth"):
            _require(type(candidate[field]) is bool, "INVALID_FIELD_TYPE")
        for field in NUMERIC_FIELDS & candidate.keys():
            _number(candidate[field])
        for field in {"notes", "description"} & candidate.keys():
            _require(type(candidate[field]) is str, "INVALID_FIELD_TYPE")
        _array(candidate["source_ids"])
        references: set[str] = set()
        for source_id in candidate["source_ids"]:
            _text(source_id)
            _unique(source_id, references)
            _require(source_id in source_ids, "UNKNOWN_SOURCE_ID")


def error_result(code: str) -> dict[str, Any]:
    """Return a bounded error envelope without reflecting malformed input."""
    return {
        "schema_version": RESULT_VERSION, "request_id": None, "status": "ERROR",
        "advisory_only": True, "can_promote_truth": False, "verification_status": "NOT_CHECKED",
        "attention_interpretation": "ALLOCATION_NOT_TRUTH_CONFIDENCE",
        "reason_codes": [code], "ranked_candidates": [], "rejected_candidates": [],
        "sources": [], "source_diagnostics": [], "reported_metrics": [],
    }


def discover(request: dict | str | bytes | bytearray) -> dict[str, Any]:
    """Rank structurally valid, eligible candidates with the shared pure kernel.

    The operation does no I/O. Source observations and historical metrics are
    caller-reported advisory inputs, not reauthenticated by this function.
    """
    try:
        if isinstance(request, (str, bytes, bytearray)):
            request = strict_json_loads(request)
        validate_request(request)
        eligible, rejected = [], []
        for candidate in request["candidates"]:
            reasons = []
            if candidate["descension_target"] not in DESCENSION_TARGETS:
                reasons.append("INVALID_DESCENSION_TARGET")
            if not candidate["advisory_only"]:
                reasons.append("ADVISORY_ONLY_REQUIRED")
            if candidate["can_promote_truth"]:
                reasons.append("TRUTH_PROMOTION_FORBIDDEN")
            if reasons:
                rejected.append({"candidate_id": candidate["candidate_id"], "reason_codes": reasons})
            else:
                eligible.append(candidate)
        ranked = rank_candidates(eligible, weights=default_weights(request["policy"]["mode"]),
                                 beta=request["policy"]["beta"])
        if any(not math.isfinite(row.score) or not math.isfinite(row.probability) for row in ranked):
            return error_result("NUMERIC_OVERFLOW")
        rows = []
        for rank, row in enumerate(ranked, 1):
            candidate = eligible[row.source_index]
            rows.append({"candidate_id": row.candidate_id, "rank": rank,
                         "taste_score": row.score, "attention_probability": row.probability,
                         "selected": rank <= request["top_k"],
                         "descension_target": candidate["descension_target"],
                         "suggested_route": candidate["suggested_route"],
                         "source_ids": list(candidate["source_ids"])})
        incomplete = any(source["availability"] == "MISSING" or source["integrity_check"] == "NOT_CHECKED"
                         for source in request["sources"])
        reasons = []
        if not eligible:
            reasons.append("NO_ELIGIBLE_CANDIDATES")
        if rejected:
            reasons.append("CANDIDATES_REJECTED")
        if incomplete:
            reasons.append("SOURCE_MATERIAL_INCOMPLETE")
        result = error_result("unused")
        result.update({
            "request_id": request["request_id"],
            "status": "UNKNOWN" if not eligible else "PARTIAL" if rejected or incomplete else "OK",
            "reason_codes": reasons, "ranked_candidates": rows,
            "rejected_candidates": sorted(rejected, key=lambda row: row["candidate_id"]),
            "sources": deepcopy(request["sources"]),
            "source_diagnostics": list(request["source_diagnostics"]),
            "reported_metrics": deepcopy(request["reported_metrics"]),
        })
        return result
    except DuplicateKeyError:
        return error_result("DUPLICATE_KEY")
    except NonFiniteNumberError:
        return error_result("INVALID_NUMBER")
    except DiscoverValidationError as error:
        return error_result(error.code)
    except (ValueError, RecursionError):
        return error_result("INVALID_JSON")
    except OverflowError:
        return error_result("NUMERIC_OVERFLOW")


def encode_result(result: dict[str, Any]) -> bytes:
    """Stable UTF-8 serialization, including one trailing newline."""
    return (json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
