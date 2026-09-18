"""Review-only complete-PASS power proposal.

The registered scientific PASS floors are not changed here. Stronger planning
alternatives are used only to choose candidate sample sizes while REVIEW_PENDING.
Nothing in this module authorizes freeze or confirmation.
"""
from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from math import ceil
from typing import Any, Sequence

from .freeze_review import _complete_component_power_at_floor
from .manifest import ABGPAnalysisPlan
from .power import _binomial_upper_tail


_COMPONENT_ALPHA = Fraction(1, 80)  # 0.0125
_MIN_POWER = 0.80


def _feasible_envelope(registered: Sequence[float], planning_effect: float) -> tuple[float, ...]:
    # Discordance q must satisfy q >= |delta|. Registered points below a stronger
    # planning alternative are mathematically impossible, so include the exact
    # q=delta boundary and retain all registered feasible points above it.
    return tuple(sorted({planning_effect, *(float(q) for q in registered if float(q) >= planning_effect)}))


@lru_cache(maxsize=None)
def _complete_component_min(
    n: int,
    planning_effect_text: str,
    observed_floor_text: str,
    envelope: tuple[float, ...],
) -> tuple[float, tuple[tuple[float, float], ...]]:
    effect = Fraction(planning_effect_text)
    floor = Fraction(observed_floor_text)
    points = []
    for q in envelope:
        power = _complete_component_power_at_floor(
            n=n,
            discordance_rate=Fraction(str(q)),
            true_effect=effect,
            alpha=_COMPONENT_ALPHA,
            observed_effect_floor=floor,
        )
        points.append((float(q), float(power)))
    return min(power for _, power in points), tuple(points)


def _component_review(
    *,
    proposed_n: int,
    planning_effect: float,
    observed_floor: float,
    registered_envelope: Sequence[float],
    component_count: int,
) -> dict[str, Any]:
    envelope = _feasible_envelope(registered_envelope, planning_effect)
    minimum, points = _complete_component_min(
        proposed_n, str(planning_effect), str(observed_floor), envelope
    )
    lower = max(0.0, 1.0 - component_count * (1.0 - minimum))
    return {
        "observed_pass_floor": observed_floor,
        "planning_effect": planning_effect,
        "component_count": component_count,
        "feasible_discordance_envelope": list(envelope),
        "component_power_points": [
            {"discordance_rate": q, "complete_component_power": power}
            for q, power in points
        ],
        "minimum_complete_component_power": minimum,
        "dependence_agnostic_component_union_lower_bound": lower,
    }


def build_planning_proposal(plan: ABGPAnalysisPlan) -> dict[str, Any]:
    if plan.status not in ("REVIEW_PENDING", "FROZEN"):
        raise ValueError("planning review requires REVIEW_PENDING or FROZEN plan")
    frozen = plan.status == "FROZEN"
    qualification = plan.raw["qualification"]
    approved = qualification.get("approved_planning", {})
    approved_effects = approved.get("effects", {})
    paired = qualification["paired_nuisance_envelope"]
    g_env = qualification["g_nuisance_envelope"]["max_dose_discordance_rates"]

    a = _component_review(
        proposed_n=int(plan.arms["A"]["n"]),
        planning_effect=float(approved_effects.get("A", 0.10)),
        observed_floor=float(plan.arms["A"]["effect_floor"]),
        registered_envelope=paired["A"]["discordance_rates"],
        component_count=3,
    )
    a.update({
        "proposed_n": int(plan.arms["A"]["n"]),
        "current_review_n": int(plan.arms["A"]["n"]),
        "conservative_complete_pass_lower_bound": a["dependence_agnostic_component_union_lower_bound"],
    })

    b = _component_review(
        proposed_n=int(plan.arms["B"]["worlds_per_direction"]),
        planning_effect=float(approved_effects.get("B", 0.25)),
        observed_floor=float(plan.arms["B"]["effect_floor_each_control"]),
        registered_envelope=paired["B"]["discordance_rates"],
        component_count=36,
    )
    total_worlds = 12 * int(plan.arms["B"]["worlds_per_direction"])
    agreement_threshold = ceil(0.90 * total_worlds)
    planning_agreement = float(approved.get("B_all_four_world_agreement", 0.95))
    agreement_power = float(_binomial_upper_tail(total_worlds, agreement_threshold, planning_agreement))
    b_combined = max(
        0.0,
        1.0
        - 36 * (1.0 - b["minimum_complete_component_power"])
        - (1.0 - agreement_power),
    )
    b.update({
        "proposed_worlds_per_direction": int(plan.arms["B"]["worlds_per_direction"]),
        "proposed_total_worlds": total_worlds,
        "current_review_worlds_per_direction": int(plan.arms["B"]["worlds_per_direction"]),
        "independent_unit_count_for_agreement_planning": total_worlds,
        "interventions_per_world": int(plan.arms["B"]["interventions_per_unit"]),
        "observed_pooled_agreement_gate": 0.90,
        "planning_world_all_four_agreement": planning_agreement,
        "agreement_gate_success_threshold_worlds": agreement_threshold,
        "conservative_agreement_gate_power": agreement_power,
        "conservative_complete_pass_lower_bound": b_combined,
        "agreement_power_model": (
            "conservative world-unit model: a world counts as planning success only when all four nested "
            "intervention orderings agree; >=90% successful worlds is sufficient for the registered >=90% pooled gate"
        ),
    })

    g = _component_review(
        proposed_n=int(plan.arms["G"]["n_worlds"]),
        planning_effect=float(approved_effects.get("G", 0.25)),
        observed_floor=float(qualification["g_nuisance_envelope"]["max_dose_effect_floor"]),
        registered_envelope=g_env,
        component_count=1,
    )
    g.update({
        "proposed_n": int(plan.arms["G"]["n_worlds"]),
        "current_review_n": int(plan.arms["G"]["n_worlds"]),
        "conservative_complete_pass_lower_bound": g["minimum_complete_component_power"],
        "power_model": (
            "registered conservative world-blocked max-dose-only model; all lower-dose signal fixed to zero"
        ),
    })

    p = _component_review(
        proposed_n=int(plan.arms["P"]["n"]),
        planning_effect=float(approved_effects.get("P", 0.10)),
        observed_floor=float(plan.arms["P"]["effect_floor"]),
        registered_envelope=paired["P"]["discordance_rates"],
        component_count=7,
    )
    p.update({
        "proposed_n": int(plan.arms["P"]["n"]),
        "current_review_n": int(plan.arms["P"]["n"]),
        "conservative_complete_pass_lower_bound": p["dependence_agnostic_component_union_lower_bound"],
        "deletion_closeness_planning": "MECHANICALLY_IDENTICAL_TO_COLD_POTENTIAL_OUTCOME",
        "deletion_closeness_note": (
            "deletion-to-cold equality is mechanically enforced rather than powered: executed deletion "
            "removes the sole retained lineage, and deleted and cold invocations receive the same null "
            "retained state and the same deterministic future-task payload"
        ),
        "reacquisition_gate_planning": "MECHANICALLY_REENTERS_FROZEN_ACQUISITION_PROCEDURE",
    })

    arms = {"A": a, "B": b, "G": g, "P": p}
    if not all(arm["conservative_complete_pass_lower_bound"] >= _MIN_POWER for arm in arms.values()):
        raise AssertionError("rounded planning proposal does not meet the requested conservative 0.80 lower bound")

    return {
        "schema": "abgp.complete-pass-planning-proposal.v1",
        "status": "FROZEN_APPROVED" if frozen else "JOINT_REVIEW_REQUIRED",
        "approved_by_collaborators": frozen,
        "scientific_pass_criteria_changed": False,
        "complete_pass_power_qualified": frozen,
        "minimum_required_power": _MIN_POWER,
        "familywise_alpha": float(plan.familywise_alpha),
        "component_alpha": float(_COMPONENT_ALPHA),
        "alpha_provenance": (
            "worst-case first Holm threshold across four arm-level p-values; B's 36 components form one IUT "
            "and do not receive a second multiplicity correction"
        ),
        "planning_alternative_rule": (
            "planning true effects are strictly above observed scientific PASS floors; infeasible registered "
            "discordance points q<planning effect are replaced by the exact feasible boundary q=planning effect"
        ),
        "arms": arms,
        "joint_decisions_requested": [] if frozen else [
            "approve or revise the planning effects A=.10, B=.25, G=.25, P=.10",
            "confirm the already-reviewed counts remain A=4096, B=1015/direction, G=421, P=4096",
            "approve B planning all-four world agreement=.95 for the >=.90 pooled observed gate",
            "approve P deletion-to-cold equality as a mechanically enforced gate rather than a separate power target",
        ],
        "normative_update_required_after_approval": not frozen,
        "count_change_requested": False,
        "confirmatory_namespace_used": False,
        "freeze_authorized": frozen,
    }
