from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/accepted_certificate_dedup_v4_4_12")
SUMMARY = ROOT / "summary.json"
CLASSES = ROOT / "dedup_classes.json"
MAP = ROOT / "certificate_to_class.json"
DOC = Path("docs/sorrydb_v4_4_12_accepted_certificate_dedup_ledger.md")
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_12_accepted_certificate_dedup_ledger.py")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after


def test_summary_counts():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.12"
    assert s["accepted_certificate_count"] == 4
    assert s["unique_repair_class_count"] == 2
    assert s["duplicate_certificate_count"] == 2
    assert s["all_patch_accepted"] is True


def test_all_certificates_mapped():
    c = load(CLASSES)["classes"]
    m = load(MAP)["certificate_to_class"]
    certs = sorted(cert for cls in c for cert in cls["certificate_ids"])
    assert sorted(m.keys()) == certs
    assert len(certs) == 4
    assert len(set(m.values())) == 2


def test_classes_have_patch_accepted_evidence():
    c = load(CLASSES)["classes"]
    assert len(c) == 2
    for cls in c:
        assert cls["certificate_ids"]
        assert cls["source_snippet"]
        assert cls["patch_snippet"]
        for verdict in cls["verdicts"]:
            assert verdict["verdict"] == "PATCH_ACCEPTED"
            assert verdict["baseline_verdict"] == "BASELINE_PASSED"
            assert verdict["patch_apply_verdict"] == "PATCH_APPLIED"
            assert verdict["patch_verdict"] == "PATCH_ACCEPTED"


def test_docs_boundary_language():
    text = DOC.read_text(encoding="utf-8")
    assert "Bounded claim" in text
    assert "Does not claim" in text
    assert "two unique repair classes" in text
    assert "duplicate certificate identities" in text
    assert "new Lean replay" in text
