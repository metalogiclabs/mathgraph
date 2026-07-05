from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/source_cleanliness_v4_4_14")
SUMMARY = ROOT / "summary.json"
DOC = Path("docs/sorrydb_v4_4_14_source_cleanliness_replay_restoration_ledger.md")
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_14_source_cleanliness_replay_restoration_ledger.py")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after


def test_summary_records_cleanliness():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.14"
    assert s["status"] == "SOURCE_CLEANLINESS_REPLAY_RESTORATION_LEDGERED"
    assert s["commit_matches"] is True
    assert s["target_exists"] is True
    assert "git_status_clean" in s
    assert "source_has_untracked_paths" in s
    assert s["source_tracked_changes_clean"] is True
    assert isinstance(s["source_untracked_paths"], list)
    assert s["target_diff_clean"] is True
    assert s["full_diff_clean"] is True
    assert s["restoration_invariant_passed"] is True


def test_probe_artifacts_exist():
    assert (ROOT / "commit_probe.json").exists()
    assert (ROOT / "git_status_probe.json").exists()
    assert (ROOT / "target_diff_probe.json").exists()
    assert (ROOT / "diff_name_probe.json").exists()


def test_docs_boundary_language():
    text = DOC.read_text(encoding="utf-8")
    assert "Bounded claim" in text
    assert "Does not claim" in text
    assert "no git diff" in text
    assert "semantic portability" in text
