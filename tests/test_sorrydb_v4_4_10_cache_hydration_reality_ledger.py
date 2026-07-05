import json
from pathlib import Path

ROOT = Path("artifacts/sorrydb/cache_hydration_reality_v4_4_10")
SUMMARY = ROOT / "summary.json"
BASELINE = ROOT / "baseline_contact.json"
DOC = Path("docs/sorrydb_v4_4_10_cache_hydration_reality_ledger.md")


def test_summary_records_cache_hydration_success():
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert s["status"] == "CACHE_HYDRATION_REALITY_LEDGERED"
    assert s["mathlib_olean_exists"] is True
    assert s["baseline_contact_passed"] is True
    assert s["baseline_returncode"] == 0


def test_summary_records_nonclaims():
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert "patch replay success" in s["does_not_claim"]
    assert "upstream submission" in s["does_not_claim"]


def test_baseline_contact_artifact_records_success():
    b = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert b["returncode"] == 0
    assert "MetaExamples/Fiddle.lean" in " ".join(b["cmd"])


def test_doc_records_next_frontier():
    t = DOC.read_text(encoding="utf-8")
    assert "Mathlib.olean exists" in t
    assert "v4.4.11" in t
    assert "streaming controlled replay" in t
