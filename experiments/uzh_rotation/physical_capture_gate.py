#!/usr/bin/env python3
"""Independent encoder edge-count preflight, not a flight-performance proof."""
import csv
import hashlib
import json
from pathlib import Path
import sys
from physical_clock_envelope import qualify

KINDS = ("camera", "gyro", "encoder")

def _positive_int(x):
    return type(x) is int and x > 0

def audit(path):
    manifest = Path(path).resolve()
    d = json.loads(manifest.read_text())
    errors = []
    streams = d.get("streams", {})
    if not isinstance(streams, dict):
        return ["invalid streams"]
    for kind in KINDS:
        s = streams.get(kind)
        if not isinstance(s, dict):
            errors.append(f"{kind}: missing stream")
            continue
        rel = s.get("path")
        if not isinstance(rel, str) or not rel:
            errors.append(f"{kind}: missing file path")
            continue
        f = (manifest.parent / rel).resolve()
        if not f.is_relative_to(manifest.parent) or not f.is_file():
            errors.append(f"{kind}: missing or escaping file")
            continue
        if hashlib.sha256(f.read_bytes()).hexdigest() != s.get("sha256"):
            errors.append(f"{kind}: hash mismatch")
        ts = s.get("timestamps_ns")
        if not isinstance(ts, list) or len(ts) < 2 or any(type(t) is not int for t in ts) or any(a >= b for a, b in zip(ts, ts[1:])):
            errors.append(f"{kind}: nonmonotonic timestamps")
        if not isinstance(s.get("clock_id"), str) or not s["clock_id"]:
            errors.append(f"{kind}: missing clock identity")
    encoder = streams.get("encoder")
    if isinstance(encoder, dict) and isinstance(encoder.get("path"), str):
        ef = (manifest.parent / encoder["path"]).resolve()
        if ef.is_relative_to(manifest.parent) and ef.is_file():
            try:
                with ef.open(newline="") as h:
                    rows = list(csv.DictReader(h))
                pulses = d.get("encoder_pulses_per_revolution")
                if not _positive_int(pulses):
                    errors.append("invalid encoder resolution")
                elif len(rows) < 2:
                    errors.append("insufficient encoder edges")
                else:
                    times = [int(row["timestamp_ns"]) for row in rows]
                    counts = [int(row["unwrapped_count"]) for row in rows]
                    if any(a >= b for a, b in zip(times, times[1:])):
                        errors.append("encoder timestamps not strictly increasing")
                    if any(b - a != 1 for a, b in zip(counts, counts[1:])):
                        errors.append("encoder count gaps/reversal; no verified full turns")
                    elif (counts[-1] - counts[0]) // pulses < 5:
                        errors.append("fewer than five encoder-derived complete turns")
                    if encoder.get("timestamps_ns") != times:
                        errors.append("encoder manifest timestamps differ from source")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(f"invalid encoder edge CSV: {exc}")
    if not isinstance(d.get("independent_timing_calibration_sha256"), str) or len(d["independent_timing_calibration_sha256"]) != 64:
        errors.append("missing independent calibration identity")
    errors.extend(qualify(manifest.parent, d.get("clock_calibration")))
    if not d.get("frozen_first_turn_map_sha256"):
        errors.append("missing frozen map identity")
    if d.get("encoder_used_by_estimator") is not False:
        errors.append("encoder isolation not attested")
    return errors

def main():
    try:
        issues = audit(sys.argv[1])
    except (IndexError, ValueError, OSError, TypeError, KeyError) as exc:
        issues = [f"invalid manifest: {exc}"]
    print(json.dumps({"state": "UNKNOWN" if issues else "STRUCTURAL_CANDIDATE_ONLY", "issues": issues}, indent=2))
    return bool(issues)

if __name__ == "__main__":
    sys.exit(main())
