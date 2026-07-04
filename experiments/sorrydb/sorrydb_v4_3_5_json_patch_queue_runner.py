#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


QUEUE_RUN_DISABLED = "QUEUE_RUN_DISABLED"
QUEUE_RUN_COMPLETED = "QUEUE_RUN_COMPLETED"
QUEUE_RUN_COMPLETED_WITH_FAILURES = "QUEUE_RUN_COMPLETED_WITH_FAILURES"
QUEUE_RUN_IN_PROGRESS = "QUEUE_RUN_IN_PROGRESS"
QUEUE_RUN_INTERRUPTED = "QUEUE_RUN_INTERRUPTED"
OBSTRUCTED_QUEUE_MISSING = "OBSTRUCTED_QUEUE_MISSING"
OBSTRUCTED_QUEUE_INVALID_JSON = "OBSTRUCTED_QUEUE_INVALID_JSON"
OBSTRUCTED_QUEUE_INVALID_ENTRY = "OBSTRUCTED_QUEUE_INVALID_ENTRY"
OBSTRUCTED_REPLAY_SCRIPT_MISSING = "OBSTRUCTED_REPLAY_SCRIPT_MISSING"


REQUIRED_ENTRY_KEYS = {
    "candidate_id",
    "repo_root",
    "file_path",
    "source_snippet",
    "patch_snippet",
}


OPTIONAL_ENTRY_KEYS = {
    "project",
    "project_commit",
    "certificate_id",
    "certificate_version",
    "restore_check",
    "timeout_seconds",
    "run_baseline_first",
    "min_free_gb",
}


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_queue(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], OBSTRUCTED_QUEUE_MISSING
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [], OBSTRUCTED_QUEUE_INVALID_JSON

    if isinstance(data, dict) and isinstance(data.get("candidates"), list):
        candidates = data["candidates"]
    elif isinstance(data, list):
        candidates = data
    else:
        return [], OBSTRUCTED_QUEUE_INVALID_ENTRY

    for entry in candidates:
        if not isinstance(entry, dict):
            return [], OBSTRUCTED_QUEUE_INVALID_ENTRY
        missing = REQUIRED_ENTRY_KEYS - set(entry)
        if missing:
            return [], OBSTRUCTED_QUEUE_INVALID_ENTRY
        for key in REQUIRED_ENTRY_KEYS:
            if not isinstance(entry.get(key), str) or not entry.get(key):
                return [], OBSTRUCTED_QUEUE_INVALID_ENTRY

    return candidates, ""


def build_replay_env(entry: dict[str, Any], work_root: Path) -> dict[str, str]:
    e = os.environ.copy()
    candidate_root = work_root / "candidates" / entry["candidate_id"]

    e["SORRYDB_V430_REPO_ROOT"] = entry["repo_root"]
    e["SORRYDB_V430_FILE_PATH"] = entry["file_path"]
    e["SORRYDB_V430_WORK_ROOT"] = str(candidate_root)
    e["SORRYDB_V430_ALLOW_PATCH"] = "1"
    e["SORRYDB_V430_SOURCE_SNIPPET"] = entry["source_snippet"]
    e["SORRYDB_V430_PATCH_SNIPPET"] = entry["patch_snippet"]

    e["SORRYDB_V430_TIMEOUT_SECONDS"] = str(entry.get("timeout_seconds", "120"))
    e["SORRYDB_V430_RUN_BASELINE_FIRST"] = str(entry.get("run_baseline_first", "1"))
    e["SORRYDB_V430_MIN_FREE_GB"] = str(entry.get("min_free_gb", "5"))

    if entry.get("project"):
        e["SORRYDB_V430_PROJECT"] = str(entry["project"])
    if entry.get("project_commit"):
        e["SORRYDB_V430_PROJECT_COMMIT"] = str(entry["project_commit"])
    if entry.get("certificate_id"):
        e["SORRYDB_V430_CERTIFICATE_ID"] = str(entry["certificate_id"])
    if entry.get("certificate_version"):
        e["SORRYDB_V430_CERTIFICATE_VERSION"] = str(entry["certificate_version"])
    if entry.get("restore_check"):
        e["SORRYDB_V430_RESTORE_CHECK"] = str(entry["restore_check"])

    return e


def latest_manifest(candidate_root: Path) -> str:
    hits = sorted(candidate_root.rglob("patch_replay_manifest.json"))
    if not hits:
        return ""
    return str(hits[-1])


class BoundedTail:
    def __init__(self, limit: int = 4000):
        self.limit = limit
        self.value = ""

    def append(self, text: str) -> None:
        self.value = (self.value + text)[-self.limit :]


def _consume_pipe(
    pipe: Any,
    tail: BoundedTail,
    candidate_id: str,
    stream_name: str,
    stream_output: bool,
) -> None:
    try:
        for line in iter(pipe.readline, ""):
            tail.append(line)
            if stream_output:
                print(f"[{candidate_id} {stream_name}] {line.rstrip()}", flush=True)
    finally:
        pipe.close()


def _stop_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def run_candidate(
    entry: dict[str, Any],
    work_root: Path,
    replay_script: Path,
    stream_child_output: bool = False,
) -> dict[str, Any]:
    candidate_root = work_root / "candidates" / entry["candidate_id"]
    candidate_root.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
        [sys.executable, str(replay_script)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=build_replay_env(entry, work_root),
    )
    assert proc.stdout is not None
    assert proc.stderr is not None
    stdout_tail = BoundedTail()
    stderr_tail = BoundedTail()
    readers = [
        threading.Thread(
            target=_consume_pipe,
            args=(proc.stdout, stdout_tail, entry["candidate_id"], "stdout", stream_child_output),
            daemon=True,
        ),
        threading.Thread(
            target=_consume_pipe,
            args=(proc.stderr, stderr_tail, entry["candidate_id"], "stderr", stream_child_output),
            daemon=True,
        ),
    ]
    for reader in readers:
        reader.start()

    timed_out = False
    try:
        proc.wait(timeout=int(entry.get("queue_timeout_seconds", 240)))
    except subprocess.TimeoutExpired:
        timed_out = True
        _stop_process(proc)
    except KeyboardInterrupt:
        _stop_process(proc)
        raise
    finally:
        for reader in readers:
            reader.join(timeout=5)

    manifest_path = latest_manifest(candidate_root)
    manifest_verdict = ""
    patch_certificate_id = ""
    patch_certificate_path = ""

    if manifest_path:
        try:
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
            manifest_verdict = str(manifest.get("verdict", ""))
            patch_certificate_id = str(manifest.get("patch_certificate_id", ""))
            patch_certificate_path = str(manifest.get("patch_certificate_path", ""))
        except Exception:
            manifest_verdict = "OBSTRUCTED_MANIFEST_READ"

    return {
        "candidate_id": entry["candidate_id"],
        "returncode": proc.returncode,
        "timed_out": timed_out,
        "stdout_tail": stdout_tail.value,
        "stderr_tail": stderr_tail.value,
        "manifest_path": manifest_path,
        "manifest_verdict": manifest_verdict,
        "patch_certificate_id": patch_certificate_id,
        "patch_certificate_path": patch_certificate_path,
    }


def progress_counts(results: list[dict[str, Any]]) -> tuple[int, int]:
    accepted = sum(1 for result in results if result.get("manifest_verdict") == "PATCH_ACCEPTED")
    return accepted, len(results) - accepted


def write_partial_summary(
    path: Path,
    summary: dict[str, Any],
    results: list[dict[str, Any]],
    verdict: str = QUEUE_RUN_IN_PROGRESS,
) -> dict[str, Any]:
    accepted, failed = progress_counts(results)
    partial = {
        "queue_path": summary["queue_path"],
        "work_root": summary["work_root"],
        "allow_run": summary["allow_run"],
        "replay_script": summary["replay_script"],
        "candidate_count": summary["candidate_count"],
        "completed_count": len(results),
        "accepted_count": accepted,
        "failed_count": failed,
        "results": results,
        "verdict": verdict,
    }
    path.write_text(json.dumps(partial, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return partial


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    queue_path = Path(env("SORRYDB_V435_QUEUE_PATH"))
    work_root = Path(env("SORRYDB_V435_WORK_ROOT", "/tmp/mathgraph_sorrydb_v435_queue_runner"))
    allow_run = env_flag("SORRYDB_V435_ALLOW_RUN", False)
    stream_child_output = env_flag("SORRYDB_V435_STREAM_CHILD_OUTPUT", False)
    replay_script = Path(env("SORRYDB_V435_REPLAY_SCRIPT", "experiments/sorrydb/sorrydb_v4_3_0_controlled_patch_replay.py"))

    out = work_root / "artifacts" / "runs" / "sorrydb_v4_3_5_json_patch_queue_runner" / utc_stamp()
    out.mkdir(parents=True, exist_ok=True)
    partial_path = out / "partial_queue_run_summary.json"
    summary_path = out / "queue_run_summary.json"

    summary: dict[str, Any] = {
        "queue_path": str(queue_path),
        "work_root": str(work_root),
        "allow_run": allow_run,
        "replay_script": str(replay_script),
        "candidate_count": 0,
        "results": [],
        "verdict": "",
    }

    candidates, obstruction = load_queue(queue_path)
    summary["candidate_count"] = len(candidates)

    if obstruction:
        summary["verdict"] = obstruction
    elif not replay_script.exists():
        summary["verdict"] = OBSTRUCTED_REPLAY_SCRIPT_MISSING
    elif not allow_run:
        summary["verdict"] = QUEUE_RUN_DISABLED
    else:
        results: list[dict[str, Any]] = []
        try:
            for index, entry in enumerate(candidates, start=1):
                candidate_id = entry["candidate_id"]
                print(
                    f"QUEUE_CANDIDATE_START candidate_id={candidate_id} index={index}/{len(candidates)}",
                    flush=True,
                )
                result = run_candidate(
                    entry,
                    work_root,
                    replay_script,
                    stream_child_output=stream_child_output,
                )
                results.append(result)
                print(
                    "QUEUE_CANDIDATE_DONE "
                    f"candidate_id={candidate_id} "
                    f"manifest_verdict={result['manifest_verdict']} "
                    f"returncode={result['returncode']}",
                    flush=True,
                )
                print(
                    "QUEUE_CANDIDATE_CERT "
                    f"candidate_id={candidate_id} "
                    f"patch_certificate_id={result['patch_certificate_id']}",
                    flush=True,
                )
                write_partial_summary(partial_path, summary, results)
        except KeyboardInterrupt:
            print("QUEUE_RUN_INTERRUPTED: preserving partial queue results", flush=True)
            accepted, failed = progress_counts(results)
            summary["results"] = results
            summary["completed_count"] = len(results)
            summary["accepted_count"] = accepted
            summary["failed_count"] = failed
            summary["verdict"] = QUEUE_RUN_INTERRUPTED
            write_partial_summary(partial_path, summary, results, QUEUE_RUN_INTERRUPTED)
            write_summary(summary_path, summary)
            print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
            return 130

        summary["results"] = results
        accepted, failed = progress_counts(results)
        summary["completed_count"] = len(results)
        summary["accepted_count"] = accepted
        summary["failed_count"] = failed
        summary["verdict"] = QUEUE_RUN_COMPLETED if accepted == len(results) else QUEUE_RUN_COMPLETED_WITH_FAILURES

    write_summary(summary_path, summary)
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
