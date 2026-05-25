"""Terminal-form contract for autonomous MathGraph discovery loops.

This module is intentionally small and conservative. It gives autonomous
runners a shared vocabulary for terminal eligibility without replacing the
repo's verifier and promotion-gate modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class TerminalForm(str, Enum):
    VERIFIED_PROOF = "VERIFIED_PROOF"
    FINITE_COUNTERMODEL = "FINITE_COUNTERMODEL"
    NAMED_OBSTRUCTION = "NAMED_OBSTRUCTION"
    NONE = "NONE"


class PromotionStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    CANDIDATE = "CANDIDATE"
    ADVISORY = "ADVISORY"
    RESIDUAL = "RESIDUAL"
    REJECTED = "REJECTED"


TrustLevel = PromotionStatus


@dataclass(frozen=True)
class TerminalDecision:
    terminal_form: TerminalForm
    status: PromotionStatus
    accepted: bool
    reason: str
    trust_level: str = "ADVISORY_ROUTE"
    advisory_only: bool = True
    can_promote_truth: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "terminal_form": self.terminal_form.value,
            "status": self.status.value,
            "accepted": self.accepted,
            "reason": self.reason,
            "trust_level": self.trust_level,
            "advisory_only": self.advisory_only,
            "can_promote_truth": self.can_promote_truth,
            "metadata": dict(self.metadata),
        }


def decide_terminal_form(record: Mapping[str, Any] | Any) -> TerminalDecision:
    """Return a conservative terminal decision for a raw row/certificate.

    Rules:
    - Checked finite countermodels may support FALSE terminal candidates.
    - Lean-verified rows may support TRUE terminal candidates.
    - Named obstructions are terminal only as obstruction records, never TRUE.
    - Failed finite search is residual evidence and never TRUE.
    """

    data = record.to_dict() if hasattr(record, "to_dict") else dict(record or {})
    status = str(data.get("certificate_status") or data.get("proof_status") or data.get("status") or "").lower()

    if can_promote_true(data):
        return TerminalDecision(
            terminal_form=TerminalForm.VERIFIED_PROOF,
            status=PromotionStatus.ACCEPTED,
            accepted=True,
            reason="verifier-backed TRUE evidence is present",
            trust_level="VERIFIED_PROOF",
            advisory_only=False,
            can_promote_truth=True,
            metadata=data,
        )

    if can_promote_false(data):
        return TerminalDecision(
            terminal_form=TerminalForm.FINITE_COUNTERMODEL,
            status=PromotionStatus.ACCEPTED,
            accepted=True,
            reason="finite checker produced a source-satisfying, target-violating witness",
            trust_level="FINITE_VERIFIED",
            advisory_only=False,
            can_promote_truth=True,
            metadata=data,
        )

    if status == "named_obstruction_advisory" or data.get("obstruction_name"):
        return TerminalDecision(
            terminal_form=TerminalForm.NAMED_OBSTRUCTION,
            status=PromotionStatus.ADVISORY,
            accepted=False,
            reason="obstruction is named but remains advisory until an obstruction boundary accepts it",
            metadata=data,
        )

    if status in {"failed_search", "finite_failed_small_n", "finite_failed_structured", "not_a_countermodel"} or data.get("finite_search_miss"):
        return TerminalDecision(
            terminal_form=TerminalForm.NONE,
            status=PromotionStatus.RESIDUAL,
            accepted=False,
            reason="finite-search failure is residual evidence, never TRUE",
            trust_level="RESIDUAL_EVIDENCE",
            metadata=data,
        )

    return TerminalDecision(
        terminal_form=TerminalForm.NONE,
        status=PromotionStatus.REJECTED,
        accepted=False,
        reason="record is advisory or unsupported and cannot promote truth",
        metadata=data,
    )


def can_promote_true(record: Mapping[str, Any] | Any) -> bool:
    data = record.to_dict() if hasattr(record, "to_dict") else dict(record or {})
    status = str(data.get("certificate_status") or data.get("proof_status") or data.get("status") or "").lower()
    return bool(
        data.get("lean_verified")
        or data.get("proof_verified")
        or data.get("verified_proof")
        or data.get("congruence_explain_verified")
        or status in {"lean_verified", "proof_verified", "verified_proof", "congruence_explain_verified"}
    )


def can_promote_false(record: Mapping[str, Any] | Any) -> bool:
    data = record.to_dict() if hasattr(record, "to_dict") else dict(record or {})
    status = str(data.get("certificate_status") or data.get("proof_status") or data.get("status") or "").lower()
    countermodel_status = status in {
        "finite_countermodel_found",
        "finite_countermodel_verified",
        "countermodel_verified",
    }
    checker_backed = bool(
        data.get("finite_checker_valid")
        or data.get("finite_verified")
        or (data.get("eq1_holds") is True and data.get("eq2_violated") is True)
    )
    return countermodel_status and checker_backed


def decision_as_dict(record: Mapping[str, Any] | Any) -> dict[str, Any]:
    return decide_terminal_form(record).to_dict()


def audit_terminal_rows(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [decision_as_dict(row) for row in rows]


def boundary_preserved(rows: list[Mapping[str, Any]]) -> bool:
    """True when no advisory/residual row is allowed to promote truth."""

    for row in rows:
        data = row.to_dict() if hasattr(row, "to_dict") else dict(row or {})
        if bool(data.get("advisory_only")) and bool(data.get("can_promote_truth")):
            return False
        if str(data.get("terminal_form", "")).upper() == TerminalForm.VERIFIED_PROOF.value and not can_promote_true(data):
            return False
        if str(data.get("terminal_form", "")).upper() == TerminalForm.FINITE_COUNTERMODEL.value and not can_promote_false(data):
            return False
        decision = decide_terminal_form(data)
        if decision.advisory_only and decision.can_promote_truth:
            return False
    return True
