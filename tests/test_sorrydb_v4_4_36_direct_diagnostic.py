from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/direct_diagnostic_v4_4_36")
SUMMARY = ROOT / "summary.json"
LEDGER = ROOT / "direct_diagnostic_ledger.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_36_direct_diagnostic.py")
DOC = Path("docs/sorrydb_v4_4_36_direct_diagnostic.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.36"
    assert s["status"] == "DIRECT_DIAGNOSTIC_LEDGERED"
    assert s["repo"] == "teorth/equational_theories"
    assert s["cache_get_ok"] is True
    assert s["target_replay_ok"] is False
    assert s["obstruction_class"] == "LOCAL_PROJECT_OLEAN_NOT_BUILT"
    assert s["proof_patch_dead"] is False
    assert s["upstream_contact_performed"] is False

def test_ledger():
    x = load(LEDGER)
    assert x["version"] == "v4.4.36"
    assert isinstance(x["diagnostic_steps"], list)
    assert x["obstruction_reasons"]

def test_docs_and_report():
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
    assert "Direct Diagnostic" in REPORT.read_text(encoding="utf-8")
    assert "No upstream" in REPORT.read_text(encoding="utf-8")
