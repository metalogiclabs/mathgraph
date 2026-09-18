from __future__ import annotations

from pathlib import Path
from time import perf_counter
import json

from mathgraph.abgp.analysis import analyze_p
from mathgraph.abgp.arm_p import (
    audit_p_episode_independence,
    generate_p_independent_episodes,
    p_episode_resource_audit,
    p_independent_analysis_input,
)
from mathgraph.abgp.manifest import load_analysis_plan
from mathgraph.abgp.power import qualification_power_audit


ROOT = Path(__file__).resolve().parent
ANALYSIS_PLAN = ROOT / "preregistration" / "abgp-analysis-plan-v1.json"
OUTPUT = ROOT / "abgp-p-episode-budget.json"
EPISODES = 4096


def main() -> int:
    started = perf_counter()
    episodes = generate_p_independent_episodes(EPISODES)
    generation_seconds = perf_counter() - started

    raw = p_independent_analysis_input(episodes)
    analysis = analyze_p(raw)
    independence = audit_p_episode_independence(episodes)
    resources = p_episode_resource_audit(EPISODES)
    plan = load_analysis_plan(ANALYSIS_PLAN)
    power = qualification_power_audit(plan)["arms"]["P"]

    payload = {
        "schema": "mathgraph.abgp.p-independent-episode-budget.v1",
        "mode": "DEV_QUAL_ONLY",
        "scientific_status": "METHOD_QUALIFICATION_ONLY_NOT_CONFIRMATORY_EVIDENCE",
        "confirmatory_namespace_used": False,
        "independent_acquisition_episodes": EPISODES,
        "generation_seconds_observed": generation_seconds,
        "independence_audit": independence,
        "resource_audit": resources,
        "analysis": {
            "analysis_mode": analysis["analysis_mode"],
            "raw_pvalue": analysis["raw_pvalue"],
            "effect": analysis["effect"],
            "effect_floor_pass": analysis["effect_floor_pass"],
            "targeted_deletion_gate": analysis["targeted_deletion_gate"],
            "hard_gates_pass": analysis["hard_gates_pass"],
        },
        "power": {
            "minimum_required_power": 0.80,
            "minimum_observed_power": power["minimum_observed_power"],
            "qualified": power["qualified"],
            "points": power["points"],
        },
    }
    OUTPUT.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    ok = (
        independence["primary_n"] == EPISODES
        and independence["future_tasks_per_episode"] == 4
        and independence["all_acquisition_seed_material_unique"]
        and independence["all_future_seed_material_unique"]
        and independence["one_acquisition_per_episode"]
        and independence["nested_tasks_not_counted_as_n"]
        and analysis["hard_gates_pass"]
        and analysis["effect_floor_pass"]
        and power["qualified"]
    )

    print("REALITYGRAPH / ABGP P INDEPENDENT-EPISODE BUDGET AUDIT")
    print(f"independent_acquisition_episodes {EPISODES}")
    print(f"future_tasks_per_episode {independence['future_tasks_per_episode']}")
    print(f"generation_seconds_observed {generation_seconds:.6f}")
    print(f"maximum_acquisition_candidate_checks {resources['maximum_acquisition_candidate_checks']}")
    print(f"p_effect {analysis['effect']:.6f}")
    print(f"p_minimum_power {power['minimum_observed_power']:.6f}")
    print("confirmatory_namespace_used 0")
    print("ABGP_P_EPISODE_BUDGET_OK" if ok else "ABGP_P_EPISODE_BUDGET_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
