from mathgraph.crystal import SemanticObject, UnknownSemantics, interpret_semantic_object
from mathgraph.math_claim import (
    MathClaimPayload,
    VerifiedClaimRelation,
    quotient_by_verified_equivalence,
)


def claim(name: str, statement: str) -> SemanticObject:
    return MathClaimPayload(
        claim_id=name,
        dialect="test-dialect",
        context=(("p", "Bool"),),
        assumptions=(),
        statement=statement,
        source_ref=f"fixture:{name}",
    ).semantic_object()


def test_math_claim_is_payload_dialect_behind_stable_semantic_envelope():
    obj = claim("a", "p")
    assert obj.type_id == "math.claim@1"
    assert SemanticObject.from_bytes(obj.to_bytes()) == obj
    result = interpret_semantic_object(obj, "math.claim.statement@1", {})
    assert isinstance(result, UnknownSemantics)


def test_only_verified_equivalence_merges_claim_objects():
    a = claim("a", "p")
    b = claim("b", "p && true")
    c = claim("c", "p && q")
    relations = (
        VerifiedClaimRelation(a.id, b.id, "equivalent", ("fixture:proof",)),
        VerifiedClaimRelation(c.id, a.id, "implies", ("fixture:proof",)),
        VerifiedClaimRelation(a.id, c.id, "separated", ("fixture:model",), (("p", True),)),
    )
    classes = quotient_by_verified_equivalence((a.id, b.id, c.id), relations)
    assert len(classes) == 2
    assert any(set(group) == {a.id, b.id} for group in classes)
    assert any(group == (c.id,) for group in classes)
