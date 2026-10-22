"""Replay original RobotEvt ZIPs with pinned source hashes and two yaw formulas.

No rosbag inference or sensor-level accuracy claims: this qualifies *only*
the UR5 reference trajectory for a continuously spinning visual compass.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
from scipy.spatial.transform import Rotation

from audit_robotevt_sweep import classify_trajectory


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replay_archive(path, source):
    """Verify ZIP and GT bytes, then compare independent step and Euler yaw."""
    path = Path(path)
    if sha256_file(path) != source["archive_sha256"]:
        raise ValueError(f"{source['name']}: archive SHA256 mismatch")
    with zipfile.ZipFile(path) as archive:
        gt_bytes = archive.read(source["gt_member"])
    if hashlib.sha256(gt_bytes).hexdigest() != source["gt_sha256"]:
        raise ValueError(f"{source['name']}: ground truth SHA256 mismatch")
    pose = np.loadtxt(io.BytesIO(gt_bytes))
    if pose.ndim != 2 or pose.shape[1] != 13:
        raise ValueError("Original GT must contain timestamp, row-major R and xyz")
    rotations = pose[:, 1:10].reshape(-1, 3, 3)
    independent = classify_trajectory(pose[:, 0], rotations)

    # The pre-existing qualifier expresses yaw through SciPy Euler zyx;
    # the new implementation integrates native matrix step angles instead.
    legacy_angles = np.unwrap(Rotation.from_matrix(rotations).as_euler("zyx")[:, 0])
    legacy_extent = float(np.ptp(legacy_angles) / (2 * np.pi))
    gap = abs(legacy_extent - independent["yaw_excursion_turns"])
    if gap > 0.0001:
        raise AssertionError(f"{source['name']}: Euler/matrix yaw disagreement {gap}")
    if independent["admission"] != source["expected_admission"]:
        raise AssertionError(
            f"{source['name']}: expected admission {source['expected_admission']}, "
            f"measured {independent['admission']}")
    return {
        "source_name": source["name"],
        "archive_sha256": source["archive_sha256"],
        "gt_sha256": source["gt_sha256"],
        "legacy_yaw_excursion_turns": legacy_extent,
        "method_excursion_gap_turns": gap,
        "independent": independent,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--archives-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    results = {}
    for source in manifest["sequences"]:
        name = source["name"]
        # Reject malicious or ambiguous paths supplied by a changed manifest.
        if (not name.startswith("PureRot_") or
                any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in name)):
            raise ValueError(f"Invalid source name {name!r}")
        report = replay_archive(Path(args.archives_dir) / f"{name}.zip", source)
        results[name] = report
        result = report["independent"]
        print(f"{name}: 3D path={result['absolute_3d_path_turns']:.3f} "
              f"yaw excursion={result['yaw_excursion_turns']:.3f} "
              f"longest={result['longest_directional_streak_turns']:.3f} "
              f"status={result['admission']}")
    output = {"source": manifest["source"], "qualification": results}
    Path(args.output).write_text(json.dumps(output, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
