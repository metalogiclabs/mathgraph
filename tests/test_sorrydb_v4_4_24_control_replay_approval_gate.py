from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/control_replay_approval_gate_v4_4_24")
SUMMARY = ROOT / "summary.json"
GATE = ROOT / "approval_gate.json"
COMMANDS = ROOT / "pinned_control_replay_commands_not_executed.json"
PACKET = ROOT / "manual_review_packet.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_24_control_replay_approval_gate.py")
DOC = Path("docs/sorrydb_v4_4_24_control_replay_approval_gate.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary_status_and_gate():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.24"
    assert s["status"] == "CONTROL_REPLAY_APPROVAL_GATE_LEDGERED"
    assert s["input_version"] == "v4.4.23"
    assert s["approval_state"] == "NOT_APPROVED"
    assert s["selected_action"] == "PARK_REPLAY_AND_RETURN_TO_MANUAL_OUTBOUND_REVIEW"
    assert s["replay_attempted"] is False
    assert s["approval_token_required"] == "APPROVE_PINNED_CONTROL_REPLAY_V4_4_24"

def test_gate_counts_and_policy():
    g = load(GATE)
    assert g["version"] == "v4.4.24"
    assert g["gate_type"] == "CONTROL_REPLAY_APPROVAL_GATE"
    assert g["approval_state"] == "NOT_APPROVED"
    assert g["human_approval_required_before_any_replay"] is True
    assert g["if_approved_next_commands_are_packaged_not_executed"] is True
    assert g["control_ready_count"] >= 1
    assert g["replay_attempted"] is False

def test_packaged_commands_not_executed():
    c = load(COMMANDS)
    assert c["version"] == "v4.4.24"
    assert c["command_bundle_type"] == "PINNED_CONTROL_REPLAY_COMMANDS_NOT_EXECUTED"
    assert c["approval_token_required"] == "APPROVE_PINNED_CONTROL_REPLAY_V4_4_24"
    assert isinstance(c["commands"], list)
    assert len(c["commands"]) > 0
    assert "not executed" in " ".join(c["notes"])

def test_boundary_language():
    s = load(SUMMARY)
    assert "new Lean replay" in s["does_not_claim"]
    assert "upstream acceptance" in s["does_not_claim"]
    assert "packages the pinned control replay command list but does not execute it" in " ".join(s["bounded_claim"])
    assert "Replay is parked" in PACKET.read_text(encoding="utf-8")
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
