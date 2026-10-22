"""Independent z-axis angular sweep check for RobotEvt UR5 poses.

Uses only NumPy and pairwise rotation matrices, not the existing SciPy Euler
angle or quaternion code. Z is the *reported pose frame* axis; camera/aircraft
alignment has not been independently calibrated. Offline dataset admission only.
"""

import argparse
import json
import math

import numpy as np


def classify_trajectory(timestamps, rotations):
    """Classify continuous 2+ turn fixed-z sweeps; refuse ambiguous sampling.

    Two turns means one uninterrupted *directional streak* of at least 720°.
    Small (<0.2°) per-sample reversals are ignored, not counted as evidence.
    >=90° between recorded poses is unqualified owing to temporal alias risk.
    This is a necessary-only screening gate, never proof of relocalization.
    """
    t = np.asarray(timestamps, dtype=float)
    r = np.asarray(rotations, dtype=float)
    if (r.ndim != 3 or r.shape[1:] != (3, 3) or len(r) < 10 or
            t.shape != (len(r),) or not np.all(np.isfinite(t)) or
            not np.all(np.isfinite(r)) or not np.all(np.diff(t) > 0)):
        raise ValueError("Invalid timestamp or Nx3x3 finite rotation sequence")
    orth = r @ np.transpose(r, (0, 2, 1))
    if (np.max(np.abs(orth - np.eye(3))) > 0.001 or
            np.max(np.abs(np.linalg.det(r) - 1)) > 0.001):
        raise ValueError("Invalid rotation matrix (orthogonality/determinant)")

    # Relative body-frame rotations remove the arbitrary starting attitude.
    rel = np.transpose(r[:-1], (0, 2, 1)) @ r[1:]
    step = np.arccos(np.clip((np.trace(rel, axis1=1, axis2=2) - 1) / 2, -1, 1))
    # Valid for a principally z-axis sequence, independently of Euler angles.
    dz = np.arctan2(rel[:, 1, 0] - rel[:, 0, 1],
                    rel[:, 0, 0] + rel[:, 1, 1])
    angle = np.r_[0., np.cumsum(dz)]
    full = 2 * math.pi
    absolute_path = float(np.sum(step))
    z_path = float(np.sum(np.abs(dz)))
    # The z share of a rotation-vector step is |z_axis|*step. Derive it
    # from the 3D skew matrix rather than dividing approximate planar
    # and 3D path estimates (which can round to an impossible >100%).
    skew_z = rel[:, 1, 0] - rel[:, 0, 1]
    axis_z = np.zeros_like(step)
    reliable_step = step > 1e-7
    axis_z[reliable_step] = np.clip(
        skew_z[reliable_step] / (2 * np.sin(step[reliable_step])), -1, 1)
    aligned = (float(np.sum(np.abs(axis_z) * step)) / absolute_path
               if absolute_path > 1e-8 else 0.)
    sampling_admissible = bool(np.max(step) < math.pi / 2)

    # Remove sub-threshold velocity signs, retaining the direction of every
    # consequential increment. Does not use any ground-truth future labels.
    signed = dz[np.abs(dz) > math.radians(0.2)]
    longest = 0.
    streak = 0.
    direction = 0
    reversals = 0
    for delta in signed:
        current = 1 if delta > 0 else -1
        if direction and current != direction:
            reversals += 1
            longest = max(longest, streak)
            streak = 0.
        streak += abs(float(delta))
        direction = current
    longest = max(longest, streak)

    if not sampling_admissible or aligned < 0.95 or absolute_path < 1e-8:
        admission = "UNKNOWN"
    elif longest >= 2 * full - 1e-7:
        admission = "ADMITTED"
    else:
        admission = "REJECTED"
    return {
        "samples": int(len(r)),
        "duration_s": float(t[-1] - t[0]),
        "yaw_excursion_turns": float(np.ptp(angle) / full),
        "net_yaw_turns": float(angle[-1] / full),
        "absolute_yaw_path_turns": z_path / full,
        "absolute_3d_path_turns": absolute_path / full,
        "longest_directional_streak_turns": longest / full,
        "axis_aligned_path_fraction": float(aligned),
        "direction_reversals": reversals,
        "max_step_deg": float(np.rad2deg(np.max(step))),
        "sampling_admissible": sampling_admissible,
        "admission": admission,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("groundtruth", help="Original RobotEvt N x 13 pose text")
    parser.add_argument("--output", default="robotevt_sweep_audit.json")
    args = parser.parse_args()
    pose = np.loadtxt(args.groundtruth)
    if pose.ndim != 2 or pose.shape[1] != 13:
        raise ValueError("RobotEvt ground truth must be N x 13")
    report = classify_trajectory(pose[:, 0], pose[:, 1:10].reshape(-1, 3, 3))
    with open(args.output, "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
