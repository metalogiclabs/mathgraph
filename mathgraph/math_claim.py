"""Mathematical-claim dialect objects carried by the stable Crystal envelope.

This module deliberately does not change the Crystal SemanticObject waist.
Claims are payload dialects behind that permanent waist. Cross-formulation
equivalence/implication is represented only by separately verified relations.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Iterable

from mathgraph.crystal import SemanticObject, content_id


MATH_CLAIM_TYPE = "math.claim@1"
MATH_CLAIM_INTERFACES = (
    "math.claim.provenance@1",
    "math.claim.statement@1",
)


@dataclass(frozen=True)
class MathClaimPayload:
    """One source formulation of a mathematical claim."""

    claim_id: str
    dialect: str
    context: tuple[tuple[str, str], ...]
    assumptions: tuple[str, ...]
    statement: str
    source_ref: str

    def __post_init__(self) -> None:
        if not self.claim_id or not self.dialect or not self.statement or not self.source_ref:
            raise ValueError("claim_id, dialect, statement and source_ref must be non-empty")
        names = [name for name, _ in self.context]
        if len(names) != len(set(names)):
            raise ValueError("claim context contains duplicate symbol names")

    def canonical_payload_bytes(self) -> bytes:
        payload = {
            "claim_id": self.claim_id,
            "dialect": self.dialect,
            "context": [list(item) for item in self.context],
            "assumptions": list(self.assumptions),
            "statement": self.statement,
            "source_ref": self.source_ref,
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def semantic_object(self) -> SemanticObject:
        return SemanticObject(
            type_id=MATH_CLAIM_TYPE,
            contract_version=1,
            payload=self.canonical_payload_bytes(),
            interfaces=MATH_CLAIM_INTERFACES,
        )


@dataclass(frozen=True)
class VerifiedClaimRelation:
    """Externally warranted relation between two claim formulations."""

    left_object_id: str
    right_object_id: str
    relation: str
    evidence_refs: tuple[str, ...]
    witness: tuple[tuple[str, bool], ...] = ()

    def __post_init__(self) -> None:
        if self.relation not in {"equivalent", "implies", "separated"}:
            raise ValueError(f"unsupported claim relation: {self.relation}")
        if not self.left_object_id or not self.right_object_id:
            raise ValueError("claim relation endpoints must be non-empty")
        if not self.evidence_refs:
            raise ValueError("verified claim relation requires evidence")

    @property
    def id(self) -> str:
        return content_id(self, prefix="claim-relation")


def quotient_by_verified_equivalence(
    object_ids: Iterable[str],
    relations: Iterable[VerifiedClaimRelation],
) -> tuple[tuple[str, ...], ...]:
    """Merge only endpoints with a separately verified equivalence relation."""

    ids = tuple(sorted(set(object_ids)))
    parent = {item: item for item in ids}

    def find(item: str) -> str:
        root = item
        while parent[root] != root:
            root = parent[root]
        while parent[item] != item:
            nxt = parent[item]
            parent[item] = root
            item = nxt
        return root

    def union(left: str, right: str) -> None:
        if left not in parent or right not in parent:
            raise KeyError("equivalence relation references unknown object")
        a, b = find(left), find(right)
        if a != b:
            if a < b:
                parent[b] = a
            else:
                parent[a] = b

    for relation in relations:
        if relation.relation == "equivalent":
            union(relation.left_object_id, relation.right_object_id)

    classes: dict[str, list[str]] = {}
    for item in ids:
        classes.setdefault(find(item), []).append(item)
    return tuple(sorted(tuple(sorted(group)) for group in classes.values()))
