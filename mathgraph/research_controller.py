"""Programme-level Crystal research controller.

This module is intentionally small and advisory. It does not create scientific
authority, prove claims, or execute domain actions. It selects the next
*eligible* experiment only after a campaign exposes a named residual from a
compressed warranted state.

Hard invariant:

    no residual localization -> no action

Eligibility is fail-closed:
* the candidate must target the current residual exactly;
* all protected invariants must be preserved;
* retained negative results may veto mechanisms;
* refinement requires a separator;
* reuse requires a qualified capability reference;
* an independent-or-stronger verification boundary must be planned; and
* the contraction estimate must itself carry evidence references.

Within one campaign, eligible actions are ordered by declared expected verified
residual contraction per unit cost. Across campaigns, scalar comparison is
allowed only when the selected actions explicitly share the same non-local
contraction and cost bases. Otherwise the portfolio decision is HOLD rather
than fabricating cross-domain utility.

All estimates are advisory inputs. Only the downstream verifier can promote a
scientific result.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Iterable, Sequence

from mathgraph.crystal import content_id


class ResidualStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ActionMode(str, Enum):
    REUSE = "REUSE"
    REFINE = "REFINE"
    VERIFY = "VERIFY"
    SEARCH = "SEARCH"


class VerificationGrade(IntEnum):
    NONE = 0
    SELF_CHECK = 1
    INDEPENDENT = 2
    KERNEL = 3
    OFFICIAL = 4
    SEALED = 5


_VERIFICATION_WEIGHT = {
    VerificationGrade.NONE: 0.0,
    VerificationGrade.SELF_CHECK: 0.0,
    VerificationGrade.INDEPENDENT: 1.0,
    VerificationGrade.KERNEL: 1.05,
    VerificationGrade.OFFICIAL: 1.10,
    VerificationGrade.SEALED: 1.15,
}

_MODE_TIEBREAK = {
    ActionMode.REUSE: 4,
    ActionMode.REFINE: 3,
    ActionMode.VERIFY: 2,
    ActionMode.SEARCH: 1,
}


@dataclass(frozen=True)
class CampaignState:
    campaign_id: str
    objective: str
    compressed_state_ref: str
    residual_id: str
    residual_status: ResidualStatus
    residual_evidence_refs: tuple[str, ...]
    required_invariants: tuple[str, ...] = ()
    live_capability_refs: tuple[str, ...] = ()
    retained_negative_tags: tuple[str, ...] = ()
    blocker_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.campaign_id:
            raise ValueError("campaign_id must be non-empty")
        if not self.objective:
            raise ValueError("objective must be non-empty")

    @property
    def action_ready(self) -> bool:
        return (
            self.residual_status in {ResidualStatus.UNKNOWN, ResidualStatus.OPEN}
            and bool(self.compressed_state_ref)
            and bool(self.residual_id)
            and bool(self.residual_evidence_refs)
            and not self.blocker_refs
        )


@dataclass(frozen=True)
class CandidateExperiment:
    candidate_id: str
    campaign_id: str
    description: str
    targets_residual: str
    mode: ActionMode
    expected_contraction: float
    cost_units: float
    verification_grade: VerificationGrade
    verification_plan_ref: str
    estimate_evidence_refs: tuple[str, ...]
    preserves_invariants: tuple[str, ...] = ()
    capability_refs: tuple[str, ...] = ()
    separator_refs: tuple[str, ...] = ()
    mechanism_tags: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    contraction_basis: str = "campaign_local"
    cost_basis: str = "campaign_local"

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.campaign_id:
            raise ValueError("candidate_id and campaign_id must be non-empty")
        if not self.description:
            raise ValueError("candidate description must be non-empty")
        if not 0.0 <= self.expected_contraction <= 1.0:
            raise ValueError("expected_contraction must be in [0,1]")
        if self.cost_units <= 0:
            raise ValueError("cost_units must be positive")
        if not self.contraction_basis or not self.cost_basis:
            raise ValueError("comparison bases must be non-empty")

    @property
    def score(self) -> float:
        return (
            self.expected_contraction
            * _VERIFICATION_WEIGHT[self.verification_grade]
            / self.cost_units
        )

    @property
    def comparison_key(self) -> tuple[str, str]:
        return self.contraction_basis, self.cost_basis

    @property
    def portfolio_comparable(self) -> bool:
        return self.comparison_key != ("campaign_local", "campaign_local")


@dataclass(frozen=True)
class CandidateAssessment:
    candidate_id: str
    eligible: bool
    reasons: tuple[str, ...]
    score: float
    mode: ActionMode

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "eligible": self.eligible,
            "reasons": list(self.reasons),
            "score": self.score,
            "mode": self.mode.value,
        }


@dataclass(frozen=True)
class CampaignDecision:
    campaign_id: str
    status: str
    residual_id: str
    selected_candidate_id: str | None
    selected_score: float
    assessments: tuple[CandidateAssessment, ...]
    rationale: str

    @property
    def id(self) -> str:
        return content_id(self.to_dict(), prefix="research-decision")

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "status": self.status,
            "residual_id": self.residual_id,
            "selected_candidate_id": self.selected_candidate_id,
            "selected_score": self.selected_score,
            "assessments": [x.to_dict() for x in self.assessments],
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class PortfolioDecision:
    status: str
    selected_campaign_id: str | None
    selected_candidate_id: str | None
    selected_score: float
    campaign_decisions: tuple[CampaignDecision, ...]
    rationale: str

    @property
    def id(self) -> str:
        return content_id(self.to_dict(), prefix="portfolio-decision")

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "selected_campaign_id": self.selected_campaign_id,
            "selected_candidate_id": self.selected_candidate_id,
            "selected_score": self.selected_score,
            "campaign_decisions": [x.to_dict() for x in self.campaign_decisions],
            "rationale": self.rationale,
        }


def assess_candidate(state: CampaignState, candidate: CandidateExperiment) -> CandidateAssessment:
    reasons: list[str] = []

    if not state.action_ready:
        reasons.append("campaign_not_residual_localized")
    if state.blocker_refs:
        reasons.append("campaign_blocked:" + ",".join(state.blocker_refs))
    if candidate.campaign_id != state.campaign_id:
        reasons.append("wrong_campaign")
    if candidate.targets_residual != state.residual_id:
        reasons.append("does_not_target_current_residual")

    missing_invariants = sorted(
        set(state.required_invariants) - set(candidate.preserves_invariants)
    )
    if missing_invariants:
        reasons.append("drops_protected_invariants:" + ",".join(missing_invariants))

    negative_hits = sorted(
        set(state.retained_negative_tags) & set(candidate.mechanism_tags)
    )
    if negative_hits:
        reasons.append("reopens_retained_negative:" + ",".join(negative_hits))

    if candidate.mode == ActionMode.REFINE and not candidate.separator_refs:
        reasons.append("refinement_without_separator")

    if candidate.mode == ActionMode.REUSE:
        if not candidate.capability_refs:
            reasons.append("reuse_without_capability")
        unknown_caps = sorted(
            set(candidate.capability_refs) - set(state.live_capability_refs)
        )
        if unknown_caps:
            reasons.append("reuse_capability_not_live:" + ",".join(unknown_caps))

    if candidate.verification_grade < VerificationGrade.INDEPENDENT:
        reasons.append("verification_boundary_too_weak")
    if not candidate.verification_plan_ref:
        reasons.append("missing_verification_plan")
    if not candidate.estimate_evidence_refs:
        reasons.append("unsupported_contraction_estimate")
    if candidate.expected_contraction <= 0:
        reasons.append("no_declared_residual_contraction")

    eligible = not reasons
    return CandidateAssessment(
        candidate_id=candidate.candidate_id,
        eligible=eligible,
        reasons=tuple(reasons),
        score=candidate.score if eligible else 0.0,
        mode=candidate.mode,
    )


def decide_campaign(
    state: CampaignState,
    candidates: Sequence[CandidateExperiment],
) -> CampaignDecision:
    scoped = [c for c in candidates if c.campaign_id == state.campaign_id]
    assessments = tuple(assess_candidate(state, c) for c in scoped)

    if not state.action_ready:
        blocker = (
            " Campaign blockers: " + ", ".join(state.blocker_refs) + "."
            if state.blocker_refs
            else ""
        )
        return CampaignDecision(
            campaign_id=state.campaign_id,
            status="HOLD",
            residual_id=state.residual_id,
            selected_candidate_id=None,
            selected_score=0.0,
            assessments=assessments,
            rationale=(
                "No action: campaign lacks a named residual from a compressed "
                "warranted state with residual evidence, or has an unresolved "
                "external blocker." + blocker
            ),
        )

    by_id = {c.candidate_id: c for c in scoped}
    eligible = [a for a in assessments if a.eligible]
    if not eligible:
        return CampaignDecision(
            campaign_id=state.campaign_id,
            status="HOLD",
            residual_id=state.residual_id,
            selected_candidate_id=None,
            selected_score=0.0,
            assessments=assessments,
            rationale=(
                "No action: every proposal violates the residual-first or "
                "verification gate."
            ),
        )

    selected = max(
        eligible,
        key=lambda a: (
            a.score,
            _MODE_TIEBREAK[a.mode],
            -len(by_id[a.candidate_id].assumptions),
            -by_id[a.candidate_id].cost_units,
            a.candidate_id,
        ),
    )
    return CampaignDecision(
        campaign_id=state.campaign_id,
        status="ACT",
        residual_id=state.residual_id,
        selected_candidate_id=selected.candidate_id,
        selected_score=selected.score,
        assessments=assessments,
        rationale=(
            "Selected the eligible proposal with maximum declared expected "
            "verified residual contraction per unit cost inside this campaign. "
            "Promotion still depends on its downstream verifier."
        ),
    )


def decide_portfolio(
    states: Sequence[CampaignState],
    candidates: Sequence[CandidateExperiment],
) -> PortfolioDecision:
    decisions = tuple(decide_campaign(state, candidates) for state in states)
    acting = [d for d in decisions if d.status == "ACT"]

    if not acting:
        return PortfolioDecision(
            status="HOLD",
            selected_campaign_id=None,
            selected_candidate_id=None,
            selected_score=0.0,
            campaign_decisions=decisions,
            rationale="No campaign currently has an eligible residual-first action.",
        )

    by_id = {c.candidate_id: c for c in candidates}
    selected_candidates = [
        by_id[d.selected_candidate_id]
        for d in acting
        if d.selected_candidate_id is not None
    ]

    if len(selected_candidates) > 1:
        bases = {c.comparison_key for c in selected_candidates}
        if (
            len(bases) != 1
            or any(not c.portfolio_comparable for c in selected_candidates)
        ):
            return PortfolioDecision(
                status="HOLD_INCOMPARABLE",
                selected_campaign_id=None,
                selected_candidate_id=None,
                selected_score=0.0,
                campaign_decisions=decisions,
                rationale=(
                    "Campaign-local actions exist, but their contraction/cost "
                    "bases are not one explicitly shared non-local scale. "
                    "Refusing to fabricate a cross-domain ranking."
                ),
            )

    selected = max(
        acting,
        key=lambda d: (
            d.selected_score,
            d.campaign_id,
            d.selected_candidate_id or "",
        ),
    )
    return PortfolioDecision(
        status="ACT",
        selected_campaign_id=selected.campaign_id,
        selected_candidate_id=selected.selected_candidate_id,
        selected_score=selected.selected_score,
        campaign_decisions=decisions,
        rationale=(
            "Programme choice is the best campaign-local eligible action under "
            "one explicitly shared contraction/cost basis."
        ),
    )


def campaign_state_from_dict(data: dict) -> CampaignState:
    return CampaignState(
        campaign_id=str(data["campaign_id"]),
        objective=str(data["objective"]),
        compressed_state_ref=str(data.get("compressed_state_ref", "")),
        residual_id=str(data.get("residual_id", "")),
        residual_status=ResidualStatus(str(data.get("residual_status", "UNKNOWN"))),
        residual_evidence_refs=tuple(data.get("residual_evidence_refs", ())),
        required_invariants=tuple(data.get("required_invariants", ())),
        live_capability_refs=tuple(data.get("live_capability_refs", ())),
        retained_negative_tags=tuple(data.get("retained_negative_tags", ())),
        blocker_refs=tuple(data.get("blocker_refs", ())),
    )


def candidate_from_dict(data: dict) -> CandidateExperiment:
    return CandidateExperiment(
        candidate_id=str(data["candidate_id"]),
        campaign_id=str(data["campaign_id"]),
        description=str(data["description"]),
        targets_residual=str(data["targets_residual"]),
        mode=ActionMode(str(data["mode"])),
        expected_contraction=float(data["expected_contraction"]),
        cost_units=float(data["cost_units"]),
        verification_grade=VerificationGrade[str(data["verification_grade"])],
        verification_plan_ref=str(data.get("verification_plan_ref", "")),
        estimate_evidence_refs=tuple(data.get("estimate_evidence_refs", ())),
        preserves_invariants=tuple(data.get("preserves_invariants", ())),
        capability_refs=tuple(data.get("capability_refs", ())),
        separator_refs=tuple(data.get("separator_refs", ())),
        mechanism_tags=tuple(data.get("mechanism_tags", ())),
        assumptions=tuple(data.get("assumptions", ())),
        contraction_basis=str(data.get("contraction_basis", "campaign_local")),
        cost_basis=str(data.get("cost_basis", "campaign_local")),
    )


def partition_candidates(
    candidates: Iterable[CandidateExperiment],
    campaign_id: str,
) -> tuple[CandidateExperiment, ...]:
    return tuple(c for c in candidates if c.campaign_id == campaign_id)


@dataclass(frozen=True)
class CalibrationRecord:
    """Observed verifier-backed reward for one immediately preceding pilot.

    A record may guide at most the next continuation decision for the same
    campaign, and only when resulting_state_ref exactly matches the current
    compressed campaign state. This prevents stale historical performance
    from silently becoming a forecast for a different residual.
    """

    calibration_id: str
    calibration_epoch: str
    campaign_id: str
    pilot_residual_id: str
    pilot_candidate_id: str
    resulting_state_ref: str
    contraction_basis: str
    cost_basis: str
    frozen_atoms: int
    credited_atoms: int
    wall_seconds: float
    evidence_refs: tuple[str, ...]
    invariants_preserved: bool = True

    def __post_init__(self) -> None:
        if not self.calibration_id or not self.calibration_epoch:
            raise ValueError("calibration id/epoch must be non-empty")
        if not self.campaign_id or not self.resulting_state_ref:
            raise ValueError("campaign/resulting state must be non-empty")
        if self.frozen_atoms <= 0:
            raise ValueError("frozen_atoms must be positive")
        if not 0 <= self.credited_atoms <= self.frozen_atoms:
            raise ValueError("credited_atoms must be in [0,frozen_atoms]")
        if self.wall_seconds <= 0:
            raise ValueError("wall_seconds must be positive")
        if not self.evidence_refs:
            raise ValueError("calibration evidence must be non-empty")
        if not self.contraction_basis or not self.cost_basis:
            raise ValueError("calibration bases must be non-empty")

    @property
    def contraction_fraction(self) -> float:
        return self.credited_atoms / self.frozen_atoms

    @property
    def observed_score(self) -> float:
        return self.contraction_fraction / self.wall_seconds

    @property
    def comparison_key(self) -> tuple[str, str]:
        return self.contraction_basis, self.cost_basis

    def to_dict(self) -> dict:
        return {
            "calibration_id": self.calibration_id,
            "calibration_epoch": self.calibration_epoch,
            "campaign_id": self.campaign_id,
            "pilot_residual_id": self.pilot_residual_id,
            "pilot_candidate_id": self.pilot_candidate_id,
            "resulting_state_ref": self.resulting_state_ref,
            "contraction_basis": self.contraction_basis,
            "cost_basis": self.cost_basis,
            "frozen_atoms": self.frozen_atoms,
            "credited_atoms": self.credited_atoms,
            "contraction_fraction": self.contraction_fraction,
            "wall_seconds": self.wall_seconds,
            "observed_score": self.observed_score,
            "evidence_refs": list(self.evidence_refs),
            "invariants_preserved": self.invariants_preserved,
        }


@dataclass(frozen=True)
class CalibratedContinuationDecision:
    status: str
    selected_campaign_id: str | None
    selected_candidate_id: str | None
    selected_observed_score: float
    campaign_decisions: tuple[CampaignDecision, ...]
    calibration_records: tuple[CalibrationRecord, ...]
    missing_campaign_ids: tuple[str, ...]
    rationale: str

    @property
    def id(self) -> str:
        return content_id(self.to_dict(), prefix="calibrated-continuation")

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "selected_campaign_id": self.selected_campaign_id,
            "selected_candidate_id": self.selected_candidate_id,
            "selected_observed_score": self.selected_observed_score,
            "campaign_decisions": [x.to_dict() for x in self.campaign_decisions],
            "calibration_records": [x.to_dict() for x in self.calibration_records],
            "missing_campaign_ids": list(self.missing_campaign_ids),
            "rationale": self.rationale,
        }


def decide_calibrated_continuation(
    states: Sequence[CampaignState],
    candidates: Sequence[CandidateExperiment],
    calibrations: Sequence[CalibrationRecord],
    *,
    calibration_epoch: str,
) -> CalibratedContinuationDecision:
    """Allocate one continuation slot from fresh observed pilot rewards.

    A campaign pilot can guide one continuation slot only when its resulting
    state is exactly the campaign's current compressed state. Missing or stale
    calibration forces HOLD. The observed score is a policy signal, not
    scientific authority and not a proof of global optimality.
    """

    decisions = tuple(decide_campaign(state, candidates) for state in states)
    acting = [d for d in decisions if d.status == "ACT"]
    if not acting:
        return CalibratedContinuationDecision(
            status="HOLD",
            selected_campaign_id=None,
            selected_candidate_id=None,
            selected_observed_score=0.0,
            campaign_decisions=decisions,
            calibration_records=(),
            missing_campaign_ids=(),
            rationale="No campaign currently has an eligible continuation action.",
        )

    state_by_campaign = {s.campaign_id: s for s in states}
    fresh = [
        r for r in calibrations
        if r.calibration_epoch == calibration_epoch and r.invariants_preserved
    ]
    matched: list[CalibrationRecord] = []
    missing: list[str] = []
    for decision in acting:
        state = state_by_campaign[decision.campaign_id]
        rows = [
            r for r in fresh
            if r.campaign_id == decision.campaign_id
            and r.resulting_state_ref == state.compressed_state_ref
        ]
        if len(rows) != 1:
            missing.append(decision.campaign_id)
        else:
            matched.append(rows[0])

    if missing:
        return CalibratedContinuationDecision(
            status="HOLD_PARTIAL_CALIBRATION",
            selected_campaign_id=None,
            selected_candidate_id=None,
            selected_observed_score=0.0,
            campaign_decisions=decisions,
            calibration_records=tuple(matched),
            missing_campaign_ids=tuple(sorted(missing)),
            rationale=(
                "At least one live campaign lacks exactly one fresh calibration "
                "record whose resulting state equals its current compressed state. "
                "Refusing to transfer stale or absent pilot reward into a programme ranking."
            ),
        )

    bases = {r.comparison_key for r in matched}
    if len(bases) != 1:
        return CalibratedContinuationDecision(
            status="HOLD_INCOMPARABLE",
            selected_campaign_id=None,
            selected_candidate_id=None,
            selected_observed_score=0.0,
            campaign_decisions=decisions,
            calibration_records=tuple(matched),
            missing_campaign_ids=(),
            rationale=(
                "Fresh pilot records exist for all live campaigns but do not share "
                "one exact observed contraction/cost basis."
            ),
        )

    by_campaign = {r.campaign_id: r for r in matched}
    selected = max(
        acting,
        key=lambda d: (
            by_campaign[d.campaign_id].observed_score,
            d.campaign_id,
            d.selected_candidate_id or "",
        ),
    )
    record = by_campaign[selected.campaign_id]
    return CalibratedContinuationDecision(
        status="ACT_CONTINUATION",
        selected_campaign_id=selected.campaign_id,
        selected_candidate_id=selected.selected_candidate_id,
        selected_observed_score=record.observed_score,
        campaign_decisions=decisions,
        calibration_records=tuple(matched),
        missing_campaign_ids=(),
        rationale=(
            "Allocated one continuation slot to the campaign with the highest "
            "fresh observed verified-residual contraction per hosted wall-second "
            "under one shared basis. This is an explicit one-step policy signal, "
            "not proof of global scientific optimality."
        ),
    )


def calibration_from_dict(data: dict) -> CalibrationRecord:
    return CalibrationRecord(
        calibration_id=str(data["calibration_id"]),
        calibration_epoch=str(data["calibration_epoch"]),
        campaign_id=str(data["campaign_id"]),
        pilot_residual_id=str(data["pilot_residual_id"]),
        pilot_candidate_id=str(data["pilot_candidate_id"]),
        resulting_state_ref=str(data["resulting_state_ref"]),
        contraction_basis=str(data["contraction_basis"]),
        cost_basis=str(data["cost_basis"]),
        frozen_atoms=int(data["frozen_atoms"]),
        credited_atoms=int(data["credited_atoms"]),
        wall_seconds=float(data["wall_seconds"]),
        evidence_refs=tuple(data.get("evidence_refs", ())),
        invariants_preserved=bool(data.get("invariants_preserved", True)),
    )
