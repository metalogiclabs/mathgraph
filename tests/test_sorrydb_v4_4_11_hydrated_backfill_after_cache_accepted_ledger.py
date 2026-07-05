import json
from pathlib import Path

ROOT = Path("artifacts/sorrydb/hydrated_backfill_after_cache_v4_4_11")
SUMMARY = ROOT / "summary.json"
MANIFEST_INDEX = ROOT / "manifest_index.json"
CERTIFICATE_INDEX = ROOT / "certificate_index.json"
DOC = Path("docs/sorrydb_v4_4_11_hydrated_backfill_after_cache_accepted_ledger.md")


def test_summary_records_four_acceptances():
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    assert s["queue_verdict"] == "QUEUE_RUN_COMPLETED"
    assert s["candidate_count"] == 4
    assert s["completed_count"] == 4
    assert s["accepted_count"] == 4
    assert s["failed_count"] == 0
    assert s["manifest_count"] == 4
    assert s["certificate_count"] == 4
    assert s["all_patch_accepted"] is True


def test_manifest_index_records_terminal_verdicts():
    rows = json.loads(MANIFEST_INDEX.read_text(encoding="utf-8"))
    assert len(rows) == 4
    assert {r["verdict"] for r in rows} == {"PATCH_ACCEPTED"}
    assert {r["baseline_verdict"] for r in rows} == {"BASELINE_PASSED"}
    assert {r["patch_apply_verdict"] for r in rows} == {"PATCH_APPLIED"}
    assert {r["patch_verdict"] for r in rows} == {"PATCH_ACCEPTED"}


def test_certificate_index_records_four_certificates():
    rows = json.loads(CERTIFICATE_INDEX.read_text(encoding="utf-8"))
    assert len(rows) == 4
    assert {r["status"] for r in rows} == {"PATCH_ACCEPTED"}


def test_artifact_files_exist():
    assert len(list((ROOT / "manifests").glob("*.manifest.json"))) == 4
    assert len(list((ROOT / "patch_certificates").glob("*.json"))) == 4
    assert (ROOT / "runner_summaries/queue_run_summary.json").exists()


def test_doc_records_nonclaim_and_next_frontier():
    t = DOC.read_text(encoding="utf-8")
    assert "accepted_count=4" in t
    assert "duplicated certificate identities" in t
    assert "v4.4.12" in t
