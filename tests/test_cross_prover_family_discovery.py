from mathgraph.cross_prover_family_discovery import (
    annotate_replayability,
    compile_family_bundle,
    discover_family,
    extract_pvs_lemmas,
    extract_pvs_proved_formulas,
    normalize_surface,
    render_lean_family,
)


def sources():
    return {
        "a": """
T: THEORY
BEGIN
a1: LEMMA FORALL (x: real): FORALL (y: real): x^2 + y^2 >= 2 * x * y
a2: LEMMA FORALL (x: real): FORALL (y: real): x > 0 AND y > 0 IMPLIES x * y > 0
a3: LEMMA EXISTS (x: real): x^3 = 2
END T
""",
        "b": """
U: THEORY
BEGIN
b1: LEMMA FORALL (x, y: real): x > 0 AND y > 0 IMPLIES x * y > 0
b2: LEMMA FORALL (x: real): x < 0 OR x >= 0
END U
""",
    }


def proofs():
    return {
        "a": """(|T|
 (|a1| 0 (|a1-0| "" 1 ("" (CAD) NIL NIL) NIL SHOSTAK))
)
""",
        "b": """(|U|
 (|b1| 0 (|b1-0| "" 1 ("" (CAD *) NIL NIL) NIL SHOSTAK))
 (|b2| 0 (|b2-0| "" 1 ("" (CAD *) NIL NIL) NIL SHOSTAK))
)
""",
    }


def test_extraction_and_binder_normalization():
    rows=extract_pvs_lemmas(sources()["b"])
    assert len(rows)==2
    assert rows[0][1]==normalize_surface(
        "FORALL (x: real): FORALL (y: real): x > 0 AND y > 0 IMPLIES x * y > 0"
    )


def test_shape_discovery_deduplicates_without_using_names():
    out=discover_family(sources(),proofs())
    assert out["source_lemma_count"]==5
    assert out["supported_occurrence_count"]==4
    assert out["source_verified_occurrence_count"]==3
    assert out["source_unverified_supported_occurrence_count"]==1
    assert out["unsupported_occurrence_count"]==1
    assert out["unique_canonical_claim_count"]==3
    assert out["verified_unique_claim_count"]==3
    dup=out["duplicate_semantic_groups"]
    assert len(dup)==1
    assert dup[0]["claim_id"]=="real.positive_product2@1"
    assert dup[0]["source_occurrence_count"]==2
    assert dup[0]["source_authority_occurrence_count"]==1
    assert dup[0]["source_unverified_occurrence_count"]==1


def test_rendered_lean_skips_reused_claim():
    out=discover_family(sources(),proofs())
    lean=render_lean_family(out,skip_claim_ids=["real.amgm2@1"])
    assert "amgm2_real" not in lean
    assert "positive_product2" in lean
    assert "order_split_zero" in lean


def test_family_bundle_requires_exact_qualified_partition():
    out=discover_family(sources(),proofs())
    obj=compile_family_bundle(
        out,
        reused_claim_ids=["real.amgm2@1"],
        newly_qualified_claim_ids=[
            "real.positive_product2@1",
            "real.order_split_zero@1",
        ],
        evidence_refs=["run:test"],
    )
    assert obj.id.startswith("semantic:")
    assert "cross-prover.claim-family@1" in obj.interfaces


def test_proof_file_extractor_reads_only_top_level_formula_entries():
    prf="""(|T|
 (|a1| 0
  (|a1-0| "" 1 ("" (CAD) NIL NIL) NIL SHOSTAK))
 (|a1_TCC1| 0
  (|a1_TCC1-1| "" 1 ("" (SUBTYPE-TCC) NIL NIL) NIL SHOSTAK))
)
"""
    assert extract_pvs_proved_formulas(prf)=={"a1","a1_TCC1"}


def test_unique_claim_without_pinned_source_proof_stays_out_of_consumer_family():
    ps=proofs()
    ps["b"]="""(|U|
 (|b1| 0 (|b1-0| "" 1 ("" (CAD *) NIL NIL) NIL SHOSTAK))
)
"""
    out=discover_family(sources(),ps)
    assert out["verified_unique_claim_count"]==2
    order=next(x for x in out["unique_claims"] if x["claim_id"]=="real.order_split_zero@1")
    assert order["source_authority_status"]=="UNKNOWN_SOURCE_UNVERIFIED"
    lean=render_lean_family(out)
    assert "order_split_zero" not in lean


def test_replayability_is_distinct_from_semantic_discovery():
    out=discover_family(sources())
    annotated=annotate_replayability(
        out,
        {
            "a":"(|T| (|a1| 0 (|a1-0| \"\" 1 (\"\" (CAD) NIL NIL) NIL NIL)))",
            "b":"(|U| (|b1| 0 (|b1-0| \"\" 1 (\"\" (CAD) NIL NIL) NIL NIL)))",
        },
    )
    assert annotated["replayable_supported_occurrence_count"]==2
    assert annotated["unreplayable_supported_occurrence_count"]==2
    assert annotated["qualifiable_unique_claim_count"]==2
    amgm=next(x for x in annotated["unique_claims"] if x["claim_id"]=="real.amgm2@1")
    assert amgm["replayable_occurrence_count"]==1
    order=next(x for x in annotated["unique_claims"] if x["claim_id"]=="real.order_split_zero@1")
    assert order["source_qualification_status"]=="UNKNOWN_NO_REPLAYABLE_SOURCE"


def test_v2_explicit_witness_constructor_spans_quantifier_shapes():
    src={
        "q": """
Q: THEORY
BEGIN
a: LEMMA FORALL (x: real): EXISTS (y: real): y > x
b: LEMMA EXISTS (x: real): FORALL (y: real): x * y = 0
c: LEMMA FORALL (x: real): FORALL (y: real): EXISTS (z: real): FORALL (w: real): w^2 + z > x + y
END Q
"""
    }
    prf={
        "q": """(|Q|
 (|a| 0)
 (|b| 0)
 (|c| 0)
)
"""
    }
    out=discover_family(src,prf)
    assert out["supported_occurrence_count"]==3
    assert out["unique_canonical_claim_count"]==3
    assert out["verified_unique_claim_count"]==3
    assert {x["certificate_schema"] for x in out["unique_claims"]}=={"explicit_witness"}
    lean=render_lean_family(out)
    assert "exists_above_real" in lean
    assert "zero_annihilator_real" in lean
    assert "square_shift_dominates" in lean


def test_v3_algebraic_root_constructor_spans_root_shapes():
    src={
        "q": """
Q: THEORY
BEGIN
a: LEMMA EXISTS (x: real): x^2 = 2
b: LEMMA FORALL (x: real): x > 0 IMPLIES EXISTS (y: real): y * y = x
c: LEMMA FORALL (x: real): FORALL (y: real): EXISTS (z: real): z^2 = x^2 + y^2
d: LEMMA FORALL (x: real): EXISTS (y: real): x^2 + y^2 = 1 OR x^2 > 1
END Q
"""
    }
    prf={"q": """(|Q|
 (|a| 0)
 (|b| 0)
 (|c| 0)
 (|d| 0)
)
"""}
    out=discover_family(src,prf)
    assert out["supported_occurrence_count"]==4
    assert out["unique_canonical_claim_count"]==4
    assert out["verified_unique_claim_count"]==4
    assert {x["certificate_schema"] for x in out["unique_claims"]}=={"algebraic_root_witness"}
    lean=render_lean_family(out)
    assert "sqrt_two_exists" in lean
    assert "positive_has_square_root" in lean
    assert "sum_squares_has_root" in lean
    assert "circle_or_outside" in lean


def test_v4_quantifier_witness_duality_spans_polarities():
    src={
        "q": """
Q: THEORY
BEGIN
a: LEMMA NOT (FORALL (x: real): EXISTS (y: real): x * y = 1)
b: LEMMA FORALL (b, c: real): (FORALL (z: real): z^2 + b * z + c > 0) IMPLIES b^2 < 4 * c
c: LEMMA FORALL (a: real): a > 0 IMPLIES (FORALL (z: real): EXISTS (w: real): w * a > z)
d: LEMMA FORALL (c: real): (FORALL (z: real): EXISTS (w: real): w > z AND w * c > 1) IMPLIES c > 0
e: LEMMA FORALL (a: real): (EXISTS (u, v: real): u * u + v * v = a) IMPLIES a >= 0
END Q
"""
    }
    prf={"q": """(|Q|
 (|a| 0)
 (|b| 0)
 (|c| 0)
 (|d| 0)
 (|e| 0)
)
"""}
    out=discover_family(src,prf)
    assert out["supported_occurrence_count"]==5
    assert out["unique_canonical_claim_count"]==5
    assert out["verified_unique_claim_count"]==5
    assert {x["certificate_schema"] for x in out["unique_claims"]}=={"quantifier_witness_duality"}
    lean=render_lean_family(out)
    assert "zero_has_no_multiplicative_inverse" in lean
    assert "positive_quadratic_discriminant_negative" in lean
    assert "positive_scale_unbounded_above" in lean
    assert "unbounded_positive_product_forces_positive_factor" in lean
    assert "sum_two_squares_parameter_nonnegative" in lean


def test_v5_final_true_pair_has_distinct_mechanisms():
    src={
        "q": """
Q: THEORY
BEGIN
a: LEMMA EXISTS (x: real): EXISTS (y: real): x^2 + y^2 = 1 AND y = x^2
b: LEMMA FORALL (c: real): EXISTS (x: real): x^3 - 3 * x + c = 0
END Q
"""
    }
    prf={"q": """(|Q|
 (|a| 0)
 (|b| 0)
)
"""}
    out=discover_family(src,prf)
    assert out["supported_occurrence_count"]==2
    assert out["unique_canonical_claim_count"]==2
    schemas={x["claim_id"]:x["certificate_schema"] for x in out["unique_claims"]}
    assert schemas["real.parabola_meets_unit_circle@1"]=="composed_algebraic_witness"
    assert schemas["real.depressed_cubic_has_root@1"]=="bounded_intermediate_value"
    lean=render_lean_family(out)
    assert "parabola_meets_unit_circle" in lean
    assert "every_depressed_cubic_has_real_root" in lean
