import json
from pathlib import Path

ROOT = Path("artifacts/sorrydb/streaming_reality_v4_3_8")
SUMMARY = ROOT / "summary.json"
DOC = Path("docs/sorrydb_v4_3_8_streaming_reality_ledger.md")


def load_summary():
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def test_summary_records_streaming_reality_passed():
    s = load_summary()
    assert s["status"] == "STREAMING_REALITY_PASSED"
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


def test_runner_summaries_validate():
    q = json.loads((ROOT / "runner_summaries/queue_run_summary.json").read_text(encoding="utf-8"))
    assert q["verdict"] == "QUEUE_RUN_COMPLETED"
    assert q["accepted_count"] == 2
    assert q["failed_count"] == 0

    partials = sorted((ROOT / "runner_summaries").glob("partial_queue_run_summary_*.json"))
    assert partials
    for path in partials:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "verdict" in data
        assert "results" in data


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


def test_doc_records_bounded_claim_and_nonclaims():
    t = DOC.read_text(encoding="utf-8")
    assert "STREAMING_REALITY_PASSED" in t
    assert "real Lean contact" in t
    assert "visible progress" in t
    assert "partial summary" in t
    assert "general proof repair" in t
    assert "upstream submission" in t
