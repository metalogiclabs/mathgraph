from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/reviewer_patch_note_v4_4_18")
SUMMARY = ROOT / "summary.json"
CHECKLIST = ROOT / "replay_checklist.json"
NOTE = ROOT / "reviewer_patch_note.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_18_reviewer_patch_note_replay_checklist.py")
DOC = Path("docs/sorrydb_v4_4_18_reviewer_patch_note_replay_checklist.md")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after


def test_summary_counts_and_status():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.18"
    assert s["status"] == "REVIEWER_PATCH_NOTE_REPLAY_CHECKLIST_LEDGERED"
    assert s["input_version"] == "v4.4.17"
    assert s["patch_count"] == 2
    assert s["accepted_replay_certificate_count"] == 4
    assert s["unique_repair_class_count"] == 2
    assert s["checklist_command_count"] >= 5


def test_checklist_contents():
    c = load(CHECKLIST)
    assert c["version"] == "v4.4.18"
    assert c["target_repo"] == "siddhartha-gadgil/MetaExamples"
    assert c["target_file"] == "MetaExamples/Fiddle.lean"
    joined = "\n".join(c["commands"])
    assert "git checkout edbb75e784db19846a1c19841e182b797afc18bb" in joined
    assert "lake env lean MetaExamples/Fiddle.lean" in joined
    assert "source snippet matches exactly" in " ".join(c["acceptance_criteria"])


def test_note_has_patch_candidates_and_boundaries():
    note = NOTE.read_text(encoding="utf-8")
    assert "upstream-patch-001" in note
    assert "upstream-patch-002" in note
    assert "Nat.le_add_right n 1" in note
    assert "Nat.succ_le_succ (Nat.le_add_right n 1)" in note
    assert "Bounded claim" in note
    assert "Does not claim" in note
    assert "upstream acceptance" in note


def test_doc_boundary_language():
    doc = DOC.read_text(encoding="utf-8")
    assert "Bounded claim" in doc
    assert "Does not claim" in doc
    assert "exact replay checklist" in doc
