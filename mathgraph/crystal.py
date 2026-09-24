"""Minimal executable MathGraph crystal primitives.

This module is intentionally domain-agnostic.  It captures only representation
laws already exercised elsewhere in the programme:

* consequence-relative quotienting and falsification,
* typed hyperedges with conjunctive external support,
* revocation-sensitive reclosure,
* stateful robust viability, and
* action quotienting by induced protected transition.

The module does not create authority.  ``support_refs`` and ``evidence_refs``
are opaque references to independently checked authority/evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence


JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


def _canonical(value: Any) -> JSONValue:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Mapping):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (set, frozenset)):
        return [_canonical(v) for v in sorted(value, key=repr)]
    if isinstance(value, tuple):
        return [_canonical(v) for v in value]
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"not canonically serializable: {type(value)!r}")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def content_id(value: Any, *, prefix: str = "mg") -> str:
    return f"{prefix}:{hashlib.sha256(canonical_bytes(value)).hexdigest()}"


@dataclass(frozen=True)
class Boundary:
    """Scope relative to which distinctions are consequential."""

    objective: str
    context: tuple[tuple[str, str], ...] = ()

    @property
    def id(self) -> str:
        return content_id(self, prefix="boundary")


@dataclass(frozen=True)
class ConsequentialState:
    """Raw state plus the protected signature used for quotient identity."""

    name: str
    protected_signature: tuple[str, ...]
    raw_signature: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResidualPair:
    """Witness that a proposed representation merged a consequential distinction."""

    left: str
    right: str
    representation_key: tuple[str, ...]
    left_target: tuple[str, ...]
    right_target: tuple[str, ...]


@dataclass(frozen=True)
class Hyperedge:
    """A typed transition requiring all support refs conjunctively.

    Multiple Hyperedges with the same ``failure_class`` represent alternative
    repair/capability routes.  Support refs are opaque external authority IDs.
    """

    source: str
    target: str
    failure_class: str
    support_refs: frozenset[str] = frozenset()
    action_class: str | None = None
    evidence_refs: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        return content_id(self, prefix="edge")

    def is_live(self, live_supports: set[str] | frozenset[str]) -> bool:
        return self.support_refs.issubset(live_supports)


@dataclass(frozen=True)
class Residual:
    state: str
    failure_class: str
    reason: str


@dataclass(frozen=True)
class IntervalOutcome:
    """One outcome of an interval-valued transition effect."""

    target: str
    lower: str
    upper: str


@dataclass(frozen=True)
class IntervalDistributionEffect:
    """A normalized interval distribution over consequential targets.

    This is the first quantitative effect admitted by a protected separator.
    Deterministic transitions are the degenerate case with one [1,1] outcome.
    Decimal bounds are stored canonically as strings so content identity does
    not depend on binary floating-point representation.
    """

    outcomes: tuple[IntervalOutcome, ...]

    def __post_init__(self) -> None:
        from decimal import Decimal

        if not self.outcomes:
            raise ValueError("an interval distribution needs at least one outcome")
        lowers = []
        uppers = []
        seen: set[str] = set()
        for outcome in self.outcomes:
            if outcome.target in seen:
                raise ValueError("duplicate target in interval distribution")
            seen.add(outcome.target)
            lo = Decimal(outcome.lower)
            hi = Decimal(outcome.upper)
            if lo < 0 or hi > 1 or lo > hi:
                raise ValueError("invalid probability interval")
            lowers.append(lo)
            uppers.append(hi)
        one = Decimal("1")
        if sum(lowers) > one or sum(uppers) < one:
            raise ValueError("intervals admit no normalized distribution")

    @property
    def id(self) -> str:
        return content_id(self, prefix="effect")

    @property
    def qualitative_support(self) -> tuple[str, ...]:
        return tuple(sorted(outcome.target for outcome in self.outcomes))


def deterministic_effect(target: str) -> IntervalDistributionEffect:
    return IntervalDistributionEffect((IntervalOutcome(target, "1", "1"),))


@dataclass(frozen=True)
class RateOutcome:
    """One target with a non-negative continuous-time transition rate."""

    target: str
    rate: str


@dataclass(frozen=True)
class RateKernelEffect:
    """A CTMC-style rate kernel over consequential targets.

    Unlike a probability distribution, rates are non-negative intensities and
    need not sum to one. Holding times are therefore part of the future
    consequence. This type was admitted only after an external PRISM CTMC
    separator showed identical qualitative support with different rates can
    change a protected time-bounded probability.
    """

    outcomes: tuple[RateOutcome, ...]

    def __post_init__(self) -> None:
        from decimal import Decimal

        if not self.outcomes:
            raise ValueError("a rate kernel needs at least one outcome")
        seen: set[str] = set()
        for outcome in self.outcomes:
            if outcome.target in seen:
                raise ValueError("duplicate target in rate kernel")
            seen.add(outcome.target)
            rate = Decimal(outcome.rate)
            if rate < 0:
                raise ValueError("transition rate must be non-negative")
        if all(Decimal(outcome.rate) == 0 for outcome in self.outcomes):
            raise ValueError("rate kernel must have positive total exit rate")

    @property
    def id(self) -> str:
        return content_id(self, prefix="effect")

    @property
    def qualitative_support(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                outcome.target
                for outcome in self.outcomes
                if outcome.rate != "0"
            )
        )



def quotient_states(states: Sequence[ConsequentialState]) -> dict[tuple[str, ...], tuple[str, ...]]:
    """Collapse raw states exactly by their declared protected signature."""

    classes: dict[tuple[str, ...], list[str]] = {}
    for state in states:
        classes.setdefault(state.protected_signature, []).append(state.name)
    return {signature: tuple(sorted(names)) for signature, names in classes.items()}


def find_quotient_falsifiers(
    representation: Mapping[str, tuple[str, ...]],
    protected_target: Mapping[str, tuple[str, ...]],
) -> tuple[ResidualPair, ...]:
    """Return same-representation/different-target witnesses.

    An empty result is only evidence relative to the supplied finite boundary;
    it is never promoted to a universal equivalence claim by this function.
    """

    groups: dict[tuple[str, ...], list[str]] = {}
    for name, rep_key in representation.items():
        groups.setdefault(rep_key, []).append(name)

    witnesses: list[ResidualPair] = []
    for rep_key, names in groups.items():
        ordered = sorted(names)
        for i, left in enumerate(ordered):
            for right in ordered[i + 1 :]:
                if protected_target[left] != protected_target[right]:
                    witnesses.append(
                        ResidualPair(
                            left=left,
                            right=right,
                            representation_key=rep_key,
                            left_target=protected_target[left],
                            right_target=protected_target[right],
                        )
                    )
    return tuple(witnesses)


def live_routes(
    edges: Iterable[Hyperedge], live_supports: set[str] | frozenset[str]
) -> tuple[Hyperedge, ...]:
    return tuple(edge for edge in edges if edge.is_live(live_supports))


def uncovered_failures(
    state: str,
    failures: Iterable[str],
    edges: Iterable[Hyperedge],
    live_supports: set[str] | frozenset[str],
) -> tuple[Residual, ...]:
    """Reclose one-step live coverage and expose only remaining residuals."""

    live = live_routes(edges, live_supports)
    out: list[Residual] = []
    for failure in failures:
        if not any(edge.source == state and edge.failure_class == failure for edge in live):
            out.append(Residual(state, failure, "no_live_supported_route"))
    return tuple(out)


def greatest_viability_kernel(
    states: Iterable[str],
    failures: Iterable[str],
    edges: Iterable[Hyperedge],
    live_supports: set[str] | frozenset[str],
) -> frozenset[str]:
    """Greatest robust post-fixed set for a finite disturbance/repair system.

    A state survives iff, for every admitted failure class, at least one live
    supported route leads from that state back into the surviving set.  This is
    deliberately stronger than static per-failure cover because edge targets
    encode consequential mutable state (resource/interference effects).
    """

    kernel = set(states)
    failures = tuple(failures)
    live = live_routes(edges, live_supports)

    changed = True
    while changed:
        changed = False
        keep: set[str] = set()
        for state in kernel:
            if all(
                any(
                    edge.source == state
                    and edge.failure_class == failure
                    and edge.target in kernel
                    for edge in live
                )
                for failure in failures
            ):
                keep.add(state)
        if keep != kernel:
            kernel = keep
            changed = True
    return frozenset(kernel)


def action_quotient(
    actions: Iterable[str],
    sources: Iterable[str],
    induced_targets: Mapping[tuple[str, str], str],
) -> dict[tuple[str, ...], tuple[str, ...]]:
    """Quotient actions by their induced protected transition signature."""

    ordered_sources = tuple(sorted(sources))
    classes: dict[tuple[str, ...], list[str]] = {}
    for action in actions:
        signature = tuple(induced_targets[(source, action)] for source in ordered_sources)
        classes.setdefault(signature, []).append(action)
    return {signature: tuple(sorted(names)) for signature, names in classes.items()}
