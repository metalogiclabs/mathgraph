from mathgraph.cross_prover_consequence_search import (
    RELATION_KIND,
    alpha_normalize_surface,
    discover_consequence_routes,
    render_lean_adapters,
)


AVAILABLE = {
    "real.square_shift_dominates@1",
    "real.amgm2@1",
    "real.sum_squares_has_root@1",
    "real.circle_or_outside@1",
    "real.common_upper_bound2@1",
    "real.unbounded_above@1",
}


def heldout_residual_sources():
    return {
        "renamed3": """
T3: THEORY
BEGIN
foo: LEMMA (FORALL (a: real): FORALL (b: real): EXISTS (c: real): c > a AND c < b)
  IMPLIES FALSE
bar: LEMMA (EXISTS (a: real): FORALL (b: real): EXISTS (c: real): c * c = b - a)
  IMPLIES FALSE
baz: LEMMA FORALL (a: real): EXISTS (b: real): FORALL (c: real): c * c + b > a
qux: LEMMA FORALL (a: real): FORALL (b: real): FORALL (c: real):
  a^2 + b^2 + c^2 >= 2 * a * b
sphere: LEMMA FORALL (a: real): FORALL (b: real): EXISTS (c: real):
  a^2 + b^2 + c^2 = 1 OR a^2 + b^2 > 1
END T3
""",
        "renamed4": """
T4: THEORY
BEGIN
top3: LEMMA FORALL (a: real): FORALL (b: real): FORALL (c: real): EXISTS (d: real):
  d > a AND d > b AND d > c
bad3: LEMMA (FORALL (a: real): FORALL (b: real): FORALL (c: real): EXISTS (d: real):
  d > a AND d > b AND d < c) IMPLIES FALSE
altsum: LEMMA FORALL (a: real): EXISTS (b: real): FORALL (c: real): EXISTS (d: real):
  d > a + b + c
END T4
""",
    }


def test_alpha_normalization_ignores_bound_variable_names():
    a=alpha_normalize_surface(
        "FORALL (x: real): EXISTS (y: real): FORALL (z: real): z * z + y > x"
    )
    b=alpha_normalize_surface(
        "FORALL (foo: real): EXISTS (bar: real): FORALL (baz: real): baz * baz + bar > foo"
    )
    assert a==b


def test_five_heldout_routes_found_without_theorem_names():
    out=discover_consequence_routes(
        heldout_residual_sources(),
        available_claim_ids=sorted(AVAILABLE),
    )
    assert out["relation_kind"]==RELATION_KIND
    assert out["source_lemma_count"]==8
    assert out["routed_occurrence_count"]==5
    assert out["unresolved_occurrence_count"]==3
    assert out["ambiguous_occurrence_count"]==0
    assert {x["formula"] for x in out["routes"]}=={
        "baz","qux","sphere","top3","altsum",
    }
    assert {x["formula"] for x in out["unresolved"]}=={
        "foo","bar","bad3",
    }
    lean=render_lean_adapters(out)
    assert "heldout_shift_from_square_shift" in lean
    assert "heldout_sos_from_amgm2" in lean
    assert "heldout_sphere_from_root_circle" in lean
    assert "heldout_upper3_from_upper2" in lean
    assert "heldout_sum_from_unbounded" in lean


def test_exact_ablation_removes_each_route():
    expected={
        "real.square_shift_dominates@1":"baz",
        "real.amgm2@1":"qux",
        "real.sum_squares_has_root@1":"sphere",
        "real.circle_or_outside@1":"sphere",
        "real.common_upper_bound2@1":"top3",
        "real.unbounded_above@1":"altsum",
    }
    base=discover_consequence_routes(
        heldout_residual_sources(),
        available_claim_ids=sorted(AVAILABLE),
    )
    assert base["routed_occurrence_count"]==5
    for claim_id, formula in expected.items():
        out=discover_consequence_routes(
            heldout_residual_sources(),
            available_claim_ids=sorted(AVAILABLE-{claim_id}),
        )
        assert formula not in {x["formula"] for x in out["routes"]}
        row=next(x for x in out["unresolved"] if x["formula"]==formula)
        assert row["status"]=="UNKNOWN_MISSING_PREREQUISITE"
        assert claim_id in row["missing_prerequisite_claim_ids"]


def test_sham_capability_set_finds_no_route():
    out=discover_consequence_routes(
        heldout_residual_sources(),
        available_claim_ids=[f"sham.claim.{i}@1" for i in range(6)],
    )
    assert out["routed_occurrence_count"]==0
    assert out["unresolved_occurrence_count"]==8
