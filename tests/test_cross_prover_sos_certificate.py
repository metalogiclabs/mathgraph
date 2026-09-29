import json
from pathlib import Path

from mathgraph.cross_prover_sos_certificate import (
    claim_difference,
    discover_linear_square_certificate,
    render_lean_certificate_proof,
    verify_certificate,
)

MANIFEST=Path("experiments/crystal_cross_prover_cad_v1/manifest.json")


def test_amgm_source_claim_compiles_to_exact_square_certificate():
    claim=json.loads(MANIFEST.read_text())["canonical_claim"]
    cert=discover_linear_square_certificate(claim)
    assert cert is not None
    assert cert.to_dict()=={
        "type":"weighted_linear_square",
        "x":"1",
        "y":"-1",
        "constant":"0",
        "weight":"1",
    }
    assert verify_certificate(claim,cert)


def test_certificate_expands_to_exact_target_difference():
    claim=json.loads(MANIFEST.read_text())["canonical_claim"]
    cert=discover_linear_square_certificate(claim)
    assert cert is not None
    p=claim_difference(claim)
    assert p[(2,0)]==1
    assert p[(1,1)]==-2
    assert p[(0,2)]==1
    assert cert.polynomial()==p


def test_certificate_renders_closed_lean_check_not_search_prompt():
    claim=json.loads(MANIFEST.read_text())["canonical_claim"]
    cert=discover_linear_square_certificate(claim)
    proof=render_lean_certificate_proof(cert)
    assert "sq_nonneg" in proof
    assert "nlinarith" in proof
