from __future__ import annotations

import json
from pathlib import Path

import pytest

from mathgraph.program_calibration import (
    CALIBRATION_V1_REF,
    LiveAction,
    MeasurementRecord,
    compare_completed_actions,
    decide_live_from_completed_measurements,
)


LEDGER = Path(
    "experiments/crystal_program_calibration_v2/completed_measurements_v2.json"
)


def _records():
    obj = json.loads(LEDGER.read_text(encoding="utf-8"))
    return [
        MeasurementRecord(
            campaign_id=row["campaign_id"],
            action_id=row["action_id"],
            contract_ref=obj["contract_ref"],
            prospective_freeze_ref=row["prospective_freeze_ref"],
            frozen_atoms=row["frozen_atoms"],
            credited_atoms=row["credited_atoms"],
            job_started_at=row["job_started_at"],
            job_completed_at=row["job_completed_at"],
            invariants_preserved=row["invariants_preserved"],
            evidence_refs=tuple(row["evidence_refs"]),
        )
        for row in obj["records"]
    ]


def test_corrected_job_wall_measurements_match_frozen_contract():
    records = {row.campaign_id: row for row in _records()}
    assert records["nucleus"].wall_seconds == 32
    assert records["nucleus"].contraction_fraction == 1.0
    assert records["nucleus"].utility_per_second == pytest.approx(0.03125)

    assert records["ethereum"].wall_seconds == 189
    assert records["ethereum"].contraction_fraction == 1.0
    assert records["ethereum"].utility_per_second == pytest.approx(1 / 189)

    assert records["cross-prover"].wall_seconds == 376
    assert records["cross-prover"].contraction_fraction == 0.0
    assert records["cross-prover"].utility_per_second == 0.0


def test_completed_actions_are_comparable_but_only_retrospectively():
    result = compare_completed_actions(_records())
    assert result.status == "MEASURED_COMPARABLE"
    assert result.best_observed_action_id == "nucleus-neutral-head-kind-quotient-v1"
    assert "does not authorize" in result.rationale


def test_past_campaign_measurement_cannot_authorize_new_action():
    records = _records()
    old_nucleus = next(x for x in records if x.campaign_id == "nucleus")
    actions = [
        LiveAction(
            campaign_id="nucleus",
            action_id="nucleus-bool-constructor-whnf-v1",
            prospective_measurement_id=old_nucleus.id,
        ),
        LiveAction(
            campaign_id="cross-prover",
            action_id="cross-prover-post-alg-bis-grammar-refinement-v1",
            prospective_measurement_id=None,
        ),
    ]
    result = decide_live_from_completed_measurements(actions, records)
    assert result.status == "HOLD_UNCALIBRATED"
    assert result.selected_action_id is None
    assert set(result.missing_measurement_actions) == {
        "nucleus-bool-constructor-whnf-v1",
        "cross-prover-post-alg-bis-grammar-refinement-v1",
    }


def test_live_action_requires_exact_measurement_identity():
    records = _records()
    nucleus = next(x for x in records if x.campaign_id == "nucleus")
    same = LiveAction(
        campaign_id="nucleus",
        action_id=nucleus.action_id,
        prospective_measurement_id=nucleus.id,
    )
    result = decide_live_from_completed_measurements([same], records)
    assert result.status == "ACT"
    assert result.selected_action_id == nucleus.action_id


def test_regression_invalidates_measurement():
    with pytest.raises(ValueError, match="regression"):
        MeasurementRecord(
            campaign_id="x",
            action_id="a",
            contract_ref=CALIBRATION_V1_REF,
            prospective_freeze_ref="freeze:x",
            frozen_atoms=1,
            credited_atoms=1,
            job_started_at="2026-09-30T00:00:00Z",
            job_completed_at="2026-09-30T00:00:01Z",
            invariants_preserved=False,
            evidence_refs=("e",),
        )


def test_changed_contract_is_rejected():
    with pytest.raises(ValueError, match="outside"):
        MeasurementRecord(
            campaign_id="x",
            action_id="a",
            contract_ref="different-contract",
            prospective_freeze_ref="freeze:x",
            frozen_atoms=1,
            credited_atoms=1,
            job_started_at="2026-09-30T00:00:00Z",
            job_completed_at="2026-09-30T00:00:01Z",
            invariants_preserved=True,
            evidence_refs=("e",),
        )
