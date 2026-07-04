import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_3_5_json_patch_queue_runner.py"
QUEUE = ROOT / "artifacts/sorrydb/patch_queues/sorrydb_v4_3_5_two_known_accepted_patches.json"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v435_queue", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_sample_queue_is_valid_json():
    data = json.loads(QUEUE.read_text(encoding="utf-8"))
    assert "candidates" in data
    assert len(data["candidates"]) == 2


def test_load_queue_accepts_sample_queue():
    mod = load_module()
    candidates, obstruction = mod.load_queue(QUEUE)
    assert obstruction == ""
    assert len(candidates) == 2
    assert candidates[0]["candidate_id"] == "metaexamples-fiddle-line97-eg1"


def test_load_queue_rejects_missing_file(tmp_path):
    mod = load_module()
    candidates, obstruction = mod.load_queue(tmp_path / "missing.json")
    assert candidates == []
    assert obstruction == mod.OBSTRUCTED_QUEUE_MISSING


def test_load_queue_rejects_invalid_entry(tmp_path):
    mod = load_module()
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"candidates": [{"candidate_id": "x"}]}), encoding="utf-8")
    candidates, obstruction = mod.load_queue(bad)
    assert candidates == []
    assert obstruction == mod.OBSTRUCTED_QUEUE_INVALID_ENTRY


def test_build_replay_env_maps_candidate_to_v430_env(tmp_path):
    mod = load_module()
    candidates, obstruction = mod.load_queue(QUEUE)
    assert obstruction == ""
    env = mod.build_replay_env(candidates[0], tmp_path)
    assert env["SORRYDB_V430_ALLOW_PATCH"] == "1"
    assert env["SORRYDB_V430_FILE_PATH"] == "MetaExamples/Fiddle.lean"
    assert env["SORRYDB_V430_CERTIFICATE_ID"] == "sorrydb-v4-3-5-queue-metaexamples-fiddle-line97-eg1"
    assert "extract_goal using eg₁" in env["SORRYDB_V430_SOURCE_SNIPPET"]


def test_doc_records_disabled_default_and_next_frontier():
    t = Path("docs/sorrydb_v4_3_5_json_patch_queue_runner.md").read_text(encoding="utf-8")
    assert "SORRYDB_V435_ALLOW_RUN=0" in t
    assert "QUEUE_RUN_DISABLED" in t
    assert "two PATCH_ACCEPTED manifests" in t
