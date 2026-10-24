#!/usr/bin/env python3
"""Structural source admission only: never certifies heading recovery."""
import hashlib
import json
from pathlib import Path
import sys

KINDS = ("camera", "gyro", "encoder")

def audit(path):
    manifest = Path(path).resolve()
    d = json.loads(manifest.read_text())
    errors = []
    streams = d.get("streams", {})
    for kind in KINDS:
        s = streams.get(kind)
        if not isinstance(s, dict):
            errors.append(f"{kind}: missing stream")
            continue
        rel = s.get("path")
        if not isinstance(rel, str):
            errors.append(f"{kind}: missing file path")
            continue
        f = (manifest.parent / rel).resolve()
        if not f.is_relative_to(manifest.parent) or not f.is_file():
            errors.append(f"{kind}: missing or escaping file")
        elif hashlib.sha256(f.read_bytes()).hexdigest() != s.get("sha256"):
            errors.append(f"{kind}: hash mismatch")
        ts = s.get("timestamps_ns")
        if not isinstance(ts, list) or len(ts) < 2 or any(type(t) is not int for t in ts) or any(a >= b for a, b in zip(ts, ts[1:])):
            errors.append(f"{kind}: nonmonotonic timestamps")
        if not isinstance(s.get("clock_id"), str) or not s["clock_id"]:
            errors.append(f"{kind}: missing clock identity")
    turns = d.get("encoder_complete_revolutions")
    if type(turns) is not int or turns < 5:
        errors.append("fewer than five independently established revolutions")
    if not d.get("independent_timing_calibration_sha256"):
        errors.append("missing independent calibration")
    if d.get("held_out_timing_envelope_passed") is not True:
        errors.append("unqualified held-out timing envelope")
    if not d.get("frozen_first_turn_map_sha256"):
        errors.append("missing frozen map identity")
    if d.get("encoder_used_by_estimator") is not False:
        errors.append("encoder isolation unverified")
    return errors

def main():
    try:
        issues = audit(sys.argv[1])
    except (IndexError, ValueError, OSError, TypeError, KeyError) as e:
        issues = [f"invalid manifest: {e}"]
    print(json.dumps({"state": "UNKNOWN" if issues else "STRUCTURAL_CANDIDATE_ONLY", "issues": issues}, indent=2))
    return bool(issues)

if __name__ == "__main__":
    sys.exit(main())
