from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/commented_sorry_filter_v4_4_31")
SUMMARY = ROOT / "summary.json"
LEDGER = ROOT / "commented_sorry_filter.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_31_commented_sorry_filter.py")
DOC = Path("docs/sorrydb_v4_4_31_commented_sorry_filter.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary_boundary_and_previous_parked():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.31"
    assert s["status"] == "COMMENTED_SORRY_FILTER_LEDGERED"
    assert s["input_version"] == "v4.4.30"
    assert s["previous_selected_status"] == "PARKED_COMMENTED_SORRY_ONLY"
    assert s["clone_attempted"] is False
    assert s["build_attempted"] is False
    assert s["replay_attempted"] is False
    assert s["upstream_contact_performed"] is False

def test_ledger_shape():
    x = load(LEDGER)
    assert x["version"] == "v4.4.31"
    assert x["filter_type"] == "COMMENTED_SORRY_FILTER_AND_ACTIVE_TARGET_RESELECTOR"
    assert x["constraints"]["cached_source_only"] is True
    assert x["constraints"]["no_clone"] is True
    assert x["constraints"]["no_lean_replay"] is True
    assert x["evaluated_candidate_count"] >= x["active_candidate_count"]
    assert x["parked_comment_only_count"] >= 1

def test_selected_candidate_if_any_is_active():
    s = load(SUMMARY)
    x = load(LEDGER)
    selected = x["selected_candidate"]
    if selected:
        assert selected["candidate_id"] == s["selected_candidate_id"]
        assert selected["active_sorry_count"] > 0
        assert selected["status"] == "ACTIVE_SORRY_REPLAY_CANDIDATE"

def test_docs_and_report():
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
    assert "Commented Sorry Filter" in REPORT.read_text(encoding="utf-8")
    assert "No clone" in REPORT.read_text(encoding="utf-8")
