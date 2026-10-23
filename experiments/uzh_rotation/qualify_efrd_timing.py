"""EFRD lab1 real IMU-to-external-mocap timestamp audit (development-only).

Not a visual compass, flight validation, or heading correction. External mocap
is used strictly for OFFLINE source qualification; it is never supplied to a
navigation estimator or to camera-event matching.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

SOURCE_SHA256 = "2fac73513203739df46fb085a4e67f8f41e7c2aa9ebfdd115d97b34a9929e484"
MOCAP_TOPIC = "/vrpn_client_node/Rigid0/pose"
SENSOR_TOPICS = ("/dvs/imu", "/imu/data")
MAX_LAG_S = 0.200
LAG_STEP_S = 0.005
MIN_EVAL_S = 10.0
MIN_SIDE_SAMPLES = 150


def sha256_file(file):
    h = hashlib.sha256()
    with Path(file).open("rb") as stream:
        for block in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def source_time_ns(stamp):
    sec, nsec = int(stamp.sec), int(stamp.nanosec)
    if nsec < 0 or nsec >= 1_000_000_000:
        raise ValueError("invalid original header nanoseconds")
    return sec * 1_000_000_000 + nsec


def check_times(ns, min_samples=2):
    x = np.asarray(ns, dtype=np.int64)
    if x.ndim != 1 or len(x) < min_samples:
        raise ValueError("insufficient source timestamps")
    step = np.diff(x)
    if np.any(step <= 0):
        raise ValueError("duplicate or reversed source timestamps")
    return x


def mocap_angular_speed(ns, quaternion):
    """Geodesic SO(3) speed; no post-hoc yaw-axis selection."""
    times = check_times(ns, 21)
    q = np.asarray(quaternion, dtype=np.float64)
    if q.shape != (len(times), 4) or not np.all(np.isfinite(q)):
        raise ValueError("invalid source mocap quaternion shape/values")
    norms = np.linalg.norm(q, axis=1)
    if np.any(np.abs(norms - 1.) > 0.05) or np.any(norms < 1e-6):
        raise ValueError("invalid source quaternion norm")
    R = Rotation.from_quat(q / norms[:, None])
    step = (R[:-1].inv() * R[1:]).magnitude()
    dt = np.diff(times).astype(np.float64) * 1e-9
    mid = times[:-1] + np.diff(times) // 2
    rate = step / dt
    if not np.all(np.isfinite(rate)):
        raise ValueError("nonfinite motion-capture speed")
    return mid, rate


def correlation(a, b):
    x = np.asarray(a, dtype=float)
    y = np.asarray(b, dtype=float)
    if (x.ndim != 1 or y.shape != x.shape or len(x) < MIN_SIDE_SAMPLES or
            not np.all(np.isfinite(x)) or not np.all(np.isfinite(y))):
        return None
    xx, yy = x - x.mean(), y - y.mean()
    divisor = math.sqrt(float(xx @ xx) * float(yy @ yy))
    if divisor <= 1e-12:
        return None
    return float((xx @ yy) / divisor)


def frozen_offset_split(mocap_ns, mocap_rate, gyro_ns, gyro_norm):
    """Fit first chronological half only; zero-lag comparison on later half.

    Search lags from -200ms to +200ms inclusive on a fixed 5ms grid.
    Positive lag means sample IMU at mocap_time+lag. No data-derived
    coordinate-axis choice or event-camera observation enters this method.
    """
    a = check_times(mocap_ns, 301)
    b = check_times(gyro_ns, 301)
    av = np.asarray(mocap_rate, dtype=float)
    bv = np.asarray(gyro_norm, dtype=float)
    if (av.shape != a.shape or bv.shape != b.shape or
            not np.isfinite(av).all() or not np.isfinite(bv).all() or
            np.any(av < 0) or np.any(bv < 0)):
        raise ValueError("invalid nonnegative rate stream")
    origin = min(int(a[0]), int(b[0]))
    x = (a - origin).astype(np.float64) * 1e-9
    y = (b - origin).astype(np.float64) * 1e-9

    start = max(x[0], y[0] + MAX_LAG_S)
    end = min(x[-1], y[-1] - MAX_LAG_S)
    result = {
        "reference":"independent mocap quaternion-increment angular-speed magnitude",
        "imu_signal":"norm of original uncalibrated 3D angular velocity",
        "lag_sign":"sample IMU at mocap_time + lag",
        "search_lag_min_s":-MAX_LAG_S,
        "search_lag_max_s":MAX_LAG_S,
        "search_lag_step_s":LAG_STEP_S,
        "shared_origin_ns":origin,
        "common_support_start_s":float(start),
        "common_support_end_s":float(end),
        "used_truth_for_navigation":False,
        "used_camera_events":False,
        "absolute_heading_error_bound":"NOT_ESTABLISHED",
        "cross_recording_replication":"NOT_TESTED",
    }
    if end - start < MIN_EVAL_S:
        return dict(result, status="UNKNOWN_NO_SUFFICIENT_COMMON_CLOCK")
    midpoint = (start + end) * 0.5
    train = (x >= start) & (x < midpoint)
    verify = (x >= midpoint) & (x <= end)
    if train.sum() < MIN_SIDE_SAMPLES or verify.sum() < MIN_SIDE_SAMPLES:
        return dict(result, status="UNKNOWN_INSUFFICIENT_CHRONOLOGICAL_SAMPLES")

    def score(lag, mask):
        v = x[mask] + lag
        if v[0] < y[0] or v[-1] > y[-1]:
            return None
        return correlation(av[mask], np.interp(v, y, bv))

    # Finite declared grid, with deterministic tie-break toward zero lag.
    lags = np.arange(-40, 41, dtype=int) * LAG_STEP_S
    scored = [(int(i), score(float(lag), train)) for i, lag in enumerate(lags)]
    scored = [(i, c) for i, c in scored if c is not None]
    if not scored:
        return dict(result, status="UNKNOWN_UNINFORMATIVE_TRAINING")
    winner = max(scored, key=lambda z: (z[1], -abs(float(lags[z[0]])), -float(lags[z[0]])))
    lag = float(lags[winner[0]])
    val_shifted = score(lag, verify)
    val_zero = score(0., verify)
    train_zero = score(0., train)
    metrics = {
        "selected_lag_s":round(lag, 9),
        "calibration_training_correlation":winner[1],
        "training_zero_lag_correlation":train_zero,
        "validation_frozen_lag_correlation":val_shifted,
        "validation_zero_lag_correlation":val_zero,
        "train_reference_intervals":int(train.sum()),
        "validation_reference_intervals":int(verify.sum()),
        "predeclared_lag_grid_size":81,
        "validation_used_for_selection":False,
        "absolute_angle_correction_authorized":False,
    }
    if val_shifted is None or val_zero is None:
        state = "UNKNOWN_UNINFORMATIVE_VALIDATION"
    elif val_shifted > val_zero + 1e-9 and winner[1] > 0.3 and val_shifted > 0.3:
        state = "CANDIDATE_WITHIN_RECORDING_LAG_TRANSFER"
    else:
        state = "NO_VALIDATED_TIMING_ADVANTAGE"
    return dict(result, status=state, metrics=metrics)


def replay(path):
    from rosbags.highlevel import AnyReader

    p = Path(path)
    sha = sha256_file(p)
    if sha != SOURCE_SHA256:
        raise ValueError("original EFRD lab1 bag source SHA256 mismatch")
    out = {
        "source":"EFRD original author-hosted lab1.bag",
        "source_sha256":sha,
        "source_bytes":p.stat().st_size,
        "mocap_topic":MOCAP_TOPIC,
        "development_source_already_exposed":True,
        "lab2_source_values_unopened":True,
        "camera_events_not_decoded":True,
        "mocap_never_used_as_visual_tracker_input":True,
        "navigation_correction_authorized":False,
        "qualification":"real-source temporal consistency only",
        "sensor_audits":{},
    }
    with AnyReader([p]) as reader:
        mocap = [c for c in reader.connections if c.topic == MOCAP_TOPIC]
        if len(mocap) != 1 or "PoseStamped" not in mocap[0].msgtype:
            out["status"] = "UNKNOWN_MOCAP_NOT_AUTHENTICATED"
            return out
        qt, q = [], []
        for c, _, raw in reader.messages(connections=mocap):
            m = reader.deserialize(raw, c.msgtype)
            qt.append(source_time_ns(m.header.stamp))
            o = m.pose.orientation
            q.append((o.x, o.y, o.z, o.w))
        try:
            reference_t, reference_rates = mocap_angular_speed(qt, q)
        except ValueError as exc:
            out["status"] = "UNKNOWN_MOCAP_CHRONOLOGY"
            out["reason"] = str(exc)
            return out
        out["mocap_pose_samples"] = len(qt)
        out["mocap_source_header_duration_s"] = (int(qt[-1]) - int(qt[0])) * 1e-9

        for topic in SENSOR_TOPICS:
            matches = [c for c in reader.connections if c.topic == topic]
            if len(matches) != 1 or "Imu" not in matches[0].msgtype:
                out["sensor_audits"][topic] = {"status":"UNKNOWN_NO_UNIQUE_IMU_SOURCE"}
                continue
            gt, gr = [], []
            for c, _, raw in reader.messages(connections=matches):
                m = reader.deserialize(raw, c.msgtype)
                gt.append(source_time_ns(m.header.stamp))
                w = m.angular_velocity
                gr.append(math.sqrt(w.x*w.x + w.y*w.y + w.z*w.z))
            time = np.asarray(gt, dtype=np.int64)
            out["sensor_audits"][topic] = {
                "imu_samples":len(time),
                "first_header_ns":int(time[0]) if len(time) else None,
                "last_header_ns":int(time[-1]) if len(time) else None,
                "repeated_header_times":int(np.sum(np.diff(time) == 0)),
                "reversed_header_times":int(np.sum(np.diff(time) < 0)),
            }
            try:
                gate = frozen_offset_split(reference_t, reference_rates, time, gr)
                out["sensor_audits"][topic]["timing"] = gate
                out["sensor_audits"][topic]["status"] = gate["status"]
            except ValueError as exc:
                out["sensor_audits"][topic]["status"] = "UNKNOWN_UNQUALIFIED_GYRO_SOURCE"
                out["sensor_audits"][topic]["reason"] = str(exc)

    out["status"] = "SOURCE_DIAGNOSTIC_ONLY"
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bag", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = replay(args.bag)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("EFRD_LAB1_TIMING", json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
