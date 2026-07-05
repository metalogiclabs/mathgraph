from pathlib import Path
import csv
import json
import os
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/upstream_repair_flywheel_tracker_v4_4_26")
SUMMARY = ROOT / "summary.json"
ATTEMPT = ROOT / "attempt_001.json"
CSV = ROOT / "attempts.csv"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_26_upstream_repair_flywheel_tracker.py")
DOC = Path("docs/sorrydb_v4_4_26_upstream_repair_flywheel_tracker.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    env = dict(os.environ)
    current = load(ATTEMPT)
    env["UPSTREAM_CONTACT_URL"] = current["upstream_contact_url"] or "NOT_SENT"
    subprocess.run([sys.executable, str(SCRIPT)], check=True, env=env)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary_shape():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.26"
    assert s["tracker_type"] == "SORRY_TO_PR_FLYWHEEL"
    assert s["attempt_count"] == 1
    assert "10 upstream-visible Lean repair attempts" in s["goal"]
    assert "upstream acceptance" in s["does_not_claim"]
    assert s["accepted_count"] == 0

def test_attempt_shape():
    a = load(ATTEMPT)
    assert a["attempt_id"] == "sorry-pr-001"
    assert a["target_repo"] == "siddhartha-gadgil/MetaExamples"
    assert a["target_file"] == "MetaExamples/Fiddle.lean"
    assert a["patch_count"] == 2
    assert a["local_replay_status"] == "ACCEPTED_IN_PINNED_CHECKOUT"
    assert a["external_outcome"] in {"PENDING", "NOT_SENT"}

def test_csv_exists_and_matches():
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["attempt_id"] == "sorry-pr-001"
    assert rows[0]["target_repo"] == "siddhartha-gadgil/MetaExamples"

def test_docs_and_report():
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
    assert "Sorry-to-PR flywheel" in DOC.read_text(encoding="utf-8")
    assert "Current attempt" in REPORT.read_text(encoding="utf-8")
