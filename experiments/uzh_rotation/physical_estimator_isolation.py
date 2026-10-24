#!/usr/bin/env python3
"""Execute a Python estimator with only camera, gyro and frozen map mounted.

Security boundary: a constrained Docker container, not a Python import convention.
No encoder, host workspace, Git checkout, or network is mounted. This qualifies
input isolation *for executions through this launcher*, NOT hardware performance.
"""
import json
import os
from pathlib import Path
import subprocess

IMAGE = "python:3.11-slim"

class IsolationError(RuntimeError):
    pass

def _file(value):
    p = Path(value).resolve(strict=True)
    if not p.is_file():
        raise IsolationError(f"not a regular file: {p}")
    return p

def command(estimator, camera, gyro, first_turn_map, image=IMAGE):
    paths = [ _file(x) for x in (estimator, camera, gyro, first_turn_map) ]
    destinations = ("/estimator.py", "/camera.csv", "/gyro.csv", "/frozen_map.json")
    args = [
        "docker", "run", "--rm", "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "64", "--memory", "256m", "--cpus", "1",
        "--user", "65534:65534",
        "--tmpfs", "/tmp:rw,nosuid,noexec,size=8m"
    ]
    for source, target in zip(paths, destinations):
        args += ["--mount", f"type=bind,src={source},dst={target},readonly"]
    args += [image, "python", "/estimator.py", "/camera.csv", "/gyro.csv", "/frozen_map.json"]
    # Encoder is not among the permitted mounts. No host directories are mounted.
    return args

def execute(estimator, camera, gyro, first_turn_map, *, timeout=30):
    args = command(estimator, camera, gyro, first_turn_map)
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IsolationError(f"isolated run unavailable: {exc}") from exc
    if result.returncode:
        raise IsolationError(f"isolated estimator failed (exit {result.returncode}): {result.stderr[:1000]}")
    try:
        payload = json.loads(result.stdout)
    except ValueError as exc:
        raise IsolationError("estimator did not emit a JSON result") from exc
    if not isinstance(payload, dict):
        raise IsolationError("estimator output must be a JSON object")
    return payload

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("estimator")
    p.add_argument("camera")
    p.add_argument("gyro")
    p.add_argument("first_turn_map")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = execute(a.estimator, a.camera, a.gyro, a.first_turn_map)
    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
