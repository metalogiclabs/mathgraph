from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/local_bounded_discovery_v4_4_22")
SUMMARY = ROOT / "summary.json"
DISCOVERY = ROOT / "discovery.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_22_local_bounded_discovery.py")
DOC = Path("docs/sorrydb_v4_4_22_local_bounded_discovery.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after

def test_summary_status_and_counts():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.22"
    assert s["status"] == "LOCAL_BOUNDED_DISCOVERY_LEDGERED"
    assert s["input_version"] == "v4.4.21"
    assert s["candidate_count"] == 5
    assert s["searched_file_count"] > 0
    assert s["replay_attempted"] is False
    assert isinstance(s["status_counts"], dict)

def test_discovery_constraints():
    d = load(DISCOVERY)
    assert d["version"] == "v4.4.22"
    assert d["candidate_count"] == 5
    assert len(d["observations"]) == 5
    assert d["constraints"]["no_clone"] is True
    assert d["constraints"]["no_network"] is True
    assert d["constraints"]["no_lean_replay"] is True
    assert d["constraints"]["no_heavy_lake_build"] is True
    assert d["constraints"]["existing_artifacts_and_source_cache_only"] is True

def test_observation_terminal_statuses():
    d = load(DISCOVERY)
    allowed = {
        "CONTROL_TARGET_LOCATED",
        "OBSTRUCTED_CONTROL_TARGET_MISSING",
        "LOCAL_EXACT_SOURCE_MATCH_FOUND_REPLAY_NOT_ATTEMPTED",
        "OBSTRUCTED_NO_LOCAL_EXACT_SOURCE_MATCH",
        "LOCAL_SELECTOR_HITS_FOUND_NAMED_ADAPTER_REQUIRED",
        "OBSTRUCTED_NO_LOCAL_SELECTOR_HITS",
        "OBSTRUCTED_NO_LOCAL_FRESH_TARGET_FOUND",
    }
    for obs in d["observations"]:
        assert obs["terminal_status"] in allowed
        assert obs["replay_attempted"] is False

def test_boundary_language():
    s = load(SUMMARY)
    assert "that selector hits are valid replay targets" in s["does_not_claim"]
    assert "that any fresh target verifies" in s["does_not_claim"]
    assert "without cloning, networking, Lean replay, or heavy builds" in " ".join(s["bounded_claim"])
    assert "does not clone repositories" in REPORT.read_text(encoding="utf-8")
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
