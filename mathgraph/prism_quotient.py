"""Consequence-relative quotienting for finite MathGraph interval MDPs.

This module does not infer a safe quotient.  It applies an explicit state map
and leaves preservation as an AdapterContract qualification obligation.  The
first qualified use is the source-pinned PRISM robot reachability boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from mathgraph.crystal import (
    AdapterContract,
    IntervalDistributionEffect,
    IntervalOutcome,
    SemanticObject,
    canonical_bytes,
)
from mathgraph.prism_adapter import (
    AdaptedIntervalMDP,
    IntervalAction,
    PRISM_REACHABILITY_INTERFACE,
)


STATE_IDENTITY_INTERFACE = "state.identity@1"


@dataclass(frozen=True)
class QuotientAdaptation:
    model: AdaptedIntervalMDP
    contract: AdapterContract
    state_map: tuple[tuple[str, str], ...]

    @property
    def semantic_object(self) -> SemanticObject:
        payload = canonical_bytes(
            {
                "states": list(self.model.states),
                "actions": [
                    {
                        "source": action.source,
                        "action": action.action,
                        "outcomes": [
                            {
                                "target": outcome.target,
                                "lower": outcome.lower,
                                "upper": outcome.upper,
                            }
                            for outcome in action.effect.outcomes
                        ],
                    }
                    for action in self.model.actions
                ],
                "labels": [
                    {"name": name, "states": list(states)}
                    for name, states in self.model.labels
                ],
                "source_ref": self.model.source_ref,
                "state_map": [
                    {"source": source, "target": target}
                    for source, target in self.state_map
                ],
            }
        )
        return SemanticObject(
            type_id="mathgraph.interval-mdp.quotient",
            contract_version=1,
            payload=payload,
            interfaces=(PRISM_REACHABILITY_INTERFACE,),
        )


def interval_mdp_quotient_contract(
    *,
    source_space: str = "mathgraph.interval-mdp@1",
    target_space: str = "mathgraph.interval-mdp.quotient@1",
    partition_id: str,
    evidence_refs: tuple[str, ...] = (),
) -> AdapterContract:
    return AdapterContract(
        adapter_id=f"mathgraph.interval-mdp.reachability-quotient:{partition_id}",
        contract_version=1,
        source_space=source_space,
        target_space=target_space,
        preserves_interfaces=(PRISM_REACHABILITY_INTERFACE,),
        assumption_refs=(
            "assumption:partition-qualified-on-protected-reachability",
        ),
        evidence_refs=evidence_refs,
    )


def _normalized_group_interval(
    *,
    group_lowers: list[str],
    group_uppers: list[str],
    all_lowers: list[str],
    all_uppers: list[str],
) -> tuple[str, str]:
    """Project normalized interval probabilities through a target quotient.

    Endpoint sums alone are not sound enough: source outcomes are coupled by
    the global normalization constraint. The exact marginal envelope implied
    by independent per-outcome bounds plus sum(p)=1 is

      lower = max(sum(group lows), 1 - sum(other uppers))
      upper = min(sum(group uppers), 1 - sum(other lowers)).
    """

    one = Decimal(1)
    group_low = sum((Decimal(value) for value in group_lowers), Decimal(0))
    group_high = sum((Decimal(value) for value in group_uppers), Decimal(0))
    all_low = sum((Decimal(value) for value in all_lowers), Decimal(0))
    all_high = sum((Decimal(value) for value in all_uppers), Decimal(0))
    other_low = all_low - group_low
    other_high = all_high - group_high
    lower = max(group_low, one - other_high)
    upper = min(group_high, one - other_low)
    if lower < 0:
        lower = Decimal(0)
    if upper > 1:
        upper = Decimal(1)
    if lower > upper:
        raise ValueError("quotient projection produced infeasible interval")
    return format(lower, "f"), format(upper, "f")


def quotient_interval_mdp(
    model: AdaptedIntervalMDP,
    state_map: Mapping[str, str],
    *,
    partition_id: str,
) -> QuotientAdaptation:
    """Apply an explicit finite quotient to an interval MDP.

    All original states must be mapped. Outcomes that land in the same quotient
    state are aggregated by summing their lower and upper probability bounds.
    Duplicate quotient actions created by merging equivalent source states are
    removed canonically.
    """

    missing = sorted(set(model.states) - set(state_map))
    extra = sorted(set(state_map) - set(model.states))
    if missing:
        raise ValueError(f"quotient state map missing states: {missing}")
    if extra:
        raise ValueError(f"quotient state map has unknown states: {extra}")
    if any(not target for target in state_map.values()):
        raise ValueError("quotient target states must be non-empty")

    canonical_map = tuple(sorted((state, state_map[state]) for state in model.states))
    quotient_states = tuple(sorted(set(state_map.values())))

    action_keys: set[
        tuple[str, str, tuple[tuple[str, str, str], ...]]
    ] = set()
    quotient_actions: list[IntervalAction] = []

    for action in model.actions:
        by_target: dict[str, dict[str, list[str]]] = {}
        for outcome in action.effect.outcomes:
            target = state_map[outcome.target]
            bucket = by_target.setdefault(target, {"lower": [], "upper": []})
            bucket["lower"].append(outcome.lower)
            bucket["upper"].append(outcome.upper)

        all_lowers = [
            outcome.lower for outcome in action.effect.outcomes
        ]
        all_uppers = [
            outcome.upper for outcome in action.effect.outcomes
        ]
        projected = []
        for target in sorted(by_target):
            lower, upper = _normalized_group_interval(
                group_lowers=by_target[target]["lower"],
                group_uppers=by_target[target]["upper"],
                all_lowers=all_lowers,
                all_uppers=all_uppers,
            )
            projected.append(IntervalOutcome(target, lower, upper))
        outcomes = tuple(projected)
        quotient_action = IntervalAction(
            source=state_map[action.source],
            action=action.action,
            effect=IntervalDistributionEffect(outcomes),
        )
        key = (
            quotient_action.source,
            quotient_action.action,
            tuple(
                (outcome.target, outcome.lower, outcome.upper)
                for outcome in quotient_action.effect.outcomes
            ),
        )
        if key not in action_keys:
            action_keys.add(key)
            quotient_actions.append(quotient_action)

    quotient_labels = tuple(
        sorted(
            (
                label,
                tuple(sorted({state_map[state] for state in states})),
            )
            for label, states in model.labels
        )
    )

    quotient_model = AdaptedIntervalMDP(
        states=quotient_states,
        actions=tuple(
            sorted(
                quotient_actions,
                key=lambda action: (
                    action.source,
                    action.action,
                    tuple(
                        (outcome.target, outcome.lower, outcome.upper)
                        for outcome in action.effect.outcomes
                    ),
                ),
            )
        ),
        labels=quotient_labels,
        source_ref=f"{model.source_ref}#quotient={partition_id}",
    )
    return QuotientAdaptation(
        model=quotient_model,
        contract=interval_mdp_quotient_contract(partition_id=partition_id),
        state_map=canonical_map,
    )
