from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/replay_obstruction_classifier_v4_4_35")
SUMMARY = ROOT / "summary.json"
LEDGER = ROOT / "replay_obstruction_classifier.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_35_replay_obstruction_classifier.py")
DOC = Path("docs/sorrydb_v4_4_35_replay_obstruction_classifier.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary_boundary():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.35"
    assert s["status"] == "REPLAY_OBSTRUCTION_CLASSIFIED"
    assert s["input_version"] == "v4.4.34"
    assert s["repo"] == "teorth/equational_theories"
    assert s["proof_patch_dead"] is False
    assert s["rerun_performed"] is False
    assert s["upstream_contact_performed"] is False
    assert "new Lean replay" in s["does_not_claim"]

def test_ledger_shape():
    x = load(LEDGER)
    assert x["version"] == "v4.4.35"
    assert x["classifier_type"] == "REPLAY_OBSTRUCTION_CLASSIFIER"
    assert x["prior_replay_status"] == "REJECTED_BY_LOCAL_REPLAY"
    assert x["obstruction_class"] in [
        "DEPENDENCY_BOOTSTRAP_INCOMPLETE_NOT_PROOF_REJECTION",
        "LEAN_PROOF_OR_TYPE_OBSTRUCTION",
        "LOCAL_REPLAY_ACCEPTED",
        "UNCLASSIFIED_REPLAY_OBSTRUCTION",
    ]
    assert x["proof_patch_dead"] is False

def test_docs_and_report():
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
    assert "Replay Obstruction Classifier" in REPORT.read_text(encoding="utf-8")
    assert "No Lean rerun" in REPORT.read_text(encoding="utf-8")
