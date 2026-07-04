import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_gap_envelope_from_witness_lawbook_artifact_exists_and_is_bounded():
    path = ROOT / "artifacts" / "lawbook" / "finite_htilt_coordinate_gap_envelope_from_witness_v1.json"
    data = json.loads(path.read_text())

    assert data["artifact_id"] == "finite_htilt_coordinate_gap_envelope_from_witness_v1"
    assert data["status"] == "VERIFIED_PROOF"
    assert data["claim_type"] == "pure_real_list_algebra"
    assert "HTilt.CoordinateChecklist" in data["imports"]

    proves = data["boundary"]["proves"]
    assert "strict real-part gap witness builds PositiveGapEnvelope a δ coords" in proves
    assert "raw residual and strict-gap witnesses build CoordinateEnvelopeChecklist c a b B δ coords" in proves
    assert "raw residual and strict-gap witnesses imply shifted dominance through the reusable core API" in proves

    nonclaims = set(data["boundary"]["does_not_prove"])
    assert "that any coordinate is an eigenvalue" in nonclaims
    assert "that the coordinate list is a matrix spectrum" in nonclaims
    assert "Perron-root alignment" in nonclaims
    assert "Perron-Frobenius invocation" in nonclaims

def test_gap_envelope_from_witness_docs_and_file_exist():
    lean_file = ROOT / "examples" / "verifier_fixtures" / "lean" / "htilt_coordinate_gap_envelope_from_witness.lean"
    doc = ROOT / "docs" / "finite_htilt_coordinate_gap_envelope_from_witness_v1.md"

    text = lean_file.read_text()
    assert "import HTilt.CoordinateChecklist" in text
    assert "positive_gap_envelope_from_delta_witness" in text
    assert "checklist_from_raw_witnesses" in text
    assert "dominance_from_raw_witnesses" in text

    doc_text = doc.read_text()
    assert "Gap Envelope From Witness" in doc_text
    assert "PositiveGapEnvelope" in doc_text
    assert "pre-spectral" in doc_text
