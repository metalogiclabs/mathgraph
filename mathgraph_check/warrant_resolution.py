"""Deterministic bounded warrant closure over externally admitted inputs.

This module does not authenticate evidence or accept mathematical claims into
the terminal-form kernel. Receipt and relation construction is a trusted caller
boundary: adapters must qualify them independently before calling resolve_graph.
Neither a label nor a self-hash establishes authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

KINDS = frozenset(("formal", "documentary"))


@dataclass(frozen=True)
class Claim:
    id: str
    kind: str
    scope: str

    def __post_init__(self):
        if not self.id or self.kind not in KINDS or not self.scope:
            raise ValueError("INVALID_CLAIM_TYPE")


@dataclass(frozen=True)
class Receipt:
    """Externally qualified evidence; this value object is not a verifier."""

    id: str
    kind: str
    scope: str

    def __post_init__(self):
        if not self.id or self.kind not in KINDS or not self.scope:
            raise ValueError("INVALID_RECEIPT_TYPE")


@dataclass(frozen=True)
class Route:
    conclusion: str
    evidence: tuple[str, ...]
    premises: tuple[str, ...] = ()
    relation: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "premises", tuple(self.premises))


@dataclass(frozen=True)
class QualifiedRelation:
    """Admitted adapter for one exact source and destination boundary.

    Only verified_adapter is supported. The named verifier must be an admitted
    formal receipt at the target scope; evidence receipts must match the target
    kind and scope. Caller admission attests that the verifier checked this
    particular relation. Their presence here checks references, not provenance.
    Withdrawing any qualification receipt disables every route using it.
    """

    id: str
    source_kind: str
    source_scope: str
    target_kind: str
    target_scope: str
    verifier: str
    evidence: tuple[str, ...]
    kind: str = "verified_adapter"

    def __post_init__(self):
        object.__setattr__(self, "evidence", tuple(self.evidence))
        if self.kind != "verified_adapter":
            raise ValueError("UNSUPPORTED_RELATION")
        if (not self.id or self.source_kind not in KINDS or self.target_kind not in KINDS
                or not self.source_scope or not self.target_scope
                or not self.verifier or not self.evidence):
            raise ValueError("INVALID_RELATION")


@dataclass(frozen=True)
class ResolutionSet:
    states: Mapping[str, str]
    active_routes: tuple[Route, ...]

    def __post_init__(self):
        object.__setattr__(self, "states", MappingProxyType(dict(self.states)))
        object.__setattr__(self, "active_routes", tuple(self.active_routes))


def resolve_graph(
    claims: Sequence[Claim],
    routes: Sequence[Route],
    receipts: Sequence[Receipt],
    *,
    withdrawn: frozenset[str] = frozenset(),
    relations: Sequence[QualifiedRelation] = (),
) -> ResolutionSet:
    """Least fixed point of conjunctive routes and alternative justifications.

    Unrooted cycles remain UNKNOWN. Withdrawal removes support, never infers a
    refutation. Validate even inactive routes so invalid graphs fail closed.
    """
    cl = {c.id: c for c in claims}
    ev = {r.id: r for r in receipts}
    rel = {r.id: r for r in relations}
    if len(cl) != len(claims) or len(ev) != len(receipts):
        raise ValueError("DUPLICATE_CLAIM_OR_RECEIPT")
    if len(rel) != len(relations):
        raise ValueError("DUPLICATE_RELATION")
    if not withdrawn.issubset(ev.keys()):
        raise ValueError("UNKNOWN_WITHDRAWAL_TARGET")
    if len(set(routes)) != len(routes):
        raise ValueError("DUPLICATE_ROUTE")
    # Validate destination use first: a relation cannot widen its target scope.
    for route in routes:
        if route.conclusion not in cl or not route.evidence:
            raise ValueError("INVALID_ROUTE")
        if any(x not in ev for x in route.evidence):
            raise ValueError("UNKNOWN_ROUTE_RECEIPT")
        if any(x not in cl for x in route.premises):
            raise ValueError("UNKNOWN_ROUTE_PREMISE")
        dest = cl[route.conclusion]
        boundary = (dest.kind, dest.scope)
        bridge = None
        if route.relation is not None:
            if route.relation not in rel:
                raise ValueError("UNKNOWN_ROUTE_RELATION")
            bridge = rel[route.relation]
            if (bridge.target_kind, bridge.target_scope) != boundary:
                raise ValueError("RELATION_TARGET_MISMATCH")
        allowed = {boundary}
        if bridge is not None:
            allowed.add((bridge.source_kind, bridge.source_scope))
        if any((ev[x].kind, ev[x].scope) not in allowed for x in route.evidence):
            raise ValueError("CROSS_BOUNDARY_EVIDENCE_WITHOUT_BRIDGE")
        if any((cl[x].kind, cl[x].scope) not in allowed for x in route.premises):
            raise ValueError("CROSS_BOUNDARY_PREMISE_WITHOUT_BRIDGE")
    for bridge in relations:
        if bridge.verifier not in ev:
            raise ValueError("UNKNOWN_RELATION_VERIFIER")
        if any(x not in ev for x in bridge.evidence):
            raise ValueError("UNKNOWN_RELATION_RECEIPT")
        verifier = ev[bridge.verifier]
        if (verifier.kind, verifier.scope) != ("formal", bridge.target_scope):
            raise ValueError("UNQUALIFIED_RELATION_VERIFIER")
        if any((ev[x].kind, ev[x].scope) != (bridge.target_kind, bridge.target_scope)
               for x in bridge.evidence):
            raise ValueError("UNQUALIFIED_RELATION_EVIDENCE")

    def evidence_is_live(route: Route) -> bool:
        required = route.evidence
        if route.relation is not None:
            bridge = rel[route.relation]
            required += (bridge.verifier,) + bridge.evidence
        return all(x not in withdrawn for x in required)

    active: set[str] = set()
    while True:
        added = {route.conclusion for route in routes
                 if evidence_is_live(route) and all(p in active for p in route.premises)} - active
        if not added:
            break
        active.update(added)
    states = {
        key: ("WARRANTED_BOUNDED" if cl[key].kind == "formal"
              else "SOURCE_DOCUMENTED") if key in active else "UNKNOWN"
        for key in sorted(cl)
    }
    surviving = tuple(sorted(
        (route for route in routes
         if evidence_is_live(route) and all(p in active for p in route.premises)),
        key=lambda route: (route.conclusion, route.evidence, route.premises, route.relation or ""),
    ))
    return ResolutionSet(states, surviving)


def reclose(
    claims: Sequence[Claim], routes: Sequence[Route], receipts: Sequence[Receipt], *,
    withdrawn: frozenset[str] = frozenset(),
) -> dict[str, str]:
    """Historical API: source/scope-preserving graph closure as a plain dict."""
    return dict(resolve_graph(claims, routes, receipts, withdrawn=withdrawn).states)


def compare_snapshots(
    before: Mapping[str, str], after: Mapping[str, str],
) -> dict[str, dict]:
    if before.keys() != after.keys():
        raise ValueError("DIFFERENT_CLAIM_UNIVERSE")
    result = {}
    for claim in sorted(before):
        old, new = before[claim], after[claim]
        status = "STALE" if old != "UNKNOWN" and new == "UNKNOWN" else new
        result[claim] = {"before": old, "after": status, "changed": old != status}
    return result
