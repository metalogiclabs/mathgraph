import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_modsq_residual_builder_lawbook_artifact_exists_and_is_bounded():
    path = ROOT / "artifacts" / "lawbook" / "finite_htilt_coordinate_modsq_residual_builder_v1.json"
    data = json.loads(path.read_text())

    assert data["artifact_id"] == "finite_htilt_coordinate_modsq_residual_builder_v1"
    assert data["status"] == "VERIFIED_PROOF"
    assert data["claim_type"] == "pure_real_list_algebra"
    assert "HTilt.CoordinateChecklist" in data["imports"]

    proves = data["boundary"]["proves"]
    assert "raw pointwise modulus-square residual evidence builds ResidualEnvelope a b B coords" in proves
    assert "raw residual evidence can feed the imported finite coordinate dominance master theorem" in proves

    nonclaims = set(data["boundary"]["does_not_prove"])
    assert "that any coordinate is an eigenvalue" in nonclaims
    assert "that the coordinate list is a matrix spectrum" in nonclaims
    assert "Perron-root alignment" in nonclaims
    assert "Perron-Frobenius invocation" in nonclaims

def test_modsq_residual_builder_docs_and_file_exist():
    lean_file = ROOT / "examples" / "verifier_fixtures" / "lean" / "htilt_coordinate_modsq_residual_builder.lean"
    doc = ROOT / "docs" / "finite_htilt_coordinate_modsq_residual_builder_v1.md"

    text = lean_file.read_text()
    assert "import HTilt.CoordinateChecklist" in text
    assert "modsq_residual_bound_builds_residual_envelope" in text
    assert "finite_coordinate_shifted_dominance_from_modsq_residual" in text

    doc_text = doc.read_text()
    assert "Modulus-Square Residual Builder" in doc_text
    assert "ResidualEnvelope" in doc_text
    assert "pre-spectral" in doc_text
