#!/usr/bin/env python3
"""Five-turn source admission: structural qualification only, not heading recovery."""
import csv
import hashlib
import json
from pathlib import Path
import sys

from physical_clock_envelope import qualify

KINDS = ("camera", "gyro", "encoder")

def _timestamps(path):
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "timestamp_ns" not in reader.fieldnames:
            raise ValueError("CSV lacks timestamp_ns")
        times = [int(row["timestamp_ns"]) for row in reader]
    if len(times) < 2 or any(t < 0 for t in times):
        raise ValueError("missing/invalid timestamp samples")
    if any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError("timestamps must strictly increase")
    return times

def _admit_file(root, record, role, errors):
    if not isinstance(record, dict):
        errors.append(f"{role}: missing record")
        return None
    rel = record.get("path")
    if not isinstance(rel, str) or not rel:
        errors.append(f"{role}: missing file path")
        return None
    candidate = (root / rel).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        errors.append(f"{role}: missing, escaping or non-file source")
        return None
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != record.get("sha256"):
        errors.append(f"{role}: file hash mismatch")
    return candidate

def audit(path):
    manifest = Path(path).resolve()
    d = json.loads(manifest.read_text())
    errors = []
    root = manifest.parent
    streams = d.get("streams")
    if not isinstance(streams, dict):
        return ["missing streams"]
    admitted = {}
    for kind in KINDS:
        record = streams.get(kind)
        file = _admit_file(root, record, kind, errors)
        if file is None:
            continue
        admitted[kind] = file
        if not isinstance(record.get("clock_id"), str) or not record["clock_id"]:
            errors.append(f"{kind}: missing clock identity")
        try:
            native = _timestamps(file)
            if record.get("timestamps_ns") != native:
                errors.append(f"{kind}: manifest/source timestamp disagreement")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"{kind}: malformed source timestamps: {exc}")
    if len(set(admitted.values())) != len(admitted):
        errors.append("distinct sensors share one source file")

    encoder = admitted.get("encoder")
    pulses = d.get("encoder_pulses_per_revolution")
    if type(pulses) is not int or pulses <= 0:
        errors.append("invalid encoder pulses per revolution")
    elif encoder is not None:
        try:
            with encoder.open(newline="") as source:
                rows = list(csv.DictReader(source))
            counts = [int(row["unwrapped_count"]) for row in rows]
            if any(b - a != 1 for a, b in zip(counts, counts[1:])):
                errors.append("encoder count gap or reversal")
            elif len(counts) < 2 or (counts[-1] - counts[0]) // pulses < 5:
                errors.append("fewer than five source-derived encoder turns")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"invalid encoder source counts: {exc}")

    errors.extend(qualify(root, d.get("clock_calibration")))

    frozen = _admit_file(root, d.get("frozen_first_turn_map"), "frozen map", errors)
    if frozen is not None and frozen in admitted.values():
        errors.append("frozen map shares a raw sensor source")
    if d.get("encoder_used_by_estimator") is not False:
        errors.append("encoder non-use is not attested; real enforcement requires isolation-run evidence")
    return errors

def main():
    try:
        issues = audit(sys.argv[1])
    except (IndexError, ValueError, OSError, TypeError, KeyError) as exc:
        issues = [f"invalid manifest: {exc}"]
    print(json.dumps({"state": "UNKNOWN" if issues else "STRUCTURAL_CANDIDATE_ONLY",
                      "issues": issues}, indent=2))
    return bool(issues)

if __name__ == "__main__":
    sys.exit(main())
