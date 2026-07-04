import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_positive_gap_lawbook_artifact_exists_and_is_bounded():
    path = ROOT / "artifacts" / "lawbook" / "finite_htilt_shift_bound_from_positive_gap_v1.json"
    data = json.loads(path.read_text())

    assert data["artifact_id"] == "finite_htilt_shift_bound_from_positive_gap_v1"
    assert data["status"] == "VERIFIED_PROOF"
    assert data["claim_type"] == "pure_real_list_algebra"

    proves = data["boundary"]["proves"]
    assert "positive-gap finite-list shift bound" in proves
    assert "single computable scalar inequality B < 2*c*δ implies dominance under gap and residual assumptions" in proves

    nonclaims = set(data["boundary"]["does_not_prove"])
    assert "actual spectrum extraction from a matrix" in nonclaims
    assert "construction of B from a matrix spectrum" in nonclaims
    assert "construction of δ from a matrix spectral gap" in nonclaims
    assert "Perron-root alignment" in nonclaims
    assert "Perron-Frobenius invocation" in nonclaims

def test_positive_gap_docs_keep_boundary():
    doc = (ROOT / "docs" / "finite_htilt_shift_bound_from_positive_gap_v1.md").read_text()
    assert "single scalar shift condition" in doc
    assert "purely real/list algebra" in doc
    assert "does not prove actual spectrum extraction" in doc
    assert "Perron-Frobenius invocation" in doc
