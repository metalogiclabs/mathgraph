"""Verified goal-relative capability calculus.

This module is the executable thin waist for strategy-like domains where:

* a state exposes a finite set of certified capabilities;
* applying a capability may have multiple adversarial/nondeterministic outcomes;
* some states are protected goals;
* some states are forbidden failures; and
* capabilities are live only while their external support remains live.

The calculus deliberately separates two fixed points.

1. Forced-goal attractor (least fixed point):
   a state is winning when there exists a live capability whose every outcome
   is already winning. The resulting rank strictly decreases along the chosen
   capability under every adversarial outcome, yielding a finite progress
   certificate.

2. Safety / drawing kernel (greatest fixed point):
   excluding forbidden states, a state is safe when it is an explicitly safe
   terminal or there exists a live capability whose every outcome remains
   safe. Cycles are allowed here; that is exactly why this is a greatest
   fixed point rather than a reachability attractor.

Arbitration:
* if a state is in the forced-goal attractor, choose a rank-decreasing
  capability;
* otherwise, if it is in the safety kernel, choose a safety-preserving
  capability;
* otherwise emit a typed residual.

The module creates no semantic authority. support_refs and evidence_refs are
opaque references to independently qualified evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .crystal import content_id


@dataclass(frozen=True)
class CapabilityStep:
    """One extensional guarded capability transition."""

    source: str
    capability_id: str
    outcomes: tuple[str, ...]
    support_refs: frozenset[str] = frozenset()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("capability source must be non-empty")
        if not self.capability_id:
            raise ValueError("capability id must be non-empty")
        if not self.outcomes:
            raise ValueError("capability must expose at least one outcome")
        if any(not outcome for outcome in self.outcomes):
            raise ValueError("capability outcomes must be non-empty state ids")
        object.__setattr__(self, "outcomes", tuple(sorted(set(self.outcomes))))
        object.__setattr__(
            self, "evidence_refs", tuple(sorted(set(self.evidence_refs)))
        )

    @property
    def id(self) -> str:
        return content_id(self, prefix="capability-step")

    def is_live(self, live_supports: set[str] | frozenset[str]) -> bool:
        return self.support_refs.issubset(live_supports)


@dataclass(frozen=True)
class StrategyDecision:
    state: str
    mode: str
    capability_id: str | None
    outcomes: tuple[str, ...]
    rank_before: int | None = None
    rank_after_max: int | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrategyResidual:
    state: str
    reason: str
    live_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class StrategyCalculusResult:
    forced_goal_states: frozenset[str]
    safety_states: frozenset[str]
    goal_rank: tuple[tuple[str, int], ...]
    decisions: tuple[StrategyDecision, ...]
    residuals: tuple[StrategyResidual, ...]

    @property
    def id(self) -> str:
        return content_id(self, prefix="strategy-calculus")

    @property
    def rank_map(self) -> dict[str, int]:
        return dict(self.goal_rank)

    @property
    def decision_map(self) -> dict[str, StrategyDecision]:
        return {decision.state: decision for decision in self.decisions}


def _validate_world(
    states: set[str],
    steps: Sequence[CapabilityStep],
    goals: set[str],
    forbidden: set[str],
    safe_terminals: set[str],
) -> None:
    if goals - states:
        raise ValueError(f"goals outside state space: {sorted(goals - states)}")
    if forbidden - states:
        raise ValueError(
            f"forbidden states outside state space: {sorted(forbidden - states)}"
        )
    if safe_terminals - states:
        raise ValueError(
            f"safe terminals outside state space: {sorted(safe_terminals - states)}"
        )
    if goals & forbidden:
        raise ValueError("goal states cannot also be forbidden")
    for step in steps:
        if step.source not in states:
            raise ValueError(f"capability source outside state space: {step.source}")
        outside = set(step.outcomes) - states
        if outside:
            raise ValueError(
                f"capability outcomes outside state space: {sorted(outside)}"
            )


def _live_by_source(
    states: set[str],
    steps: Sequence[CapabilityStep],
    live_supports: set[str] | frozenset[str],
) -> dict[str, tuple[CapabilityStep, ...]]:
    grouped: dict[str, list[CapabilityStep]] = {state: [] for state in states}
    for step in steps:
        if step.is_live(live_supports):
            grouped[step.source].append(step)
    return {
        state: tuple(
            sorted(
                grouped[state],
                key=lambda step: (step.capability_id, step.outcomes, step.id),
            )
        )
        for state in states
    }


def forced_goal_attractor(
    states: Iterable[str],
    goals: Iterable[str],
    steps: Sequence[CapabilityStep],
    live_supports: set[str] | frozenset[str],
) -> tuple[frozenset[str], dict[str, int], dict[str, CapabilityStep]]:
    """Least fixed point for forced finite progress to a protected goal."""

    state_set = set(states)
    goal_set = set(goals)
    _validate_world(state_set, steps, goal_set, set(), set())

    live = _live_by_source(state_set, steps, live_supports)
    winning = set(goal_set)
    rank = {state: 0 for state in goal_set}
    witness: dict[str, CapabilityStep] = {}

    while True:
        additions: list[tuple[int, str, CapabilityStep]] = []
        for state in sorted(state_set - winning):
            candidates: list[tuple[int, str, CapabilityStep]] = []
            for step in live[state]:
                if all(outcome in winning for outcome in step.outcomes):
                    worst = max(rank[outcome] for outcome in step.outcomes)
                    candidates.append((worst + 1, step.capability_id, step))
            if candidates:
                additions.append(
                    min(candidates, key=lambda item: (item[0], item[1], item[2].id))
                )

        if not additions:
            break

        for new_rank, state, step in additions:
            winning.add(state)
            rank[state] = new_rank
            witness[state] = step

    return frozenset(winning), rank, witness


def safety_kernel(
    states: Iterable[str],
    forbidden: Iterable[str],
    safe_terminals: Iterable[str],
    steps: Sequence[CapabilityStep],
    live_supports: set[str] | frozenset[str],
) -> tuple[frozenset[str], dict[str, CapabilityStep]]:
    """Greatest fixed point for indefinite protected non-failure."""

    state_set = set(states)
    forbidden_set = set(forbidden)
    safe_terminal_set = set(safe_terminals)
    _validate_world(
        state_set,
        steps,
        set(),
        forbidden_set,
        safe_terminal_set,
    )
    live = _live_by_source(state_set, steps, live_supports)

    kernel = state_set - forbidden_set
    while True:
        remove: set[str] = set()
        for state in sorted(kernel):
            if state in safe_terminal_set:
                continue
            has_safe_step = any(
                all(outcome in kernel for outcome in step.outcomes)
                for step in live[state]
            )
            if not has_safe_step:
                remove.add(state)
        if not remove:
            break
        kernel -= remove

    witness: dict[str, CapabilityStep] = {}
    for state in sorted(kernel):
        if state in safe_terminal_set:
            continue
        candidates = [
            step
            for step in live[state]
            if all(outcome in kernel for outcome in step.outcomes)
        ]
        if candidates:
            witness[state] = min(
                candidates,
                key=lambda step: (step.capability_id, step.outcomes, step.id),
            )
    return frozenset(kernel), witness


def compile_strategy_calculus(
    *,
    states: Iterable[str],
    goals: Iterable[str],
    forbidden: Iterable[str],
    safe_terminals: Iterable[str],
    steps: Sequence[CapabilityStep],
    live_supports: set[str] | frozenset[str],
) -> StrategyCalculusResult:
    """Compile goal progress, safety arbitration and typed residuals."""

    state_set = set(states)
    goal_set = set(goals)
    forbidden_set = set(forbidden)
    safe_terminal_set = set(safe_terminals)
    _validate_world(
        state_set,
        steps,
        goal_set,
        forbidden_set,
        safe_terminal_set,
    )

    live = _live_by_source(state_set, steps, live_supports)
    winning, rank, goal_witness = forced_goal_attractor(
        state_set, goal_set, steps, live_supports
    )
    safe, safety_witness = safety_kernel(
        state_set, forbidden_set, safe_terminal_set | goal_set, steps, live_supports
    )

    decisions: list[StrategyDecision] = []
    residuals: list[StrategyResidual] = []

    for state in sorted(state_set):
        if state in goal_set:
            decisions.append(
                StrategyDecision(
                    state=state,
                    mode="goal_terminal",
                    capability_id=None,
                    outcomes=(),
                    rank_before=0,
                    rank_after_max=0,
                )
            )
            continue

        if state in winning:
            step = goal_witness[state]
            after = max(rank[outcome] for outcome in step.outcomes)
            before = rank[state]
            if not after < before:
                raise AssertionError("goal-progress witness does not decrease rank")
            decisions.append(
                StrategyDecision(
                    state=state,
                    mode="goal_progress",
                    capability_id=step.capability_id,
                    outcomes=step.outcomes,
                    rank_before=before,
                    rank_after_max=after,
                    evidence_refs=step.evidence_refs,
                )
            )
            continue

        if state in safe:
            if state in safe_terminal_set:
                decisions.append(
                    StrategyDecision(
                        state=state,
                        mode="safe_terminal",
                        capability_id=None,
                        outcomes=(),
                    )
                )
                continue
            step = safety_witness[state]
            if not all(outcome in safe for outcome in step.outcomes):
                raise AssertionError("safety witness exits safety kernel")
            decisions.append(
                StrategyDecision(
                    state=state,
                    mode="safety",
                    capability_id=step.capability_id,
                    outcomes=step.outcomes,
                    evidence_refs=step.evidence_refs,
                )
            )
            continue

        residuals.append(
            StrategyResidual(
                state=state,
                reason=(
                    "no_live_capability_forced_to_goal_or_preserving_safety"
                    if state not in forbidden_set
                    else "forbidden_state"
                ),
                live_capabilities=tuple(
                    sorted(step.capability_id for step in live[state])
                ),
            )
        )

    return StrategyCalculusResult(
        forced_goal_states=winning,
        safety_states=safe,
        goal_rank=tuple(sorted(rank.items())),
        decisions=tuple(decisions),
        residuals=tuple(residuals),
    )


def verify_strategy_calculus(
    result: StrategyCalculusResult,
    *,
    states: Iterable[str],
    goals: Iterable[str],
    forbidden: Iterable[str],
    safe_terminals: Iterable[str],
    steps: Sequence[CapabilityStep],
    live_supports: set[str] | frozenset[str],
) -> None:
    """Independently re-check every compiled calculus invariant."""

    expected = compile_strategy_calculus(
        states=states,
        goals=goals,
        forbidden=forbidden,
        safe_terminals=safe_terminals,
        steps=steps,
        live_supports=live_supports,
    )
    if result != expected:
        raise AssertionError("strategy calculus object failed deterministic replay")

    ranks = result.rank_map
    winning = result.forced_goal_states
    safe = result.safety_states
    goals_set = set(goals)
    forbidden_set = set(forbidden)

    for decision in result.decisions:
        if decision.mode == "goal_progress":
            if decision.state not in winning:
                raise AssertionError("goal-progress decision outside attractor")
            if not decision.outcomes:
                raise AssertionError("goal-progress decision has no outcomes")
            if any(outcome not in winning for outcome in decision.outcomes):
                raise AssertionError("goal-progress decision exits attractor")
            if decision.rank_before != ranks[decision.state]:
                raise AssertionError("incorrect rank_before")
            if decision.rank_after_max != max(ranks[o] for o in decision.outcomes):
                raise AssertionError("incorrect rank_after_max")
            if not decision.rank_after_max < decision.rank_before:
                raise AssertionError("non-decreasing goal rank")
        elif decision.mode == "safety":
            if decision.state not in safe or decision.state in forbidden_set:
                raise AssertionError("invalid safety decision source")
            if any(outcome not in safe for outcome in decision.outcomes):
                raise AssertionError("safety decision exits kernel")
        elif decision.mode == "goal_terminal":
            if decision.state not in goals_set:
                raise AssertionError("goal terminal not a goal")
