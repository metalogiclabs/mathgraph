import json
from pathlib import Path

ROOT = Path("artifacts/sorrydb/emitted_patch_certificates_v4_3_4")
SUMMARY = ROOT / "summary.json"
DOC = Path("docs/sorrydb_v4_3_4_emitter_reality_ledger.md")


def load_summary():
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def test_summary_records_reality_run_passed():
    s = load_summary()
    assert s["status"] == "EMITTER_REALITY_RUN_PASSED"
    assert s["manifest_count"] == 2
    assert s["emitted_certificate_count"] == 2


def test_emitted_certificates_exist_and_are_patch_accepted():
    certs = sorted(ROOT.glob("sorrydb-v4-3-4-emitted-*.json"))
    assert len(certs) == 2
    for path in certs:
        c = json.loads(path.read_text(encoding="utf-8"))
        assert c["status"] == "PATCH_ACCEPTED"
        assert c["final_verdict"] == "PATCH_ACCEPTED"
        assert c["lean_returncode"] == 0


def test_summary_records_manifest_verdicts():
    s = load_summary()
    for m in s["manifests"]:
        assert m["verdict"] == "PATCH_ACCEPTED"
        assert m["baseline_verdict"] == "BASELINE_PASSED"
        assert m["patch_apply_verdict"] == "PATCH_APPLIED"
        assert m["patch_verdict"] == "PATCH_ACCEPTED"
        assert m["patch_certificate_id"]


def test_restore_checks_recorded():
    s = load_summary()
    text = json.dumps(s, ensure_ascii=False)
    assert "line 97 restored" in text
    assert "line 99 restored" in text


def test_doc_records_bounded_claims_and_nonclaims():
    t = DOC.read_text(encoding="utf-8")
    assert "EMITTER_REALITY_RUN_PASSED" in t
    assert "automatic emitter successfully promoted" in t
    assert "general proof repair" in t
    assert "JSON patch queue" in t
