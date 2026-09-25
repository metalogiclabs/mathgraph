"""Candidate compact Crystal core: a three-valued protected-continuation machine.

This module is deliberately smaller than the existing domain dialects. It does
not replace them or create authority. It asks whether protected consequences can
be represented as views of one object:

    quotient state --typed continuation/test--> protected outcome/state
                         {WARRANTED, EXCLUDED, UNKNOWN}

Support/evidence remain orthogonal authority metadata. Domain syntax,
provenance prose, proof traces and raw state are not semantic coordinates unless
a protected continuation distinguishes them.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import json
from typing import Iterable
from mathgraph.crystal import SemanticObject, content_id

class ContinuationStatus(str, Enum):
    WARRANTED = "WARRANTED"
    EXCLUDED = "EXCLUDED"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class ProtectedContinuation:
    source: str
    continuation: str
    outcome: tuple[str, ...]
    status: ContinuationStatus
    target: str | None = None
    support_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source or not self.continuation:
            raise ValueError("source and continuation must be non-empty")
        if not self.outcome:
            raise ValueError("protected outcome must be non-empty")
        object.__setattr__(self, "support_refs", tuple(sorted(set(self.support_refs))))
        object.__setattr__(self, "evidence_refs", tuple(sorted(set(self.evidence_refs))))

    @property
    def id(self) -> str:
        return content_id(self, prefix="continuation")

    def is_live(self, live_supports: set[str] | frozenset[str]) -> bool:
        return self.status is ContinuationStatus.WARRANTED and set(self.support_refs).issubset(live_supports)

@dataclass(frozen=True)
class ProtectedContinuationMachine:
    boundary_ref: str
    states: tuple[str, ...]
    continuations: tuple[ProtectedContinuation, ...]

    def __post_init__(self) -> None:
        if not self.boundary_ref:
            raise ValueError("boundary_ref must be non-empty")
        canonical_states = tuple(sorted(set(self.states)))
        object.__setattr__(self, "states", canonical_states)
        known = set(canonical_states)
        for edge in self.continuations:
            if edge.source not in known:
                raise ValueError(f"unknown continuation source: {edge.source}")
            if edge.target is not None and edge.target not in known:
                raise ValueError(f"unknown continuation target: {edge.target}")
        ordered = tuple(sorted(
            self.continuations,
            key=lambda e: (e.source,e.continuation,e.outcome,e.status.value,e.target or "",e.support_refs,e.evidence_refs),
        ))
        if len({edge.id for edge in ordered}) != len(ordered):
            raise ValueError("duplicate protected continuation")
        object.__setattr__(self, "continuations", ordered)

    @property
    def id(self) -> str:
        return content_id(self, prefix="future-machine")

    def semantic_object(self) -> SemanticObject:
        payload = json.dumps({
            "boundary_ref": self.boundary_ref,
            "states": list(self.states),
            "continuations": [{
                "source": e.source, "continuation": e.continuation,
                "outcome": list(e.outcome), "status": e.status.value,
                "target": e.target, "support_refs": list(e.support_refs),
                "evidence_refs": list(e.evidence_refs),
            } for e in self.continuations],
        }, sort_keys=True, separators=(",", ":")).encode()
        return SemanticObject(
            type_id="future.protected.partial@1",
            contract_version=1,
            payload=payload,
            interfaces=("future.bracket@1","future.quotient@1","future.residual@1","future.support@1"),
        )

    def edges_from(self, state: str) -> tuple[ProtectedContinuation, ...]:
        if state not in self.states:
            raise KeyError(state)
        return tuple(e for e in self.continuations if e.source == state)

    def lower_signature(self, state: str):
        return tuple((e.continuation,e.outcome,e.target) for e in self.edges_from(state)
                     if e.status is ContinuationStatus.WARRANTED)

    def upper_signature(self, state: str):
        return tuple((e.continuation,e.outcome,e.target) for e in self.edges_from(state)
                     if e.status is not ContinuationStatus.EXCLUDED)

    def unresolved(self, state: str | None = None):
        edges = self.continuations if state is None else self.edges_from(state)
        return tuple(e for e in edges if e.status is ContinuationStatus.UNKNOWN)

    def live_signature(self, state: str, live_supports: set[str] | frozenset[str]):
        return tuple((e.continuation,e.outcome,e.target) for e in self.edges_from(state)
                     if e.is_live(live_supports))

    def future_classes(self, *, use_upper: bool = False):
        groups = {}
        for state in self.states:
            sig = self.upper_signature(state) if use_upper else self.lower_signature(state)
            groups.setdefault(sig, []).append(state)
        return {sig: tuple(sorted(items)) for sig,items in groups.items()}

def relation_machine(states: Iterable[str], relations: Iterable[tuple[str,str,str,tuple[str,...]]], *, boundary_ref: str):
    edges=[]
    for left,right,relation,evidence_refs in relations:
        if relation not in {"equivalent","implies","separated"}:
            raise ValueError(relation)
        edges.append(ProtectedContinuation(left,f"relation:{relation}",(right,),ContinuationStatus.WARRANTED,evidence_refs=evidence_refs))
    return ProtectedContinuationMachine(boundary_ref,tuple(states),tuple(edges))

def equivalence_classes_from_relations(machine: ProtectedContinuationMachine):
    parent={s:s for s in machine.states}
    def find(x):
        while parent[x] != x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra != rb:
            if ra < rb: parent[rb]=ra
            else: parent[ra]=rb
    for e in machine.continuations:
        if e.status is ContinuationStatus.WARRANTED and e.continuation=="relation:equivalent":
            union(e.source,e.outcome[0])
    groups={}
    for s in machine.states:
        groups.setdefault(find(s),[]).append(s)
    return tuple(sorted(tuple(sorted(g)) for g in groups.values()))
