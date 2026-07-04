import json
from pathlib import Path

ROOT = Path("artifacts/sorrydb/hydrated_backfill_reality_v4_4_8")
SUMMARY = ROOT / "summary.json"
DOC = Path("docs/sorrydb_v4_4_8_hydrated_backfill_reality_ledger.md")


def load_summary():
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def test_summary_records_reality_contact_with_failures():
    s = load_summary()
    assert s["status"] == "HYDRATED_BACKFILL_REALITY_LEDGERED"
    assert s["queue_verdict"] == "QUEUE_RUN_COMPLETED_WITH_FAILURES"
    assert s["candidate_count"] == 4
    assert s["completed_count"] == 4
    assert s["accepted_count"] == 0
    assert s["failed_count"] == 4


def test_summary_records_cache_build_obstruction():
    s = load_summary()
    assert s["primary_obstruction"] == "OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY"
    assert s["obstruction_counts"]["OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY"] == 4
    assert "Mathlib" in s["primary_obstruction_detail"]


def test_artifacts_are_present():
    assert (ROOT / "runner_summaries/queue_run_summary.json").exists()
    assert len(list((ROOT / "manifests").glob("*.manifest.json"))) == 4
    assert len(list((ROOT / "runner_summaries").glob("partial_queue_run_summary_*.json"))) >= 1


def test_manifests_record_obstruction():
    for path in (ROOT / "manifests").glob("*.manifest.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["verdict"] == "OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY"
        assert data["baseline_verdict"] == "OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY"


def test_doc_records_boundary_and_nonclaims():
    t = DOC.read_text(encoding="utf-8")
    assert "QUEUE_RUN_COMPLETED_WITH_FAILURES" in t
    assert "OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY" in t
    assert "Mathlib.olean" in t
    assert "Lean replay success" in t
    assert "upstream submission" in t
