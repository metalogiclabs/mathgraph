import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_coordinate_checklist_lawbook_artifact_exists_and_is_bounded():
    path = ROOT / "artifacts" / "lawbook" / "finite_htilt_coordinate_envelope_checklist_v1.json"
    data = json.loads(path.read_text())

    assert data["artifact_id"] == "finite_htilt_coordinate_envelope_checklist_v1"
    assert data["status"] == "VERIFIED_PROOF"
    assert data["claim_type"] == "pure_real_list_algebra"

    proves = data["boundary"]["proves"]
    assert "bundled coordinate-envelope checklist predicate" in proves
    assert "checklist implies shifted dominance for every coordinate in a finite list" in proves

    nonclaims = set(data["boundary"]["does_not_prove"])
    assert "that the coordinate list is a matrix spectrum" in nonclaims
    assert "actual spectrum extraction from a matrix" in nonclaims
    assert "eigenvalue existence" in nonclaims
    assert "Perron-root alignment" in nonclaims
    assert "Perron-Frobenius invocation" in nonclaims

def test_coordinate_checklist_docs_keep_boundary():
    doc = (ROOT / "docs" / "finite_htilt_coordinate_envelope_checklist_v1.md").read_text()
    assert "bundled certificate/checklist layer" in doc
    assert "reusable certificate interface" in doc
    assert "does not prove that the coordinate list is a matrix spectrum" in doc
    assert "Perron-Frobenius invocation" in doc
