from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/scale_path_selector_v4_4_16")
SUMMARY = ROOT / "summary.json"
REPORT = ROOT / "scale_path_report.json"
REPORT_MD = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_16_scale_path_selector.py")
DOC = Path("docs/sorrydb_v4_4_16_scale_path_selector.md")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after


def test_summary_selects_upstream_patch_package():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.16"
    assert s["status"] == "SCALE_PATH_SELECTED"
    assert s["selected_path_id"] == "upstream_patch_package"
    assert s["lawbook_seed_count"] == 2
    assert s["unique_repair_classes"] == 2
    assert s["next_frontier"] == "v4.4.17 build the upstream-facing exact-source patch evidence bundle"


def test_report_ranking():
    r = load(REPORT)
    assert r["version"] == "v4.4.16"
    assert r["selected"]["path_id"] == "upstream_patch_package"
    assert len(r["ranked_options"]) == 3
    scores = [x["score"] for x in r["ranked_options"]]
    assert scores == sorted(scores, reverse=True)


def test_boundary_language():
    s = load(SUMMARY)
    assert "upstream acceptance" in s["does_not_claim"]
    assert "semantic portability beyond exact-source replay or verified adapters" in s["does_not_claim"]
    assert "exact-source patch evidence bundle" in " ".join(s["bounded_claim"])
    assert "Selected path" in REPORT_MD.read_text(encoding="utf-8")
    assert "Bounded claim" in DOC.read_text(encoding="utf-8")
