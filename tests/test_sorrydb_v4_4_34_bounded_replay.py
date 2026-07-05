from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/bounded_replay_v4_4_34")
SUMMARY = ROOT / "summary.json"
RESULT = ROOT / "bounded_replay_result.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_34_bounded_replay.py")
DOC = Path("docs/sorrydb_v4_4_34_bounded_replay.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_reuses_cached_replay_result():
    before = RESULT.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = RESULT.read_text(encoding="utf-8")
    assert before == after

def test_summary_boundary():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.34"
    assert s["status"] == "BOUNDED_REPLAY_LEDGERED"
    assert s["input_version"] == "v4.4.33"
    assert s["repo"] == "teorth/equational_theories"
    assert s["patch_attempted"] is True
    assert s["build_attempted"] is False
    assert s["replay_attempted"] is True
    assert s["upstream_contact_performed"] is False
    assert s["replay_status"] in [
        "ACCEPTED_NO_SORRY_IN_PATCHED_TARGET",
        "ACCEPTED_BUT_SORRY_REMAINS",
        "REJECTED_BY_LOCAL_REPLAY",
        "TIMEOUT",
    ]

def test_result_shape():
    r = load(RESULT)
    assert r["version"] == "v4.4.34"
    assert r["replay_type"] == "BOUNDED_SELECTED_PATCH_REPLAY"
    assert r["selected_patch_id"] == "patch-001-exact-constructor-four-fields"
    assert r["replay_attempted"] is True
    assert r["upstream_contact_performed"] is False
    assert isinstance(r["replay_step"], dict)

def test_docs_and_report():
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
    assert "Bounded Replay" in REPORT.read_text(encoding="utf-8")
    assert "No upstream" in REPORT.read_text(encoding="utf-8")
