"""Narrow source-pinned PRISM IMDP adapter for MathGraph Crystal.

The adapter intentionally preserves one consequence family only:
interval-probabilistic reachability. Reward semantics are outside the contract
and therefore remain UNKNOWN rather than being approximated or inferred.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, getcontext
import re
from typing import Iterable

from mathgraph.crystal import (
    AdapterContract,
    IntervalDistributionEffect,
    IntervalOutcome,
    SemanticObject,
    canonical_bytes,
)


PRISM_REACHABILITY_INTERFACE = "probability.reachability.interval@1"
PRISM_REWARD_INTERFACE = "reward.expected-time@1"


@dataclass(frozen=True)
class IntervalAction:
    source: str
    action: str
    effect: IntervalDistributionEffect


@dataclass(frozen=True)
class AdaptedIntervalMDP:
    states: tuple[str, ...]
    actions: tuple[IntervalAction, ...]
    labels: tuple[tuple[str, tuple[str, ...]], ...]
    source_ref: str

    def actions_from(self, state: str) -> tuple[IntervalAction, ...]:
        return tuple(action for action in self.actions if action.source == state)

    def states_for_label(self, label: str) -> tuple[str, ...]:
        for candidate, states in self.labels:
            if candidate == label:
                return states
        raise KeyError(label)

    @property
    def semantic_object(self) -> SemanticObject:
        payload = canonical_bytes(
            {
                "states": list(self.states),
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
                    for action in self.actions
                ],
                "labels": [
                    {"name": name, "states": list(states)}
                    for name, states in self.labels
                ],
                "source_ref": self.source_ref,
            }
        )
        return SemanticObject(
            type_id="mathgraph.interval-mdp",
            contract_version=1,
            payload=payload,
            interfaces=(PRISM_REACHABILITY_INTERFACE,),
        )


@dataclass(frozen=True)
class PrismAdaptation:
    model: AdaptedIntervalMDP
    contract: AdapterContract

    @property
    def semantic_object(self) -> SemanticObject:
        return self.model.semantic_object


def prism_interval_adapter_contract(
    *,
    source_ref: str,
    evidence_refs: tuple[str, ...] = (),
) -> AdapterContract:
    return AdapterContract(
        adapter_id="prism.imdp-to-mathgraph.interval-mdp",
        contract_version=1,
        source_space=f"prism.imdp:{source_ref}",
        target_space="mathgraph.interval-mdp@1",
        preserves_interfaces=(PRISM_REACHABILITY_INTERFACE,),
        assumption_refs=("assumption:source-pin-verified",),
        evidence_refs=evidence_refs,
    )


def _eval_atom(expr: str, env: dict[str, Decimal]) -> Decimal:
    expr = expr.strip()
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", expr):
        return Decimal(expr)
    if expr in env:
        return env[expr]
    match = re.fullmatch(r"1-([A-Za-z_][A-Za-z0-9_]*)", expr)
    if match and match.group(1) in env:
        return Decimal(1) - env[match.group(1)]
    raise ValueError(f"unsupported probability expression: {expr}")


def _eval_constant(expr: str, env: dict[str, Decimal]) -> Decimal:
    expr = expr.strip()
    direct = re.fullmatch(
        r"([0-9]+(?:\.[0-9]+)?)([+-])([A-Za-z_][A-Za-z0-9_]*)",
        expr,
    )
    if direct and direct.group(3) in env:
        base = Decimal(direct.group(1))
        offset = env[direct.group(3)]
        return base + offset if direct.group(2) == "+" else base - offset
    return _eval_atom(expr, env)


def _parse_probability(
    token: str,
    env: dict[str, Decimal],
) -> tuple[str, str]:
    token = token.strip()
    if token.startswith("[") and token.endswith("]"):
        pieces = token[1:-1].split(",")
        if len(pieces) != 2:
            raise ValueError(f"invalid interval probability: {token}")
        lower = _eval_atom(pieces[0], env)
        upper = _eval_atom(pieces[1], env)
    else:
        lower = upper = _eval_atom(token, env)
    return format(lower, "f"), format(upper, "f")


def adapt_prism_imdp(
    source: str,
    *,
    delta: str,
    source_ref: str,
) -> PrismAdaptation:
    """Lower the supported finite one-variable PRISM interval-MDP subset.

    Unsupported syntax fails closed. This is deliberately not a general PRISM
    parser; the preservation claim is tied to the exact source-pinned subset
    qualified by the hosted gate.
    """

    text = source.replace("\r\n", "\n")
    if not re.search(r"(?m)^mdp\s*$", text):
        raise ValueError("adapter requires PRISM mdp source")

    state_decl = re.search(r"(?m)^s:\[0\.\.([0-9]+)\];\s*$", text)
    if state_decl is None:
        raise ValueError("adapter requires one finite state variable s")
    max_state = int(state_decl.group(1))
    states = tuple(f"s{i}" for i in range(max_state + 1))

    env: dict[str, Decimal] = {"delta": Decimal(delta)}
    for name, expr in re.findall(
        r"(?m)^const double ([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+);\s*$",
        text,
    ):
        env[name] = _eval_constant(expr, env)

    actions: list[IntervalAction] = []
    command_pattern = re.compile(
        r"(?m)^\[([^\]]+)\]\s+s=([0-9]+)\s*->\s*(.*?);\s*$"
    )
    commands = list(command_pattern.finditer(text))
    if not commands:
        raise ValueError("adapter found no supported PRISM commands")

    for command in commands:
        action_name = command.group(1)
        source_state = int(command.group(2))
        if not 0 <= source_state <= max_state:
            raise ValueError("command source state is out of range")
        outcomes: list[IntervalOutcome] = []
        for branch in re.split(r"\s+\+\s+", command.group(3).strip()):
            branch_match = re.fullmatch(
                r"(.+?):\(s'=([0-9]+)\)",
                branch.strip(),
            )
            if branch_match is None:
                raise ValueError(f"unsupported PRISM branch: {branch}")
            target_state = int(branch_match.group(2))
            if not 0 <= target_state <= max_state:
                raise ValueError("command target state is out of range")
            lower, upper = _parse_probability(branch_match.group(1), env)
            outcomes.append(
                IntervalOutcome(f"s{target_state}", lower, upper)
            )
        actions.append(
            IntervalAction(
                source=f"s{source_state}",
                action=action_name,
                effect=IntervalDistributionEffect(tuple(outcomes)),
            )
        )

    labels: list[tuple[str, tuple[str, ...]]] = []
    for name, expr in re.findall(
        r'(?m)^label "([^"]+)"\s*=\s*([^;]+);\s*$',
        text,
    ):
        label_states: list[str] = []
        for term in expr.split("|"):
            match = re.fullmatch(r"s=([0-9]+)", term.strip())
            if match is None:
                raise ValueError(f"unsupported PRISM label expression: {expr}")
            value = int(match.group(1))
            if not 0 <= value <= max_state:
                raise ValueError("label state is out of range")
            label_states.append(f"s{value}")
        labels.append((name, tuple(sorted(set(label_states)))))

    if not labels:
        raise ValueError("adapter found no supported labels")

    model = AdaptedIntervalMDP(
        states=states,
        actions=tuple(actions),
        labels=tuple(sorted(labels)),
        source_ref=source_ref,
    )
    return PrismAdaptation(
        model=model,
        contract=prism_interval_adapter_contract(source_ref=source_ref),
    )


def _effect_expectation(
    effect: IntervalDistributionEffect,
    values: dict[str, Decimal],
    *,
    maximize_uncertainty: bool,
) -> Decimal:
    probabilities: dict[str, Decimal] = {}
    uppers: dict[str, Decimal] = {}
    for outcome in effect.outcomes:
        probabilities[outcome.target] = Decimal(outcome.lower)
        uppers[outcome.target] = Decimal(outcome.upper)

    remaining = Decimal(1) - sum(probabilities.values())
    ordered_targets = sorted(
        probabilities,
        key=lambda target: values[target],
        reverse=maximize_uncertainty,
    )
    for target in ordered_targets:
        capacity = uppers[target] - probabilities[target]
        added = min(remaining, capacity)
        probabilities[target] += added
        remaining -= added
        if remaining == 0:
            break
    if remaining != 0:
        raise ValueError("interval effect admits no normalized distribution")

    return sum(
        probabilities[target] * values[target]
        for target in probabilities
    )


def reachability_state_extrema(
    model: AdaptedIntervalMDP,
    *,
    target_label: str,
    tolerance: str = "1e-24",
    max_iterations: int = 10000,
) -> dict[str, tuple[Decimal, Decimal]]:
    """Compute protected max-min/max-max reachability from every state."""

    getcontext().prec = max(getcontext().prec, 50)
    targets = frozenset(model.states_for_label(target_label))
    if not targets:
        raise ValueError("target label has no states")

    def solve(*, maximize_uncertainty: bool) -> dict[str, Decimal]:
        values = {
            state: Decimal(1) if state in targets else Decimal(0)
            for state in model.states
        }
        tol = Decimal(tolerance)
        for _ in range(max_iterations):
            updated = dict(values)
            for state in model.states:
                if state in targets:
                    updated[state] = Decimal(1)
                    continue
                candidates = [
                    _effect_expectation(
                        action.effect,
                        values,
                        maximize_uncertainty=maximize_uncertainty,
                    )
                    for action in model.actions_from(state)
                ]
                updated[state] = max(candidates) if candidates else Decimal(0)
            if max(
                abs(updated[state] - values[state])
                for state in model.states
            ) <= tol:
                return updated
            values = updated
        raise RuntimeError("reachability iteration did not converge")

    lower = solve(maximize_uncertainty=False)
    upper = solve(maximize_uncertainty=True)
    return {
        state: (lower[state], upper[state])
        for state in model.states
    }


def reachability_extrema(
    model: AdaptedIntervalMDP,
    *,
    target_label: str,
    tolerance: str = "1e-24",
    max_iterations: int = 10000,
) -> tuple[Decimal, Decimal]:
    """Compute max-min and max-max infinite-horizon reachability from s0."""

    values = reachability_state_extrema(
        model,
        target_label=target_label,
        tolerance=tolerance,
        max_iterations=max_iterations,
    )
    return values["s0"]
