import json
from pathlib import Path

from mathgraph.cross_prover_sos_certificate import (
    claim_difference,
    compile_certificate_capability,
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


def test_warranted_source_compiles_to_certificate_capability():
    m=json.loads(MANIFEST.read_text())
    claim=m["canonical_claim"]
    cert=discover_linear_square_certificate(claim)
    authority=json.loads(Path("evidence/crystal-cross-prover-cad-v1.json").read_text())
    obj=compile_certificate_capability(claim,cert,authority)
    assert obj.id.startswith("semantic:")
    assert "certificate.sum-of-squares@1" in obj.interfaces


def test_unwarranted_source_cannot_promote_certificate():
    m=json.loads(MANIFEST.read_text())
    claim=m["canonical_claim"]
    cert=discover_linear_square_certificate(claim)
    authority=json.loads(Path("evidence/crystal-cross-prover-cad-v1.json").read_text())
    authority["status"]="CANDIDATE"
    try:
        compile_certificate_capability(claim,cert,authority)
    except ValueError:
        pass
    else:
        raise AssertionError("unwarranted source must fail closed")
