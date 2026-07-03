import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_spectral_shift_lawbook_artifact_exists_and_is_bounded():
    path = ROOT / "artifacts" / "lawbook" / "finite_htilt_spectral_shift_order_v1.json"
    data = json.loads(path.read_text())

    assert data["artifact_id"] == "finite_htilt_spectral_shift_order_v1"
    assert data["status"] == "VERIFIED_PROOF"
    assert data["claim_type"] == "pure_real_algebra"

    proves = data["boundary"]["proves"]
    assert "pure real shifted squared-modulus identity" in proves
    assert "sufficient real inequality for shifted modulus dominance" in proves

    nonclaims = set(data["boundary"]["does_not_prove"])
    assert "Perron-root alignment" in nonclaims
    assert "Perron-Frobenius invocation" in nonclaims
    assert "Markov convergence" in nonclaims

def test_spectral_shift_docs_keep_boundary():
    doc = (ROOT / "docs" / "finite_htilt_spectral_shift_order_v1.md").read_text()
    assert "pure real algebra" in doc
    assert "does not invoke Perron-Frobenius" in doc
    assert "does not prove any matrix spectral theorem" in doc
