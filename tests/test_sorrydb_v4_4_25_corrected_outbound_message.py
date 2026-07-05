from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/corrected_outbound_message_v4_4_25")
SUMMARY = ROOT / "summary.json"
MESSAGE = ROOT / "corrected_outbound_message.md"
PR_BODY = ROOT / "corrected_upstream_pr_body.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_25_corrected_outbound_message.py")
DOC = Path("docs/sorrydb_v4_4_25_corrected_outbound_message.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.25"
    assert s["status"] == "CORRECTED_OUTBOUND_MESSAGE_LEDGERED"
    assert s["input_version"] == "v4.4.19"
    assert s["detected_prior_message_duplicate"] is True
    assert s["replacement_terms_unique"] is True
    assert s["upstream_contact_performed"] is False
    assert s["replay_attempted"] is False

def test_corrected_message_has_two_distinct_replacements():
    msg = MESSAGE.read_text(encoding="utf-8")
    assert "Patch 1:" in msg
    assert "Patch 2:" in msg
    assert "Nat.le_add_right n 1" in msg
    assert "Nat.succ_le_succ" in msg
    assert msg.count("Replacement:") == 2
    assert "not a claim of upstream acceptance" in msg

def test_pr_body_records_correction():
    body = PR_BODY.read_text(encoding="utf-8")
    assert "duplicated the Patch 1 summary" in body
    assert "no upstream message is sent" in body
    assert "Does not claim" in body

def test_doc():
    doc = DOC.read_text(encoding="utf-8")
    assert "Bounded claim" in doc
    assert "Does not claim" in doc
    assert "manual review" in doc
