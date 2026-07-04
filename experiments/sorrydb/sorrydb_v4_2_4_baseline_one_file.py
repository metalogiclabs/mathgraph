#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GIB = 1024 ** 3
BANNER = "MATHGRAPH x SORRYDB v4.2.4 — BASELINE-ONLY REPLAY MANIFEST"

BASELINE_PASSED = "BASELINE_PASSED"
OBSTRUCTED_DISK_PRESSURE = "OBSTRUCTED_DISK_PRESSURE"
OBSTRUCTED_SOURCE_MISSING = "OBSTRUCTED_SOURCE_MISSING"
OBSTRUCTED_REPO_MISSING = "OBSTRUCTED_REPO_MISSING"
OBSTRUCTED_UNSAFE_COMMAND = "OBSTRUCTED_UNSAFE_COMMAND"
OBSTRUCTED_BASELINE_TIMEOUT = "OBSTRUCTED_BASELINE_TIMEOUT"
OBSTRUCTED_BASELINE_COMPILE_FAILURE = "OBSTRUCTED_BASELINE_COMPILE_FAILURE"
OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY = "OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY"


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def nearest_existing(path: Path) -> Path:
    probe = path.expanduser()
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe


def free_gb(path: Path) -> float:
    return round(shutil.disk_usage(nearest_existing(path)).free / GIB, 3)


def command_is_safe(cmd: list[str], allow_cache_get: bool) -> bool:
    joined = " ".join(cmd)
    forbidden = [
        "lake update",
        "elan default",
        "elan override",
        "rm -rf",
        "sudo",
        "curl ",
        "wget ",
        "git clone",
        "git fetch",
        "git checkout",
    ]
    if not allow_cache_get:
        forbidden.append("lake exe cache get")
    return not any(x in joined for x in forbidden)


def classify(returncode: int, stdout: str, stderr: str, timed_out: bool) -> str:
    text = f"{stdout}\n{stderr}"
    if timed_out:
        return OBSTRUCTED_BASELINE_TIMEOUT
    if returncode == 0:
        return BASELINE_PASSED
    lowered = text.casefold()
    cache_markers = [
        "no such file or directory",
        "unknown package",
        "missing manifest",
        "invalid manifest",
        "toolchain",
        "failed to download",
        "could not download",
        "dependency",
        "lakefile",
        "olean",
        "build failed",
    ]
    if any(marker in lowered for marker in cache_markers):
        return OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY
    return OBSTRUCTED_BASELINE_COMPILE_FAILURE


def run_process_group(cmd: list[str], cwd: Path, timeout: int) -> dict[str, Any]:
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = proc.communicate()
    return {
        "cmd": cmd,
        "cwd": str(cwd),
        "returncode": proc.returncode,
        "timed_out": timed_out,
        "stdout_tail": (stdout or "")[-4000:],
        "stderr_tail": (stderr or "")[-4000:],
    }


def main() -> int:
    print(BANNER)

    repo_root = Path(env("SORRYDB_V424_REPO_ROOT"))
    file_path = env("SORRYDB_V424_FILE_PATH")
    work_root = Path(env("SORRYDB_V424_WORK_ROOT", "/tmp/mathgraph_sorrydb_v424_baseline_one_file"))
    required_gb = float(env("SORRYDB_V424_MIN_FREE_GB", "20"))
    timeout = int(env("SORRYDB_V424_TIMEOUT_SECONDS", "60"))
    allow_cache_get = env_flag("SORRYDB_V424_ALLOW_CACHE_GET", False)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = work_root / "artifacts" / "runs" / "sorrydb_v4_2_4_baseline_only_replay" / timestamp
    out.mkdir(parents=True, exist_ok=True)

    source = repo_root / file_path if file_path else repo_root
    summary: dict[str, Any] = {
        "repo_root": str(repo_root),
        "file_path": file_path,
        "source": str(source),
        "work_root": str(work_root),
        "required_gb": required_gb,
        "free_gb": {
            str(work_root): free_gb(work_root),
            str(repo_root): free_gb(repo_root),
            str(Path.home()): free_gb(Path.home()),
            str(Path.home() / ".cache"): free_gb(Path.home() / ".cache"),
        },
        "allow_cache_get": allow_cache_get,
        "timeout_seconds": timeout,
        "command": [],
        "result": {},
        "verdict": "",
    }

    if min(summary["free_gb"].values()) < required_gb:
        summary["verdict"] = OBSTRUCTED_DISK_PRESSURE
    elif not repo_root.exists():
        summary["verdict"] = OBSTRUCTED_REPO_MISSING
    elif not source.exists():
        summary["verdict"] = OBSTRUCTED_SOURCE_MISSING
    else:
        cmd = ["lake", "env", "lean", file_path]
        summary["command"] = cmd
        if not command_is_safe(cmd, allow_cache_get):
            summary["verdict"] = OBSTRUCTED_UNSAFE_COMMAND
        else:
            result = run_process_group(cmd, repo_root, timeout)
            summary["result"] = result
            summary["verdict"] = classify(
                int(result.get("returncode") or 0),
                str(result.get("stdout_tail") or ""),
                str(result.get("stderr_tail") or ""),
                bool(result.get("timed_out")),
            )

    (out / "baseline_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
