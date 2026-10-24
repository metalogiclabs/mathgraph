#!/usr/bin/env python3
"""Source-faithful NAVIGATION-only adapter for canonical MGVC sensor bundles.

Consumes the existing role-disjoint MGVC-PHYSICAL-1 NAVIGATION contract.
Uses the canonical verifier to check original hashes, sizes, source chronology
and forbidden encoder fields before extracting camera/gyro CSV for the
supplemental model. It never accepts or opens an encoder bundle. Output is NOT
a canonical navigation decision record or a physical acceptance certificate.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from physical_evidence_gate import check_manifest, read_lines

SOURCES = ("sensors.jsonl", "decisions.jsonl", "timing.json")

def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_csv(path, cols, data):
    with Path(path).open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(data)

def convert(nav_dir, out_dir):
    nav_dir = Path(nav_dir).resolve(strict=True)
    output = Path(out_dir).resolve()
    if output == nav_dir or output.is_relative_to(nav_dir):
        raise ValueError("adapter output must not modify original navigation capture")
    # Delegate source admission to the already-qualified original role verifier.
    manifest = check_manifest(nav_dir, "nav_manifest.json", "NAVIGATION", SOURCES)
    sensor_path = nav_dir / "sensors.jsonl"
    records = read_lines(sensor_path)
    camera = []
    gyro = []
    for event in records:
        k = event.get("kind")
        if k == "COLUMN":
            if set(event) != {"seq", "t_ns", "kind", "status", "column_u16"}:
                raise ValueError("invalid original COLUMN event schema")
            status = event["status"]
            val = event["column_u16"]
            if status not in ("OK", "OCCLUDED"):
                raise ValueError("invalid original column status")
            if status == "OK":
                if type(val) is not int or not 0 <= val <= 65535:
                    raise ValueError("malformed 16-bit original column")
            elif val is not None:
                raise ValueError("occluded column has unexpected value")
            camera.append((event["t_ns"], 0 if val is None else val,
                           int(status == "OK")))
        elif k == "GYRO":
            if set(event) != {"seq", "t_ns", "kind", "omega_rad_s"}:
                raise ValueError("invalid original GYRO event schema")
            w = event["omega_rad_s"]
            if type(w) not in (int, float) or not math.isfinite(w):
                raise ValueError("nonfinite original gyro")
            gyro.append((event["t_ns"], w))
        else:
            raise ValueError("unknown original navigation sensor kind")
    if len(camera) < 2 or len(gyro) < 2:
        raise ValueError("insufficient admitted navigation sensor samples")
    output.mkdir(parents=True, exist_ok=True)
    camera_csv, gyro_csv = output / "camera.csv", output / "gyro.csv"
    write_csv(camera_csv, ("timestamp_ns", "bits16", "usable"), camera)
    write_csv(gyro_csv, ("timestamp_ns", "gyro_z_rad_s"), gyro)
    evidence = {
        "state": "SUPPLEMENTAL_NAVIGATION_SOURCE_ADAPTED_ONLY",
        "source_format": "MGVC-PHYSICAL-1",
        "capture_mode_as_claimed": manifest["mode"],
        "capture_id": manifest["capture_id"],
        "original_nav_manifest_sha256": file_sha256(nav_dir / "nav_manifest.json"),
        "original_sensor_sha256": file_sha256(sensor_path),
        "camera_samples": len(camera),
        "gyro_samples": len(gyro),
        "converted_camera_sha256": file_sha256(camera_csv),
        "converted_gyro_sha256": file_sha256(gyro_csv),
        "encoder_input_provided": False,
        "independent_heading_scored": False,
        "physical_navigation_authorized": False,
    }
    (output / "adapter_evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    return evidence

def main():
    p = argparse.ArgumentParser()
    p.add_argument("navigation_bundle")
    p.add_argument("output_directory")
    a = p.parse_args()
    print(json.dumps(convert(a.navigation_bundle, a.output_directory),
                     sort_keys=True))

if __name__ == "__main__":
    main()
