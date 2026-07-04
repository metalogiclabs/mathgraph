import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_artifact_and_boundary():
    data = json.loads((ROOT / "artifacts/lawbook/finite_htilt_coordinate_raw_evidence_core_v1.json").read_text())
    assert data["status"] == "VERIFIED_PROOF"
    names = " ".join(data["verified_declarations"])
    assert "raw_modsq_residual_builds_residual_envelope" in names
    assert "finite_coordinate_shifted_dominance_from_raw_evidence" in names
    nonclaims = " ".join(data["boundary"]["does_not_prove"]).lower()
    for term in ("eigenvalue", "matrix spectrum", "perron-root", "perron-frobenius"):
        assert term in nonclaims

def test_core_and_smoke_fixture():
    core = (ROOT / "experiments/continuation_claim_audit_lab/lean_project/HTilt/CoordinateChecklist.lean").read_text()
    smoke = (ROOT / "examples/verifier_fixtures/lean/htilt_coordinate_raw_evidence_core_smoke.lean").read_text()
    assert "theorem coordinate_envelope_checklist_from_raw_evidence" in core
    assert "theorem finite_coordinate_shifted_dominance_from_raw_evidence" in core
    assert "import HTilt.CoordinateChecklist" in smoke
    assert "smoke_raw_evidence_checklist_from_core" in smoke
