from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/compact_lawbook_seed_v4_4_13")
SUMMARY = ROOT / "summary.json"
SEEDS = ROOT / "lawbook_seed_index.json"
QUEUE = ROOT / "replay_seed_queue.json"
DOC = Path("docs/sorrydb_v4_4_13_compact_lawbook_seed_bundle.md")
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_13_compact_lawbook_seed_bundle.py")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after


def test_summary_counts():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.13"
    assert s["status"] == "COMPACT_LAWBOOK_SEED_BUNDLE_LEDGERED"
    assert s["accepted_certificate_count"] == 4
    assert s["unique_repair_class_count"] == 2
    assert s["duplicate_certificate_count"] == 2
    assert s["lawbook_seed_count"] == 2


def test_seed_index_contracts():
    data = load(SEEDS)
    assert data["version"] == "v4.4.13"
    assert data["seed_count"] == 2
    for seed in data["seeds"]:
        assert seed["status"] == "LAWBOOK_SEED_READY"
        assert seed["source_snippet"]
        assert seed["patch_snippet"]
        assert seed["replay_evidence"]["verdict"] == "PATCH_ACCEPTED"
        assert seed["replay_evidence"]["baseline_verdict"] == "BASELINE_PASSED"
        assert seed["reuse_contract"]["requires_exact_source_or_verified_adapter"] is True
        assert seed["reuse_contract"]["requires_lean_replay_before_promotion"] is True
        assert seed["reuse_contract"]["portable_without_replay"] is False


def test_replay_seed_queue():
    q = load(QUEUE)
    assert q["version"] == "v4.4.13"
    assert q["queue_type"] == "DEDUPED_ACCEPTED_REPAIR_SEED_QUEUE"
    assert q["candidate_count"] == 2
    assert len(q["candidates"]) == 2
    for c in q["candidates"]:
        assert c["requires_replay"] is True
        assert c["expected_replay_verdict"] == "PATCH_ACCEPTED"


def test_docs_boundary_language():
    text = DOC.read_text(encoding="utf-8")
    assert "Bounded claim" in text
    assert "Does not claim" in text
    assert "replay seed bundle" in text
    assert "portable without exact-source replay" in text
