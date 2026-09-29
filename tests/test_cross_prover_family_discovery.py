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
a3: LEMMA EXISTS (x: real): x^2 = 2
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
