from mathgraph.cross_prover_sufficient_interface import (
    RELATION_KIND,
    discover_sufficient_interfaces,
    render_lean_projection,
)


def test_projection_is_typed_as_stronger_interface_not_same_meaning():
    sources={
        "renamed": """
T: THEORY
BEGIN
foo: LEMMA FORALL (x: real, l: list[real]):
  f(x) > x^2 AND member(x, l) AND length(l) = 3 IMPLIES f(x) > -1
END T
"""
    }
    proofs={"renamed": """(|T|
 (|foo| 0)
)
"""}
    out=discover_sufficient_interfaces(sources,proofs)
    assert out["candidate_count"]==1
    row=out["candidates"][0]
    assert row["formula"]=="foo"
    assert row["relation_kind"]==RELATION_KIND
    assert RELATION_KIND=="INTERFACE_IMPLIES_SOURCE_INSTANCE"
    assert row["interface_id"]=="interface.above_square_gt_neg_one@1"
    assert row["source_proof_status"]=="PINNED_PROOF_PRESENT"


def test_projection_family_renders_interface_and_adapter_pairs():
    sources={
        "q": """
Q: THEORY
BEGIN
a: LEMMA FORALL (x: real): (FORALL (z: real): g(z) <= 1) AND
  (x > 0 IMPLIES EXISTS (z: real): z * z = x) AND x > 2 IMPLIES x > 1
b: LEMMA FORALL (x: real, l: list[real]): P(x) AND cons?(l) AND
  (FORALL (z: real): f(z) >= 0) AND f(x) > x^2 AND x /= 0 IMPLIES f(x) > 0
END Q
"""
    }
    proofs={"q": """(|Q|
 (|a| 0)
 (|b| 0)
)
"""}
    out=discover_sufficient_interfaces(sources,proofs)
    assert out["candidate_count"]==2
    lean=render_lean_projection(out)
    assert "gt_two_gt_one_interface" in lean
    assert "source_skip_from_interface" in lean
    assert "above_nonzero_square_positive_interface" in lean
    assert "source_mix_from_interface" in lean
