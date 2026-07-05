from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/attempt002_repo_recon_v4_4_29")
SUMMARY = ROOT / "summary.json"
RECON = ROOT / "repo_recon.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_29_attempt002_repo_recon.py")
DOC = Path("docs/sorrydb_v4_4_29_attempt002_repo_recon.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_is_deterministic_enough():
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    s = load(SUMMARY)
    assert s["version"] == "v4.4.29"

def test_summary_boundary():
    s = load(SUMMARY)
    assert s["status"] == "ATTEMPT002_REPO_RECON_LEDGERED"
    assert s["input_version"] == "v4.4.28"
    assert s["repo"] == "EdAyers/lean-subtask"
    assert s["clone_attempted"] is True
    assert s["build_attempted"] is False
    assert s["replay_attempted"] is False
    assert s["upstream_contact_performed"] is False
    assert "new Lean replay" in s["does_not_claim"]

def test_recon_shape():
    r = load(RECON)
    assert r["version"] == "v4.4.29"
    assert r["recon_type"] == "ATTEMPT002_REPO_RECON_BEFORE_REPLAY"
    assert r["target_path"] == "src/examples/vector.lean"
    assert r["build_attempted"] is False
    assert r["replay_attempted"] is False
    assert r["decision"] == "DO_NOT_REPLAY_YET_REQUIRES_LEAN3_ENV_AND_EQUATE_CONTEXT"
    assert isinstance(r["steps"], list)

def test_source_window_if_target_exists():
    r = load(RECON)
    if r["target_exists"]:
        assert r["sorry_count"] >= 1
        assert "sorry" in r["exact_source_window"]

def test_docs_and_report():
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
    assert "Repo Recon" in REPORT.read_text(encoding="utf-8")
    assert "No Lean build" in REPORT.read_text(encoding="utf-8")
