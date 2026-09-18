from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QualificationFixture:
    fixture_id: str
    arm: str
    fixture_class: str
    expected_verdict: str
    expected_reason_codes: tuple[str, ...]
    namespace: str
    raw_input: dict[str, Any]
    witness: dict[str, Any]


_N = 64
_TREATMENT = [1] * _N
_WEAK = [1] * 40 + [0] * 24
_WEAKER = [1] * 36 + [0] * 28
_B_PER_DIRECTION = 16
_B_DIRECTIONS = tuple(f"d{i:02d}" for i in range(12))
_B_LABELS = [direction for direction in _B_DIRECTIONS for _ in range(_B_PER_DIRECTION)]
_B_N = len(_B_LABELS)
_G_N = 32


def _a_positive() -> dict[str, Any]:
    return {
        "treatment": list(_TREATMENT),
        "baselines": {
            "fixed_language_bayes": list(_WEAK),
            "sham_expansion": list(_WEAKER),
            "equal_compute_recheck": list(_WEAK),
        },
        "representation_growth_gate": True,
        "hard_gates": {
            "message_nonidentifying": True,
            "single_message": True,
            "single_repair_round": True,
            "budget_ok": True,
            "old_language_complete": True,
            "future_no_verifier": True,
            "no_future_target_leak": True,
            "sham_budget_matched": True,
        },
        "qualification_evidence": {
            "r0_collision_count": 16,
            "differently_optimal_collision_count": 16,
            "posterior_support_min": 2,
            "extension_nonmeasurable": True,
            "extension_strictly_refines": True,
            "future_message_absent": True,
            "acquisition_future_seed_disjoint": True,
        },
    }


def _b_positive() -> dict[str, Any]:
    return {
        "treatment": [1] * _B_N,
        "wrong_class": [0] * _B_N,
        "shuffled_coupling": [0] * _B_N,
        "acquisition_posterior_target_bisimulation_bayes": [0] * _B_N,
        "direction_labels": list(_B_LABELS),
        "intervention_agreement": [1] * (_B_N * 4),
        "hard_gates": {
            "grammar_independence": True,
            "no_translation": True,
            "no_primitive_dictionary_by_construction": True,
            "no_shared_surface_serialization": True,
            "all_12_ordered_directions": True,
            "all_interventions_present": True,
            "bisimulation_bound": True,
        },
        "qualification_evidence": {
            "grammar_family_count": 4,
            "direction_count": 12,
            "interventions_nested_per_world": 4,
            "target_bisimulation_residual_ambiguity": True,
            "acquisition_posterior_residual_ambiguity": True,
            "all_four_interventions_resolved_by_transfer": True,
        },
    }


def _g_pairs(relevant: int, irrelevant: int) -> list[dict[str, int]]:
    return [
        {
            "world_id": world,
            "weight": weight,
            "relevant": relevant,
            "irrelevant": irrelevant,
        }
        for world in range(_G_N)
        for weight in (2, 5, 10, 20)
    ]


def _g_positive() -> dict[str, Any]:
    return {
        "pairs": _g_pairs(1, 0),
        "max_dose_relevant": [1] * _G_N,
        "max_dose_irrelevant": [0] * _G_N,
        "hard_gates": {
            "preclassified": True,
            "matched_corruption": True,
            "nonzero_dose_nonempty": True,
            "same_evaluator": True,
        },
        "qualification_evidence": {
            "relevance_known_before_corruption": True,
            "dose_weights": [2, 5, 10, 20],
            "randomization_unit": "world",
            "all_doses_jointly_blocked": True,
            "causal_relevant_only_flip": True,
        },
    }


def _p_positive() -> dict[str, Any]:
    deletion = list(_WEAK)
    baselines = {
        "cold": list(_WEAK),
        "equal_compute_recheck": list(_WEAK),
        "verbal_rule_negative": list(_WEAKER),
        "size_matched_sham": list(_WEAKER),
        "wrong_class_object": list(_WEAKER),
        "target_only_bisimulation_bayes": list(_WEAK),
        "posterior_only_retained_bayes": list(_WEAK),
        "targeted_deletion": deletion,
    }
    return {
        "retained": list(_TREATMENT),
        "baselines": baselines,
        "hard_gates": {
            "zero_verifier": True,
            "zero_search": True,
            "label_free": True,
            "source_distinct": True,
            "restart_clean": True,
            "lineage_targeted": True,
            "targeted_deletion": True,
        },
        "post_deletion_accuracy": sum(deletion) / len(deletion),
        "cold_accuracy": sum(_WEAK) / len(_WEAK),
        "reacquisition_search_count": 4,
        "reacquisition_restored": True,
        "inferential_unit": "independent_acquisition_episode",
        "future_tasks_per_episode": 4,
        "qualification_evidence": {
            "independent_acquisition_per_unit": True,
            "nested_future_count_fixed": True,
            "nested_futures_not_counted_as_n": True,
            "restart_byte_exact": True,
            "posterior_only_insufficient": True,
            "target_bisimulation_insufficient": True,
            "lineage_deletion_removes_residual": True,
            "reacquisition_reenters_search": True,
        },
    }


def passing_qualification_matrix() -> dict[str, dict[str, Any]]:
    return {"A": _a_positive(), "B": _b_positive(), "G": _g_positive(), "P": _p_positive()}


def _fixture(
    fixture_id: str,
    arm: str,
    fixture_class: str,
    expected_verdict: str,
    raw: dict[str, Any],
    *,
    reason_codes: tuple[str, ...] = (),
    witness: dict[str, Any] | None = None,
) -> QualificationFixture:
    return QualificationFixture(
        fixture_id=fixture_id,
        arm=arm,
        fixture_class=fixture_class,
        expected_verdict=expected_verdict,
        expected_reason_codes=reason_codes,
        namespace="ABGP-QUAL-v1",
        raw_input=raw,
        witness=witness or {},
    )


def qualification_fixtures() -> tuple[QualificationFixture, ...]:
    fixtures: list[QualificationFixture] = []

    a = _a_positive()
    fixtures.append(_fixture(
        "A_PLANTED_GROWTH", "A", "PLANTED_POSITIVE", "PASS", deepcopy(a),
        witness={
            "satisfiable": True,
            "causal_status_known_by_construction": True,
            "old_information_collision": ["w0", "w1"],
            "old_posterior_action_support": ["a0", "a1"],
            "earned_observable_split": {"w0": 0, "w1": 1},
            "sealed_future_seed_distinct": True,
        },
    ))
    a_bayes = deepcopy(a)
    a_bayes["baselines"]["fixed_language_bayes"] = list(_TREATMENT)
    fixtures.append(_fixture(
        "A_BAYES_SUFFICIENT", "A", "ORDINARY_EXPLANATION", "FAIL", a_bayes,
        witness={"ordinary_explanation": "same-evidence fixed-language Bayes is sufficient"},
    ))
    a_reencode = deepcopy(a)
    a_reencode["representation_growth_gate"] = False
    fixtures.append(_fixture(
        "A_REENCODING_ONLY", "A", "ORDINARY_EXPLANATION", "FAIL", a_reencode,
        witness={"ordinary_explanation": "candidate is measurable from the old information algebra"},
    ))
    a_sham = deepcopy(a)
    a_sham["baselines"]["sham_expansion"] = list(_TREATMENT)
    fixtures.append(_fixture(
        "A_SHAM_EQUIVALENT", "A", "ORDINARY_EXPLANATION", "FAIL", a_sham,
        witness={"ordinary_explanation": "matched sham explains the prospective gain"},
    ))
    a_leak = deepcopy(a)
    a_leak["hard_gates"]["message_nonidentifying"] = False
    fixtures.append(_fixture(
        "A_DIRECT_ANSWER_LEAK", "A", "BROKEN_MECHANICS", "INVALID", a_leak,
        reason_codes=("A_DIRECT_ACTION_IDENTIFYING_MESSAGE",),
        witness={"protocol_defect": "verifier message uniquely identifies protected action"},
    ))

    b = _b_positive()
    fixtures.append(_fixture(
        "B_PLANTED_TRANSFER", "B", "PLANTED_POSITIVE", "PASS", deepcopy(b),
        witness={
            "satisfiable": True,
            "causal_status_known_by_construction": True,
            "target_only_bisimulation_ambiguous": True,
            "acquisition_posterior_ambiguous": True,
            "transferred_structure_resolves_interventions": True,
            "direction_iut": True,
        },
    ))
    b_bisim = deepcopy(b)
    b_bisim["acquisition_posterior_target_bisimulation_bayes"] = [1] * _B_N
    fixtures.append(_fixture(
        "B_TARGET_BISIM_SUFFICIENT", "B", "ORDINARY_EXPLANATION", "FAIL", b_bisim,
        witness={"ordinary_explanation": "target-side bisimulation already determines protected order"},
    ))
    b_post = deepcopy(b)
    b_post["acquisition_posterior_target_bisimulation_bayes"] = [1] * _B_N
    fixtures.append(_fixture(
        "B_POSTERIOR_SUFFICIENT", "B", "ORDINARY_EXPLANATION", "FAIL", b_post,
        witness={"ordinary_explanation": "acquisition posterior carry-forward already determines protected order"},
    ))
    b_shuffle = deepcopy(b)
    b_shuffle["shuffled_coupling"] = [1] * _B_N
    fixtures.append(_fixture(
        "B_SHUFFLED_ONLY", "B", "ORDINARY_EXPLANATION", "FAIL", b_shuffle,
        witness={"ordinary_explanation": "marginal structure without consequence coupling matches treatment"},
    ))
    b_leak = deepcopy(b)
    b_leak["hard_gates"]["no_translation"] = False
    fixtures.append(_fixture(
        "B_TRANSLATION_LEAK", "B", "BROKEN_MECHANICS", "INVALID", b_leak,
        reason_codes=("B_TRANSLATION_LEAK",),
        witness={"protocol_defect": "deterministic cross-grammar translation supplied"},
    ))

    g = _g_positive()
    fixtures.append(_fixture(
        "G_PLANTED_DOSE_RESPONSE", "G", "PLANTED_POSITIVE", "PASS", deepcopy(g),
        witness={
            "satisfiable": True,
            "causal_status_known_by_construction": True,
            "preclassified_relevant_cells": True,
            "relevant_corruption_changes_order": True,
            "irrelevant_corruption_preserves_order": True,
            "world_blocked_exchangeability": True,
        },
    ))
    g_null = deepcopy(g)
    g_null["pairs"] = _g_pairs(0, 0)
    g_null["max_dose_relevant"] = [0] * _G_N
    g_null["max_dose_irrelevant"] = [0] * _G_N
    fixtures.append(_fixture(
        "G_NULL_RELEVANCE", "G", "ORDINARY_EXPLANATION", "FAIL", g_null,
        witness={"ordinary_explanation": "no relevance-by-dose interaction"},
    ))
    g_damage = deepcopy(g)
    g_damage["pairs"] = _g_pairs(1, 1)
    g_damage["max_dose_relevant"] = [1] * _G_N
    g_damage["max_dose_irrelevant"] = [1] * _G_N
    fixtures.append(_fixture(
        "G_GLOBAL_DAMAGE_ONLY", "G", "ORDINARY_EXPLANATION", "FAIL", g_damage,
        witness={"ordinary_explanation": "corruption amount, not relevance, explains damage"},
    ))
    g_reverse = deepcopy(g)
    g_reverse["pairs"] = _g_pairs(0, 1)
    g_reverse["max_dose_relevant"] = [0] * _G_N
    g_reverse["max_dose_irrelevant"] = [1] * _G_N
    fixtures.append(_fixture(
        "G_REVERSED_RELEVANCE", "G", "ORDINARY_EXPLANATION", "FAIL", g_reverse,
        witness={"ordinary_explanation": "effect is in the opposite preregistered direction"},
    ))
    g_posthoc = deepcopy(g)
    g_posthoc["hard_gates"]["preclassified"] = False
    fixtures.append(_fixture(
        "G_POSTHOC_LABELS", "G", "BROKEN_MECHANICS", "INVALID", g_posthoc,
        reason_codes=("G_POSTHOC_RELEVANCE_LABEL",),
        witness={"protocol_defect": "relevance labels assigned after corruption"},
    ))

    p = _p_positive()
    fixtures.append(_fixture(
        "P_PLANTED_PERSISTENCE", "P", "PLANTED_POSITIVE", "PASS", deepcopy(p),
        witness={
            "satisfiable": True,
            "causal_status_known_by_construction": True,
            "hard_restart_retained_bytes_only": True,
            "independent_acquisition_per_unit": True,
            "posterior_only_insufficient": True,
            "target_bisimulation_insufficient": True,
            "deletion_removes_residual": True,
            "reacquisition_restores": True,
        },
    ))
    p_post = deepcopy(p)
    p_post["baselines"]["posterior_only_retained_bayes"] = list(_TREATMENT)
    fixtures.append(_fixture(
        "P_POSTERIOR_MEMORY_SUFFICIENT", "P", "ORDINARY_EXPLANATION", "FAIL", p_post,
        witness={"ordinary_explanation": "posterior-only retained Bayesian memory explains future advantage"},
    ))
    p_bisim = deepcopy(p)
    p_bisim["baselines"]["target_only_bisimulation_bayes"] = list(_TREATMENT)
    fixtures.append(_fixture(
        "P_TARGET_BISIM_SUFFICIENT", "P", "ORDINARY_EXPLANATION", "FAIL", p_bisim,
        witness={"ordinary_explanation": "target-side observational equivalence explains future action"},
    ))
    p_sham = deepcopy(p)
    p_sham["baselines"]["size_matched_sham"] = list(_TREATMENT)
    fixtures.append(_fixture(
        "P_SHAM_SUFFICIENT", "P", "ORDINARY_EXPLANATION", "FAIL", p_sham,
        witness={"ordinary_explanation": "size-matched sham explains retained-object gain"},
    ))
    p_noncausal = deepcopy(p)
    p_noncausal["baselines"]["targeted_deletion"] = list(_TREATMENT)
    p_noncausal["post_deletion_accuracy"] = 1.0
    fixtures.append(_fixture(
        "P_NONCAUSAL_RETENTION", "P", "ORDINARY_EXPLANATION", "FAIL", p_noncausal,
        witness={"ordinary_explanation": "lineage deletion leaves treatment-level performance intact"},
    ))
    p_restart = deepcopy(p)
    p_restart["hard_gates"]["restart_clean"] = False
    fixtures.append(_fixture(
        "P_RESTART_LEAK", "P", "BROKEN_MECHANICS", "INVALID", p_restart,
        reason_codes=("P_RESTART_STATE_LEAK",),
        witness={"protocol_defect": "pre-restart process state survives hard restart"},
    ))

    return tuple(fixtures)
