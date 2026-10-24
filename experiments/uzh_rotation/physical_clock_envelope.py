#!/usr/bin/env python3
"""Independent numeric clock-envelope preflight.

CSV columns: reference_timestamp_ns,sensor_timestamp_ns.
Calibration residuals are computed against a declared frozen offset.
A holdout must be separate and every residual within the frozen envelope.
This does NOT establish physical instrument authenticity.
"""
import csv
import hashlib
from pathlib import Path

def _rows(path):
    with Path(path).open(newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) < 2:
        raise ValueError("insufficient clock observations")
    pairs = [(int(r["reference_timestamp_ns"]), int(r["sensor_timestamp_ns"])) for r in rows]
    if any(a[0] >= b[0] or a[1] >= b[1] for a,b in zip(pairs,pairs[1:])):
        raise ValueError("nonmonotonic clock observations")
    return pairs

def qualify(root, config):
    if not isinstance(config, dict):
        return ["missing clock calibration"]
    issues = []
    try:
        offset = config["frozen_offset_ns"]
        bound = config["frozen_max_abs_residual_ns"]
        if type(offset) is not int or type(bound) is not int or bound < 0:
            raise ValueError("invalid frozen offset/bound")
        traces = []
        paths = []
        for role in ("calibration", "holdout"):
            rel = config[role + "_path"]
            path = (root / rel).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError(role + ": missing or escaping file")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != config[role + "_sha256"]:
                raise ValueError(role + ": hash mismatch")
            traces.append(_rows(path))
            paths.append(path)
        if paths[0] == paths[1]:
            raise ValueError("calibration and holdout are identical")
        if not (traces[0][-1][0] < traces[1][0][0] or traces[1][-1][0] < traces[0][0][0]):
            raise ValueError("calibration and holdout time windows overlap")
        for role, rows in zip(("calibration", "holdout"), traces):
            if any(abs(sensor - reference - offset) > bound for reference, sensor in rows):
                issues.append(role + ": residual exceeds frozen envelope")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        issues.append("clock qualification invalid: " + str(exc))
    return issues
