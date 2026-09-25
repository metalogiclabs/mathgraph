"""Generic finite semantic-relation profiles.

This module is a domain extension behind Crystal's stable SemanticObject
envelope.  It does not create authority: evidence that a finite boundary is the
right protected boundary remains an external qualification obligation.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from itertools import combinations

from mathgraph.crystal import SemanticObject


@dataclass(frozen=True)
class FinitePredicateProfile:
    name: str
    cases: tuple[str, ...]
    truth: tuple[bool, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("profile name must be non-empty")
        if len(self.cases) != len(self.truth):
            raise ValueError("cases/truth length mismatch")
        if len(set(self.cases)) != len(self.cases):
            raise ValueError("duplicate finite cases")

    def semantic_object(self) -> SemanticObject:
        payload = json.dumps(
            {
                "name": self.name,
                "cases": list(self.cases),
                "truth": list(self.truth),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return SemanticObject(
            type_id="relation.finite.predicate@1",
            contract_version=1,
            payload=payload,
            interfaces=(
                "relation.equivalence@1",
                "relation.implication@1",
                "relation.separator@1",
            ),
        )


@dataclass(frozen=True)
class FiniteObservationProfile:
    name: str
    cases: tuple[str, ...]
    signatures: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("profile name must be non-empty")
        if len(self.cases) != len(self.signatures):
            raise ValueError("cases/signatures length mismatch")
        if len(set(self.cases)) != len(self.cases):
            raise ValueError("duplicate finite cases")

    def semantic_object(self) -> SemanticObject:
        payload = json.dumps(
            {
                "name": self.name,
                "cases": list(self.cases),
                "signatures": [list(sig) for sig in self.signatures],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return SemanticObject(
            type_id="relation.finite.observation@1",
            contract_version=1,
            payload=payload,
            interfaces=(
                "relation.partition@1",
                "relation.quotient-falsifier@1",
                "relation.separator@1",
            ),
        )

    def partition(self) -> dict[tuple[str, ...], tuple[str, ...]]:
        groups: dict[tuple[str, ...], list[str]] = {}
        for case, signature in zip(self.cases, self.signatures):
            groups.setdefault(signature, []).append(case)
        return {
            signature: tuple(sorted(items))
            for signature, items in groups.items()
        }


def _aligned(
    left_cases: tuple[str, ...], right_cases: tuple[str, ...]
) -> None:
    if left_cases != right_cases:
        raise ValueError("finite relation profiles use different case boundaries")


def predicate_equivalent(
    left: FinitePredicateProfile,
    right: FinitePredicateProfile,
) -> bool:
    _aligned(left.cases, right.cases)
    return left.truth == right.truth


def predicate_implies(
    left: FinitePredicateProfile,
    right: FinitePredicateProfile,
) -> bool:
    _aligned(left.cases, right.cases)
    return all((not a) or b for a, b in zip(left.truth, right.truth))


def predicate_separator(
    left: FinitePredicateProfile,
    right: FinitePredicateProfile,
) -> tuple[str, bool, bool] | None:
    _aligned(left.cases, right.cases)
    for case, a, b in zip(left.cases, left.truth, right.truth):
        if a != b:
            return case, a, b
    return None


def quotient_falsifiers(
    representation: FiniteObservationProfile,
    protected: FiniteObservationProfile,
) -> tuple[tuple[str, str], ...]:
    _aligned(representation.cases, protected.cases)
    rep = dict(zip(representation.cases, representation.signatures))
    target = dict(zip(protected.cases, protected.signatures))
    out: list[tuple[str, str]] = []
    for left, right in combinations(representation.cases, 2):
        if rep[left] == rep[right] and target[left] != target[right]:
            out.append((left, right))
    return tuple(out)
