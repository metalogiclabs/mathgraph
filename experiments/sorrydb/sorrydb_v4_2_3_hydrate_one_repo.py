#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


GIB = 1024 ** 3
BANNER = "MATHGRAPH x SORRYDB v4.2.3 — SINGLE-REPO HYDRATION MANIFEST"

OBSTRUCTED_DISK_PRESSURE = "OBSTRUCTED_DISK_PRESSURE"
OBSTRUCTED_UNSAFE_REPO_URL = "OBSTRUCTED_UNSAFE_REPO_URL"
OBSTRUCTED_REPO_NOT_CACHED = "OBSTRUCTED_REPO_NOT_CACHED"
OBSTRUCTED_GIT_FAILURE = "OBSTRUCTED_GIT_FAILURE"
HYDRATED_REPO_AT_RECORDED_COMMIT = "HYDRATED_REPO_AT_RECORDED_COMMIT"


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def free_gb(path: Path) -> float:
    probe = path.expanduser()
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return round(shutil.disk_usage(probe).free / GIB, 3)


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> dict:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        return {
            "cmd": cmd,
            "cwd": str(cwd) if cwd else None,
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": cmd,
            "cwd": str(cwd) if cwd else None,
            "returncode": 124,
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "TIMEOUT",
        }


def safe_url(repo: str) -> bool:
    return repo.startswith("https://github.com/") and not any(x in repo for x in [";", "&", "|", "`", "$", "\n"])


def main() -> int:
    print(BANNER)

    repo = env("SORRYDB_V423_REPO")
    commit = env("SORRYDB_V423_COMMIT")
    cache_path = Path(env("SORRYDB_V423_CACHE_PATH"))
    work_root = Path(env("SORRYDB_V423_WORK_ROOT", "/tmp/mathgraph_sorrydb_v423_hydrate_one_repo"))
    required_gb = float(env("SORRYDB_V423_MIN_FREE_GB", "20"))
    timeout = int(env("SORRYDB_V423_TIMEOUT_SECONDS", "120"))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = work_root / "artifacts" / "runs" / "sorrydb_v4_2_3_single_repo_hydration" / timestamp
    out.mkdir(parents=True, exist_ok=True)

    summary = {
        "repo": repo,
        "commit": commit,
        "cache_path": str(cache_path),
        "work_root": str(work_root),
        "required_gb": required_gb,
        "free_gb": {
            str(work_root): free_gb(work_root),
            str(cache_path.parent): free_gb(cache_path.parent),
            str(Path.home()): free_gb(Path.home()),
        },
        "commands": [],
        "repo_exists_before": cache_path.exists(),
        "repo_exists_after": False,
        "head_commit": "",
        "verdict": "",
    }

    if min(summary["free_gb"].values()) < required_gb:
        summary["verdict"] = OBSTRUCTED_DISK_PRESSURE
        (out / "hydration_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    if not safe_url(repo):
        summary["verdict"] = OBSTRUCTED_UNSAFE_REPO_URL
        (out / "hydration_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    if not repo or not commit or not str(cache_path):
        summary["verdict"] = OBSTRUCTED_REPO_NOT_CACHED
        (out / "hydration_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if not cache_path.exists():
        r = run(["git", "clone", "--no-tags", "--filter=blob:none", repo, str(cache_path)], timeout=timeout)
        summary["commands"].append(r)
        if r["returncode"] != 0:
            summary["verdict"] = OBSTRUCTED_GIT_FAILURE
            (out / "hydration_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
            print(json.dumps(summary, indent=2, sort_keys=True))
            return 0

    r = run(["git", "fetch", "--depth", "1", "origin", commit], cwd=cache_path, timeout=timeout)
    summary["commands"].append(r)
    if r["returncode"] != 0:
        summary["verdict"] = OBSTRUCTED_GIT_FAILURE
        (out / "hydration_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    r = run(["git", "checkout", "--detach", commit], cwd=cache_path, timeout=timeout)
    summary["commands"].append(r)
    if r["returncode"] != 0:
        summary["verdict"] = OBSTRUCTED_GIT_FAILURE
        (out / "hydration_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    r = run(["git", "rev-parse", "HEAD"], cwd=cache_path, timeout=timeout)
    summary["commands"].append(r)
    summary["head_commit"] = r["stdout_tail"].strip()
    summary["repo_exists_after"] = cache_path.exists()
    summary["verdict"] = (
        HYDRATED_REPO_AT_RECORDED_COMMIT
        if summary["head_commit"] == commit
        else OBSTRUCTED_GIT_FAILURE
    )

    (out / "hydration_manifest.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
