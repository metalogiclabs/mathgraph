from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/attempt002_snippet_inspection_v4_4_28")
SUMMARY = ROOT / "summary.json"
INSPECTION = ROOT / "snippet_inspection.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_28_attempt002_snippet_inspection.py")
DOC = Path("docs/sorrydb_v4_4_28_attempt002_snippet_inspection.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_reuses_cached_raw_files():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary_boundary():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.28"
    assert s["status"] == "ATTEMPT002_SNIPPET_INSPECTION_LEDGERED"
    assert s["input_version"] == "v4.4.27"
    assert s["inspected_candidate_count"] <= 5
    assert s["clone_attempted"] is False
    assert s["replay_attempted"] is False
    assert s["upstream_contact_performed"] is False
    assert "new Lean replay" in s["does_not_claim"]

def test_inspection_shape():
    x = load(INSPECTION)
    assert x["version"] == "v4.4.28"
    assert x["inspection_type"] == "ATTEMPT002_TOP_CANDIDATE_SNIPPET_INSPECTION"
    assert x["constraints"]["no_clone"] is True
    assert x["constraints"]["no_lean_replay"] is True
    assert x["constraints"]["no_upstream_contact"] is True
    assert isinstance(x["inspections"], list)
    assert len(x["inspections"]) <= 5

def test_selected_candidate_if_present_has_snippet():
    s = load(SUMMARY)
    x = load(INSPECTION)
    selected = x["selected_candidate"]
    if selected:
        assert selected["candidate_id"] == s["selected_candidate_id"]
        assert selected["fetch_ok"] is True
        assert selected["sorry_count"] > 0
        assert selected["windows"]
        assert "sorry" in selected["windows"][0]["snippet"]

def test_docs_and_report():
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
    assert "Selected candidate" in REPORT.read_text(encoding="utf-8")
    assert "No clone" in REPORT.read_text(encoding="utf-8")
