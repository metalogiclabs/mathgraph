#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


QUEUE_RUN_DISABLED = "QUEUE_RUN_DISABLED"
QUEUE_RUN_COMPLETED = "QUEUE_RUN_COMPLETED"
QUEUE_RUN_COMPLETED_WITH_FAILURES = "QUEUE_RUN_COMPLETED_WITH_FAILURES"
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


def run_candidate(entry: dict[str, Any], work_root: Path, replay_script: Path) -> dict[str, Any]:
    candidate_root = work_root / "candidates" / entry["candidate_id"]
    candidate_root.mkdir(parents=True, exist_ok=True)

    proc = subprocess.run(
        [sys.executable, str(replay_script)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=build_replay_env(entry, work_root),
        timeout=int(entry.get("queue_timeout_seconds", 240)),
    )

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
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
        "manifest_path": manifest_path,
        "manifest_verdict": manifest_verdict,
        "patch_certificate_id": patch_certificate_id,
        "patch_certificate_path": patch_certificate_path,
    }


def main() -> int:
    queue_path = Path(env("SORRYDB_V435_QUEUE_PATH"))
    work_root = Path(env("SORRYDB_V435_WORK_ROOT", "/tmp/mathgraph_sorrydb_v435_queue_runner"))
    allow_run = env_flag("SORRYDB_V435_ALLOW_RUN", False)
    replay_script = Path(env("SORRYDB_V435_REPLAY_SCRIPT", "experiments/sorrydb/sorrydb_v4_3_0_controlled_patch_replay.py"))

    out = work_root / "artifacts" / "runs" / "sorrydb_v4_3_5_json_patch_queue_runner" / utc_stamp()
    out.mkdir(parents=True, exist_ok=True)

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
        results = []
        for entry in candidates:
            results.append(run_candidate(entry, work_root, replay_script))
        summary["results"] = results
        accepted = sum(1 for r in results if r.get("manifest_verdict") == "PATCH_ACCEPTED")
        summary["accepted_count"] = accepted
        summary["failed_count"] = len(results) - accepted
        summary["verdict"] = QUEUE_RUN_COMPLETED if accepted == len(results) else QUEUE_RUN_COMPLETED_WITH_FAILURES

    path = out / "queue_run_summary.json"
    path.write_text(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
