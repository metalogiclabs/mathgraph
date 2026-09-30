from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from mathgraph.research_controller import (
    ActionMode,
    CampaignState,
    CandidateExperiment,
    ResidualStatus,
    VerificationGrade,
    candidate_from_dict,
    campaign_state_from_dict,
    decide_campaign,
    decide_portfolio,
)


FIXTURE = Path("experiments/crystal_program_controller_v1/frozen_ros_replay.json")


def _load_cases():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


def test_no_localized_residual_means_no_action():
    state = CampaignState(
        campaign_id="x",
        objective="protected objective",
        compressed_state_ref="",
        residual_id="",
        residual_status=ResidualStatus.UNKNOWN,
        residual_evidence_refs=(),
    )
    candidate = CandidateExperiment(
        candidate_id="tempting",
        campaign_id="x",
        description="act before the residual is named",
        targets_residual="",
        mode=ActionMode.SEARCH,
        expected_contraction=1.0,
        cost_units=0.1,
        verification_grade=VerificationGrade.OFFICIAL,
        verification_plan_ref="official",
        estimate_evidence_refs=("estimate",),
    )
    decision = decide_campaign(state, [candidate])
    assert decision.status == "HOLD"
    assert decision.selected_candidate_id is None
    assert "campaign_not_residual_localized" in decision.assessments[0].reasons


def test_candidate_must_target_the_current_residual_exactly():
    state = CampaignState(
        campaign_id="x",
        objective="protected objective",
        compressed_state_ref="state:1",
        residual_id="residual:one",
        residual_status=ResidualStatus.UNKNOWN,
        residual_evidence_refs=("evidence:residual",),
    )
    candidate = CandidateExperiment(
        candidate_id="broad",
        campaign_id="x",
        description="broad unrelated search",
        targets_residual="residual:other",
        mode=ActionMode.SEARCH,
        expected_contraction=1.0,
        cost_units=0.1,
        verification_grade=VerificationGrade.OFFICIAL,
        verification_plan_ref="official",
        estimate_evidence_refs=("estimate",),
    )
    assessment = decide_campaign(state, [candidate]).assessments[0]
    assert not assessment.eligible
    assert "does_not_target_current_residual" in assessment.reasons


def test_retained_negative_vetoes_attractive_reopened_mechanism():
    state = CampaignState(
        campaign_id="x",
        objective="protected objective",
        compressed_state_ref="state:1",
        residual_id="r",
        residual_status=ResidualStatus.UNKNOWN,
        residual_evidence_refs=("evidence:r",),
        retained_negative_tags=("old-failure",),
    )
    bad = CandidateExperiment(
        candidate_id="bad",
        campaign_id="x",
        description="cheap but already falsified route",
        targets_residual="r",
        mode=ActionMode.SEARCH,
        expected_contraction=1.0,
        cost_units=0.1,
        verification_grade=VerificationGrade.OFFICIAL,
        verification_plan_ref="official",
        estimate_evidence_refs=("estimate:bad",),
        mechanism_tags=("old-failure",),
    )
    good = CandidateExperiment(
        candidate_id="good",
        campaign_id="x",
        description="earned residual refinement",
        targets_residual="r",
        mode=ActionMode.REFINE,
        expected_contraction=0.2,
        cost_units=2.0,
        verification_grade=VerificationGrade.INDEPENDENT,
        verification_plan_ref="independent",
        estimate_evidence_refs=("estimate:good",),
        separator_refs=("separator:1",),
    )
    decision = decide_campaign(state, [bad, good])
    assert decision.selected_candidate_id == "good"
    bad_assessment = next(a for a in decision.assessments if a.candidate_id == "bad")
    assert "reopens_retained_negative:old-failure" in bad_assessment.reasons


def test_refinement_requires_an_earned_separator():
    state = CampaignState(
        campaign_id="x",
        objective="protected objective",
        compressed_state_ref="state:1",
        residual_id="r",
        residual_status=ResidualStatus.UNKNOWN,
        residual_evidence_refs=("evidence:r",),
    )
    candidate = CandidateExperiment(
        candidate_id="refine",
        campaign_id="x",
        description="unearned distinction",
        targets_residual="r",
        mode=ActionMode.REFINE,
        expected_contraction=0.5,
        cost_units=1.0,
        verification_grade=VerificationGrade.KERNEL,
        verification_plan_ref="kernel",
        estimate_evidence_refs=("estimate",),
    )
    assessment = decide_campaign(state, [candidate]).assessments[0]
    assert not assessment.eligible
    assert "refinement_without_separator" in assessment.reasons


def test_reuse_requires_a_live_capability():
    state = CampaignState(
        campaign_id="x",
        objective="protected objective",
        compressed_state_ref="state:1",
        residual_id="r",
        residual_status=ResidualStatus.UNKNOWN,
        residual_evidence_refs=("evidence:r",),
        live_capability_refs=("cap:live",),
    )
    candidate = CandidateExperiment(
        candidate_id="reuse",
        campaign_id="x",
        description="reuse stale capability",
        targets_residual="r",
        mode=ActionMode.REUSE,
        expected_contraction=0.5,
        cost_units=1.0,
        verification_grade=VerificationGrade.INDEPENDENT,
        verification_plan_ref="independent",
        estimate_evidence_refs=("estimate",),
        capability_refs=("cap:stale",),
    )
    assessment = decide_campaign(state, [candidate]).assessments[0]
    assert not assessment.eligible
    assert "reuse_capability_not_live:cap:stale" in assessment.reasons


def test_frozen_cross_project_replay_selects_recorded_consequential_move():
    cases = _load_cases()
    assert len(cases) >= 7
    for case in cases:
        state = campaign_state_from_dict(case["state"])
        candidates = [candidate_from_dict(x) for x in case["candidates"]]
        decision = decide_campaign(state, candidates)
        assert decision.status == "ACT", (case["case_id"], decision.to_dict())
        assert decision.selected_candidate_id == case["expected_selected"], (
            case["case_id"],
            decision.to_dict(),
        )


def test_residual_localization_ablation_forces_hold_across_replay():
    for case in _load_cases():
        state = campaign_state_from_dict(case["state"])
        candidates = [candidate_from_dict(x) for x in case["candidates"]]
        ablated = replace(state, compressed_state_ref="")
        decision = decide_campaign(ablated, candidates)
        assert decision.status == "HOLD", (case["case_id"], decision.to_dict())


def test_negative_memory_is_causal_across_replay():
    changed = 0
    for case in _load_cases():
        state = campaign_state_from_dict(case["state"])
        candidates = [candidate_from_dict(x) for x in case["candidates"]]
        normal = decide_campaign(state, candidates)
        ablated = decide_campaign(
            replace(state, retained_negative_tags=()),
            candidates,
        )
        if ablated.selected_candidate_id != normal.selected_candidate_id:
            changed += 1
    assert changed == len(_load_cases())


def test_separator_ablation_blocks_refinement_when_no_other_route_is_live():
    checked = 0
    for case in _load_cases():
        state = campaign_state_from_dict(case["state"])
        candidates = [candidate_from_dict(x) for x in case["candidates"]]
        selected = next(
            c for c in candidates if c.candidate_id == case["expected_selected"]
        )
        if selected.mode != ActionMode.REFINE:
            continue
        checked += 1
        mutated = [
            replace(c, separator_refs=()) if c.candidate_id == selected.candidate_id else c
            for c in candidates
        ]
        decision = decide_campaign(state, mutated)
        assert decision.selected_candidate_id != selected.candidate_id
        assessment = next(
            a for a in decision.assessments if a.candidate_id == selected.candidate_id
        )
        assert "refinement_without_separator" in assessment.reasons
    assert checked >= 5


def test_portfolio_controller_compares_only_normalized_eligible_scores():
    a = CampaignState(
        campaign_id="a",
        objective="a",
        compressed_state_ref="state:a",
        residual_id="ra",
        residual_status=ResidualStatus.UNKNOWN,
        residual_evidence_refs=("ea",),
    )
    b = CampaignState(
        campaign_id="b",
        objective="b",
        compressed_state_ref="state:b",
        residual_id="rb",
        residual_status=ResidualStatus.UNKNOWN,
        residual_evidence_refs=("eb",),
    )
    ca = CandidateExperiment(
        candidate_id="ca",
        campaign_id="a",
        description="a candidate",
        targets_residual="ra",
        mode=ActionMode.VERIFY,
        expected_contraction=0.4,
        cost_units=2.0,
        verification_grade=VerificationGrade.INDEPENDENT,
        verification_plan_ref="va",
        estimate_evidence_refs=("xa",),
    )
    cb = CandidateExperiment(
        candidate_id="cb",
        campaign_id="b",
        description="b candidate",
        targets_residual="rb",
        mode=ActionMode.VERIFY,
        expected_contraction=0.5,
        cost_units=1.0,
        verification_grade=VerificationGrade.INDEPENDENT,
        verification_plan_ref="vb",
        estimate_evidence_refs=("xb",),
    )
    decision = decide_portfolio([a, b], [ca, cb])
    assert decision.status == "ACT"
    assert decision.selected_campaign_id == "b"
    assert decision.selected_candidate_id == "cb"
