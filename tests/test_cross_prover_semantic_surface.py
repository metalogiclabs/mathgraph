import json
from pathlib import Path

import pytest

from mathgraph.cross_prover_semantic_surface import (
    CrossProverAuthority,
    compile_cross_prover_capability,
    render_lean_file,
    render_pvs_claim,
    verify_pvs_source_surface,
)

MANIFEST = Path("experiments/crystal_cross_prover_cad_v1/manifest.json")


def test_pvs_renderer_matches_exact_demo_surface():
    m=json.loads(MANIFEST.read_text())
    source="""
cad_demo: THEORY
BEGIN
  d_amgm: LEMMA FORALL (x: real): FORALL (y: real): x^2 + y^2 >= 2 * x * y
END cad_demo
"""
    result=verify_pvs_source_surface(m,source)
    assert result["status"]=="EXACT_CANONICAL_SURFACE_MATCH"
    assert result["pvs_formula"]==render_pvs_claim(m)


def test_lean_renderer_carries_same_canonical_claim():
    m=json.loads(MANIFEST.read_text())
    lean=render_lean_file(m)
    assert "theorem amgm2_real (x y : ℝ)" in lean
    assert "x ^ 2 + y ^ 2 ≥ 2 * x * y" in lean
    assert "nlinarith [sq_nonneg (x - y)]" in lean


def test_capability_requires_explicit_dual_verifier_authority():
    m=json.loads(MANIFEST.read_text())
    obj=compile_cross_prover_capability(
        m,
        CrossProverAuthority(
            pvs_replay_ref="github-run:pvs",
            lean_replay_ref="github-run:lean",
            source_match_ref="source-match:sha256",
        ),
    )
    assert obj.id.startswith("semantic:")
    assert "real.polynomial.amgm2@1" in obj.interfaces
    assert "provenance.cross-prover@1" in obj.interfaces


def test_surface_mismatch_fails_closed():
    m=json.loads(MANIFEST.read_text())
    bad="d_amgm: LEMMA FORALL (x: real): FORALL (y: real): x^2 + y^2 >= 3 * x * y"
    with pytest.raises((ValueError,AssertionError)):
        verify_pvs_source_surface(m,bad)
