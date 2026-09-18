from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .analysis import analyze_matrix
from .arm_a import (
    a_growth_analysis_input,
    audit_a_growth_episodes,
    generate_a_growth_episodes,
)
from .arm_b import generate_b_dev_records, grammar_families
from .arm_g import generate_g_dev_records
from .arm_p import (
    audit_p_episode_independence,
    generate_p_independent_episodes,
    p_independent_analysis_input,
)
from .freeze_review import (
    audit_a_stochastic_ancestry,
    audit_g_exchangeability_design,
    audit_p_stochastic_ancestry,
)
from .manifest import (
    ConfirmatoryLockedError,
    load_analysis_plan,
    load_design_manifest,
    reject_confirmatory_namespace,
)


_ROOT = Path(__file__).resolve().parents[2]
_DESIGN_PATH = _ROOT / "preregistration" / "abgp-design-manifest-v1.json"
_ANALYSIS_PATH = _ROOT / "preregistration" / "abgp-analysis-plan-v1.json"
_DEV_NAMESPACE = "ABGP-DEV-v1"


def _b_inputs(records: list[Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    families = grammar_families()
    alphabets = [set(g.surface_alphabet) for g in families]
    disjoint = all(
        alphabets[i].isdisjoint(alphabets[j])
        for i in range(len(alphabets))
        for j in range(i + 1, len(alphabets))
    )
    directions = [(r.acquisition_family, r.transfer_family) for r in records]
    hard = {
        "grammar_independence": False,  # Fixed answer codecs are not independent grammar generation.
        "no_translation": all(g.translation_table is None for g in families),
        "no_primitive_dictionary_by_construction": False,  # Not established by inventory counts.
        "no_shared_surface_serialization": disjoint,
        "all_12_ordered_directions": len(set(directions)) == 12,
        "all_interventions_present": all(len(r.intervention_results) == 4 for r in records),
        "direction_world_roots_unique": len({r.seed_digest for r in records}) == len(records),
        "recovery_path_verified": all(r.recovery_path_verified for r in records),
        "bisimulation_bound": all(r.bisimulation_separation_witness for r in records),
    }
    intervention_bits = [bit for record in records for _, bit in record.intervention_results]
    return (
        {
            "treatment": [r.treatment_success for r in records],
            "wrong_class": [r.wrong_class_success for r in records],
            "shuffled_coupling": [r.shuffled_coupling_success for r in records],
            "acquisition_posterior_target_bisimulation_bayes": [
                r.bisimulation_bayes_success for r in records
            ],
            "direction_labels": [f"{a}->{b}" for a, b in directions],
            "intervention_agreement": intervention_bits,
            "hard_gates": hard,
        },
        {
            "record_count": len(records),
            "inferential_unit": "ordered_direction_world_pair",
            "ordered_directions": len(set(directions)),
            "interventions_per_unit": 4,
            "intervention_evaluations": len(intervention_bits),
            "surface_alphabets_pairwise_disjoint": disjoint,
            "serialization_schema_count": len({g.serialization_schema for g in families}),
            "inference_route_count": len({g.inference_route for g in families}),
            "primary_control_count": 3,
            "posterior_bisim_control_is_executable": False,
            "exact_source_history_posterior_is_executable": True,
            "implementation_scope": "EXECUTED_CODEC_CONTROL_NOT_INDEPENDENT_GRAMMAR_LEARNING",
            "all_recovery_paths_verified": hard["recovery_path_verified"],
            "all_bisimulation_separators_present": hard["bisimulation_bound"],
            "direction_world_roots_unique": hard["direction_world_roots_unique"],
        },
    )


def _g_inputs(records: list[Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    weights = {0.1: 2, 0.25: 5, 0.5: 10, 1.0: 20}
    nonzero = [r for r in records if r.dose > 0]
    maxdose = [r for r in records if r.dose == 1.0]
    exchangeability = audit_g_exchangeability_design(records)
    hard = {
        "preclassified": all(r.relevance_computed_before_corruption for r in records),
        "matched_corruption": all(
            r.relevant_corruption_count == r.irrelevant_corruption_count
            and r.relevant_corruption_magnitude == r.irrelevant_corruption_magnitude
            for r in records
        ),
        "nonzero_dose_nonempty": all(r.relevant_corruption_count > 0 for r in nonzero),
        "same_evaluator": False,  # Legacy G flip bits are planted, not evaluator outputs.
        "world_exchangeability_contract": bool(
            exchangeability["joint_world_vector_exchangeability_under_null"]
        ),
    }
    return (
        {
            "pairs": [
                {
                    "world_id": r.world_index,
                    "weight": weights[r.dose],
                    "relevant": r.relevant_flip,
                    "irrelevant": r.irrelevant_flip,
                }
                for r in nonzero
            ],
            "max_dose_relevant": [r.relevant_flip for r in maxdose],
            "max_dose_irrelevant": [r.irrelevant_flip for r in maxdose],
            "hard_gates": hard,
        },
        {
            "world_count": len({r.world_index for r in records}),
            "record_count": len(records),
            "randomization_unit": "world",
            "relevance_computed_before_corruption": hard["preclassified"],
            "matched_count_and_magnitude": hard["matched_corruption"],
            "exchangeability_contract": exchangeability,
        },
    )


def _p_episode_audit(episodes: list[Any]) -> dict[str, Any]:
    audit = dict(audit_p_episode_independence(episodes))
    audit["stochastic_ancestry"] = audit_p_stochastic_ancestry(episodes)
    audit.update(
        {
            "future_verifier_calls": sum(e.future_verifier_calls for e in episodes),
            "future_reconstruction_search_count": sum(
                e.future_reconstruction_search_count for e in episodes
            ),
            "all_source_distinct": all(e.source_distinct and not e.forbidden_shared_features for e in episodes),
            "all_label_free": all(not e.applicability_used_target_labels for e in episodes),
            "reacquisition_search_count_after_deletion": sum(
                e.acquisition_search_count for e in episodes
            ),
            "unique_retained_object_digests": len({e.retained_object_digest for e in episodes}),
        }
    )
    return audit


def run_dev_matrix(
    *,
    a_count: int = 64,
    b_worlds_per_direction: int = 8,
    g_worlds: int = 32,
    p_count: int = 64,
) -> dict[str, Any]:
    design = load_design_manifest(_DESIGN_PATH)
    analysis_plan = load_analysis_plan(_ANALYSIS_PATH)
    if design.confirmatory_execution_enabled:
        raise ConfirmatoryLockedError("DEV runner refuses a manifest with confirmation enabled")

    a_records = generate_a_growth_episodes(a_count)
    b_records = generate_b_dev_records(b_worlds_per_direction)
    g_records = generate_g_dev_records(g_worlds)
    p_records = generate_p_independent_episodes(p_count)

    a_input = a_growth_analysis_input(a_records)
    a_input["hard_gates"]["executed_generation"] = False
    a_audit = audit_a_growth_episodes(a_records)
    a_audit["stochastic_ancestry"] = audit_a_stochastic_ancestry(a_records)
    b_input, b_audit = _b_inputs(b_records)
    g_input, g_audit = _g_inputs(g_records)
    p_input = p_independent_analysis_input(p_records)
    p_input["hard_gates"]["executed_generation"] = False
    p_audit = _p_episode_audit(p_records)

    analysis_inputs = {"A": a_input, "B": b_input, "G": g_input, "P": p_input}
    analysis = analyze_matrix(analysis_inputs)

    return {
        "schema": "mathgraph.abgp.dev-matrix-summary.v2",
        "mode": "DEV_ONLY",
        "confirmatory_namespace_used": False,
        "design": {
            "status": design.status,
            "confirmatory_execution_enabled": design.confirmatory_execution_enabled,
            "design_version": design.raw["design_version"],
            "manifest_digest": design.digest,
            "analysis_plan_digest": analysis_plan.digest,
            "registered_confirmatory_task_counts": {
                "A": design.raw["arms"]["A"]["task_count"],
                "B_worlds_per_direction": design.raw["arms"]["B"]["fresh_worlds_per_direction"],
                "G": design.raw["arms"]["G"]["task_count"],
                "P": design.raw["arms"]["P"]["task_count"],
            },
        },
        "dev_counts": {
            "A": a_count,
            "B_worlds_per_direction": b_worlds_per_direction,
            "G": g_worlds,
            "P": p_count,
        },
        "raw_records": {
            "A": [asdict(record) for record in a_records],
            "B": [asdict(record) for record in b_records],
            "G": [asdict(record) for record in g_records],
            "P": [asdict(record) for record in p_records],
        },
        "analysis_inputs": analysis_inputs,
        "audits": {"A": a_audit, "B": b_audit, "G": g_audit, "P": p_audit},
        "analysis": analysis,
        "scientific_status": "DEVELOPMENT_MECHANICS_ONLY_NOT_CONFIRMATORY_EVIDENCE",
    }


def run_matrix(*, namespace: str, **kwargs: Any) -> dict[str, Any]:
    if namespace != _DEV_NAMESPACE:
        reject_confirmatory_namespace(namespace)
    return run_dev_matrix(**kwargs)


def write_dev_summary(path: str | Path, summary: dict[str, Any]) -> None:
    target = Path(path)
    target.write_text(
        json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
