"""Fail-closed diagnostic for original ECRot Brandenburg IMU chronology.

This post-holdout diagnostic must not be presented as prospective validation.
Do not repair timestamps or infer ground-truth heading from gyroscope integration.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np


def inspect_chronology(header_s, bag_s, angular_velocity):
    h = np.asarray(header_s, dtype=np.float64)
    b = np.asarray(bag_s, dtype=np.float64)
    w = np.asarray(angular_velocity, dtype=np.float64)
    if h.ndim != 1 or len(h) < 2 or b.shape != h.shape or w.shape != (len(h), 3):
        raise ValueError("invalid IMU arrays")
    if not np.all(np.isfinite(h)) or not np.all(np.isfinite(b)) or not np.all(np.isfinite(w)):
        raise ValueError("nonfinite source observations")
    dh, db = np.diff(h), np.diff(b)
    backwards = np.flatnonzero(dh < 0)
    duplicates = np.flatnonzero(dh == 0)
    bag_backwards = np.flatnonzero(db < 0)
    positive = dh > 0
    median_dt = float(np.median(dh[positive])) if np.any(positive) else None
    gap_idxs = np.flatnonzero(dh > 10 * median_dt) if median_dt is not None else np.array([], dtype=int)
    # A diagnostic integral using only successive, strictly positive header-time
    # intervals; excluded discontinuities are NOT silently bridged.
    increments = (w[:-1] + w[1:]) / 2 * np.maximum(dh[:, None], 0)
    increments[~positive] = 0.
    gyro_integral = np.sum(increments, axis=0)
    abs_rotation = np.sum(np.abs(increments), axis=0)
    typical = np.median(np.abs(w), axis=0).tolist()
    def cases(indices):
        return [{"index": int(i), "before": float(h[i]), "after": float(h[i+1]),
                 "delta_sec": float(dh[i]), "bag_delta_sec":float(db[i])}
                for i in indices[:12]]
    return {
        "imu_samples": int(len(h)), "first_header_sec": float(h[0]),
        "last_header_sec": float(h[-1]),
        "header_negative_delta_count": int(len(backwards)),
        "header_duplicate_delta_count": int(len(duplicates)),
        "bag_negative_delta_count": int(len(bag_backwards)),
        "header_large_gap_count": int(len(gap_idxs)),
        "median_positive_sample_period_sec": median_dt,
        "first_header_negative_examples": cases(backwards),
        "first_header_duplicate_examples": cases(duplicates),
        "first_header_gap_examples": cases(gap_idxs),
        "bag_minus_header_first_sec": float(b[0]-h[0]),
        "bag_minus_header_last_sec": float(b[-1]-h[-1]),
        "median_abs_rate_xyz": typical,
        "naive_y_integral_on_positive_intervals_turns": float(gyro_integral[1]/(2*math.pi)),
        "abs_y_travel_on_positive_intervals_turns": float(abs_rotation[1]/(2*math.pi)),
        "diagnostic_only": True,
        "absolute_heading_truth": "UNAVAILABLE",
        "original_parser_accepts_imu": bool(not len(backwards) and not len(duplicates)),
    }


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for part in iter(lambda: source.read(16*1024*1024), b""):
            digest.update(part)
    return digest.hexdigest()


def probe(path):
    from rosbags.highlevel import AnyReader
    file = Path(path)
    digest = sha256(file)
    with AnyReader([file]) as reader:
        connections = [{"topic": c.topic, "msgtype":c.msgtype,
                        "messages":c.msgcount} for c in reader.connections]
        imu = [c for c in reader.connections if c.topic == "/dvs/imu"]
        events = [c for c in reader.connections if c.topic == "/dvs/events"]
        if len(imu) != 1 or len(events) != 1:
            raise ValueError("expected one IMU and one EventArray connection")
        header, bag, rate = [], [], []
        for conn, timestamp, raw in reader.messages(connections=imu):
            msg = reader.deserialize(raw, conn.msgtype)
            header.append(int(msg.header.stamp.sec) + int(msg.header.stamp.nanosec)*1e-9)
            bag.append(timestamp * 1e-9)
            rate.append([msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z])
    return {
        "experiment": "ECRot Brandenburg post-holdout diagnostic (not frozen prospective outcome)",
        "original_bag_sha256":digest,
        "original_file_size":file.stat().st_size,
        "connections":connections,
        "chronology": inspect_chronology(header,bag,rate),
        "state": "DIAGNOSTIC_ONLY; no heading correction authorized"
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--bag",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=probe(args.bag)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("ECRot BRBG SOURCE SHA256",result["original_bag_sha256"])
    print("ECRot BRBG CHRONOLOGY",json.dumps(result["chronology"],sort_keys=True))
    print("ECRot BRBG STATUS DIAGNOSTIC_ONLY")
if __name__=="__main__":
    main()
