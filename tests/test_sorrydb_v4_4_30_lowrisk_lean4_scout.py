from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/lowrisk_lean4_scout_v4_4_30")
SUMMARY = ROOT / "summary.json"
SCOUT = ROOT / "lowrisk_lean4_scout.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_30_lowrisk_lean4_scout.py")
DOC = Path("docs/sorrydb_v4_4_30_lowrisk_lean4_scout.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_reuses_cache():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary_boundary():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.30"
    assert s["status"] == "LOWRISK_LEAN4_SCOUT_LEDGERED"
    assert s["input_version"] == "v4.4.29"
    assert s["parked_repo"] == "EdAyers/lean-subtask"
    assert s["clone_attempted"] is False
    assert s["build_attempted"] is False
    assert s["replay_attempted"] is False
    assert s["upstream_contact_performed"] is False
    assert "new Lean replay" in s["does_not_claim"]

def test_scout_shape():
    scout = load(SCOUT)
    assert scout["version"] == "v4.4.30"
    assert scout["scout_type"] == "LOWRISK_LEAN4_ATTEMPT002_REPLACEMENT_SCOUT"
    assert scout["constraints"]["no_clone"] is True
    assert scout["constraints"]["no_lean_replay"] is True
    assert scout["constraints"]["github_api_only"] is True
    assert isinstance(scout["inspected_candidates"], list)

def test_selected_if_present():
    scout = load(SCOUT)
    selected = scout["selected_candidate"]
    if selected:
        assert selected["fetch_ok"] is True
        assert selected["score"] is not None
        assert selected["windows"]
        assert "sorry" in selected["windows"][0]["snippet"]

def test_docs_and_report():
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
    assert "Low-Risk Lean4 Scout" in REPORT.read_text(encoding="utf-8")
    assert "No clone" in REPORT.read_text(encoding="utf-8")
