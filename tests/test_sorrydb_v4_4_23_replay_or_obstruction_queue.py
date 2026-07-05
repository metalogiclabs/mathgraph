from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/replay_or_obstruction_queue_v4_4_23")
SUMMARY = ROOT / "summary.json"
QUEUE = ROOT / "replay_or_obstruction_queue.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_23_replay_or_obstruction_queue.py")
DOC = Path("docs/sorrydb_v4_4_23_replay_or_obstruction_queue.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary_status_and_counts():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.23"
    assert s["status"] == "REPLAY_OR_OBSTRUCTION_QUEUE_LEDGERED"
    assert s["input_version"] == "v4.4.22"
    assert s["item_count"] == 5
    assert s["replay_attempted"] is False
    assert s["ready_count"] + s["obstruction_count"] == 5
    assert isinstance(s["status_counts"], dict)

def test_queue_constraints():
    q = load(QUEUE)
    assert q["version"] == "v4.4.23"
    assert q["queue_type"] == "REPLAY_OR_OBSTRUCTION_QUEUE_FROM_LOCAL_BOUNDED_DISCOVERY"
    assert q["item_count"] == 5
    assert len(q["items"]) == 5
    assert q["global_constraints"]["no_replay_executed"] is True
    assert q["global_constraints"]["human_approval_required_before_replay"] is True
    assert q["global_constraints"]["no_heavy_lake_build_without_approval"] is True
    assert q["global_constraints"]["selector_hits_are_not_replay_targets_without_adapter"] is True

def test_item_states_are_bounded():
    q = load(QUEUE)
    allowed = {
        "READY_FOR_CONTROL_REPLAY_IF_APPROVED",
        "READY_FOR_EXACT_SOURCE_REPLAY_IF_APPROVED",
        "OBSTRUCTED_INTERNAL_EVIDENCE_MATCH_ONLY",
        "OBSTRUCTED_NAMED_ADAPTER_REQUIRED",
        "OBSTRUCTED_UNCLASSIFIED_LOCAL_MATCH",
        "OBSTRUCTED_CONTROL_TARGET_MISSING",
        "OBSTRUCTED_NO_LOCAL_EXACT_SOURCE_MATCH",
        "OBSTRUCTED_NO_LOCAL_SELECTOR_HITS",
        "OBSTRUCTED_NO_LOCAL_FRESH_TARGET_FOUND",
    }
    for item in q["items"]:
        assert item["queue_status"] in allowed
        assert item["requires_human_approval"] is True
        assert item["requires_heavy_build"] is False

def test_boundary_language():
    s = load(SUMMARY)
    assert "that internal artifact matches are fresh targets" in s["does_not_claim"]
    assert "that selector hits are valid replay targets" in s["does_not_claim"]
    assert "no Lean replay, clone, network access, or heavy build is executed" in " ".join(s["bounded_claim"])
    assert "does not run Lean" in REPORT.read_text(encoding="utf-8")
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
