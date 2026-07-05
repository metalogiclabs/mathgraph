from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/fresh_source_replay_pilot_queue_v4_4_21")
SUMMARY = ROOT / "summary.json"
QUEUE = ROOT / "pilot_queue.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_21_fresh_source_replay_pilot_queue.py")
DOC = Path("docs/sorrydb_v4_4_21_fresh_source_replay_pilot_queue.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary_status_and_counts():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.21"
    assert s["status"] == "FRESH_SOURCE_REPLAY_PILOT_QUEUE_LEDGERED"
    assert s["input_version"] == "v4.4.20"
    assert s["selected_followup_path"] == "fresh_source_replay_pilot"
    assert s["candidate_count"] == 5
    assert s["max_candidate_targets"] == 5
    assert s["control_candidate_count"] == 1
    assert s["fresh_discovery_candidate_count"] == 4

def test_queue_constraints():
    q = load(QUEUE)
    assert q["version"] == "v4.4.21"
    assert q["queue_type"] == "BOUNDED_FRESH_SOURCE_REPLAY_PILOT_QUEUE"
    assert q["candidate_count"] == 5
    assert len(q["candidates"]) == 5
    assert q["global_constraints"]["requires_exact_source_match_or_named_adapter"] is True
    assert q["global_constraints"]["no_heavy_lake_build_without_approval"] is True
    assert q["global_constraints"]["no_external_contact"] is True
    assert q["global_constraints"]["no_broad_source_world_mining"] is True

def test_candidate_payloads():
    q = load(QUEUE)
    ids = [c["candidate_id"] for c in q["candidates"]]
    assert ids == [
        "fresh-pilot-001",
        "fresh-pilot-002",
        "fresh-pilot-003",
        "fresh-pilot-004",
        "fresh-pilot-005",
    ]
    assert q["candidates"][0]["freshness_status"] == "CONTROL_NOT_FRESH"
    assert all(c["requires_heavy_build"] is False for c in q["candidates"])
    assert "Nat.le_add_right n 1" in q["candidates"][1]["replacement_snippet"]
    assert "Nat.succ_le_succ" in q["candidates"][2]["replacement_snippet"]

def test_boundary_language():
    s = load(SUMMARY)
    assert "that any fresh target currently exists" in s["does_not_claim"]
    assert "permission to run heavy lake builds on low disk" in s["does_not_claim"]
    assert "exact source match or a named adapter" in " ".join(s["bounded_claim"])
    assert "queue only" in REPORT.read_text(encoding="utf-8")
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
