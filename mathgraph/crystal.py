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


_SEMANTIC_OBJECT_MAGIC = bytes((77, 71, 83, 79, 0, 1))


def _pack_u32(value: int) -> bytes:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("value does not fit canonical u32")
    return value.to_bytes(4, "big")


def _pack_u64(value: int) -> bytes:
    if not 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError("value does not fit canonical u64")
    return value.to_bytes(8, "big")


def _pack_text(value: str) -> bytes:
    data = value.encode("utf-8")
    return _pack_u32(len(data)) + data


@dataclass(frozen=True)
class SemanticObject:
    """Opaque, content-addressed semantic object envelope.

    The microkernel owns only this envelope. Payload is meaning-bearing
    canonical bytes defined by type_id + contract_version; an older runtime
    must preserve those bytes without interpreting or normalising them.
    Interfaces are stable semantic contracts advertised by the object and are
    canonicalised as a sorted set.

    Envelope encoding v1 is deterministic:
    MAGIC | type-id | u32 version | interface-set | u64 payload-len | payload.

    Unknown semantic types are valid objects. Unsupported interpretation
    returns UnknownSemantics rather than degrading the payload.
    """

    type_id: str
    contract_version: int
    payload: bytes
    interfaces: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.type_id:
            raise ValueError("semantic object type_id must be non-empty")
        if not 0 <= self.contract_version <= 0xFFFFFFFF:
            raise ValueError("contract_version must fit canonical u32")
        if not isinstance(self.payload, bytes):
            raise TypeError("semantic object payload must be bytes")
        if any(not interface for interface in self.interfaces):
            raise ValueError("interface ids must be non-empty")
        canonical_interfaces = tuple(sorted(set(self.interfaces)))
        object.__setattr__(self, "interfaces", canonical_interfaces)

    @property
    def id(self) -> str:
        return f"semantic:{hashlib.sha256(self.to_bytes()).hexdigest()}"

    def to_bytes(self) -> bytes:
        type_bytes = self.type_id.encode("utf-8")
        out = bytearray(_SEMANTIC_OBJECT_MAGIC)
        out += _pack_u32(len(type_bytes))
        out += type_bytes
        out += _pack_u32(self.contract_version)
        out += _pack_u32(len(self.interfaces))
        for interface in self.interfaces:
            out += _pack_text(interface)
        out += _pack_u64(len(self.payload))
        out += self.payload
        return bytes(out)

    @classmethod
    def from_bytes(cls, data: bytes) -> "SemanticObject":
        """Decode only the stable envelope; never interpret opaque payload."""

        if not isinstance(data, bytes):
            raise TypeError("semantic object transport must be bytes")
        if not data.startswith(_SEMANTIC_OBJECT_MAGIC):
            raise ValueError("unknown semantic object envelope")
        offset = len(_SEMANTIC_OBJECT_MAGIC)

        def take(count: int) -> bytes:
            nonlocal offset
            end = offset + count
            if count < 0 or end > len(data):
                raise ValueError("truncated semantic object")
            chunk = data[offset:end]
            offset = end
            return chunk

        def take_u32() -> int:
            return int.from_bytes(take(4), "big")

        def take_u64() -> int:
            return int.from_bytes(take(8), "big")

        type_id = take(take_u32()).decode("utf-8")
        contract_version = take_u32()
        interfaces = []
        for _ in range(take_u32()):
            interfaces.append(take(take_u32()).decode("utf-8"))
        payload = take(take_u64())
        if offset != len(data):
            raise ValueError("trailing bytes in semantic object")

        obj = cls(type_id, contract_version, payload, tuple(interfaces))
        if obj.to_bytes() != data:
            raise ValueError("non-canonical semantic object encoding")
        return obj


@dataclass(frozen=True)
class UnknownSemantics:
    """Typed epistemic residual produced by unsupported interpretation."""

    object_id: str
    requested_interface: str
    reason: str = "missing_interface"


def interpret_semantic_object(
    obj: SemanticObject,
    interface_id: str,
    interpreters: Mapping[str, Any],
) -> Any | UnknownSemantics:
    """Interpret through a supported interface or preserve typed UNKNOWN.

    Registering a future interpreter can add operations over an old object,
    but cannot change the object canonical bytes or identity.
    """

    if interface_id not in obj.interfaces or interface_id not in interpreters:
        return UnknownSemantics(obj.id, interface_id)
    interpreter = interpreters[interface_id]
    if not callable(interpreter):
        raise TypeError("semantic interface interpreter must be callable")
    return interpreter(obj)

@dataclass(frozen=True)
class AdapterContract:
    """Content-addressed claim about a translation preservation boundary.

    The contract does not make itself true. ``evidence_refs`` point to
    independent qualification evidence. A runtime may use only preservation
    interfaces named here; every other requested consequence is UNKNOWN.
    """

    adapter_id: str
    contract_version: int
    source_space: str
    target_space: str
    preserves_interfaces: tuple[str, ...]
    assumption_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.adapter_id:
            raise ValueError("adapter_id must be non-empty")
        if not 0 <= self.contract_version <= 0xFFFFFFFF:
            raise ValueError("contract_version must fit canonical u32")
        if not self.source_space or not self.target_space:
            raise ValueError("source_space and target_space must be non-empty")
        if any(not x for x in self.preserves_interfaces):
            raise ValueError("preserved interface ids must be non-empty")
        object.__setattr__(
            self,
            "preserves_interfaces",
            tuple(sorted(set(self.preserves_interfaces))),
        )
        object.__setattr__(
            self,
            "assumption_refs",
            tuple(sorted(set(self.assumption_refs))),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(set(self.evidence_refs))),
        )

    @property
    def id(self) -> str:
        return content_id(self, prefix="adapter")


@dataclass(frozen=True)
class UnknownTranslation:
    """Typed residual for a consequence outside an adapter contract."""

    object_id: str
    adapter_contract_id: str
    requested_interface: str
    reason: str


def translate_semantic_object(
    obj: SemanticObject,
    contract: AdapterContract,
    requested_interface: str,
) -> SemanticObject | UnknownTranslation:
    """Transport an opaque semantic object under an explicit preservation claim.

    This reference operation models the conservative case where the adapter
    preserves the canonical semantic envelope itself. It may claim a protected
    interface only when both the object implements that interface and the
    adapter contract explicitly preserves it. No payload interpretation or
    normalisation occurs here.
    """

    if requested_interface not in contract.preserves_interfaces:
        return UnknownTranslation(
            obj.id,
            contract.id,
            requested_interface,
            "outside_preservation_contract",
        )
    if requested_interface not in obj.interfaces:
        return UnknownTranslation(
            obj.id,
            contract.id,
            requested_interface,
            "object_missing_interface",
        )
    # Re-decode canonical bytes to exercise the actual transport boundary.
    translated = SemanticObject.from_bytes(obj.to_bytes())
    if translated.id != obj.id:
        raise AssertionError("lossless translation changed semantic identity")
    return translated

def lower_semantic_object(
    obj: SemanticObject,
    contract: AdapterContract,
    requested_interface: str,
    lowerer: Any,
) -> SemanticObject | UnknownTranslation:
    """Apply a real lowering under an explicit preservation contract.

    Unlike ``translate_semantic_object``, the target may have a different
    concrete type, payload and content identity. The microkernel checks only
    that the requested interface is in-contract on both sides and that the
    lowerer returns a canonical SemanticObject. Actual semantic preservation
    remains a qualification obligation referenced by the contract evidence.
    """

    if requested_interface not in contract.preserves_interfaces:
        return UnknownTranslation(
            obj.id, contract.id, requested_interface, "outside_preservation_contract"
        )
    if requested_interface not in obj.interfaces:
        return UnknownTranslation(
            obj.id, contract.id, requested_interface, "object_missing_interface"
        )
    if not callable(lowerer):
        raise TypeError("semantic adapter lowerer must be callable")
    target = lowerer(obj)
    if not isinstance(target, SemanticObject):
        raise TypeError("semantic adapter lowerer must return SemanticObject")
    if requested_interface not in target.interfaces:
        return UnknownTranslation(
            obj.id, contract.id, requested_interface, "target_missing_interface"
        )
    # Exercise canonical target transport before exposing the lowering result.
    target = SemanticObject.from_bytes(target.to_bytes())
    return target

def compose_adapter_contracts(
    first: AdapterContract,
    second: AdapterContract,
    *,
    adapter_id: str | None = None,
) -> AdapterContract:
    """Mechanically compose compatible adapter preservation contracts.

    Only interfaces preserved by both legs survive composition. Assumptions
    and evidence compose by set union plus explicit component-contract refs.
    """

    if first.target_space != second.source_space:
        raise ValueError("adapter spaces do not compose")
    shared = tuple(sorted(set(first.preserves_interfaces) & set(second.preserves_interfaces)))
    return AdapterContract(
        adapter_id=adapter_id or f"{second.adapter_id}∘{first.adapter_id}",
        contract_version=1,
        source_space=first.source_space,
        target_space=second.target_space,
        preserves_interfaces=shared,
        assumption_refs=first.assumption_refs + second.assumption_refs,
        evidence_refs=(
            first.evidence_refs
            + second.evidence_refs
            + (f"adapter-contract:{first.id}", f"adapter-contract:{second.id}")
        ),
    )


def compose_lower_semantic_object(
    obj: SemanticObject,
    first: AdapterContract,
    second: AdapterContract,
    requested_interface: str,
    first_lowerer: Any,
    second_lowerer: Any,
    *,
    adapter_id: str | None = None,
) -> SemanticObject | UnknownTranslation:
    """Compose two non-identity lowerings under the mechanically composed contract."""

    composed = compose_adapter_contracts(first, second, adapter_id=adapter_id)
    if requested_interface not in composed.preserves_interfaces:
        return UnknownTranslation(
            obj.id, composed.id, requested_interface, "outside_preservation_contract"
        )
    middle = lower_semantic_object(obj, first, requested_interface, first_lowerer)
    if isinstance(middle, UnknownTranslation):
        return middle
    return lower_semantic_object(middle, second, requested_interface, second_lowerer)

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
class ObservationMap:
    """Observer/interface partition over underlying consequential states.

    Entries map an underlying state identity to the observation exposed at a
    declared interface. States sharing an observation are intentionally
    indistinguishable to that interface. The map carries no truth authority;
    it is a content-addressed consequential coordinate when protected futures
    depend on what the acting/querying observer can distinguish.
    """

    entries: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        states = [state for state, _ in self.entries]
        if len(states) != len(set(states)):
            raise ValueError("observation map contains duplicate states")

    @property
    def id(self) -> str:
        return content_id(self, prefix="observer")

    def observe(self, state: str) -> str:
        for candidate, observation in self.entries:
            if candidate == state:
                return observation
        raise KeyError(state)

    @property
    def classes(self) -> dict[str, tuple[str, ...]]:
        classes: dict[str, list[str]] = {}
        for state, observation in self.entries:
            classes.setdefault(observation, []).append(state)
        return {
            observation: tuple(sorted(states))
            for observation, states in classes.items()
        }


@dataclass(frozen=True)
class ControlMap:
    """Local control/ownership over choice points.

    Entries map a stable choice-point identity to a controller identity.
    This is intentionally not part of Boundary: a fixed protected
    coalition/query can have different lawful futures when control of local
    choices changes while states and effects remain identical.

    Controller identities are opaque semantic identifiers. This object does
    not define game theory, coalitions, or scheduler policy; those remain typed
    boundary/interface semantics.
    """

    entries: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        points = [point for point, _ in self.entries]
        if len(points) != len(set(points)):
            raise ValueError("control map contains duplicate choice points")

    @property
    def id(self) -> str:
        return content_id(self, prefix="control")

    def controller(self, choice_point: str) -> str:
        for candidate, controller in self.entries:
            if candidate == choice_point:
                return controller
        raise KeyError(choice_point)

    @property
    def by_controller(self) -> dict[str, tuple[str, ...]]:
        grouped: dict[str, list[str]] = {}
        for point, controller in self.entries:
            grouped.setdefault(controller, []).append(point)
        return {
            controller: tuple(sorted(points))
            for controller, points in grouped.items()
        }


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
        from decimal import Decimal

        return tuple(
            sorted(
                outcome.target
                for outcome in self.outcomes
                if Decimal(outcome.rate) != 0
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
