from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/active_target_recon_v4_4_32")
SUMMARY = ROOT / "summary.json"
RECON = ROOT / "active_target_recon.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_32_active_target_recon.py")
DOC = Path("docs/sorrydb_v4_4_32_active_target_recon.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_runs():
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    assert load(SUMMARY)["version"] == "v4.4.32"

def test_summary_boundary():
    s = load(SUMMARY)
    assert s["status"] == "ACTIVE_TARGET_RECON_LEDGERED"
    assert s["input_version"] == "v4.4.31"
    assert s["repo"] == "teorth/equational_theories"
    assert s["target_path"] == "equational_theories/Definability/Law43.lean"
    assert s["clone_attempted"] is True
    assert s["build_attempted"] is False
    assert s["replay_attempted"] is False
    assert s["patch_attempted"] is False
    assert s["upstream_contact_performed"] is False

def test_recon_shape():
    r = load(RECON)
    assert r["version"] == "v4.4.32"
    assert r["recon_type"] == "ACTIVE_TARGET_RECON_BEFORE_REPLAY"
    assert isinstance(r["steps"], list)
    assert r["build_attempted"] is False
    assert r["replay_attempted"] is False
    assert r["patch_attempted"] is False
    if r["target_exists"]:
        assert r["active_sorry_count"] >= 1
        assert r["active_sorry_windows"]

def test_docs_and_report():
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
    assert "Active Target Recon" in REPORT.read_text(encoding="utf-8")
    assert "No Lean build" in REPORT.read_text(encoding="utf-8")
