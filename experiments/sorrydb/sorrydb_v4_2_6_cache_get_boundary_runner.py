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
BANNER = "MATHGRAPH x SORRYDB v4.2.6 — CACHE-GET BOUNDARY RUNNER"

CACHE_GET_DISABLED = "CACHE_GET_DISABLED"
CACHE_GET_PASSED = "CACHE_GET_PASSED"
CACHE_GET_FAILED = "CACHE_GET_FAILED"
OBSTRUCTED_DISK_PRESSURE = "OBSTRUCTED_DISK_PRESSURE"
OBSTRUCTED_REPO_MISSING = "OBSTRUCTED_REPO_MISSING"
OBSTRUCTED_SOURCE_MISSING = "OBSTRUCTED_SOURCE_MISSING"
OBSTRUCTED_UNSAFE_COMMAND = "OBSTRUCTED_UNSAFE_COMMAND"
OBSTRUCTED_CACHE_GET_TIMEOUT = "OBSTRUCTED_CACHE_GET_TIMEOUT"
BASELINE_PASSED = "BASELINE_PASSED"
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
    if "lake exe cache get" in joined and not allow_cache_get:
        return False
    return not any(x in joined for x in forbidden)


def classify_baseline(returncode: int, stdout: str, stderr: str, timed_out: bool) -> str:
    text = f"{stdout}\n{stderr}"
    if timed_out:
        return OBSTRUCTED_BASELINE_TIMEOUT
    if returncode == 0:
        return BASELINE_PASSED
    lowered = text.casefold()
    cache_markers = [
        "unknown module prefix",
        "mathlib.olean",
        "no directory 'mathlib'",
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


def classify_cache_get(returncode: int, stdout: str, stderr: str, timed_out: bool) -> str:
    if timed_out:
        return OBSTRUCTED_CACHE_GET_TIMEOUT
    if returncode == 0:
        return CACHE_GET_PASSED
    return CACHE_GET_FAILED


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

    repo_root = Path(env("SORRYDB_V426_REPO_ROOT"))
    file_path = env("SORRYDB_V426_FILE_PATH")
    work_root = Path(env("SORRYDB_V426_WORK_ROOT", "/tmp/mathgraph_sorrydb_v426_cache_get_boundary"))
    required_gb = float(env("SORRYDB_V426_MIN_FREE_GB", "25"))
    cache_timeout = int(env("SORRYDB_V426_CACHE_GET_TIMEOUT_SECONDS", "600"))
    baseline_timeout = int(env("SORRYDB_V426_BASELINE_TIMEOUT_SECONDS", "60"))
    allow_cache_get = env_flag("SORRYDB_V426_ALLOW_CACHE_GET", False)
    run_baseline_after_cache = env_flag("SORRYDB_V426_RUN_BASELINE_AFTER_CACHE", True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = work_root / "artifacts" / "runs" / "sorrydb_v4_2_6_cache_get_boundary_runner" / timestamp
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
        "run_baseline_after_cache": run_baseline_after_cache,
        "cache_get_timeout_seconds": cache_timeout,
        "baseline_timeout_seconds": baseline_timeout,
        "cache_get_command": ["lake", "exe", "cache", "get"],
        "baseline_command": ["lake", "env", "lean", file_path],
        "cache_get_result": {},
        "baseline_result": {},
        "cache_get_verdict": "",
        "baseline_verdict": "",
        "verdict": "",
    }

    if min(summary["free_gb"].values()) < required_gb:
        summary["verdict"] = OBSTRUCTED_DISK_PRESSURE
    elif not repo_root.exists():
        summary["verdict"] = OBSTRUCTED_REPO_MISSING
    elif not source.exists():
        summary["verdict"] = OBSTRUCTED_SOURCE_MISSING
    elif not allow_cache_get:
        summary["cache_get_verdict"] = CACHE_GET_DISABLED
        summary["verdict"] = CACHE_GET_DISABLED
    elif not command_is_safe(summary["cache_get_command"], allow_cache_get=True):
        summary["verdict"] = OBSTRUCTED_UNSAFE_COMMAND
    else:
        cache_result = run_process_group(summary["cache_get_command"], repo_root, cache_timeout)
        summary["cache_get_result"] = cache_result
        summary["cache_get_verdict"] = classify_cache_get(
            int(cache_result.get("returncode") or 0),
            str(cache_result.get("stdout_tail") or ""),
            str(cache_result.get("stderr_tail") or ""),
            bool(cache_result.get("timed_out")),
        )

        if summary["cache_get_verdict"] != CACHE_GET_PASSED:
            summary["verdict"] = summary["cache_get_verdict"]
        elif not run_baseline_after_cache:
            summary["verdict"] = CACHE_GET_PASSED
        elif not command_is_safe(summary["baseline_command"], allow_cache_get=True):
            summary["verdict"] = OBSTRUCTED_UNSAFE_COMMAND
        else:
            baseline_result = run_process_group(summary["baseline_command"], repo_root, baseline_timeout)
            summary["baseline_result"] = baseline_result
            summary["baseline_verdict"] = classify_baseline(
                int(baseline_result.get("returncode") or 0),
                str(baseline_result.get("stdout_tail") or ""),
                str(baseline_result.get("stderr_tail") or ""),
                bool(baseline_result.get("timed_out")),
            )
            summary["verdict"] = summary["baseline_verdict"]

    (out / "cache_get_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
