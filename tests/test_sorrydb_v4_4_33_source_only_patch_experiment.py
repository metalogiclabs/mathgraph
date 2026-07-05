from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/source_only_patch_experiment_v4_4_33")
SUMMARY = ROOT / "summary.json"
EXP = ROOT / "source_only_patch_experiment.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_33_source_only_patch_experiment.py")
DOC = Path("docs/sorrydb_v4_4_33_source_only_patch_experiment.md")

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_script_runs():
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    assert load(SUMMARY)["version"] == "v4.4.33"

def test_summary_boundary():
    s = load(SUMMARY)
    assert s["status"] == "SOURCE_ONLY_PATCH_EXPERIMENT_LEDGERED"
    assert s["input_version"] == "v4.4.32"
    assert s["repo"] == "teorth/equational_theories"
    assert s["target_path"] == "equational_theories/Definability/Law43.lean"
    assert s["clone_attempted"] is True
    assert s["build_attempted"] is False
    assert s["replay_attempted"] is False
    assert s["upstream_contact_performed"] is False
    assert "new Lean replay" in s["does_not_claim"]

def test_experiment_shape():
    x = load(EXP)
    assert x["version"] == "v4.4.33"
    assert x["experiment_type"] == "SOURCE_ONLY_PATCH_EXPERIMENT_BEFORE_REPLAY"
    assert x["patch_candidate_count"] >= 3
    assert x["selected_patch"]
    assert x["selected_patch"]["status"] == "SOURCE_ONLY_PATCH_CANDIDATE_NOT_REPLAYED"
    assert x["build_attempted"] is False
    assert x["replay_attempted"] is False

def test_patch_files_exist():
    x = load(EXP)
    for patch in x["patches"]:
        p = Path(patch["patched_file"])
        assert p.exists()
        assert p.read_text(encoding="utf-8")

def test_docs_and_report():
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
    assert "Source-Only Patch Experiment" in REPORT.read_text(encoding="utf-8")
    assert "No Lean build" in REPORT.read_text(encoding="utf-8")
