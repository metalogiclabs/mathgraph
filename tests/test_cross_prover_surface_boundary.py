from mathgraph.cross_prover_surface_boundary import (
    classify_real_object_surface,
    classify_source_family,
)


def test_closed_real_formula_is_object_level():
    out=classify_real_object_surface(
        "EXISTS (x: real): x^2 - 1 = 0 AND x > 0"
    )
    assert out["status"]=="OBJECT_LEVEL_CLOSED_REAL_ARITHMETIC"
    assert out["unsupported_identifiers"]==[]


def test_prover_internal_symbols_stay_unknown():
    out=classify_real_object_surface(
        "tq(6, P1, Q1, null[real]) = 0"
    )
    assert out["status"]=="UNKNOWN_PROVER_INTERNAL_OR_UNSUPPORTED_SYMBOL"
    assert {"tq","P1","Q1","null"}.issubset(set(out["unsupported_identifiers"]))


def test_free_real_variable_is_not_silently_closed():
    out=classify_real_object_surface(
        "meval(mpol(P1))(cons(x, null)) = x^2 - 1"
    )
    assert out["status"]=="UNKNOWN_PROVER_INTERNAL_OR_UNSUPPORTED_SYMBOL"
    assert "x" in out["unsupported_identifiers"]


def test_tarski_shape_partition():
    src="""
T: THEORY
BEGIN
e1: LEMMA tq(6, P1, Q1, null[real]) = 0
e4: LEMMA meval(mpol(P1))(cons(x, null)) = x^2 - 1
e6: LEMMA EXISTS (x: real): x^2 - 1 = 0 AND x > 0
e8: LEMMA NOT (EXISTS (x: real): x^2 - 1 = 0 AND -x^2 > 0)
END T
"""
    out=classify_source_family({"T":src})
    assert out["object_level_count"]==2
    assert out["typed_unknown_count"]==2
    assert {x["formula"] for x in out["object_level"]}=={"e6","e8"}
    assert {x["formula"] for x in out["typed_unknown"]}=={"e1","e4"}
