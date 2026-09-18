from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .analysis import analyze_matrix
from .manifest import load_analysis_plan, load_design_manifest
from .power import qualification_power_audit
from .qualification_fixtures import passing_qualification_matrix, qualification_fixtures
from .statistical_reference import run_statistical_reference_audit


_ROOT = Path(__file__).resolve().parents[2]
_DESIGN_PATH = _ROOT / "preregistration" / "abgp-design-manifest-v1.json"
_ANALYSIS_PATH = _ROOT / "preregistration" / "abgp-analysis-plan-v1.json"
_QUALIFICATION_SCHEMA = "mathgraph.abgp.qualification.v1"
_SCIENTIFIC_PATHS = (
    "mathgraph/abgp/analysis.py",
    "mathgraph/abgp/arm_a.py",
    "mathgraph/abgp/arm_b.py",
    "mathgraph/abgp/arm_g.py",
    "mathgraph/abgp/arm_p.py",
    "mathgraph/abgp/b_iut.py",
    "mathgraph/abgp/power.py",
    "mathgraph/abgp/qualification_fixtures.py",
    "mathgraph/abgp/statistical_reference.py",
    "mathgraph/abgp/validity.py",
)
_EXPECTED_ANALYSIS_MODES = {
    "A": "STRENGTHENED_REPRESENTATION_GROWTH",
    "B": "DIRECTION_STRATIFIED_IUT",
    "G": "WORLD_BLOCKED_REPEATED_MEASURES",
    "P": "INDEPENDENT_EPISODE_POSTERIOR_BISIMULATION",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _file_digest(relative_path: str) -> str:
    return sha256((_ROOT / relative_path).read_bytes()).hexdigest()


def _scientific_code_hashes() -> dict[str, str]:
    return {path: _file_digest(path) for path in _SCIENTIFIC_PATHS}


def _fixture_row(fixture: Any, base_matrix: dict[str, dict[str, Any]]) -> dict[str, Any]:
    matrix = deepcopy(base_matrix)
    matrix[fixture.arm] = deepcopy(fixture.raw_input)
    result = analyze_matrix(matrix)
    arm_result = result["arms"][fixture.arm]
    observed_reason_codes = tuple(arm_result.get("validity_reason_codes", ()))
    expected_reason_codes = tuple(fixture.expected_reason_codes)
    reason_match = (
        observed_reason_codes == expected_reason_codes
        if expected_reason_codes
        else not observed_reason_codes
    )
    observed_verdict = str(arm_result["verdict"])
    matched = observed_verdict == fixture.expected_verdict and reason_match
    return {
        "fixture_id": fixture.fixture_id,
        "arm": fixture.arm,
        "fixture_class": fixture.fixture_class,
        "namespace": fixture.namespace,
        "expected_verdict": fixture.expected_verdict,
        "observed_verdict": observed_verdict,
        "expected_reason_codes": list(expected_reason_codes),
        "observed_reason_codes": list(observed_reason_codes),
        "matched_expectation": matched,
        "raw_input_digest": _digest(fixture.raw_input),
        "witness_digest": _digest(fixture.witness),
        "arm_raw_pvalue": arm_result.get("raw_pvalue"),
        "arm_effect": arm_result.get("effect"),
        "arm_analysis_mode": arm_result.get("analysis_mode"),
    }


def _analysis_path_audit(base_matrix: dict[str, dict[str, Any]]) -> dict[str, Any]:
    result = analyze_matrix(deepcopy(base_matrix))
    observed = {
        arm: result["arms"][arm].get("analysis_mode") for arm in ("A", "B", "G", "P")
    }
    matches = {
        arm: observed[arm] == _EXPECTED_ANALYSIS_MODES[arm] for arm in _EXPECTED_ANALYSIS_MODES
    }
    return {
        "expected_modes": dict(_EXPECTED_ANALYSIS_MODES),
        "observed_modes": observed,
        "all_hardened_paths_active": all(matches.values()),
        "mode_matches": matches,
    }


def _power_table(power_audit: dict[str, Any], design: Any, analysis: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.append({
        "arm": "A",
        "inferential_unit": design.arms["A"]["inferential_unit"],
        "dependence_structure": "proposed independent episodes; full sampling-model audit pending",
        "n": int(analysis.arms["A"]["n"]),
        "effect_floor": float(analysis.arms["A"]["effect_floor"]),
        "component_alpha": float(power_audit["component_alpha"]),
        "nuisance_envelope": list(analysis.raw["qualification"]["paired_nuisance_envelope"]["A"]["discordance_rates"]),
        "minimum_power": float(power_audit["arms"]["A"]["minimum_observed_power"]),
    })
    rows.append({
        "arm": "B",
        "inferential_unit": design.arms["B"]["name"] + ": ordered-direction world unit",
        "dependence_structure": "12 direction strata; 4 interventions nested per world; 36-component IUT with dependence-agnostic union-bound power lower bound",
        "n": int(power_audit["arms"]["B"]["n"]),
        "worlds_per_direction": int(power_audit["arms"]["B"]["worlds_per_direction"]),
        "effect_floor": float(analysis.arms["B"]["effect_floor_each_control"]),
        "component_alpha": float(power_audit["component_alpha"]),
        "nuisance_envelope": list(analysis.raw["qualification"]["paired_nuisance_envelope"]["B"]["discordance_rates"]),
        "minimum_power": float(power_audit["arms"]["B"]["minimum_observed_power"]),
    })
    rows.append({
        "arm": "G",
        "inferential_unit": design.arms["G"]["inferential_unit"],
        "dependence_structure": "one world-level relevant/irrelevant sign exchange jointly across all nonzero doses",
        "n": int(analysis.arms["G"]["n_worlds"]),
        "effect_floor": float(analysis.raw["qualification"]["g_nuisance_envelope"]["max_dose_effect_floor"]),
        "component_alpha": float(power_audit["component_alpha"]),
        "nuisance_envelope": list(analysis.raw["qualification"]["g_nuisance_envelope"]["max_dose_discordance_rates"]),
        "minimum_power": float(power_audit["arms"]["G"]["minimum_observed_power"]),
    })
    rows.append({
        "arm": "P",
        "inferential_unit": design.arms["P"]["inferential_unit"],
        "dependence_structure": "one acquisition/restart episode; exactly four fixed nested futures collapsed to one binary episode outcome",
        "n": int(analysis.arms["P"]["n"]),
        "effect_floor": float(analysis.arms["P"]["effect_floor"]),
        "component_alpha": float(power_audit["component_alpha"]),
        "nuisance_envelope": list(analysis.raw["qualification"]["paired_nuisance_envelope"]["P"]["discordance_rates"]),
        "minimum_power": float(power_audit["arms"]["P"]["minimum_observed_power"]),
    })
    for row in rows:
        row["power_scope"] = "HISTORICAL_COMPONENT_SIGNIFICANCE_ONLY_NOT_COMPLETE_PASS"
    return rows


def run_qualification() -> dict[str, Any]:
    """Run deterministic DEV/QUAL-only methodological qualification."""

    design = load_design_manifest(_DESIGN_PATH)
    analysis = load_analysis_plan(_ANALYSIS_PATH)
    if design.status not in ("REVIEW_PENDING", "FROZEN") or design.confirmatory_execution_enabled:
        raise ValueError("qualification requires REVIEW_PENDING/FROZEN design with confirmation disabled")

    base_matrix = passing_qualification_matrix()
    path_audit = _analysis_path_audit(base_matrix)
    rows = [_fixture_row(fixture, base_matrix) for fixture in qualification_fixtures()]
    reference_audit = run_statistical_reference_audit()
    power_audit = qualification_power_audit(analysis)

    fixtures_match = all(row["matched_expectation"] for row in rows)
    namespaces_safe = all(
        row["namespace"].startswith(("ABGP-DEV-", "ABGP-QUAL-"))
        and "ABGP-CONFIRM" not in row["namespace"]
        for row in rows
    )
    qualified = (
        fixtures_match
        and namespaces_safe
        and path_audit["all_hardened_paths_active"]
        and reference_audit.get("status") == "PASS"
        and bool(power_audit.get("qualified"))
    )

    class_counts: dict[str, int] = {}
    for row in rows:
        class_counts[row["fixture_class"]] = class_counts.get(row["fixture_class"], 0) + 1

    artifact: dict[str, Any] = {
        "schema": _QUALIFICATION_SCHEMA,
        "mode": "QUALIFICATION_ONLY",
        "verdict": "HARNESS_QUALIFIED" if qualified else "HARNESS_NOT_QUALIFIED",
        "qualification_scope": "STATISTICAL_AND_SYNTHETIC_FIXTURE_HARNESS_ONLY",
        "implementation_qualified": False,
        "complete_pass_power_qualified": False,
        "freeze_authorized": False,
        "confirmatory_namespace_used": False,
        "design_status": design.status,
        "confirmatory_execution_enabled": design.confirmatory_execution_enabled,
        "design_manifest_digest": design.digest,
        "analysis_plan_digest": analysis.digest,
        "scientific_code_hashes": _scientific_code_hashes(),
        "analysis_path_audit": path_audit,
        "fixture_count": len(rows),
        "fixture_class_counts": dict(sorted(class_counts.items())),
        "fixtures": rows,
        "statistical_reference_audit": reference_audit,
        "power_audit": power_audit,
        "power_inferential_unit_table": _power_table(power_audit, design, analysis),
        "safety": {
            "qualification_namespaces_only": namespaces_safe,
            "confirmatory_namespace_accessed": False,
            "all_fixture_expectations_matched": fixtures_match,
            "all_hardened_analysis_paths_active": path_audit["all_hardened_paths_active"],
        },
        "scientific_interpretation": "SYNTHETIC_FIXTURE_HARNESS_ONLY_NO_END_TO_END_IMPLEMENTATION_CLAIM",
    }
    artifact["qualification_digest"] = _digest(artifact)
    return json.loads(_canonical_json(artifact))


def write_qualification_artifact(path: str | Path, artifact: dict[str, Any]) -> None:
    target = Path(path)
    target.write_text(_canonical_json(artifact) + "\n", encoding="utf-8")
