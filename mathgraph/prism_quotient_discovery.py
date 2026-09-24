"""Exhaustive finite discovery of consequence-relative interval-MDP quotients.

This is intentionally a bounded discovery procedure, not a universal
minimizer.  For a small finite model it enumerates target-respecting state
partitions, constructs each typed quotient, and retains only those whose
protected reachability signature agrees with the unquotiented model from every
source state.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from mathgraph.crystal import content_id
from mathgraph.prism_adapter import (
    AdaptedIntervalMDP,
    reachability_state_extrema,
)
from mathgraph.prism_quotient import (
    QuotientAdaptation,
    quotient_interval_mdp,
)


Partition = tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class QuotientDiscoveryResult:
    partition: Partition
    state_map: tuple[tuple[str, str], ...]
    quotient: QuotientAdaptation
    tested_partitions: int
    accepted_partitions: int
    coarser_partitions_rejected: int
    coarsest_partitions: tuple[Partition, ...]
    reference_values: tuple[tuple[str, str, str], ...]


def _set_partitions(items: tuple[str, ...]) -> tuple[Partition, ...]:
    """Enumerate canonical set partitions using restricted-growth strings."""

    if not items:
        return ((),)

    assignments = [0] * len(items)
    out: list[Partition] = []

    def visit(index: int, max_label: int) -> None:
        if index == len(items):
            blocks: dict[int, list[str]] = {}
            for item, label in zip(items, assignments):
                blocks.setdefault(label, []).append(item)
            partition = tuple(
                sorted(tuple(sorted(block)) for block in blocks.values())
            )
            out.append(partition)
            return

        for label in range(max_label + 2):
            assignments[index] = label
            visit(index + 1, max(max_label, label))

    assignments[0] = 0

    def visit_rest(index: int, max_label: int) -> None:
        if index == len(items):
            blocks: dict[int, list[str]] = {}
            for item, label in zip(items, assignments):
                blocks.setdefault(label, []).append(item)
            out.append(
                tuple(sorted(tuple(sorted(block)) for block in blocks.values()))
            )
            return
        for label in range(max_label + 2):
            assignments[index] = label
            visit_rest(index + 1, max(max_label, label))

    visit_rest(1, 0)
    return tuple(sorted(set(out), key=lambda p: (len(p), p)))


def _respects_target_membership(
    partition: Partition,
    targets: frozenset[str],
) -> bool:
    for block in partition:
        membership = {state in targets for state in block}
        if len(membership) != 1:
            return False
    return True


def _state_map(partition: Partition) -> dict[str, str]:
    ordered = tuple(sorted(partition))
    mapping: dict[str, str] = {}
    for index, block in enumerate(ordered):
        name = f"q{index}"
        for state in block:
            mapping[state] = name
    return mapping


def _values_match(
    original: dict[str, tuple[Decimal, Decimal]],
    reduced: dict[str, tuple[Decimal, Decimal]],
    mapping: dict[str, str],
    tolerance: Decimal,
) -> bool:
    for state, (lower, upper) in original.items():
        q_lower, q_upper = reduced[mapping[state]]
        if abs(lower - q_lower) > tolerance:
            return False
        if abs(upper - q_upper) > tolerance:
            return False
    return True


def discover_coarsest_reachability_quotient(
    model: AdaptedIntervalMDP,
    *,
    target_label: str,
    tolerance: str = "1e-18",
    max_states: int = 8,
) -> QuotientDiscoveryResult:
    """Exhaustively find the coarsest quotient preserving protected reachability.

    Safety criterion:
      * target membership is never mixed with non-target membership;
      * after quotient construction, max-min and max-max reachability from
        every original state agree with the original model within tolerance.

    Ties between equally coarse safe partitions are resolved canonically, while
    all equally coarse partitions are returned for audit.
    """

    if len(model.states) > max_states:
        raise ValueError(
            f"exhaustive quotient discovery limited to {max_states} states"
        )

    targets = frozenset(model.states_for_label(target_label))
    reference = reachability_state_extrema(
        model,
        target_label=target_label,
    )
    tol = Decimal(tolerance)

    partitions = tuple(
        partition
        for partition in _set_partitions(tuple(sorted(model.states)))
        if _respects_target_membership(partition, targets)
    )

    accepted: list[tuple[Partition, QuotientAdaptation]] = []
    for partition in partitions:
        mapping = _state_map(partition)
        partition_id = content_id(
            {
                "target_label": target_label,
                "partition": [list(block) for block in partition],
            },
            prefix="partition",
        )
        candidate = quotient_interval_mdp(
            model,
            mapping,
            partition_id=partition_id,
        )
        candidate_values = reachability_state_extrema(
            candidate.model,
            target_label=target_label,
        )
        if _values_match(reference, candidate_values, mapping, tol):
            accepted.append((partition, candidate))

    if not accepted:
        raise RuntimeError("no protected-reachability-preserving partition found")

    min_classes = min(len(partition) for partition, _ in accepted)
    coarsest = tuple(
        partition
        for partition, _ in accepted
        if len(partition) == min_classes
    )
    coarsest = tuple(sorted(coarsest))
    selected = coarsest[0]
    selected_candidate = next(
        candidate
        for partition, candidate in accepted
        if partition == selected
    )
    mapping = _state_map(selected)

    coarser_rejected = sum(
        1
        for partition in partitions
        if len(partition) < min_classes
    )

    return QuotientDiscoveryResult(
        partition=selected,
        state_map=tuple(sorted(mapping.items())),
        quotient=selected_candidate,
        tested_partitions=len(partitions),
        accepted_partitions=len(accepted),
        coarser_partitions_rejected=coarser_rejected,
        coarsest_partitions=coarsest,
        reference_values=tuple(
            (
                state,
                str(reference[state][0]),
                str(reference[state][1]),
            )
            for state in sorted(reference)
        ),
    )
