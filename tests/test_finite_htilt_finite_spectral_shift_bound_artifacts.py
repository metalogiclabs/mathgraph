import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_finite_spectral_bound_lawbook_artifact_exists_and_is_bounded():
    path = ROOT / "artifacts" / "lawbook" / "finite_htilt_finite_spectral_shift_bound_v1.json"
    data = json.loads(path.read_text())

    assert data["artifact_id"] == "finite_htilt_finite_spectral_shift_bound_v1"
    assert data["status"] == "VERIFIED_PROOF"
    assert data["claim_type"] == "pure_real_list_algebra"

    proves = data["boundary"]["proves"]
    assert "finite-list lift of pairwise dominance" in proves
    assert "finite-list lift from a shared residual envelope B" in proves

    nonclaims = set(data["boundary"]["does_not_prove"])
    assert "actual spectrum extraction from a matrix" in nonclaims
    assert "Perron-root alignment" in nonclaims
    assert "Perron-Frobenius invocation" in nonclaims
    assert "Markov convergence" in nonclaims

def test_finite_spectral_bound_docs_keep_boundary():
    doc = (ROOT / "docs" / "finite_htilt_finite_spectral_shift_bound_v1.md").read_text()
    assert "finite-list lift" in doc
    assert "safe algebraic boundary" in doc
    assert "does not prove actual spectrum extraction" in doc
    assert "Perron-Frobenius invocation" in doc
