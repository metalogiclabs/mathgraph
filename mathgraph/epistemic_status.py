"""Read-only public projection of MathGraph's independent epistemic axes.

This module does not verify claims and cannot promote truth. It only renders
authority already present in verifier-bound artifacts alongside independently
qualified digestion, statement-fidelity, and generalization states.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping


_TERMINAL_STATUSES = {
    "VERIFIED_PROOF",
    "FINITE_COUNTERMODEL",
    "REFUTATION_CERTIFICATE",
}


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return dict(value.to_dict())
    if isinstance(value, Mapping):
        return dict(value)
    return {"value": str(value)}


def _scalar(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _status(value: Any, default: str = "UNKNOWN") -> str:
    value = _scalar(value)
    return default if value in {None, ""} else str(value)


def _metadata(data: Mapping[str, Any]) -> dict[str, Any]:
    raw = data.get("metadata")
    return dict(raw) if isinstance(raw, Mapping) else {}


def _direct_boundary(value: Any, data: Mapping[str, Any]) -> bool:
    for method_name in ("has_valid_truth_boundary", "has_boundary_evidence"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                if bool(method()):
                    return True
            except Exception:
                pass
    terminal = _status(data.get("terminal_form"), "")
    return bool(
        data.get("verifier_boundary_crossed")
        and data.get("certificate_id")
        and terminal in _TERMINAL_STATUSES
    )


def _verification_status(data: Mapping[str, Any]) -> str:
    terminal = _status(data.get("terminal_form"), "")
    if terminal in _TERMINAL_STATUSES:
        return terminal
    status = _status(data.get("status"), "")
    return status if status in _TERMINAL_STATUSES else "UNKNOWN"


def _sidecar_axis(sidecar: Mapping[str, Any], key: str) -> dict[str, Any]:
    raw = sidecar.get(key)
    return dict(raw) if isinstance(raw, Mapping) else {}


def build_epistemic_status_view(value: Any, *, sidecar: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Project an object into four public, non-conflated epistemic axes."""

    data = _as_dict(value)
    meta = _metadata(data)
    side = dict(sidecar or {})
    object_type = value.__class__.__name__ if not isinstance(value, Mapping) else str(data.get("record_type") or "mapping")

    verification_status = _verification_status(data)
    direct_boundary = _direct_boundary(value, data)

    inherited = _sidecar_axis(side, "formal_verification")
    inherited_ok = bool(
        not direct_boundary
        and inherited.get("authority") == "INHERITED_ONLY"
        and _status(inherited.get("status")) == verification_status
        and isinstance(data.get("boundary"), Mapping)
        and bool(data.get("boundary"))
    )
    verification_truth = bool(direct_boundary or inherited_ok)
    verification_authority = (
        "VERIFIER_BOUND"
        if direct_boundary
        else "INHERITED_VERIFIER_BOUND"
        if inherited_ok
        else "NONE"
    )
    if verification_status in _TERMINAL_STATUSES and not verification_truth:
        verification_status = "BOUNDARY_MISSING"

    digestion_status = "UNKNOWN"
    if object_type == "ProofDigestionTrace":
        digestion_status = _status(data.get("status"))
    else:
        digestion_status = _status(
            _sidecar_axis(side, "human_digest").get(
                "status", meta.get("digestion_status", data.get("digestion_status"))
            )
        )

    fidelity_status = "UNKNOWN"
    if object_type == "FaithfulnessAssessment":
        fidelity_status = _status(data.get("status"))
    else:
        fidelity_status = _status(
            _sidecar_axis(side, "statement_fidelity").get(
                "status", meta.get("faithfulness_status", data.get("faithfulness_status"))
            )
        )

    generalization_status = "UNKNOWN"
    if object_type == "ReusableSchemaCandidate":
        generalization_status = "ADVISORY_CANDIDATE"
    else:
        generalization_status = _status(
            _sidecar_axis(side, "reusable_generalization").get(
                "status", meta.get("generalization_status", data.get("generalization_status"))
            )
        )

    source_id = (
        data.get("entry_id")
        or data.get("artifact_id")
        or data.get("trace_id")
        or data.get("assessment_id")
        or data.get("schema_id")
        or data.get("claim_id")
    )

    return {
        "surface_kind": "MATHGRAPH_EPISTEMIC_STATUS_V0",
        "source_object_type": object_type,
        "source_id": source_id,
        "verification": {
            "status": verification_status,
            "authority": verification_authority,
            "truth_promoting": verification_truth,
        },
        "human_digest": {
            "status": digestion_status,
            "authority": "ADVISORY",
            "truth_promoting": False,
        },
        "statement_fidelity": {
            "status": fidelity_status,
            "authority": "INDEPENDENT_NON_PROMOTING",
            "truth_promoting": False,
        },
        "generalization": {
            "status": generalization_status,
            "authority": "ADVISORY",
            "truth_promoting": False,
        },
        "boundary_policy": (
            "Only the verification axis can inherit or carry mathematical truth authority. "
            "Digestion, statement fidelity, and generalization are independently qualified "
            "and do not promote truth."
        ),
        "advisory": True,
    }


def audit_epistemic_status_view(view: Mapping[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    def add(severity: str, code: str, message: str) -> None:
        findings.append({"severity": severity, "code": code, "message": message})

    verification = view.get("verification", {})
    if verification.get("truth_promoting") and verification.get("authority") not in {
        "VERIFIER_BOUND",
        "INHERITED_VERIFIER_BOUND",
    }:
        add("CRITICAL", "TRUTH_WITHOUT_VERIFIER_AUTHORITY", "Truth promotion lacks verifier-bound authority.")

    for axis in ("human_digest", "statement_fidelity", "generalization"):
        state = view.get(axis, {})
        if state.get("truth_promoting"):
            add("CRITICAL", "NON_VERIFICATION_AXIS_PROMOTES_TRUTH", f"{axis} must not promote truth.")
        if state.get("authority") in {"VERIFIER_BOUND", "INHERITED_VERIFIER_BOUND"}:
            add("CRITICAL", "NON_VERIFICATION_AXIS_CLAIMS_VERIFIER_AUTHORITY", f"{axis} claims verifier authority.")

    if not view.get("boundary_policy"):
        add("CRITICAL", "MISSING_BOUNDARY_POLICY", "Public epistemic status view lacks boundary policy.")

    return findings


def epistemic_status_to_markdown(view: Mapping[str, Any]) -> str:
    rows = [
        ("Verification", view.get("verification", {})),
        ("Human digest", view.get("human_digest", {})),
        ("Statement fidelity", view.get("statement_fidelity", {})),
        ("Generalization", view.get("generalization", {})),
    ]
    lines = [
        "# MathGraph Epistemic Status",
        "",
        "| axis | status | authority | truth-promoting |",
        "| --- | --- | --- | --- |",
    ]
    for label, state in rows:
        lines.append(
            f"| {label} | {state.get('status', 'UNKNOWN')} | "
            f"{state.get('authority', 'UNKNOWN')} | "
            f"{'yes' if state.get('truth_promoting') else 'no'} |"
        )
    lines.extend(["", str(view.get("boundary_policy", "")), ""])
    return "\n".join(lines)
