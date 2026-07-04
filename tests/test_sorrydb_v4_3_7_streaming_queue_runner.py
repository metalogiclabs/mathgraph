import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/sorrydb/sorrydb_v4_3_5_json_patch_queue_runner.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sorrydb_v437_queue", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_partial_summary_writer_records_progress(tmp_path):
    mod = load_module()
    path = tmp_path / "partial_queue_run_summary.json"
    summary = {
        "queue_path": "/tmp/queue.json",
        "work_root": "/tmp/work",
        "allow_run": True,
        "replay_script": "/tmp/replay.py",
        "candidate_count": 2,
    }
    results = [
        {"candidate_id": "accepted", "manifest_verdict": "PATCH_ACCEPTED"},
        {"candidate_id": "failed", "manifest_verdict": "PATCH_REJECTED"},
    ]

    written = mod.write_partial_summary(path, summary, results)
    on_disk = json.loads(path.read_text(encoding="utf-8"))

    assert written == on_disk
    assert on_disk["verdict"] == mod.QUEUE_RUN_IN_PROGRESS
    assert on_disk["completed_count"] == 2
    assert on_disk["accepted_count"] == 1
    assert on_disk["failed_count"] == 1
    assert on_disk["results"] == results


def test_streaming_flag_defaults_false_and_accepts_one(monkeypatch):
    mod = load_module()
    monkeypatch.delenv("SORRYDB_V435_STREAM_CHILD_OUTPUT", raising=False)
    assert mod.env_flag("SORRYDB_V435_STREAM_CHILD_OUTPUT", False) is False
    monkeypatch.setenv("SORRYDB_V435_STREAM_CHILD_OUTPUT", "1")
    assert mod.env_flag("SORRYDB_V435_STREAM_CHILD_OUTPUT", False) is True


def test_streaming_runner_emits_progress_and_summaries(tmp_path, monkeypatch, capsys):
    mod = load_module()
    queue_path = tmp_path / "queue.json"
    replay_script = tmp_path / "fake_replay.py"
    work_root = tmp_path / "work"

    queue_path.write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "candidate_id": "fake-candidate",
                        "repo_root": str(tmp_path / "repo"),
                        "file_path": "Fake.lean",
                        "source_snippet": "by\n  sorry",
                        "patch_snippet": "by\n  trivial",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    replay_script.write_text(
        """import json
import os
import sys
from pathlib import Path

root = Path(os.environ["SORRYDB_V430_WORK_ROOT"])
out = root / "artifacts" / "runs" / "fake"
out.mkdir(parents=True, exist_ok=True)
(out / "patch_replay_manifest.json").write_text(json.dumps({
    "verdict": "PATCH_ACCEPTED",
    "patch_certificate_id": "fake-certificate",
    "patch_certificate_path": str(out / "fake-certificate.json"),
}))
print("fake replay stdout")
print("fake replay stderr", file=sys.stderr)
""",
        encoding="utf-8",
    )

    monkeypatch.setenv("SORRYDB_V435_QUEUE_PATH", str(queue_path))
    monkeypatch.setenv("SORRYDB_V435_WORK_ROOT", str(work_root))
    monkeypatch.setenv("SORRYDB_V435_REPLAY_SCRIPT", str(replay_script))
    monkeypatch.setenv("SORRYDB_V435_ALLOW_RUN", "1")
    monkeypatch.setenv("SORRYDB_V435_STREAM_CHILD_OUTPUT", "1")

    assert mod.main() == 0

    summaries = list(work_root.rglob("queue_run_summary.json"))
    partials = list(work_root.rglob("partial_queue_run_summary.json"))
    assert len(summaries) == 1
    assert len(partials) == 1

    summary = json.loads(summaries[0].read_text(encoding="utf-8"))
    partial = json.loads(partials[0].read_text(encoding="utf-8"))
    assert summary["verdict"] == mod.QUEUE_RUN_COMPLETED
    assert summary["results"][0]["returncode"] == 0
    assert summary["results"][0]["manifest_verdict"] == "PATCH_ACCEPTED"
    assert "fake replay stdout" in summary["results"][0]["stdout_tail"]
    assert partial["verdict"] == mod.QUEUE_RUN_IN_PROGRESS
    assert partial["completed_count"] == 1

    output = capsys.readouterr().out
    assert "QUEUE_CANDIDATE_START candidate_id=fake-candidate index=1/1" in output
    assert "QUEUE_CANDIDATE_DONE candidate_id=fake-candidate" in output
    assert "QUEUE_CANDIDATE_CERT candidate_id=fake-candidate" in output
    assert "[fake-candidate stdout] fake replay stdout" in output
