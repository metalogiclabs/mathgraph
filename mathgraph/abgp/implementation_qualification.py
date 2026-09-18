"""Executed ABGP implementation qualification artifact.

This binds the executed A/B/G/P generators, the registered analysis, provenance
summaries, and exact source hashes into one canonical REVIEW_PENDING artifact.
It qualifies implementation/text consistency only. It never authorizes freeze
or confirmation and deliberately does not claim complete-PASS power.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .executed_matrix import run_executed_dev_matrix
from .manifest import load_design_manifest


_ROOT = Path(__file__).resolve().parents[2]
_HASH_PATHS = (
    "preregistration/abgp-design-manifest-v1.json",
    "preregistration/abgp-analysis-plan-v1.json",
    "mathgraph/abgp/executed_a.py",
    "mathgraph/abgp/executed_b.py",
    "mathgraph/abgp/executed_g.py",
    "mathgraph/abgp/executed_p.py",
    "mathgraph/abgp/executed_p_structural.py",
    "mathgraph/abgp/executed_matrix.py",
    "mathgraph/abgp/analysis.py",
    "mathgraph/abgp/validity.py",
    "mathgraph/abgp/exchangeability.py",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_file(relative: str) -> str:
    return sha256((_ROOT / relative).read_bytes()).hexdigest()


def _hash_manifest() -> dict[str, str]:
    return {path: _digest_file(path) for path in _HASH_PATHS}


def _requirement_evidence(matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = matrix["raw_inputs"]
    ancestry = matrix["inferential_ancestry_audit"]
    receipts = matrix["generator_receipts"]
    return {
        "A_information_boundary": {
            "implemented": bool(
                raw["A"]["hard_gates"]["message_nonidentifying"]
                and raw["A"]["hard_gates"]["future_no_verifier"]
                and raw["A"]["hard_gates"]["old_language_complete"]
                and raw["A"]["representation_growth_gate"]
            ),
            "evidence": {
                "generator": receipts["A"]["schema"],
                "representation_growth_gate": receipts["A"]["representation_growth_gate"],
                "future_verifier_calls": receipts["A"]["future_verifier_calls"],
                "same_analysis_input_bound": True,
            },
        },
        "B_grammar_independence": {
            "implemented": bool(
                raw["B"]["hard_gates"]["grammar_independence"]
                and raw["B"]["hard_gates"]["no_translation"]
                and raw["B"]["hard_gates"]["no_primitive_dictionary_by_construction"]
                and raw["B"]["hard_gates"]["bisimulation_bound"]
            ),
            "evidence": {
                "record_count": receipts["B"]["record_count"],
                "direction_count": receipts["B"]["direction_count"],
                "all_grammar_independent": receipts["B"]["all_grammar_independent"],
                "all_bisimulation_separated": receipts["B"]["all_bisimulation_separated"],
            },
        },
        "G_world_exchangeability": {
            "implemented": bool(
                raw["G"]["hard_gates"]["world_exchangeability_contract"]
                and raw["G"]["hard_gates"]["preclassified"]
                and raw["G"]["hard_gates"]["matched_corruption"]
                and raw["G"]["hard_gates"]["same_evaluator"]
            ),
            "evidence": {
                "generator": receipts["G"]["schema"],
                "world_count": receipts["G"]["world_count"],
                "all_exchangeability_contracts": receipts["G"]["all_exchangeability_contracts"],
                "randomization_unit": "world",
            },
        },
        "P_restart_persistence": {
            "implemented": bool(
                raw["P"]["hard_gates"]["restart_clean"]
                and raw["P"]["hard_gates"]["zero_verifier"]
                and raw["P"]["hard_gates"]["zero_search"]
                and raw["P"]["hard_gates"]["source_distinct"]
                and raw["P"]["hard_gates"]["lineage_targeted"]
                and raw["P"].get("reacquisition_restored")
            ),
            "evidence": {
                "generator": receipts["P"]["schema"],
                "episode_count": receipts["P"]["episode_count"],
                "hard_gates": receipts["P"]["hard_gates"],
                "reacquisition_restored": bool(raw["P"].get("reacquisition_restored")),
            },
        },
        "inferential_ancestry": {
            "implemented": all(
                ancestry[arm]["no_shared_generated_ancestor_across_scored_units"]
                for arm in ("A", "B", "G", "P")
            ),
            "evidence": {
                arm: {
                    "inferential_unit": ancestry[arm]["inferential_unit"],
                    "scored_unit_count": ancestry[arm]["scored_unit_count"],
                    "scope": ancestry[arm]["scope"],
                    "statistical_independence_proved_by_this_audit":
                        ancestry[arm]["statistical_independence_proved_by_this_audit"],
                }
                for arm in ("A", "B", "G", "P")
            },
        },
        "analysis_binding": {
            "implemented": all(
                matrix["analysis"]["arms"][arm].get("validity_pass") is True
                for arm in ("A", "B", "G", "P")
            ),
            "evidence": {
                "analysis_schema": matrix["analysis"].get("schema", "registered-abgp-analysis"),
                "arm_modes": {
                    arm: matrix["analysis"]["arms"][arm].get("analysis_mode")
                    for arm in ("A", "B", "G", "P")
                },
                "raw_inputs_from_executed_generators": True,
            },
        },
    }


def run_implementation_qualification(
    *,
    a_count: int = 32,
    b_worlds_per_direction: int = 8,
    g_worlds: int = 16,
    p_count: int = 8,
    namespace: str = "ABGP-DEV-v1",
) -> dict[str, Any]:
    if namespace != "ABGP-DEV-v1":
        raise ValueError("implementation qualification accepts only ABGP-DEV-v1")
    design = load_design_manifest(_ROOT / "preregistration" / "abgp-design-manifest-v1.json")
    if design.status not in ("REVIEW_PENDING", "FROZEN") or design.confirmatory_execution_enabled:
        raise ValueError("implementation qualification requires REVIEW_PENDING/FROZEN design with confirmation disabled")

    matrix = run_executed_dev_matrix(
        a_count=a_count,
        b_worlds_per_direction=b_worlds_per_direction,
        g_worlds=g_worlds,
        p_count=p_count,
        namespace=namespace,
    )
    evidence = _requirement_evidence(matrix)
    ancestry = matrix["inferential_ancestry_audit"]
    implementation_qualified = bool(
        matrix["implementation_qualified"]
        and all(row["implemented"] for row in evidence.values())
    )

    artifact: dict[str, Any] = {
        "schema": "abgp.implementation-qualification.v1",
        "mode": "DEV_EXECUTED_IMPLEMENTATION_QUALIFICATION",
        "status": (
            "IMPLEMENTATION_QUALIFIED_FROZEN" if implementation_qualified and design.status == "FROZEN"
            else "IMPLEMENTATION_QUALIFIED_REVIEW_PENDING" if implementation_qualified
            else "IMPLEMENTATION_NOT_QUALIFIED"
        ),
        "design_status": design.status,
        "implementation_qualified": implementation_qualified,
        "complete_pass_power_qualified": False,
        "freeze_authorized": False,
        "confirmatory_namespace_used": False,
        "scientific_interpretation": "DEV_IMPLEMENTATION_QUALIFICATION_NOT_CONFIRMATORY_EVIDENCE",
        "generator_kinds": dict(matrix["generator_kinds"]),
        "dev_counts": dict(matrix["dev_counts"]),
        "implementation_gates": dict(matrix["implementation_gates"]),
        "requirement_evidence": evidence,
        "ancestry": ancestry,
        "scientific_dev_verdicts": {
            arm: matrix["analysis"]["arms"][arm]["verdict"] for arm in ("A", "B", "G", "P")
        },
        "scientific_dev_effects": {
            arm: matrix["analysis"]["arms"][arm].get("effect") for arm in ("A", "B", "G", "P")
        },
        "hash_manifest": _hash_manifest(),
        "analysis_digest": sha256(_canonical(matrix["analysis"]).encode("ascii")).hexdigest(),
        "raw_input_digest": sha256(_canonical(matrix["raw_inputs"]).encode("ascii")).hexdigest(),
        "matrix_schema": matrix["schema"],
    }
    artifact["artifact_digest"] = sha256(_canonical(artifact).encode("ascii")).hexdigest()
    return json.loads(_canonical(artifact))


def write_implementation_qualification(path: str | Path, artifact: dict[str, Any]) -> None:
    target = Path(path)
    target.write_text(_canonical(artifact) + "\n", encoding="utf-8")
