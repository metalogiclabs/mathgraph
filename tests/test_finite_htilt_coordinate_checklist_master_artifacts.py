import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_coordinate_checklist_master_lawbook_artifact_exists_and_is_bounded():
    path = ROOT / "artifacts" / "lawbook" / "finite_htilt_coordinate_checklist_master_v1.json"
    data = json.loads(path.read_text())

    assert data["artifact_id"] == "finite_htilt_coordinate_checklist_master_v1"
    assert data["status"] == "VERIFIED_PROOF"
    assert data["claim_type"] == "pure_real_list_algebra"

    proves = data["boundary"]["proves"]
    assert "canonical finite-coordinate shifted-dominance theorem" in proves
    assert "pointwise residual evidence can be consumed directly" in proves
    assert "pointwise positive-gap evidence can be consumed directly" in proves
    assert "bundled checklist implies the same finite-coordinate shifted dominance" in proves

    nonclaims = set(data["boundary"]["does_not_prove"])
    assert "that any coordinate is an eigenvalue" in nonclaims
    assert "that the coordinate list is a matrix spectrum" in nonclaims
    assert "actual spectrum extraction from a matrix" in nonclaims
    assert "Perron-root alignment" in nonclaims
    assert "Perron-Frobenius invocation" in nonclaims

def test_coordinate_checklist_master_docs_keep_boundary():
    doc = (ROOT / "docs" / "finite_htilt_coordinate_checklist_master_v1.md").read_text()
    assert "canonical compressed theorem" in doc
    assert "headline Lawbook theorem" in doc
    assert "does not prove that any coordinate is an eigenvalue" in doc
    assert "Perron-Frobenius invocation" in doc
