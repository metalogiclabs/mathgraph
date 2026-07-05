from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("artifacts/sorrydb/outbound_upstream_message_v4_4_19")
SUMMARY = ROOT / "summary.json"
PACKAGE = ROOT / "outbound_message_package.json"
LINKS = ROOT / "artifact_links.json"
MESSAGE = ROOT / "outbound_message.md"
PR_BODY = ROOT / "upstream_pr_body.md"
SNAPSHOT = ROOT / "reviewer_patch_note_snapshot.md"
SCRIPT = Path("experiments/sorrydb/sorrydb_v4_4_19_outbound_upstream_message_package.py")
DOC = Path("docs/sorrydb_v4_4_19_outbound_upstream_message_package.md")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_script_is_deterministic():
    before = SUMMARY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(SCRIPT)], check=True)
    after = SUMMARY.read_text(encoding="utf-8")
    assert before == after


def test_summary_counts_and_status():
    s = load(SUMMARY)
    assert s["version"] == "v4.4.19"
    assert s["status"] == "OUTBOUND_UPSTREAM_MESSAGE_PACKAGE_LEDGERED"
    assert s["input_version"] == "v4.4.18"
    assert s["patch_count"] == 2
    assert s["accepted_replay_certificate_count"] == 4
    assert s["unique_repair_class_count"] == 2
    assert s["human_approval_required"] is True


def test_package_paths_and_subject():
    p = load(PACKAGE)
    assert p["version"] == "v4.4.19"
    assert p["package_type"] == "OUTBOUND_UPSTREAM_MESSAGE_PACKAGE"
    assert "exact-source Lean repairs" in p["subject"]
    assert p["human_approval_required"] is True
    assert Path(p["message_path"]).exists()
    assert Path(p["pr_body_path"]).exists()
    assert Path(p["artifact_links_path"]).exists()


def test_artifact_links_exist():
    data = load(LINKS)
    assert data["version"] == "v4.4.19"
    labels = {x["label"] for x in data["links"]}
    assert "reviewer_patch_note" in labels
    assert "replay_checklist" in labels
    assert "upstream_patch_bundle" in labels
    for item in data["links"]:
        assert Path(item["path"]).exists()


def test_message_boundary_language():
    msg = MESSAGE.read_text(encoding="utf-8")
    body = PR_BODY.read_text(encoding="utf-8")
    snap = SNAPSHOT.read_text(encoding="utf-8")
    assert "not a claim of upstream acceptance" in msg
    assert "apply only if the source snippets match exactly" in msg
    assert "human review" in body
    assert "Does not claim" in body
    assert "Replay checklist" in snap


def test_doc_boundary_language():
    doc = DOC.read_text(encoding="utf-8")
    assert "Bounded claim" in doc
    assert "Does not claim" in doc
    assert "human approval" in doc
