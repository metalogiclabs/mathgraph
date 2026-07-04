import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_raw_evidence_numeric_smoke_lawbook_artifact_exists_and_is_bounded():
    path = ROOT / "artifacts" / "lawbook" / "finite_htilt_coordinate_raw_evidence_numeric_smoke_v1.json"
    data = json.loads(path.read_text())

    assert data["artifact_id"] == "finite_htilt_coordinate_raw_evidence_numeric_smoke_v1"
    assert data["status"] == "VERIFIED_PROOF"
    assert data["claim_type"] == "concrete_pure_real_list_algebra_smoke"
    assert "HTilt.CoordinateChecklist" in data["imports"]

    claim = data["claim"]
    assert claim["target_coordinate"] == "(2, 0)"
    assert claim["competitor_list"] == "[(0, 0)]"
    assert claim["B"] == 4
    assert claim["δ"] == 1
    assert claim["c"] == 3
    assert claim["numeric_shifted_comparison"] == "9 < 25"

    nonclaims = set(data["boundary"]["does_not_prove"])
    assert "that any coordinate is an eigenvalue" in nonclaims
    assert "that the coordinate list is a matrix spectrum" in nonclaims
    assert "Perron-root alignment" in nonclaims
    assert "Perron-Frobenius invocation" in nonclaims

def test_raw_evidence_numeric_smoke_docs_and_file_exist():
    lean_file = ROOT / "examples" / "verifier_fixtures" / "lean" / "htilt_coordinate_raw_evidence_numeric_smoke.lean"
    doc = ROOT / "docs" / "finite_htilt_coordinate_raw_evidence_numeric_smoke_v1.md"

    text = lean_file.read_text()
    assert "import HTilt.CoordinateChecklist" in text
    assert "import Mathlib.Tactic.NormNum" in text
    assert "numeric_singleton_raw_evidence_smoke" in text
    assert "finite_coordinate_shifted_dominance_from_raw_evidence" in text

    doc_text = doc.read_text()
    assert "Numeric Smoke" in doc_text
    assert "9 < 25" in doc_text
    assert "finite-coordinate arithmetic smoke" in doc_text
