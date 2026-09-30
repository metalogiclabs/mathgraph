from mathgraph.research_controller import (
    ActionMode,
    CalibrationRecord,
    CampaignState,
    CandidateExperiment,
    ResidualStatus,
    VerificationGrade,
    decide_calibrated_continuation,
)


BASIS = "verified_residual_atom_sharpening_fraction.v1"
COST = "github_hosted_job_wall_seconds.v1"
EPOCH = "programme-calibration-20260930-v1"


def state(cid, state_ref, residual):
    return CampaignState(
        campaign_id=cid,
        objective=f"{cid} objective",
        compressed_state_ref=state_ref,
        residual_id=residual,
        residual_status=ResidualStatus.UNKNOWN,
        residual_evidence_refs=(f"evidence:{cid}:{residual}",),
    )


def candidate(cid, residual):
    return CandidateExperiment(
        candidate_id=f"{cid}-next",
        campaign_id=cid,
        description="next residual-first action",
        targets_residual=residual,
        mode=ActionMode.VERIFY,
        expected_contraction=0.5,
        cost_units=1.0,
        verification_grade=VerificationGrade.INDEPENDENT,
        verification_plan_ref=f"verify:{cid}",
        estimate_evidence_refs=(f"estimate:{cid}",),
    )


def cal(cid, state_ref, credited, total, seconds, *, basis=BASIS, cost=COST):
    return CalibrationRecord(
        calibration_id=f"cal:{cid}",
        calibration_epoch=EPOCH,
        campaign_id=cid,
        pilot_residual_id=f"{cid}:pilot",
        pilot_candidate_id=f"{cid}:pilot-action",
        resulting_state_ref=state_ref,
        contraction_basis=basis,
        cost_basis=cost,
        frozen_atoms=total,
        credited_atoms=credited,
        wall_seconds=seconds,
        evidence_refs=(f"run:{cid}",),
    )


def test_partial_calibration_holds_instead_of_using_only_measured_campaign():
    states=[state("nucleus","run:nucleus","r1"),state("collatz","run:collatz","r2")]
    candidates=[candidate("nucleus","r1"),candidate("collatz","r2")]
    d=decide_calibrated_continuation(
        states,candidates,[cal("nucleus","run:nucleus",17,17,36)],
        calibration_epoch=EPOCH,
    )
    assert d.status=="HOLD_PARTIAL_CALIBRATION"
    assert d.selected_campaign_id is None
    assert d.missing_campaign_ids==("collatz",)


def test_stale_calibration_does_not_transfer_to_new_state():
    states=[state("nucleus","run:new","r1")]
    d=decide_calibrated_continuation(
        states,[candidate("nucleus","r1")],
        [cal("nucleus","run:old",17,17,36)],
        calibration_epoch=EPOCH,
    )
    assert d.status=="HOLD_PARTIAL_CALIBRATION"
    assert d.missing_campaign_ids==("nucleus",)


def test_mismatched_measurement_bases_hold():
    states=[state("a","run:a","ra"),state("b","run:b","rb")]
    candidates=[candidate("a","ra"),candidate("b","rb")]
    rows=[
        cal("a","run:a",1,1,10),
        cal("b","run:b",1,1,10,basis="different"),
    ]
    d=decide_calibrated_continuation(states,candidates,rows,calibration_epoch=EPOCH)
    assert d.status=="HOLD_INCOMPARABLE"
    assert d.selected_campaign_id is None


def test_all_fresh_same_basis_selects_highest_observed_one_step_reward():
    states=[state("nucleus","run:nucleus","r1"),state("cross","run:cross","r2")]
    candidates=[candidate("nucleus","r1"),candidate("cross","r2")]
    rows=[
        cal("nucleus","run:nucleus",17,17,36),
        cal("cross","run:cross",0,6,378),
    ]
    d=decide_calibrated_continuation(states,candidates,rows,calibration_epoch=EPOCH)
    assert d.status=="ACT_CONTINUATION"
    assert d.selected_campaign_id=="nucleus"
    assert d.selected_candidate_id=="nucleus-next"
    assert d.selected_observed_score==1/36
