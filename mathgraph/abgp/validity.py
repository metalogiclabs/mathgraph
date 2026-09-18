from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ValidityIssue:
    code: str
    detail: str


_FATAL_CODES: dict[str, dict[str, str]] = {
    "A": {
        "executed_generation": "A_UNEXECUTED_GENERATION",
        "message_nonidentifying": "A_DIRECT_ACTION_IDENTIFYING_MESSAGE",
        "single_message": "A_MESSAGE_BUDGET_VIOLATION",
        "single_repair_round": "A_REPAIR_BUDGET_VIOLATION",
        "budget_ok": "A_COMPUTE_BUDGET_MISMATCH",
        "old_language_complete": "A_OLD_LANGUAGE_COMPLETENESS_MISSING",
        "future_no_verifier": "A_FUTURE_VERIFIER_ACCESS",
        "no_future_target_leak": "A_FUTURE_TARGET_LEAK",
        "sham_budget_matched": "A_SHAM_BUDGET_MISMATCH",
    },
    "B": {
        "grammar_independence": "B_GRAMMAR_INDEPENDENCE_VIOLATION",
        "no_translation": "B_TRANSLATION_LEAK",
        "no_primitive_dictionary_by_construction": "B_PRIMITIVE_DICTIONARY_LEAK",
        "no_shared_surface_serialization": "B_SURFACE_SERIALIZATION_LEAK",
        "all_12_ordered_directions": "B_DIRECTION_COVERAGE_MISSING",
        "all_interventions_present": "B_INTERVENTION_COVERAGE_MISSING",
        "bisimulation_bound": "B_BISIMULATION_SPEC_UNBOUND",
    },
    "G": {
        "world_exchangeability_contract": "G_EXCHANGEABILITY_UNESTABLISHED",
        "preclassified": "G_POSTHOC_RELEVANCE_LABEL",
        "matched_corruption": "G_CORRUPTION_MISMATCH",
        "nonzero_dose_nonempty": "G_EMPTY_NONZERO_DOSE",
        "same_evaluator": "G_EVALUATOR_MISMATCH",
    },
    "P": {
        "executed_generation": "P_UNEXECUTED_GENERATION",
        "zero_verifier": "P_FUTURE_VERIFIER_ACCESS",
        "zero_search": "P_FUTURE_RECONSTRUCTION_SEARCH",
        "label_free": "P_TARGET_LABEL_APPLICABILITY",
        "source_distinct": "P_SOURCE_DISTINCTNESS_VIOLATION",
        "restart_clean": "P_RESTART_STATE_LEAK",
        "lineage_targeted": "P_ABLATION_NOT_LINEAGE_TARGETED",
    },
}


def validate_arm_input(arm: str, raw: Mapping[str, Any]) -> tuple[ValidityIssue, ...]:
    if arm not in _FATAL_CODES:
        raise ValueError(f"unknown ABGP arm: {arm}")
    gates = raw.get("hard_gates")
    if not isinstance(gates, Mapping):
        return (
            ValidityIssue(
                code=f"{arm}_HARD_GATES_MISSING",
                detail="arm input lacks a hard_gates mapping",
            ),
        )

    issues: list[ValidityIssue] = []
    for gate, code in _FATAL_CODES[arm].items():
        if gate in gates and gates[gate] is not True:
            issues.append(
                ValidityIssue(
                    code=code,
                    detail=f"validity gate {gate!r} is not true",
                )
            )
    return tuple(issues)
