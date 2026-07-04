import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_coordinate_checklist_projection_lawbook_artifact_exists_and_is_bounded():
    path = ROOT / "artifacts" / "lawbook" / "finite_htilt_coordinate_checklist_projection_v1.json"
    data = json.loads(path.read_text())

    assert data["artifact_id"] == "finite_htilt_coordinate_checklist_projection_v1"
    assert data["status"] == "VERIFIED_PROOF"
    assert data["claim_type"] == "pure_real_list_algebra"

    proves = data["boundary"]["proves"]
    assert "projection from checklist to residual envelope" in proves
    assert "projection from checklist to positive-gap envelope" in proves
    assert "projection from checklist to explicit scalar shift bound" in proves

    nonclaims = set(data["boundary"]["does_not_prove"])
    assert "that the coordinate list is a matrix spectrum" in nonclaims
    assert "actual spectrum extraction from a matrix" in nonclaims
    assert "eigenvalue existence" in nonclaims
    assert "Perron-root alignment" in nonclaims
    assert "Perron-Frobenius invocation" in nonclaims

def test_coordinate_checklist_projection_docs_keep_boundary():
    doc = (ROOT / "docs" / "finite_htilt_coordinate_checklist_projection_v1.md").read_text()
    assert "projection lemmas" in doc
    assert "reusable certificate object" in doc
    assert "does not prove that the coordinate list is a matrix spectrum" in doc
    assert "Perron-Frobenius invocation" in doc
