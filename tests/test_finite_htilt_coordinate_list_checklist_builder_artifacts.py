import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_coordinate_list_checklist_builder_lawbook_artifact_exists_and_is_bounded():
    path = ROOT / "artifacts" / "lawbook" / "finite_htilt_coordinate_list_checklist_builder_v1.json"
    data = json.loads(path.read_text())

    assert data["artifact_id"] == "finite_htilt_coordinate_list_checklist_builder_v1"
    assert data["status"] == "VERIFIED_PROOF"
    assert data["claim_type"] == "pure_real_list_algebra"

    proves = data["boundary"]["proves"]
    assert "pointwise residual evidence builds a residual envelope" in proves
    assert "pointwise positive-gap evidence builds a positive-gap envelope" in proves
    assert "finite-list coordinate-envelope checklist builder" in proves
    assert "finite-list checklist evidence implies shifted dominance for every coordinate" in proves

    nonclaims = set(data["boundary"]["does_not_prove"])
    assert "that any coordinate is an eigenvalue" in nonclaims
    assert "that the coordinate list is a matrix spectrum" in nonclaims
    assert "actual spectrum extraction from a matrix" in nonclaims
    assert "Perron-root alignment" in nonclaims
    assert "Perron-Frobenius invocation" in nonclaims

def test_coordinate_list_checklist_builder_docs_keep_boundary():
    doc = (ROOT / "docs" / "finite_htilt_coordinate_list_checklist_builder_v1.md").read_text()
    assert "direct finite-list builder" in doc
    assert "compresses that construction" in doc
    assert "does not prove that any coordinate is an eigenvalue" in doc
    assert "Perron-Frobenius invocation" in doc
