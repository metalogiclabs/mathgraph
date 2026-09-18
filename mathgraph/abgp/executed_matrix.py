"""Integrated executed DEV qualification for A/B/G/P.

This module binds only the executed generators to the registered analysis.
It is an implementation/text-consistency qualification, never confirmatory evidence.
"""
from __future__ import annotations

from typing import Any

from .analysis import analyze_matrix
from .executed_a import run_a_batch
from .executed_b import INTERVENTIONS, run_b_batch
from .executed_g import run_structural_g_batch
from .executed_p_structural import run_structural_p_batch
from .manifest import load_design_manifest


def _b_analysis_input(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise ValueError("B executed matrix requires records")
    directions = [f"{r['acquisition_family']}->{r['transfer_family']}" for r in records]
    intervention_agreement = [
        int(row["agreement"])
        for record in records
        for row in record["intervention_results"]
    ]
    all_12 = len(set(directions)) == 12
    all_interventions = all(
        tuple(row["intervention"] for row in record["intervention_results"]) == INTERVENTIONS
        for record in records
    )
    hard = {
        "grammar_independence": all(r["grammar_independence"] for r in records),
        "no_translation": all(r["source_target_surface_disjoint"] for r in records),
        "no_primitive_dictionary_by_construction": all(r["no_primitive_dictionary"] for r in records),
        "no_shared_surface_serialization": all(r["source_target_surface_disjoint"] for r in records),
        "all_12_ordered_directions": all_12,
        "all_interventions_present": all_interventions,
        "bisimulation_bound": all(r["bisimulation_separation_witness"] for r in records),
    }
    return {
        "treatment": [r["treatment_success"] for r in records],
        "wrong_class": [r["wrong_class_success"] for r in records],
        "shuffled_coupling": [r["shuffled_coupling_success"] for r in records],
        "acquisition_posterior_target_bisimulation_bayes": [
            r["old_bisimulation_bayes_success"] for r in records
        ],
        "direction_labels": directions,
        "intervention_agreement": intervention_agreement,
        "hard_gates": hard,
    }


def _all_true(mapping: dict[str, Any]) -> bool:
    return bool(mapping) and all(value is True for value in mapping.values())



def _no_duplicates(groups: list[tuple[str, ...]]) -> bool:
    flattened = [value for group in groups for value in group]
    return len(flattened) == len(set(flattened))


def _ancestry_audits(
    a: dict[str, Any],
    b_records: list[dict[str, Any]],
    g: dict[str, Any],
    p: dict[str, Any],
) -> dict[str, Any]:
    a_groups = [
        (episode["acquisition_seed_digest"], episode["future_seed_digest"])
        for episode in a["episodes"]
    ]
    b_groups = [
        (
            record["latent_world_digest"],
            record["source_grammar_digest"],
            record["target_grammar_digest"],
        )
        for record in b_records
    ]
    g_groups = [(world["base_world_digest"],) for world in g["worlds"]]
    p_groups = [
        tuple(
            [episode["source_distinctness"]["source_seed_digest"]]
            + list(episode["source_distinctness"]["future_seed_digests"])
        )
        for episode in p["episodes"]
    ]
    return {
        "A": {
            "inferential_unit": "acquisition_to_sealed_future_episode",
            "scored_unit_count": len(a_groups),
            "unique_generated_root_count": len({x for group in a_groups for x in group}),
            "no_shared_generated_ancestor_across_scored_units": _no_duplicates(a_groups),
            "fixed_protocol_objects": [
                "ABGP-DEV-v1 namespace",
                "executed structural candidate languages",
                "generator code and registered analysis",
            ],
            "statistical_independence_proved_by_this_audit": False,
            "scope": "generated acquisition/future roots only; fixed protocol objects are shared by design",
        },
        "B": {
            "inferential_unit": "ordered_direction_latent_world_pair",
            "scored_unit_count": len(b_groups),
            "unique_latent_world_roots": len({record["latent_world_digest"] for record in b_records}),
            "unique_generated_root_count": len({x for group in b_groups for x in group}),
            "no_shared_generated_ancestor_across_scored_units": _no_duplicates(b_groups),
            "fixed_protocol_objects": [
                "four grammar-family algorithms",
                "protected action-order objective",
                "registered intervention set and analysis",
            ],
            "statistical_independence_proved_by_this_audit": False,
            "scope": "fresh latent world and independently generated source/target grammar roots per ordered-direction unit",
        },
        "G": {
            "inferential_unit": "world",
            "scored_unit_count": len(g_groups),
            "unique_generated_root_count": len({x for group in g_groups for x in group}),
            "no_shared_generated_ancestor_across_scored_units": _no_duplicates(g_groups),
            "fixed_protocol_objects": [
                "paired-cell generator",
                "four-dose schedule",
                "protected evaluator and world-level randomization rule",
            ],
            "statistical_independence_proved_by_this_audit": False,
            "scope": "base-world roots; within-world doses are nested and intentionally share their world root",
        },
        "P": {
            "inferential_unit": "acquisition_restart_future_episode",
            "scored_unit_count": len(p_groups),
            "unique_generated_root_count": len({x for group in p_groups for x in group}),
            "no_shared_generated_ancestor_across_scored_units": _no_duplicates(p_groups),
            "fixed_protocol_objects": [
                "source acquisition carrier definition",
                "retained capability interpreter",
                "four future context classes and registered analysis",
            ],
            "statistical_independence_proved_by_this_audit": False,
            "scope": "source and four future generated roots; four future probes are nested within one episode",
        },
    }

def run_executed_dev_matrix(
    *,
    a_count: int = 32,
    b_worlds_per_direction: int = 8,
    g_worlds: int = 16,
    p_count: int = 8,
    namespace: str = "ABGP-DEV-v1",
) -> dict[str, Any]:
    if namespace != "ABGP-DEV-v1":
        raise ValueError("executed matrix accepts only ABGP-DEV-v1")
    if any(type(n) is not int or n <= 0 for n in (a_count, b_worlds_per_direction, g_worlds, p_count)):
        raise ValueError("all executed DEV counts must be positive integers")

    design = load_design_manifest("preregistration/abgp-design-manifest-v1.json")
    if design.status not in ("REVIEW_PENDING", "FROZEN") or design.confirmatory_execution_enabled:
        raise ValueError("executed DEV matrix requires confirmation locked and REVIEW_PENDING/FROZEN")

    a = run_a_batch(a_count)
    b_records = run_b_batch(b_worlds_per_direction)
    g = run_structural_g_batch(g_worlds)
    p = run_structural_p_batch(p_count, namespace=namespace)

    raw = {
        "A": a["analysis_input"],
        "B": _b_analysis_input(b_records),
        "G": g["analysis_input"],
        "P": p["analysis_input"],
    }
    analysis = analyze_matrix(raw)

    gates = {
        "A": _all_true(raw["A"]["hard_gates"]) and bool(raw["A"]["representation_growth_gate"]),
        "B": _all_true(raw["B"]["hard_gates"]),
        "G": _all_true(raw["G"]["hard_gates"]),
        "P": _all_true(raw["P"]["hard_gates"]) and bool(raw["P"].get("reacquisition_restored")),
    }
    implementation_qualified = all(gates.values()) and all(
        analysis["arms"][arm].get("validity_pass") is True for arm in ("A", "B", "G", "P")
    )

    return {
        "schema": "abgp.executed-dev-matrix.v1",
        "mode": "DEV_EXECUTED_IMPLEMENTATION_QUALIFICATION",
        "design_status": design.status,
        "confirmatory_execution_enabled": design.confirmatory_execution_enabled,
        "confirmatory_namespace_used": False,
        "freeze_authorized": False,
        "complete_pass_power_qualified": False,
        "implementation_qualified": implementation_qualified,
        "generator_kinds": {
            "A": "executed_structural_construction",
            "B": "independently_generated_cross_grammar",
            "G": "causal_cell_evaluator_world_randomization",
            "P": "hard_restart_source_distinct_structural_persistence",
        },
        "dev_counts": {
            "A": a_count,
            "B_worlds_per_direction": b_worlds_per_direction,
            "G": g_worlds,
            "P": p_count,
        },
        "implementation_gates": gates,
        "inferential_ancestry_audit": _ancestry_audits(a, b_records, g, p),
        "raw_inputs": raw,
        "analysis": analysis,
        "generator_receipts": {
            "A": {
                "schema": a["schema"],
                "representation_growth_gate": a["representation_growth_gate"],
                "future_verifier_calls": a["future_verifier_calls"],
            },
            "B": {
                "record_count": len(b_records),
                "direction_count": len(set(raw["B"]["direction_labels"])),
                "all_grammar_independent": raw["B"]["hard_gates"]["grammar_independence"],
                "all_bisimulation_separated": raw["B"]["hard_gates"]["bisimulation_bound"],
            },
            "G": {
                "schema": g["schema"],
                "world_count": len(g["worlds"]),
                "all_exchangeability_contracts": raw["G"]["hard_gates"]["world_exchangeability_contract"],
            },
            "P": {
                "schema": p["schema"],
                "episode_count": len(p["episodes"]),
                "hard_gates": p["hard_gates"],
            },
        },
        "scientific_interpretation": "DEV_MECHANICS_AND_TEXT_IMPLEMENTATION_ONLY_NOT_CONFIRMATORY_EVIDENCE",
    }
