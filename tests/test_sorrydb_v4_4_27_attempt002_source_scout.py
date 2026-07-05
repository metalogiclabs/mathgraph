from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/attempt002_source_scout_v4_4_27")
SUMMARY = ROOT / "summary.json"
SCOUT = ROOT / "source_scout.json"
RAW = ROOT / "raw_github_code_search.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_27_attempt002_source_scout.py")
DOC = Path("docs/sorrydb_v4_4_27_attempt002_source_scout.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_reuses_cached_raw_search():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary_boundary():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.27"
    assert s["status"] == "ATTEMPT002_SOURCE_SCOUT_LEDGERED"
    assert s["attempt001_status"] == "SENT_AWAITING_RESPONSE"
    assert s["attempt001_url"].endswith("/issues/1")
    assert s["replay_attempted"] is False
    assert s["clone_attempted"] is False
    assert s["upstream_contact_performed"] is False
    assert "new Lean replay" in s["does_not_claim"]

def test_scout_shape():
    scout = load(SCOUT)
    assert scout["version"] == "v4.4.27"
    assert scout["scout_type"] == "ATTEMPT002_SOURCE_SCOUT"
    assert scout["constraints"]["no_clone"] is True
    assert scout["constraints"]["no_lean_replay"] is True
    assert scout["constraints"]["no_upstream_contact"] is True
    assert scout["constraints"]["must_inspect_exact_source_before_replay"] is True
    assert scout["selected_candidate_count"] <= 20

def test_raw_search_cached():
    raw = load(RAW)
    assert raw["version"] == "v4.4.27"
    assert isinstance(raw["queries"], list)
    assert isinstance(raw["results"], list)

def test_docs_and_report():
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
    assert "Top candidates" in REPORT.read_text(encoding="utf-8")
    assert "No clone" in REPORT.read_text(encoding="utf-8")
