#!/usr/bin/env python3
"""Fail-closed structural audit of a five-revolution capture manifest.

Usage: python3 capture_gate.py manifest.json
Only checks capture eligibility; it never certifies navigation performance.
"""
import hashlib
import json
import pathlib
import sys

REQUIRED = ("camera", "gyro", "encoder")
def audit(path):
    p = pathlib.Path(path).resolve()
    data = json.loads(p.read_text())
    errors = []
    streams = data.get("streams", {})
    for kind in REQUIRED:
        s = streams.get(kind)
        if not isinstance(s, dict):
            errors.append(f"missing {kind} stream")
            continue
        rel = s.get("path")
        if not isinstance(rel, str):
            errors.append(f"{kind}: missing path")
            continue
        file = (p.parent / rel).resolve()
        if not file.is_relative_to(p.parent) or not file.is_file():
            errors.append(f"{kind}: missing or escaping file")
            continue
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if digest != s.get("sha256"):
            errors.append(f"{kind}: SHA256 mismatch")
        stamps = s.get("timestamps_ns")
        if not isinstance(stamps, list) or len(stamps) < 2 or any(
            not isinstance(t, int) or isinstance(t, bool) for t in stamps
        ) or any(a >= b for a, b in zip(stamps, stamps[1:])):
            errors.append(f"{kind}: invalid monotonic timestamps")
        if not s.get("clock_id"):
            errors.append(f"{kind}: missing clock identity")
    turns = data.get("encoder_complete_revolutions")
    if not isinstance(turns, int) or isinstance(turns, bool) or turns < 5:
        errors.append("fewer than five encoder-certified complete revolutions")
    if not data.get("independent_timing_calibration_sha256"):
        errors.append("missing independent timing calibration identity")
    if not data.get("held_out_timing_envelope_passed", False):
        errors.append("timing envelope not independently qualified")
    if not data.get("frozen_first_turn_map_sha256"):
        errors.append("missing frozen first-turn map hash")
    if data.get("encoder_used_by_estimator") is not False:
        errors.append("encoder isolation not declared")
    return errors

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: capture_gate.py manifest.json")
    try:
        issues = audit(sys.argv[1])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        issues = [f"invalid manifest: {exc}"]
    print(json.dumps({"status": "UNKNOWN" if issues else "CAPTURE_STRUCTURALLY_ELIGIBLE",
                      "issues": issues}, indent=2))
    sys.exit(bool(issues))
