import json
from pathlib import Path

ROOT = Path("artifacts/sorrydb/enabled_queue_reality_v4_3_6")
SUMMARY = ROOT / "summary.json"
DOC = Path("docs/sorrydb_v4_3_6_enabled_queue_reality_ledger.md")


def load_summary():
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def test_summary_records_enabled_queue_reality_passed():
    s = load_summary()
    assert s["status"] == "ENABLED_QUEUE_REALITY_PASSED"
    assert s["queue_verdict"] == "QUEUE_RUN_COMPLETED"
    assert s["candidate_count"] == 2
    assert s["accepted_count"] == 2
    assert s["failed_count"] == 0


def test_summary_records_artifact_counts():
    s = load_summary()
    assert s["manifest_count"] == 2
    assert s["certificate_count"] == 2
    assert len(list((ROOT / "manifests").glob("*.manifest.json"))) == 2
    assert len(list((ROOT / "certificates").glob("*.json"))) == 2


def test_manifests_are_patch_accepted():
    for path in (ROOT / "manifests").glob("*.manifest.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["verdict"] == "PATCH_ACCEPTED"
        assert data["baseline_verdict"] == "BASELINE_PASSED"
        assert data["patch_apply_verdict"] == "PATCH_APPLIED"
        assert data["patch_verdict"] == "PATCH_ACCEPTED"


def test_certificates_are_patch_accepted():
    for path in (ROOT / "certificates").glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["status"] == "PATCH_ACCEPTED"
        assert data["final_verdict"] == "PATCH_ACCEPTED"
        assert data["lean_returncode"] == 0


def test_restore_and_silent_obstruction_recorded():
    s = load_summary()
    text = json.dumps(s, ensure_ascii=False)
    assert "line_97" in text
    assert "line_99" in text

    doc = DOC.read_text(encoding="utf-8")
    assert "queue runner is silent" in doc
    assert "streaming runner" in doc
    assert "partial-summary" in doc


def test_doc_records_nonclaims():
    t = DOC.read_text(encoding="utf-8")
    assert "ENABLED_QUEUE_REALITY_PASSED" in t
    assert "general proof repair" in t
    assert "upstream submission" in t
