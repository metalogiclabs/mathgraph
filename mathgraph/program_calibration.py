"""Shared prospective calibration for Crystal programme control.

This layer is deliberately separate from campaign-local decision logic.

A completed measurement says how much a *specific already-run action* sharpened
its predeclared residual atoms under one frozen accounting contract. It is
evidence about that action; it is not automatically a forecast for the next
action in the same campaign.

The live portfolio must therefore fail closed whenever its current candidate
actions do not themselves have comparable prospective measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from mathgraph.crystal import content_id


SHARED_CONTRACTION_BASIS = "verified_residual_atom_sharpening_fraction.v1"
SHARED_COST_BASIS = "github_hosted_job_wall_seconds.v1"
CALIBRATION_V1_REF = (
    "metalogiclabs/mathgraph:crystal-program-calibration-v1@"
    "2d59a95ab6c28c1a1814863ab9becaaba9c83356"
)


def _parse_github_time(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("GitHub calibration timestamps must be UTC Z timestamps")
    return datetime.fromisoformat(value[:-1] + "+00:00")


@dataclass(frozen=True)
class MeasurementRecord:
    campaign_id: str
    action_id: str
    contract_ref: str
    prospective_freeze_ref: str
    frozen_atoms: int
    credited_atoms: int
    job_started_at: str
    job_completed_at: str
    invariants_preserved: bool
    evidence_refs: tuple[str, ...]
    contraction_basis: str = SHARED_CONTRACTION_BASIS
    cost_basis: str = SHARED_COST_BASIS

    def __post_init__(self) -> None:
        if not self.campaign_id or not self.action_id:
            raise ValueError("campaign_id/action_id must be non-empty")
        if self.contract_ref != CALIBRATION_V1_REF:
            raise ValueError("measurement is outside the frozen calibration contract")
        if not self.prospective_freeze_ref:
            raise ValueError("measurement requires a prospective freeze reference")
        if self.frozen_atoms <= 0:
            raise ValueError("frozen_atoms must be positive")
        if not 0 <= self.credited_atoms <= self.frozen_atoms:
            raise ValueError("credited_atoms outside frozen atom range")
        if not self.invariants_preserved:
            raise ValueError("protected-invariant regression invalidates calibration")
        if not self.evidence_refs:
            raise ValueError("measurement requires evidence refs")
        if self.contraction_basis != SHARED_CONTRACTION_BASIS:
            raise ValueError("contraction basis changed")
        if self.cost_basis != SHARED_COST_BASIS:
            raise ValueError("cost basis changed")
        if self.wall_seconds <= 0:
            raise ValueError("qualification wall time must be positive")

    @property
    def wall_seconds(self) -> float:
        start = _parse_github_time(self.job_started_at)
        end = _parse_github_time(self.job_completed_at)
        return (end - start).total_seconds()

    @property
    def contraction_fraction(self) -> float:
        return self.credited_atoms / self.frozen_atoms

    @property
    def utility_per_second(self) -> float:
        return self.contraction_fraction / self.wall_seconds

    @property
    def id(self) -> str:
        return content_id(self.to_dict(), prefix="calibration-record")

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "action_id": self.action_id,
            "contract_ref": self.contract_ref,
            "prospective_freeze_ref": self.prospective_freeze_ref,
            "frozen_atoms": self.frozen_atoms,
            "credited_atoms": self.credited_atoms,
            "contraction_fraction": self.contraction_fraction,
            "job_started_at": self.job_started_at,
            "job_completed_at": self.job_completed_at,
            "wall_seconds": self.wall_seconds,
            "utility_per_second": self.utility_per_second,
            "invariants_preserved": self.invariants_preserved,
            "evidence_refs": list(self.evidence_refs),
            "contraction_basis": self.contraction_basis,
            "cost_basis": self.cost_basis,
        }


@dataclass(frozen=True)
class CompletedActionComparison:
    status: str
    records: tuple[MeasurementRecord, ...]
    best_observed_action_id: str | None
    rationale: str

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "records": [record.to_dict() for record in self.records],
            "best_observed_action_id": self.best_observed_action_id,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class LiveAction:
    campaign_id: str
    action_id: str
    prospective_measurement_id: str | None = None


@dataclass(frozen=True)
class LivePortfolioCalibrationDecision:
    status: str
    selected_action_id: str | None
    missing_measurement_actions: tuple[str, ...]
    rationale: str

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "selected_action_id": self.selected_action_id,
            "missing_measurement_actions": list(self.missing_measurement_actions),
            "rationale": self.rationale,
        }


def compare_completed_actions(
    records: Sequence[MeasurementRecord],
) -> CompletedActionComparison:
    rows = tuple(records)
    if not rows:
        return CompletedActionComparison(
            status="NO_MEASUREMENTS",
            records=(),
            best_observed_action_id=None,
            rationale="No completed actions satisfy the shared calibration contract.",
        )
    keys = {(r.contract_ref, r.contraction_basis, r.cost_basis) for r in rows}
    if len(keys) != 1:
        raise ValueError("completed actions are not on one frozen comparison basis")
    best = max(rows, key=lambda r: (r.utility_per_second, r.action_id))
    return CompletedActionComparison(
        status="MEASURED_COMPARABLE",
        records=rows,
        best_observed_action_id=best.action_id,
        rationale=(
            "This compares completed action measurements only. It does not "
            "authorize forecasting or selecting a different future action."
        ),
    )


def decide_live_from_completed_measurements(
    actions: Sequence[LiveAction],
    completed_records: Sequence[MeasurementRecord],
) -> LivePortfolioCalibrationDecision:
    """Fail closed unless every live action points to its own completed measurement.

    A past measurement from the same campaign is deliberately insufficient.
    Measurement identity must be attached to the exact live action.
    """

    by_id = {record.id: record for record in completed_records}
    missing: list[str] = []
    measured: list[tuple[LiveAction, MeasurementRecord]] = []

    for action in actions:
        if action.prospective_measurement_id is None:
            missing.append(action.action_id)
            continue
        record = by_id.get(action.prospective_measurement_id)
        if record is None or record.action_id != action.action_id:
            missing.append(action.action_id)
            continue
        measured.append((action, record))

    if missing:
        return LivePortfolioCalibrationDecision(
            status="HOLD_UNCALIBRATED",
            selected_action_id=None,
            missing_measurement_actions=tuple(sorted(missing)),
            rationale=(
                "At least one live candidate lacks a completed prospective "
                "measurement for that exact action. Past campaign measurements "
                "are not treated as forecasts."
            ),
        )

    if not measured:
        return LivePortfolioCalibrationDecision(
            status="HOLD",
            selected_action_id=None,
            missing_measurement_actions=(),
            rationale="No live actions are present.",
        )

    keys = {
        (r.contract_ref, r.contraction_basis, r.cost_basis)
        for _, r in measured
    }
    if len(keys) != 1:
        return LivePortfolioCalibrationDecision(
            status="HOLD_INCOMPARABLE",
            selected_action_id=None,
            missing_measurement_actions=(),
            rationale="Live action measurements are not on one frozen basis.",
        )

    selected_action, _ = max(
        measured,
        key=lambda pair: (
            pair[1].utility_per_second,
            pair[0].action_id,
        ),
    )
    return LivePortfolioCalibrationDecision(
        status="ACT",
        selected_action_id=selected_action.action_id,
        missing_measurement_actions=(),
        rationale=(
            "Every live action has its own completed prospective measurement "
            "under the same frozen contract."
        ),
    )
