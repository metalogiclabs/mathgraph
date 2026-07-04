import json
from pathlib import Path

ROOT = Path("artifacts/sorrydb/mined_queue_reality_v4_4_1")
SUMMARY = ROOT / "summary.json"
DOC = Path("docs/sorrydb_v4_4_1_mined_queue_reality_ledger.md")


def load_summary():
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def test_summary_records_mined_queue_reality_passed():
    s = load_summary()
    assert s["status"] == "MINED_QUEUE_REALITY_PASSED"
    assert s["queue_verdict"] == "QUEUE_RUN_COMPLETED"
    assert s["candidate_count"] == 2
    assert s["accepted_count"] == 2
    assert s["failed_count"] == 0
    assert s["stream_child_output_enabled"] is True


def test_summary_records_artifact_counts():
    s = load_summary()
    assert s["partial_summary_count"] >= 1
    assert s["manifest_count"] == 2
    assert s["certificate_count"] == 2
    assert len(list((ROOT / "runner_summaries").glob("*.json"))) >= 2
    assert len(list((ROOT / "manifests").glob("*.manifest.json"))) == 2
    assert len(list((ROOT / "certificates").glob("*.json"))) == 2


def test_runner_summary_records_queue_completed():
    q = json.loads((ROOT / "runner_summaries/queue_run_summary.json").read_text(encoding="utf-8"))
    assert q["verdict"] == "QUEUE_RUN_COMPLETED"
    assert q["accepted_count"] == 2
    assert q["failed_count"] == 0


def test_manifests_are_patch_accepted():
    for path in (ROOT / "manifests").glob("*.manifest.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["verdict"] == "PATCH_ACCEPTED"
        assert data["baseline_verdict"] == "BASELINE_PASSED"
        assert data["patch_apply_verdict"] == "PATCH_APPLIED"
        assert data["patch_verdict"] == "PATCH_ACCEPTED"
        assert data["patch_certificate_id"]


def test_certificates_are_patch_accepted():
    for path in (ROOT / "certificates").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["status"] == "PATCH_ACCEPTED"
        assert data["final_verdict"] == "PATCH_ACCEPTED"
        assert data["lean_returncode"] == 0


def test_doc_records_loop_closure_and_nonclaims():
    t = DOC.read_text(encoding="utf-8")
    assert "MINED_QUEUE_REALITY_PASSED" in t
    assert "exact-source miner" in t
    assert "streaming queue runner" in t
    assert "real Lean replay" in t
    assert "new proof discovery" in t
    assert "upstream submission" in t
