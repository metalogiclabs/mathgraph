"""Frozen v1 protocol: evaluate declared meaning relations from authenticated evidence.

The protocol does NOT infer an interpretation from an accepted artifact.
Adapters, whose outputs remain source-specific, must supply the relation and authority.
"""
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Obligation:
    name: str
    source: str
    relation: str  # MATCH, MISMATCH, UNSUPPORTED, NO_ASSERTION
    authority: str  # ASSERTED, ANNOTATION, UNRESOLVED
    dependencies: tuple[str, ...]
    qualifier: str


def judge(o: Obligation, observed: Mapping[str, str], required: Mapping[str, str]) -> str:
    """No truth promotion; explicit evidence/authority failure wins over local success."""
    if not o.dependencies or not o.source or not o.qualifier:
        return "UNKNOWN_INCOMPLETE"
    if any(d not in observed or d not in required or observed[d] != required[d]
           for d in o.dependencies):
        return "UNKNOWN_WITHDRAWN_OR_CHANGED"
    if o.authority == "UNRESOLVED":
        return "UNKNOWN_CONTRACT"
    if o.authority == "ANNOTATION":
        return "NO_SEMANTIC_ASSERTION"
    if o.authority != "ASSERTED":
        return "UNKNOWN_AUTHORITY"
    return {
        "MATCH": "SCOPED_AGREEMENT",
        "MISMATCH": "DIVERGENT_BOUNDED",
        "UNSUPPORTED": "UNKNOWN_INTERPRETATION",
        "NO_ASSERTION": "NO_SEMANTIC_ASSERTION",
    }.get(o.relation, "UNKNOWN_RELATION")


def assess(cases: tuple[Obligation, ...],
           observed: Mapping[str, str],
           required: Mapping[str, str]) -> dict[str, str]:
    if len({c.name for c in cases}) != len(cases):
        raise ValueError("duplicate obligation name")
    return {c.name: judge(c, observed, required) for c in cases}
