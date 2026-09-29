from mathgraph.cross_prover_family_discovery import (
    compile_family_bundle,
    discover_family,
    extract_pvs_lemmas,
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


def test_extraction_and_binder_normalization():
    rows=extract_pvs_lemmas(sources()["b"])
    assert len(rows)==2
    assert rows[0][1]==normalize_surface(
        "FORALL (x: real): FORALL (y: real): x > 0 AND y > 0 IMPLIES x * y > 0"
    )


def test_shape_discovery_deduplicates_without_using_names():
    out=discover_family(sources())
    assert out["source_lemma_count"]==5
    assert out["supported_occurrence_count"]==4
    assert out["unsupported_occurrence_count"]==1
    assert out["unique_canonical_claim_count"]==3
    dup=out["duplicate_semantic_groups"]
    assert len(dup)==1
    assert dup[0]["claim_id"]=="real.positive_product2@1"
    assert dup[0]["source_occurrence_count"]==2


def test_rendered_lean_skips_reused_claim():
    out=discover_family(sources())
    lean=render_lean_family(out,skip_claim_ids=["real.amgm2@1"])
    assert "amgm2_real" not in lean
    assert "positive_product2" in lean
    assert "order_split_zero" in lean


def test_family_bundle_requires_exact_qualified_partition():
    out=discover_family(sources())
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
