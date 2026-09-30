from mathgraph.cross_prover_semantic_normalization import (
    discover_normalized_exact_reuse,
    semantic_shape_index,
    semantic_shape_key,
)


def test_alpha_renamed_cubic_has_same_key():
    a=semantic_shape_key(
        "FORALL (c: real): EXISTS (x: real): x^3 - 3 * x + c = 0"
    )
    b=semantic_shape_key(
        "FORALL (foo: real): EXISTS (bar: real): bar^3 - 3 * bar + foo = 0"
    )
    assert a==b


def test_top_not_parentheses_are_representation_only():
    a=semantic_shape_key(
        "NOT (FORALL (x: real): EXISTS (y: real): x * y = 1)"
    )
    b=semantic_shape_key(
        "NOT FORALL (a: real): EXISTS (b: real): a * b = 1"
    )
    assert a==b


def test_registry_has_no_cross_claim_collision():
    index=semantic_shape_index()
    assert all(len(ids)==1 for ids in index.values())


def test_second_heldout_gains_two_exact_reuses_without_new_claims():
    src="""
T: THEORY
BEGIN
ex_cubic: LEMMA FORALL (x: real): EXISTS (y: real): y^3 - 3 * y + x = 0
ex_amgm: LEMMA FORALL (x: real): FORALL (y: real): x^2 + y^2 >= 2 * x * y
ex_meet: LEMMA EXISTS (x: real): EXISTS (y: real): x^2 + y^2 = 1 AND y = x^2
ex_hyp: LEMMA NOT FORALL (x: real): EXISTS (y: real): x * y = 1
fresh: LEMMA FORALL (x: real): x^2 + 7 >= 0
END T
"""
    prf={"T":"""(|T|
 (|ex_cubic| 0)
 (|ex_amgm| 0)
 (|ex_meet| 0)
 (|ex_hyp| 0)
)
"""}
    out=discover_normalized_exact_reuse({"T":src},prf)
    assert out["registry_collision_count"]==0
    got={x["formula"]:x["claim_id"] for x in out["matched"]}
    assert got["ex_cubic"]=="real.depressed_cubic_has_root@1"
    assert got["ex_amgm"]=="real.amgm2@1"
    assert got["ex_meet"]=="real.parabola_meets_unit_circle@1"
    assert got["ex_hyp"]=="real.zero_has_no_multiplicative_inverse@1"
    assert "fresh" not in got


def test_semantic_change_is_not_normalized_away():
    canonical=semantic_shape_key(
        "FORALL (c: real): EXISTS (x: real): x^3 - 3 * x + c = 0"
    )
    changed=semantic_shape_key(
        "FORALL (c: real): EXISTS (x: real): x^3 - 4 * x + c = 0"
    )
    assert canonical!=changed
