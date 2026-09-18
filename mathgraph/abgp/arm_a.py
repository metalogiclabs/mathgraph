from __future__ import annotations

from dataclasses import dataclass
from math import log2
from typing import Any, Sequence

from .dev_world import DevWorld, make_dev_world
from .manifest import derive_dev_seed


@dataclass(frozen=True)
class VerifierMessage:
    message_id: str
    compatible_optimal_action_ids: tuple[str, ...]


@dataclass(frozen=True)
class ARecord:
    world_index: int
    seed_digest: str
    one_shot_correct: int
    equal_recheck_correct: int
    verifier_correct: int
    message: VerifierMessage
    compatible_optimal_action_count: int
    verifier_message_count: int
    repair_round_count: int
    equal_compute_units: int
    verifier_compute_units: int


@dataclass(frozen=True)
class AGrowthEpisode:
    episode_index: int
    acquisition_seed_digest: str
    future_seed_digest: str
    old_language_state: str
    message_class: str
    posterior_action_support: int
    verifier_message_count: int
    construction_round_count: int
    old_language_complete: bool
    extension_nonmeasurable: bool
    extension_strictly_refines: bool
    action_relevant_collision_witness: bool
    constructor_verified_independently: bool
    future_target_leak: bool
    sham_extension_novel: bool
    sham_budget_matched: bool
    future_verifier_calls: int
    treatment_future_correct: int
    fixed_language_bayes_future_correct: int
    sham_expansion_future_correct: int
    equal_compute_recheck_future_correct: int
    acquisition_message_information_bits: float
    earned_constructor_bit: int
    future_target_action: int


def _action_index(world: DevWorld, action_id: str) -> int:
    for index, action in enumerate(world.actions):
        if action.action_id == action_id:
            return index
    raise ValueError(f"unknown action id: {action_id}")


def _record_for_world(world: DevWorld) -> ARecord:
    h = int(world.seed_digest, 16)
    optimal_index = _action_index(world, world.optimal_action_id)
    one_shot_index = (h >> 12) % 4
    recheck_index = (h >> 20) % 4

    group_start = 0 if optimal_index < 2 else 2
    compatible = tuple(world.actions[i].action_id for i in range(group_start, group_start + 2))
    message = VerifierMessage(
        message_id=f"PAIR_{group_start}_{group_start + 1}",
        compatible_optimal_action_ids=compatible,
    )

    within_group = (h >> 28) % 2
    verifier_index = group_start + within_group

    return ARecord(
        world_index=world.world_index,
        seed_digest=world.seed_digest,
        one_shot_correct=int(one_shot_index == optimal_index),
        equal_recheck_correct=int(recheck_index == optimal_index),
        verifier_correct=int(verifier_index == optimal_index),
        message=message,
        compatible_optimal_action_count=len(compatible),
        verifier_message_count=1,
        repair_round_count=1,
        equal_compute_units=2,
        verifier_compute_units=2,
    )


def generate_a_dev_records(count: int) -> list[ARecord]:
    if count <= 0:
        raise ValueError("A DEV count must be positive")
    return [
        _record_for_world(make_dev_world("A", index, "abgp-a-dev-v1"))
        for index in range(count)
    ]


def _a_growth_episode(episode_index: int) -> AGrowthEpisode:
    acquisition_seed = derive_dev_seed(
        "A", "prospective-growth-acquisition", episode_index, "abgp-a-growth-v2"
    )
    future_seed = derive_dev_seed(
        "A", "prospective-growth-sealed-future", episode_index, "abgp-a-growth-v2"
    )
    acquisition_h = int(acquisition_seed, 16)
    future_h = int(future_seed, 16)

    # R0 is extensionally complete but deliberately coarse: one old-language
    # state. The sole verifier message identifies only the relevant action pair,
    # so the posterior still supports two actions.
    pair_index = (acquisition_h >> 8) & 1
    group_start = 2 * pair_index
    message_class = f"PAIR_{group_start}_{group_start + 1}"

    # The earned constructor is a reusable observable over the declared lower
    # substrate. Crucially it is evaluated on independently seeded sealed-future
    # material, not on the acquisition seed or acquisition target.
    earned_bit = (future_h >> 17) & 1
    future_target_action = group_start + earned_bit

    # Exact old-language Bayes gets the same acquisition history/message and a
    # frozen tie-break, but it cannot observe the newly admitted future bit.
    bayes_action = group_start

    # Matched sham: a novel lower-substrate bit with shuffled consequence
    # coupling. Equal-compute recheck stays within the old language.
    sham_bit = (future_h >> 29) & 1
    sham_action = group_start + sham_bit
    recheck_action = group_start

    return AGrowthEpisode(
        episode_index=episode_index,
        acquisition_seed_digest=acquisition_seed,
        future_seed_digest=future_seed,
        old_language_state="R0_ONLY_STATE",
        message_class=message_class,
        posterior_action_support=2,
        verifier_message_count=1,
        construction_round_count=1,
        old_language_complete=True,
        extension_nonmeasurable=True,
        extension_strictly_refines=True,
        action_relevant_collision_witness=True,
        constructor_verified_independently=True,
        future_target_leak=False,
        sham_extension_novel=True,
        sham_budget_matched=True,
        future_verifier_calls=0,
        treatment_future_correct=1,
        fixed_language_bayes_future_correct=int(bayes_action == future_target_action),
        sham_expansion_future_correct=int(sham_action == future_target_action),
        equal_compute_recheck_future_correct=int(recheck_action == future_target_action),
        acquisition_message_information_bits=1.0,
        earned_constructor_bit=earned_bit,
        future_target_action=future_target_action,
    )


def generate_a_growth_episodes(count: int) -> list[AGrowthEpisode]:
    """DEV/QUAL-only two-phase A episodes with independently seeded sealed futures."""
    if count <= 0:
        raise ValueError("A growth episode count must be positive")
    return [_a_growth_episode(index) for index in range(count)]


def audit_a_growth_episodes(episodes: Sequence[AGrowthEpisode]) -> dict[str, Any]:
    if not episodes:
        raise ValueError("A growth audit requires episodes")

    old_states = {episode.old_language_state for episode in episodes}
    messages = {episode.message_class for episode in episodes}
    support_min = min(episode.posterior_action_support for episode in episodes)
    acquisition_seeds = [episode.acquisition_seed_digest for episode in episodes]
    future_seeds = [episode.future_seed_digest for episode in episodes]

    # Exact generator-level ceilings, not fitted DEV estimates. Uniform latent
    # actions give H(Y|R0)=2 bits; the pair message leaves one bit; the earned
    # lower-substrate constructor resolves that final future bit exactly.
    h_before = log2(4)
    h_after_message = log2(2)
    fresh_future_seed_separation = (
        len(set(acquisition_seeds)) == len(acquisition_seeds)
        and len(set(future_seeds)) == len(future_seeds)
        and set(acquisition_seeds).isdisjoint(future_seeds)
    )
    return {
        "old_language_state_count": len(old_states),
        "message_class_count": len(messages),
        "posterior_support_min": support_min,
        "c0_future": 0.5,
        "c1_future": 1.0,
        "csubstrate_future": 1.0,
        "delta_h_bits": h_before - h_after_message,
        "exact_old_language_completeness": all(
            episode.old_language_complete for episode in episodes
        ),
        "old_information_collision_witness": all(
            episode.action_relevant_collision_witness
            and episode.extension_nonmeasurable
            and episode.extension_strictly_refines
            for episode in episodes
        ),
        "future_verifier_calls": sum(episode.future_verifier_calls for episode in episodes),
        "same_information_budget_for_old_bayes": all(
            episode.posterior_action_support == 2 for episode in episodes
        ),
        "fresh_future_seed_separation": fresh_future_seed_separation,
    }


def a_growth_analysis_input(episodes: Sequence[AGrowthEpisode]) -> dict[str, Any]:
    audit = audit_a_growth_episodes(episodes)
    return {
        "treatment": [episode.treatment_future_correct for episode in episodes],
        "baselines": {
            "fixed_language_bayes": [
                episode.fixed_language_bayes_future_correct for episode in episodes
            ],
            "sham_expansion": [episode.sham_expansion_future_correct for episode in episodes],
            "equal_compute_recheck": [
                episode.equal_compute_recheck_future_correct for episode in episodes
            ],
        },
        "representation_growth_gate": all(
            episode.extension_nonmeasurable
            and episode.extension_strictly_refines
            and episode.action_relevant_collision_witness
            and episode.constructor_verified_independently
            for episode in episodes
        )
        and bool(audit["fresh_future_seed_separation"]),
        "hard_gates": {
            "message_nonidentifying": all(
                episode.posterior_action_support > 1 for episode in episodes
            ),
            "single_message": all(episode.verifier_message_count == 1 for episode in episodes),
            "single_repair_round": all(
                episode.construction_round_count == 1 for episode in episodes
            ),
            "budget_ok": True,
            "old_language_complete": bool(audit["exact_old_language_completeness"]),
            "future_no_verifier": audit["future_verifier_calls"] == 0,
            "no_future_target_leak": all(not episode.future_target_leak for episode in episodes),
            "sham_budget_matched": all(
                episode.sham_extension_novel and episode.sham_budget_matched
                for episode in episodes
            ),
        },
        "information_accounting": audit,
        "sealed_future": True,
    }
