from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/upstream_patch_bundle_v4_4_17")
SUMMARY = ROOT / "summary.json"
BUNDLE = ROOT / "upstream_patch_bundle.json"
NOTE = ROOT / "reviewer_note.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_17_upstream_patch_evidence_bundle.py")
DOC = Path("docs/sorrydb_v4_4_17_upstream_patch_evidence_bundle.md")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after


def test_summary_counts_and_status():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.17"
    assert s["status"] == "UPSTREAM_PATCH_EVIDENCE_BUNDLE_LEDGERED"
    assert s["selected_path_id"] == "upstream_patch_package"
    assert s["patch_count"] == 2
    assert s["accepted_replay_certificate_count"] == 4
    assert s["unique_repair_class_count"] == 2
    assert s["lawbook_seed_count"] == 2


def test_bundle_patch_payloads():
    b = load(BUNDLE)
    assert b["version"] == "v4.4.17"
    assert b["bundle_type"] == "UPSTREAM_EXACT_SOURCE_PATCH_EVIDENCE_BUNDLE"
    assert b["patch_count"] == 2
    assert len(b["patches"]) == 2
    replacements = "\n".join(p["replacement_snippet"] for p in b["patches"])
    assert "Nat.le_add_right n 1" in replacements
    assert "Nat.succ_le_succ (Nat.le_add_right n 1)" in replacements
    for patch in b["patches"]:
        assert patch["source_snippet"]
        assert patch["replacement_snippet"]
        assert patch["certificate_ids"]
        assert patch["target"]["file_path"] == "MetaExamples/Fiddle.lean"
        assert patch["upstream_claim"]["requires_upstream_review"] is True
        assert patch["upstream_claim"]["requires_fresh_replay_in_recipient_checkout"] is True
        assert patch["upstream_claim"]["portable_without_replay"] is False


def test_evidence_chain_and_boundary_language():
    b = load(BUNDLE)
    roles = [x["role"] for x in b["evidence_chain"]]
    assert "accepted_replay" in roles
    assert "deduplication" in roles
    assert "lawbook_seed_packaging" in roles
    s = load(SUMMARY)
    assert "upstream acceptance" in s["does_not_claim"]
    assert "authority to modify the upstream repository" in s["does_not_claim"]
    assert "evidence for review and replay" in " ".join(s["bounded_claim"])


def test_docs_and_reviewer_note():
    note = NOTE.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")
    assert "Replay checklist" in note
    assert "Bounded claim" in note
    assert "Does not claim" in note
    assert "Bounded claim" in doc
    assert "Does not claim" in doc
