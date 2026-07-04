import json
from pathlib import Path

CERT_DIR = Path("artifacts/sorrydb/patch_certificates")
DOC = Path("docs/sorrydb_v4_3_2_patch_certificate_schema.md")

REQUIRED_KEYS = {
    "certificate_id",
    "certificate_version",
    "status",
    "project",
    "project_commit",
    "file_path",
    "source_snippet",
    "patch_snippet",
    "baseline_command",
    "patch_command",
    "baseline_verdict",
    "patch_apply_verdict",
    "patch_verdict",
    "final_verdict",
    "lean_returncode",
    "restore_check",
    "trust_boundary",
    "bounded_claim",
    "does_not_claim",
}


def load_certs():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CERT_DIR.glob("*.json"))]


def test_two_certificates_exist():
    certs = load_certs()
    assert len(certs) == 2
    ids = {c["certificate_id"] for c in certs}
    assert "sorrydb-v4-3-2-metaexamples-fiddle-line97-eg1" in ids
    assert "sorrydb-v4-3-2-metaexamples-fiddle-line99-eg2" in ids


def test_required_keys_present():
    for cert in load_certs():
        assert REQUIRED_KEYS <= set(cert)


def test_certificates_are_patch_accepted():
    for cert in load_certs():
        assert cert["status"] == "PATCH_ACCEPTED"
        assert cert["baseline_verdict"] == "BASELINE_PASSED"
        assert cert["patch_apply_verdict"] == "PATCH_APPLIED"
        assert cert["patch_verdict"] == "PATCH_ACCEPTED"
        assert cert["final_verdict"] == "PATCH_ACCEPTED"
        assert cert["lean_returncode"] == 0


def test_exact_snippets_recorded():
    text = "\n".join(json.dumps(c, sort_keys=True, ensure_ascii=False) for c in load_certs())
    assert "extract_goal using eg₁" in text
    assert "extract_goal using eg₂" in text
    assert "exact Nat.le_add_right n 1" in text
    assert "exact Nat.succ_le_succ (Nat.le_add_right n 1)" in text


def test_bounded_nonclaims_recorded():
    for cert in load_certs():
        joined = "\n".join(cert["does_not_claim"])
        assert "general proof repair" in joined
        assert "upstream submission" in joined


def test_doc_mentions_schema_and_next_frontier():
    t = DOC.read_text(encoding="utf-8")
    assert "Patch Certificate Schema" in t
    assert "exact-source-snippet plus Lean replay" in t
    assert "emit this certificate format automatically" in t
