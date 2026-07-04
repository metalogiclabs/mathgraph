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
BANNER = "MATHGRAPH x SORRYDB v4.3.0 — CONTROLLED PATCH REPLAY"

PATCH_DISABLED = "PATCH_DISABLED"
PATCH_APPLIED = "PATCH_APPLIED"
PATCH_ACCEPTED = "PATCH_ACCEPTED"
PATCH_REJECTED = "PATCH_REJECTED"
BASELINE_PASSED = "BASELINE_PASSED"
OBSTRUCTED_DISK_PRESSURE = "OBSTRUCTED_DISK_PRESSURE"
OBSTRUCTED_REPO_MISSING = "OBSTRUCTED_REPO_MISSING"
OBSTRUCTED_SOURCE_MISSING = "OBSTRUCTED_SOURCE_MISSING"
OBSTRUCTED_UNSAFE_COMMAND = "OBSTRUCTED_UNSAFE_COMMAND"
OBSTRUCTED_PATCH_TARGET_MISSING = "OBSTRUCTED_PATCH_TARGET_MISSING"
OBSTRUCTED_PATCH_AMBIGUOUS = "OBSTRUCTED_PATCH_AMBIGUOUS"
OBSTRUCTED_BASELINE_TIMEOUT = "OBSTRUCTED_BASELINE_TIMEOUT"
OBSTRUCTED_BASELINE_COMPILE_FAILURE = "OBSTRUCTED_BASELINE_COMPILE_FAILURE"
OBSTRUCTED_PATCH_TIMEOUT = "OBSTRUCTED_PATCH_TIMEOUT"
OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY = "OBSTRUCTED_CACHE_OR_BUILD_BOUNDARY"


DEFAULT_SOURCE_SNIPPET = "theorem eg₁ (n : ℕ) : n ≤ n + 1 := sorry"
DEFAULT_PATCH_SNIPPET = "theorem eg₁ (n : ℕ) : n ≤ n + 1 := by exact Nat.le_succ n"


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


def command_is_safe(cmd: list[str]) -> bool:
    joined = " ".join(cmd)
    forbidden = [
        "lake update",
        "lake exe cache get",
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
    return not any(x in joined for x in forbidden)


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
        "stdout_tail": (stdout or "")[-5000:],
        "stderr_tail": (stderr or "")[-5000:],
    }


def classify_lean(returncode: int, stdout: str, stderr: str, timed_out: bool, timeout_verdict: str) -> str:
    text = f"{stdout}\n{stderr}"
    if timed_out:
        return timeout_verdict
    if returncode == 0:
        return BASELINE_PASSED
    lowered = text.casefold()
    cache_markers = [
        "unknown module prefix",
        "mathlib.olean",
        "no directory 'mathlib'",
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


def apply_single_replacement(source_text: str, old: str, new: str) -> tuple[str, str]:
    count = source_text.count(old)
    if count == 0:
        return source_text, OBSTRUCTED_PATCH_TARGET_MISSING
    if count > 1:
        return source_text, OBSTRUCTED_PATCH_AMBIGUOUS
    return source_text.replace(old, new, 1), PATCH_APPLIED


def main() -> int:
    print(BANNER)

    repo_root = Path(env("SORRYDB_V430_REPO_ROOT"))
    file_path = env("SORRYDB_V430_FILE_PATH", "MetaExamples/Fiddle.lean")
    work_root = Path(env("SORRYDB_V430_WORK_ROOT", "/tmp/mathgraph_sorrydb_v430_patch_replay"))
    required_gb = float(env("SORRYDB_V430_MIN_FREE_GB", "10"))
    timeout = int(env("SORRYDB_V430_TIMEOUT_SECONDS", "120"))

    allow_patch = env_flag("SORRYDB_V430_ALLOW_PATCH", False)
    run_baseline_first = env_flag("SORRYDB_V430_RUN_BASELINE_FIRST", True)

    old_snippet = os.getenv("SORRYDB_V430_SOURCE_SNIPPET", DEFAULT_SOURCE_SNIPPET)
    new_snippet = os.getenv("SORRYDB_V430_PATCH_SNIPPET", DEFAULT_PATCH_SNIPPET)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = work_root / "artifacts" / "runs" / "sorrydb_v4_3_0_controlled_patch_replay" / timestamp
    out.mkdir(parents=True, exist_ok=True)

    source = repo_root / file_path if file_path else repo_root
    lean_cmd = ["lake", "env", "lean", file_path]

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
        "allow_patch": allow_patch,
        "run_baseline_first": run_baseline_first,
        "timeout_seconds": timeout,
        "baseline_command": lean_cmd,
        "patch_command": lean_cmd,
        "source_snippet": old_snippet,
        "patch_snippet": new_snippet,
        "baseline_result": {},
        "baseline_verdict": "",
        "patch_apply_verdict": "",
        "patch_result": {},
        "patch_verdict": "",
        "verdict": "",
    }

    if min(summary["free_gb"].values()) < required_gb:
        summary["verdict"] = OBSTRUCTED_DISK_PRESSURE
    elif not repo_root.exists():
        summary["verdict"] = OBSTRUCTED_REPO_MISSING
    elif not source.exists():
        summary["verdict"] = OBSTRUCTED_SOURCE_MISSING
    elif not command_is_safe(lean_cmd):
        summary["verdict"] = OBSTRUCTED_UNSAFE_COMMAND
    elif not allow_patch:
        summary["verdict"] = PATCH_DISABLED
        summary["patch_apply_verdict"] = PATCH_DISABLED
    else:
        if run_baseline_first:
            baseline_result = run_process_group(lean_cmd, repo_root, timeout)
            summary["baseline_result"] = baseline_result
            summary["baseline_verdict"] = classify_lean(
                int(baseline_result.get("returncode") or 0),
                str(baseline_result.get("stdout_tail") or ""),
                str(baseline_result.get("stderr_tail") or ""),
                bool(baseline_result.get("timed_out")),
                OBSTRUCTED_BASELINE_TIMEOUT,
            )
            if summary["baseline_verdict"] != BASELINE_PASSED:
                summary["verdict"] = summary["baseline_verdict"]

        if not summary["verdict"]:
            original = source.read_text(encoding="utf-8")
            patched, apply_verdict = apply_single_replacement(original, old_snippet, new_snippet)
            summary["patch_apply_verdict"] = apply_verdict

            if apply_verdict != PATCH_APPLIED:
                summary["verdict"] = apply_verdict
            else:
                backup = source.with_suffix(source.suffix + ".v430_backup")
                backup.write_text(original, encoding="utf-8")
                source.write_text(patched, encoding="utf-8")
                try:
                    patch_result = run_process_group(lean_cmd, repo_root, timeout)
                    summary["patch_result"] = patch_result
                    patch_lean_verdict = classify_lean(
                        int(patch_result.get("returncode") or 0),
                        str(patch_result.get("stdout_tail") or ""),
                        str(patch_result.get("stderr_tail") or ""),
                        bool(patch_result.get("timed_out")),
                        OBSTRUCTED_PATCH_TIMEOUT,
                    )
                    if patch_lean_verdict == BASELINE_PASSED:
                        summary["patch_verdict"] = PATCH_ACCEPTED
                        summary["verdict"] = PATCH_ACCEPTED
                    elif patch_lean_verdict == OBSTRUCTED_BASELINE_COMPILE_FAILURE:
                        summary["patch_verdict"] = PATCH_REJECTED
                        summary["verdict"] = PATCH_REJECTED
                    else:
                        summary["patch_verdict"] = patch_lean_verdict
                        summary["verdict"] = patch_lean_verdict
                finally:
                    source.write_text(original, encoding="utf-8")

    (out / "patch_replay_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
