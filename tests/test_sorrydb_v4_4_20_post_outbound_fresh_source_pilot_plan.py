from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/post_outbound_fresh_source_pilot_plan_v4_4_20")
SUMMARY = ROOT / "summary.json"
DECISION = ROOT / "decision.json"
NOTE = ROOT / "human_review_and_pilot_plan.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_20_post_outbound_fresh_source_pilot_plan.py")
DOC = Path("docs/sorrydb_v4_4_20_post_outbound_fresh_source_pilot_plan.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary_status_and_paths():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.20"
    assert s["status"] == "POST_OUTBOUND_FRESH_SOURCE_PILOT_PLAN_LEDGERED"
    assert s["input_version"] == "v4.4.19"
    assert s["selected_immediate_path"] == "manual_outbound_review"
    assert s["selected_followup_path"] == "fresh_source_replay_pilot"
    assert s["human_approval_required"] is True
    assert s["patch_count"] == 2
    assert s["accepted_replay_certificate_count"] == 4

def test_decision_constraints():
    d = load(DECISION)
    assert d["version"] == "v4.4.20"
    assert d["selected_immediate_path"] == "manual_outbound_review"
    assert d["selected_followup_path"] == "fresh_source_replay_pilot"
    assert "automated_external_contact" in d["blocked_paths"]
    assert d["pilot_constraints"]["max_candidate_targets"] == 5
    assert d["pilot_constraints"]["requires_exact_source_match_or_named_adapter"] is True
    assert d["pilot_constraints"]["requires_no_heavy_lake_build_without_approval"] is True

def test_boundary_language():
    s = load(SUMMARY)
    assert "automated external contact" in s["does_not_claim"]
    assert "permission to run broad clone/build jobs on low disk" in s["does_not_claim"]
    assert "manual human review" in " ".join(s["bounded_claim"])
    assert "fresh-source replay pilot" in " ".join(s["bounded_claim"])

def test_docs():
    note = NOTE.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")
    assert "Human Review Boundary" in note
    assert "Bounded claim" in note
    assert "Does not claim" in note
    assert "Bounded claim" in doc
    assert "Does not claim" in doc
