from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from hashlib import sha256
from typing import Any, Sequence

from .arm_a import AGrowthEpisode
from .arm_g import GRecord
from .arm_p import PIndependentEpisode
from .manifest import ABGPAnalysisPlan
from .power import (
    _binomial_probability,
    _binomial_upper_tail,
    _null_critical_wins,
    qualification_power_audit,
)


def _shared_ancestor_count(groups: Sequence[tuple[str, ...]]) -> int:
    owners: dict[str, set[int]] = defaultdict(set)
    for index, group in enumerate(groups):
        for ancestor in group:
            owners[str(ancestor)].add(index)
    return sum(1 for episode_ids in owners.values() if len(episode_ids) > 1)


def audit_a_stochastic_ancestry(episodes: Sequence[AGrowthEpisode]) -> dict[str, Any]:
    if not episodes:
        raise ValueError("A stochastic-ancestry audit requires episodes")
    groups = [
        (
            f"acquisition:{episode.acquisition_seed_digest}",
            f"sealed_future:{episode.future_seed_digest}",
        )
        for episode in episodes
    ]
    shared = _shared_ancestor_count(groups)
    return {
        "inferential_unit": "acquisition_to_sealed_future_episode",
        "earliest_stochastic_ancestor_rule": (
            "episode-specific acquisition seed and separately derived sealed-future seed; "
            "no randomly generated world, grammar, acquisition pool, or constructor is shared across episodes"
        ),
        "fixed_protocol_objects": [
            "old-language R0 definition",
            "constructor family and verifier-message alphabet",
            "deterministic generator code/version",
            "analysis rule",
        ],
        "sampled_objects_per_episode": ["acquisition seed material", "sealed-future seed material"],
        "shared_stochastic_ancestor_count": shared,
        "no_cross_episode_shared_stochastic_ancestor": False,
        "listed_seed_fields_disjoint": shared == 0,
        "complete_ancestry_status": "UNTRACED_LEGACY_FIXTURE",
        "episode_ancestor_digests": [list(group) for group in groups],
    }


def audit_p_stochastic_ancestry(episodes: Sequence[PIndependentEpisode]) -> dict[str, Any]:
    if not episodes:
        raise ValueError("P stochastic-ancestry audit requires episodes")
    groups = [
        tuple(
            [f"acquisition:{episode.acquisition_seed_digest}"]
            + [f"future:{seed}" for seed in episode.future_seed_digests]
        )
        for episode in episodes
    ]
    shared = _shared_ancestor_count(groups)
    return {
        "inferential_unit": "acquisition_restart_future_episode",
        "earliest_stochastic_ancestor_rule": (
            "each acquisition seed and each nested future seed is episode-specific; "
            "the retained object is a within-episode descendant and the only state crossing restart"
        ),
        "fixed_protocol_objects": [
            "24-policy candidate space",
            "four abstract context classes",
            "acquisition algorithm/version",
            "restart environment template",
            "analysis rule",
        ],
        "sampled_objects_per_episode": [
            "acquisition seed material",
            "acquired policy/retained object",
            "four future seed materials",
        ],
        "shared_stochastic_ancestor_count": shared,
        "no_cross_episode_shared_stochastic_ancestor": False,
        "listed_seed_fields_disjoint": shared == 0,
        "complete_ancestry_status": "UNTRACED_LEGACY_FIXTURE",
        "episode_ancestor_digests": [list(group) for group in groups],
    }


def _canonical_pair(pair: tuple[str, str]) -> tuple[str, str]:
    return tuple(sorted((str(pair[0]), str(pair[1]))))  # type: ignore[return-value]


def audit_g_exchangeability_design(records: Sequence[GRecord]) -> dict[str, Any]:
    if not records:
        raise ValueError("G exchangeability audit requires records")
    by_world: dict[int, list[GRecord]] = defaultdict(list)
    for record in records:
        by_world[int(record.world_index)].append(record)

    expected_doses = (0.0, 0.1, 0.25, 0.5, 1.0)
    complete_schedule = all(
        tuple(sorted(record.dose for record in world_records)) == expected_doses
        for world_records in by_world.values()
    )
    contiguous_worlds = tuple(sorted(by_world)) == tuple(range(len(by_world)))
    matched_pairs = all(
        record.relevant_corruption_count == record.irrelevant_corruption_count
        and record.relevant_corruption_magnitude == record.irrelevant_corruption_magnitude
        and len(record.relevant_corrupted_cells) == record.relevant_corruption_count
        and len(record.irrelevant_corrupted_cells) == record.irrelevant_corruption_count
        and len(record.matched_corruption_pairs) == record.relevant_corruption_count
        and tuple(pair[0] for pair in record.matched_corruption_pairs)
        == record.relevant_corrupted_cells
        and tuple(pair[1] for pair in record.matched_corruption_pairs)
        == record.irrelevant_corrupted_cells
        for record in records
    )
    preclassified = all(record.relevance_computed_before_corruption for record in records)
    pair_selection_swap_invariant = matched_pairs and all(
        tuple(_canonical_pair(pair) for pair in record.matched_corruption_pairs)
        == tuple(_canonical_pair((pair[1], pair[0])) for pair in record.matched_corruption_pairs)
        for record in records
    )

    # A complete matched schedule is necessary bookkeeping, not evidence of
    # sampling/stopping invariance or the actual joint outcome law. The previous
    # f(x),f(x) construction proved only a tautology about an invented null.
    selection_fixed = False
    generation_label_symmetric_under_null = False
    no_adaptive_stopping = False
    joint_exchangeable = False
    sharp_null_swap_invariance = False
    return {
        "null_model": "UNBOUND",
        "design_argument_status": "ACTUAL_OUTCOME_LAW_NOT_ESTABLISHED",
        "observed_schedule_complete": complete_schedule and contiguous_worlds,
        "bookkeeping_checks_pass": matched_pairs and preclassified and complete_schedule,
        "null_hypothesis": (
            "conditional on the fixed matched-pair construction and all non-label inputs, "
            "the complete within-world outcome vector is unchanged by one joint exchange "
            "of relevant/irrelevant labels across every nonzero dose"
        ),
        "randomization_unit": "world",
        "joint_exchange_scope": "all_nonzero_doses_within_world",
        "selection_fixed_before_outcomes": selection_fixed,
        "matched_pair_selection_label_swap_invariant": pair_selection_swap_invariant,
        "sharp_null_vector_swap_invariance": sharp_null_swap_invariance,
        "generation_label_symmetric_under_null": generation_label_symmetric_under_null,
        "no_adaptive_stopping": no_adaptive_stopping,
        "matched_pair_construction": matched_pairs,
        "joint_world_vector_exchangeability_under_null": joint_exchangeable,
        "world_count": len(by_world),
        "complete_fixed_dose_schedule": complete_schedule,
        "scope_note": (
            "Record checks do not establish generation, selection, stopping, or outcome-law exchangeability. "
            "A code-bound design argument is still required; no duplicated synthetic null is accepted."
        ),
    }


def _ceil_fraction(value: Fraction) -> int:
    return (value.numerator + value.denominator - 1) // value.denominator


def _complete_component_power_at_floor(
    *,
    n: int,
    discordance_rate: Fraction,
    true_effect: Fraction,
    alpha: Fraction,
    observed_effect_floor: Fraction,
) -> float:
    """Exact power for significance AND the observed effect-floor gate.

    This uses the same paired-Bernoulli model as the historical component power,
    but additionally requires the observed paired difference itself to meet the
    frozen PASS floor. At a true effect exactly equal to that floor, this event
    remains near 1/2 even as n grows; increasing n alone cannot make it an 80%
    complete-PASS planning alternative.
    """

    if n <= 0:
        raise ValueError("n must be positive")
    q = Fraction(discordance_rate)
    delta = Fraction(true_effect)
    floor = Fraction(observed_effect_floor)
    if q <= 0 or q > 1 or delta <= 0 or delta > q:
        raise ValueError("require 0 < true effect <= discordance rate <= 1")
    p10 = (q + delta) / 2
    p01 = (q - delta) / 2
    win_given_discordant = float(p10 / q)
    total = 0.0
    for discordant in range(n + 1):
        pd = _binomial_probability(n, discordant, float(q))
        if pd == 0.0:
            continue
        critical = _null_critical_wins(discordant, float(alpha))
        if critical is None:
            continue
        # (wins - losses)/n = (2*wins-discordant)/n >= floor.
        floor_wins = _ceil_fraction((Fraction(discordant, 1) + n * floor) / 2)
        minimum_wins = max(critical, floor_wins)
        if minimum_wins <= discordant:
            total += pd * _binomial_upper_tail(
                discordant,
                minimum_wins,
                win_given_discordant,
            )
    return min(1.0, max(0.0, total))


def _minimum_complete_component_power(
    *, n: int, effect: float, discordance_rates: Sequence[float], alpha: float
) -> tuple[float, list[dict[str, float]]]:
    points: list[dict[str, float]] = []
    for q in discordance_rates:
        power = _complete_component_power_at_floor(
            n=n,
            discordance_rate=Fraction(str(q)),
            true_effect=Fraction(str(effect)),
            alpha=Fraction(str(alpha)),
            observed_effect_floor=Fraction(str(effect)),
        )
        points.append({"discordance_rate": float(q), "power": power})
    return min(point["power"] for point in points), points


def freeze_power_review(plan: ABGPAnalysisPlan) -> dict[str, Any]:
    component = qualification_power_audit(plan)
    arms = {name: dict(value) for name, value in component["arms"].items()}
    qualification = plan.raw["qualification"]
    alpha = float(component["component_alpha"])

    a_min, a_points = _minimum_complete_component_power(
        n=int(plan.arms["A"]["n"]),
        effect=float(plan.arms["A"]["effect_floor"]),
        discordance_rates=[float(x) for x in qualification["paired_nuisance_envelope"]["A"]["discordance_rates"]],
        alpha=alpha,
    )
    b_min, b_points = _minimum_complete_component_power(
        n=int(plan.arms["B"]["worlds_per_direction"]),
        effect=float(plan.arms["B"]["effect_floor_each_control"]),
        discordance_rates=[float(x) for x in qualification["paired_nuisance_envelope"]["B"]["discordance_rates"]],
        alpha=alpha,
    )
    p_min, p_points = _minimum_complete_component_power(
        n=int(plan.arms["P"]["n"]),
        effect=float(plan.arms["P"]["effect_floor"]),
        discordance_rates=[float(x) for x in qualification["paired_nuisance_envelope"]["P"]["discordance_rates"]],
        alpha=alpha,
    )

    arms["A"].update(
        {
            "complete_pass_power_status": "PENDING_PLANNING_ALTERNATIVE_ABOVE_OBSERVED_FLOOR",
            "current_power_scope": "single paired significance component over declared discordance envelope",
            "complete_pass_components": 3,
            "complete_component_power_at_declared_true_effect_floor": a_min,
            "complete_component_power_points_at_floor": a_points,
            "dependence_agnostic_three_component_lower_bound_at_floor": max(0.0, 1.0 - 3 * (1.0 - a_min)),
        }
    )
    arms["B"].update(
        {
            "complete_pass_power_status": "PENDING_PLANNING_ALTERNATIVE_ABOVE_EFFECT_AND_90_PERCENT_GATES",
            "current_power_scope": "36 component significance rejections via dependence-agnostic union bound",
            "complete_pass_components": 36,
            "agreement_gate": 0.90,
            "complete_component_power_at_declared_true_effect_floor": b_min,
            "complete_component_power_points_at_floor": b_points,
            "dependence_agnostic_36_component_lower_bound_at_floor": max(0.0, 1.0 - 36 * (1.0 - b_min)),
        }
    )
    arms["P"].update(
        {
            "complete_pass_power_status": "PENDING_PLANNING_ALTERNATIVE_ABOVE_OBSERVED_FLOOR_AND_DELETION_GATE",
            "current_power_scope": "single paired significance component over declared discordance envelope",
            "complete_pass_components": 7,
            "complete_component_power_at_declared_true_effect_floor": p_min,
            "complete_component_power_points_at_floor": p_points,
            "dependence_agnostic_seven_component_lower_bound_at_floor": max(0.0, 1.0 - 7 * (1.0 - p_min)),
        }
    )
    arms["G"].update(
        {
            "complete_pass_power_status": "PENDING_PLANNING_ALTERNATIVE_ABOVE_OBSERVED_MAX_DOSE_FLOOR",
            "current_power_scope": "max-dose conservative significance calculation; lower-dose signal fixed to zero",
        }
    )
    return {
        "alpha_provenance": "four_arm_familywise_holm_worst_case_component_alpha_not_b_iut_multiplicity",
        "familywise_alpha": float(plan.familywise_alpha),
        "component_alpha_used_by_historical_audit": alpha,
        "historical_component_power_qualified": bool(component["qualified"]),
        "complete_pass_power_qualified": False,
        "arms": arms,
        "review_status": "POWER_MODEL_INCOMPLETE_FOR_FULL_ARM_PASS",
        "resolution_required": "jointly_freeze_a_planning_alternative_strictly_above_each_observed_pass_floor",
        "why_complete_power_is_not_identified": (
            "The PASS rules require the observed treatment-control difference itself to meet the same effect floor used "
            "as the historical true-effect planning alternative. Exact calculation shows that at a true effect equal to "
            "that observed floor, a component passes significance plus the effect-floor gate only about half the time. "
            "Increasing n alone does not raise this complete component event to 0.80. B also has the 0.90 pooled "
            "agreement gate, and P has deletion/reacquisition gates. A complete-arm power target therefore requires "
            "a jointly frozen planning alternative strictly above the observed PASS floor (and, for B/P, the relevant "
            "gate-level alternative/dependence specification)."
        ),
    }
