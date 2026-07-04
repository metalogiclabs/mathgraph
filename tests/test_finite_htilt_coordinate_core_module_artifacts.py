import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_coordinate_core_module_lawbook_artifact_exists_and_is_bounded():
    path = ROOT / "artifacts" / "lawbook" / "finite_htilt_coordinate_core_module_v1.json"
    data = json.loads(path.read_text())

    assert data["artifact_id"] == "finite_htilt_coordinate_core_module_v1"
    assert data["status"] == "VERIFIED_PROOF"
    assert data["claim_type"] == "lean_core_module_refactor"
    assert data["import_path"] == "HTilt.CoordinateChecklist"

    proves = data["boundary"]["proves"]
    assert "reusable HTilt Lean library target exists" in proves
    assert "HTilt.CoordinateChecklist core module compiles" in proves
    assert "downstream fixture can import HTilt.CoordinateChecklist" in proves
    assert "downstream fixture can reuse finite_coordinate_shifted_dominance_master" in proves

    nonclaims = set(data["boundary"]["does_not_prove"])
    assert "that any coordinate is an eigenvalue" in nonclaims
    assert "that the coordinate list is a matrix spectrum" in nonclaims
    assert "Perron-root alignment" in nonclaims
    assert "Perron-Frobenius invocation" in nonclaims

def test_coordinate_core_module_docs_and_files_exist():
    core = ROOT / "experiments" / "continuation_claim_audit_lab" / "lean_project" / "HTilt" / "CoordinateChecklist.lean"
    smoke = ROOT / "examples" / "verifier_fixtures" / "lean" / "htilt_coordinate_core_import_smoke.lean"
    lakefile = ROOT / "experiments" / "continuation_claim_audit_lab" / "lean_project" / "lakefile.toml"
    doc = ROOT / "docs" / "finite_htilt_coordinate_core_module_v1.md"

    assert core.exists()
    assert smoke.exists()
    assert "import HTilt.CoordinateChecklist" in smoke.read_text()
    assert "[[lean_lib]]" in lakefile.read_text()
    assert 'name = "HTilt"' in lakefile.read_text()
    assert "reusable Lean core module" in doc.read_text()
