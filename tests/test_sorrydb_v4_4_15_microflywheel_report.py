from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/microflywheel_report_v4_4_15")
SUMMARY = ROOT / "summary.json"
FLYWHEEL = ROOT / "flywheel.json"
SCOREBOARD = ROOT / "scoreboard.json"
REPORT = ROOT / "report.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_15_microflywheel_report.py")
DOC = Path("docs/sorrydb_v4_4_15_microflywheel_report.md")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after


def test_summary_headline():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.15"
    assert s["status"] == "MICROFLYWHEEL_REPORT_LEDGERED"
    assert s["headline"]["accepted_after_cache"] == 4
    assert s["headline"]["unique_repair_classes"] == 2
    assert s["headline"]["lawbook_seed_count"] == 2
    assert s["headline"]["restoration_invariant_passed"] is True


def test_scoreboard():
    s = load(SCOREBOARD)
    assert s["before_cache"]["accepted_count"] == 0
    assert s["after_cache"]["accepted_count"] == 4
    assert s["after_cache"]["failed_count"] == 0
    assert s["deduplicated"]["accepted_certificate_count"] == 4
    assert s["deduplicated"]["unique_repair_class_count"] == 2
    assert s["deduplicated"]["lawbook_seed_count"] == 2


def test_flywheel_stages():
    f = load(FLYWHEEL)
    assert f["version"] == "v4.4.15"
    assert len(f["stages"]) == 8
    assert "accepted replay" in f["loop"]


def test_report_and_doc_boundary_language():
    report = REPORT.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")
    assert "Bounded claim" in report
    assert "Does not claim" in report
    assert "obstruction-to-certificate" in report
    assert "production readiness" in report
    assert "Bounded claim" in doc
    assert "Does not claim" in doc
