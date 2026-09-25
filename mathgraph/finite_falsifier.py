"""Generic finite falsifier witness interface.

Domain-specific adapters supply a finite case space and a Boolean protected
property. This module only performs deterministic bounded search and packages
the first separating case as a content-addressed semantic witness. It does not
decide whether the supplied boundary is scientifically sufficient.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Callable, Iterable, TypeVar

from mathgraph.crystal import SemanticObject

T = TypeVar("T")


@dataclass(frozen=True)
class FiniteFalsifierWitness:
    family_id: str
    claim_ref: str
    boundary_ref: str
    case_id: str
    witness_payload: bytes
    verifier_ref: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.family_id or not self.claim_ref or not self.boundary_ref:
            raise ValueError("family_id, claim_ref and boundary_ref must be non-empty")
        if not self.case_id or not self.verifier_ref:
            raise ValueError("case_id and verifier_ref must be non-empty")
        if not isinstance(self.witness_payload, bytes):
            raise TypeError("witness_payload must be bytes")
        object.__setattr__(self, "evidence_refs", tuple(sorted(set(self.evidence_refs))))

    def semantic_object(self) -> SemanticObject:
        payload = json.dumps(
            {
                "family_id": self.family_id,
                "claim_ref": self.claim_ref,
                "boundary_ref": self.boundary_ref,
                "case_id": self.case_id,
                "witness_hex": self.witness_payload.hex(),
                "verifier_ref": self.verifier_ref,
                "evidence_refs": list(self.evidence_refs),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return SemanticObject(
            type_id="falsifier.finite.witness@1",
            contract_version=1,
            payload=payload,
            interfaces=(
                "claim.refutation@1",
                "evidence.provenance@1",
                "falsifier.finite.witness@1",
            ),
        )


@dataclass(frozen=True)
class FiniteFalsifierSearch:
    witness: FiniteFalsifierWitness | None
    checked_cases: int
    exhausted: bool


def find_first_falsifier(
    cases: Iterable[T],
    protected_property: Callable[[T], bool],
    *,
    encode_case: Callable[[T], tuple[str, bytes]],
    family_id: str,
    claim_ref: str,
    boundary_ref: str,
    verifier_ref: str,
    evidence_refs: tuple[str, ...] = (),
) -> FiniteFalsifierSearch:
    """Return the first deterministic finite counterexample, if any."""

    checked = 0
    for case in cases:
        checked += 1
        if not protected_property(case):
            case_id, payload = encode_case(case)
            return FiniteFalsifierSearch(
                witness=FiniteFalsifierWitness(
                    family_id=family_id,
                    claim_ref=claim_ref,
                    boundary_ref=boundary_ref,
                    case_id=case_id,
                    witness_payload=payload,
                    verifier_ref=verifier_ref,
                    evidence_refs=evidence_refs,
                ),
                checked_cases=checked,
                exhausted=False,
            )
    return FiniteFalsifierSearch(witness=None, checked_cases=checked, exhausted=True)
