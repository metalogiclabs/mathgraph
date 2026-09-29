from mathgraph.cross_prover_negative_controls import (
    discover_negative_controls,
    render_lean_negative_controls,
)


def test_negative_controls_are_shape_driven_and_never_promoted():
    sources={
        "q": """
Q: THEORY
BEGIN
x1: LEMMA FORALL (x: real): EXISTS (y: real): x * y = 1
x2: LEMMA FORALL (x, y: real): x^2 + y^2 >= 3 * x * y
END Q
"""
    }
    out=discover_negative_controls(sources)
    assert out["negative_count"]==2
    assert out["status"]=="CANDIDATE_COUNTERMODELS"
    assert {x["disposition"] for x in out["negative_controls"]} == {
        "REJECTED_BY_VERIFIED_COUNTERMODEL"
    }
    assert {x["formula"] for x in out["negative_controls"]} == {"x1","x2"}
    lean=render_lean_negative_controls(out)
    assert "d_inverse_countermodel" in lean
    assert "t_amgm3_countermodel" in lean
    assert "¬ (∀ x : ℝ, ∃ y : ℝ, x * y = 1)" in lean
