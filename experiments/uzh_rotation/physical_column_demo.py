#!/usr/bin/env python3
"""Deterministic synthetic six-turn capture for pipeline tests, NOT real UAV data."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random

from physical_column_replay import Gyro, build_map, camera

PULSES_PER_REV = 64
STEP_NS = 50_000_000
TURNS = 6
GYRO_BIAS_RAD_S = 0.012
TRUE_SPEED = math.tau / (PULSES_PER_REV * (STEP_NS * 1e-9))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_rows(path, columns, rows):
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

def generate(root, *, scene="distinct", blackout=False, change=False):
    if scene not in ("distinct", "ambiguous"):
        raise ValueError(scene)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    scene_rng = random.Random(62026)
    world = [scene_rng.getrandbits(16) for _ in range(PULSES_PER_REV)]
    if scene == "ambiguous":
        world = [0xA55A] * PULSES_PER_REV
    n = TURNS * PULSES_PER_REV
    times = [i * STEP_NS for i in range(n + 1)]
    camera_rows = []
    for i, t in enumerate(times):
        usable = 0 if blackout and 80 <= i < 104 else 1
        value = world[i % PULSES_PER_REV]
        if change and i >= 150:
            value ^= 0xFFFF
        camera_rows.append((t, value, usable))
    filenames = {"camera": "camera.csv", "gyro": "gyro.csv", "encoder": "encoder.csv"}
    write_rows(root / filenames["camera"], ["timestamp_ns", "bits16", "usable"], camera_rows)
    write_rows(root / filenames["gyro"], ["timestamp_ns", "gyro_z_rad_s"],
               ((t, f"{TRUE_SPEED + GYRO_BIAS_RAD_S:.16f}") for t in times))
    write_rows(root / filenames["encoder"], ["timestamp_ns", "unwrapped_count"],
               ((t, i) for i, t in enumerate(times)))

    map_path = root / "frozen_map.json"
    frozen = build_map(camera(root / filenames["camera"]),
                       Gyro(root / filenames["gyro"]),
                       timing_error_ns=0, gyro_rate_bound=0.03,
                       firstturn_phase_bound=0.08)
    map_path.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n")
    traces = {}
    for role, base in (("calibration", 100), ("holdout", 200)):
        fp = root / (role + "_clock.csv")
        write_rows(fp, ["reference_timestamp_ns", "sensor_timestamp_ns"],
                   ((base+i, base+i+2) for i in range(3)))
        traces[role + "_path"] = fp.name
        traces[role + "_sha256"] = sha(fp)
    traces["frozen_offset_ns"] = 2
    traces["frozen_max_abs_residual_ns"] = 0
    manifest = {
        "provenance": "DETERMINISTIC_SYNTHETIC_NO_HARDWARE_WARRANT",
        "streams": {kind: {
            "path": name,
            "sha256": sha(root / name),
            "timestamps_ns": times,
            "clock_id": kind + "-synthetic",
        } for kind, name in filenames.items()},
        "clock_calibration": traces,
        "encoder_pulses_per_revolution": PULSES_PER_REV,
        "frozen_first_turn_map": {
            "path": map_path.name,
            "sha256": sha(map_path),
        },
        "encoder_used_by_estimator": False,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest

def main():
    p = argparse.ArgumentParser()
    p.add_argument("directory")
    p.add_argument("--scene", choices=("distinct", "ambiguous"), default="distinct")
    p.add_argument("--blackout", action="store_true")
    p.add_argument("--change", action="store_true")
    a = p.parse_args()
    generate(a.directory, scene=a.scene, blackout=a.blackout, change=a.change)
    print("DETERMINISTIC_SYNTHETIC_CAPTURE_ONLY", a.directory)

if __name__ == "__main__":
    main()
