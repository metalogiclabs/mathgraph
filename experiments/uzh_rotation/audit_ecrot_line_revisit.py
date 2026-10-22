"""One-column ECRot event camera first-circle map and revisit auditor.

The gyro defines only a *sensor-internal angular coordinate*. There is no
independently measured heading ground truth, and this code does not claim a
sensor-level error bound, two full turns, or a flight-ready line camera.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

import numpy as np


EVENT_DTYPE = np.dtype([
    ("x", "<u2"), ("y", "<u2"), ("sec", "<u4"),
    ("nsec", "<u4"), ("p", "u1"),
])


def decode_event_packet(raw):
    """Decode the original ROS1 EventArray wire format without ROS objects."""
    if len(raw) < 28:
        raise ValueError("ROS1 event packet payload too short")
    frame_len = struct.unpack_from("<I", raw, 12)[0]
    head_end = 16 + frame_len
    if head_end + 12 > len(raw):
        raise ValueError("ROS1 event packet payload has bad Header")
    height, width, count = struct.unpack_from("<III", raw, head_end)
    if height == 0 or width == 0 or count > 10000000 or len(raw) != head_end + 12 + count * EVENT_DTYPE.itemsize:
        raise ValueError("ROS1 event packet payload length mismatch")
    events = np.frombuffer(raw, dtype=EVENT_DTYPE, count=count, offset=head_end + 12)
    if (np.any(events["x"] >= width) or np.any(events["y"] >= height) or
            np.any(events["nsec"] >= 1000000000) or np.any(events["p"] > 1)):
        raise ValueError("Event coordinate, time, or polarity invalid")
    return int(height), int(width), events


def gyro_integrated_phase(time, velocity):
    """Trapezoidal integration of the predeclared IMU y axis in radians."""
    t = np.asarray(time, dtype=float)
    w = np.asarray(velocity, dtype=float)
    if (t.ndim != 1 or w.shape != t.shape or len(t) < 2 or
            not np.all(np.isfinite(t)) or not np.all(np.isfinite(w)) or
            not np.all(np.diff(t) > 0)):
        raise ValueError("Invalid IMU times or angular rates")
    return np.r_[0., np.cumsum((w[:-1] + w[1:]) * 0.5 * np.diff(t))]


def accumulate_column_packet(events, imu_times, gyro_phase, first, tail,
                             column=320, height=480):
    """Bin only observed center-column events; first full turn trains the map.

    Subsequent events are never allowed to update the frozen first-turn map.
    There is no extrapolation beyond observed IMU time coverage.
    """
    if first.ndim != 3 or first.shape != tail.shape or first.shape[2] != 2:
        raise ValueError("Invalid first/revisit histograms")
    if height <= 0 or column < 0:
        raise ValueError("Invalid column or image height")
    selected = events[events["x"] == column]
    timestamps = selected["sec"].astype(float) + selected["nsec"] * 1e-9
    valid = (timestamps >= imu_times[0]) & (timestamps <= imu_times[-1])
    if not np.any(valid):
        return {"selected_column": len(selected), "valid_time": 0}
    sampled = selected[valid]
    phase = np.interp(timestamps[valid], imu_times, gyro_phase)
    bins, verticals = first.shape[:2]
    sectors = np.minimum((np.mod(phase, 2 * math.pi) * bins /
                          (2 * math.pi)).astype(int), bins - 1)
    rows = np.minimum((sampled["y"].astype(int) * verticals // height),
                      verticals - 1)
    polarities = sampled["p"].astype(int)
    learning = phase < 2 * math.pi
    np.add.at(first, (sectors[learning], rows[learning],
                      polarities[learning]), 1)
    np.add.at(tail, (sectors[~learning], rows[~learning],
                     polarities[~learning]), 1)
    return {"selected_column": len(selected), "valid_time": len(sampled)}


def match_angular_map(known, tail, min_events=50, min_score=0.75,
                      min_margin=0.08):
    """Unrestricted conventional cosine retrieval with a conservative gate.

    The observation's gyro-derived angular sector is deliberately NOT passed
    to this function. The gate is conventional, not a claimed MathGraph
    advantage over an equally informed robust matching baseline.
    """
    matrix = np.asarray(known, dtype=float)
    vector = np.asarray(tail, dtype=float)
    if (matrix.ndim != 2 or matrix.shape[1:] != vector.shape or
            np.any(matrix < 0) or np.any(vector < 0) or
            not np.all(np.isfinite(matrix)) or not np.all(np.isfinite(vector))):
        raise ValueError("Invalid nonnegative descriptor matrix or observation")
    candidate = {"decision": "UNKNOWN", "best_sector": None,
                 "competing_sectors": [], "best_score": None,
                 "runner_up_score": None, "margin": None}
    if float(vector.sum()) < min_events:
        return candidate
    norms = np.linalg.norm(matrix, axis=1)
    valid = matrix.sum(axis=1) >= min_events
    # A solitary mapped sector cannot establish a meaningful runner-up gap:
    # treating the absent sectors as score -1 invents false uniqueness.
    if np.count_nonzero(valid) < 2:
        return candidate
    similarities = (matrix @ vector / (
        np.maximum(norms, 1e-12) * max(np.linalg.norm(vector), 1e-12)))
    similarities[~valid] = -1
    ranking = np.argsort(-similarities, kind="stable")
    best = int(ranking[0])
    top = float(similarities[best])
    second = float(similarities[int(ranking[1])]) if len(ranking) > 1 else -1.
    margin = top - second
    contenders = np.where(valid & (similarities >= top - min_margin))[0].tolist()
    candidate.update(best_sector=best, best_score=top,
                     runner_up_score=second, margin=margin,
                     competing_sectors=contenders)
    if top >= min_score and margin >= min_margin:
        candidate["decision"] = "CANDIDATE"
    return candidate


def sha256_file(path):
    """Hash the unmodified original bag before interpreting its content."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replay_bag(path, expected_sha256):
    """Replay the original ROS1 bag; never choose matches using gyro labels.

    This is an *exploratory real sensor audit* of a partial second turn, not an
    independent yaw accuracy experiment. The only reference is integrated
    uncalibrated gyro, which is unsuitable as a ground-truth heading.
    """
    from rosbags.highlevel import AnyReader  # Optional test-only dependency.

    path = Path(path)
    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise ValueError("Original ECRot ROS bag SHA256 mismatch")

    n_bins = 64
    vertical_bins = 24
    sensor_height = 480
    sensor_width = 640
    fixed_column = 320
    first = np.zeros((n_bins, vertical_bins, 2), dtype=np.int64)
    later = np.zeros_like(first)

    with AnyReader([path]) as reader:
        imu_connections = [c for c in reader.connections if c.topic == "/dvs/imu"]
        event_connections = [c for c in reader.connections if c.topic == "/dvs/events"]
        if len(imu_connections) != 1 or len(event_connections) != 1:
            raise ValueError("Expected one original /dvs/imu and /dvs/events stream")

        imu_t = []
        angular_y = []
        for conn, _, raw in reader.messages(connections=imu_connections):
            msg = reader.deserialize(raw, conn.msgtype)
            imu_t.append(msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9)
            angular_y.append(msg.angular_velocity.y)
        imu_t = np.asarray(imu_t, dtype=float)
        angular_y = np.asarray(angular_y, dtype=float)
        phase = gyro_integrated_phase(imu_t, angular_y)

        events_total = 0
        center_column_total = 0
        center_valid_time = 0
        checked_against_rosbags = False
        packets = 0
        for conn, _, raw in reader.messages(connections=event_connections):
            height, width, events = decode_event_packet(raw)
            if height != sensor_height or width != sensor_width:
                raise ValueError("Camera geometry differs from frozen 640x480")
            if not checked_against_rosbags:
                # Independent wire-parser control against the ROS type registry.
                decoded = reader.deserialize(raw, conn.msgtype)
                if (len(decoded.events) != len(events) or
                        decoded.height != height or decoded.width != width):
                    raise ValueError("Raw EventArray count contradicts rosbags")
                for j in (0, len(events) // 2, len(events) - 1):
                    sample = decoded.events[j]
                    ev = events[j]
                    if (int(ev["x"]) != sample.x or
                            int(ev["y"]) != sample.y or
                            int(ev["sec"]) != sample.ts.sec or
                            int(ev["nsec"]) != sample.ts.nanosec or
                            bool(ev["p"]) != sample.polarity):
                        raise ValueError("Raw ROS parser disagrees with rosbags")
                checked_against_rosbags = True
            totals = accumulate_column_packet(events, imu_t, phase, first, later,
                                              column=fixed_column, height=height)
            center_column_total += int(totals["selected_column"])
            center_valid_time += int(totals["valid_time"])
            events_total += len(events)
            packets += 1

    turns = float(phase[-1] / (2 * math.pi))
    first_events = int(first.sum())
    revisit_events = int(later.sum())
    nonempty = np.flatnonzero(first.sum(axis=(1, 2)))
    tail_sectors = np.flatnonzero(later.sum(axis=(1, 2)))
    observed = []
    bank = first.reshape(n_bins, -1)
    for i in tail_sectors:
        actual = later[int(i)].reshape(-1)
        retrieval = match_angular_map(bank, actual)
        # Gyro appears only in an explicitly labelled agreement diagnostic,
        # never as a search constraint, confidence input or navigation truth.
        observed.append({
            "gyro_proxy_sector": int(i),
            "events": int(actual.sum()),
            "unrestricted_visual_retrieval": retrieval,
            "agrees_with_gyro_sector": retrieval["best_sector"] == int(i),
        })

    return {
        "source": {"name": "ECRot Charlottenburg Palace original ROS1 bag",
                   "filename": path.name, "original_sha256": actual_sha256,
                   "format": "original event camera and gyroscope; no absolute ground truth"},
        "frozen_parameters": {
            "gyro_axis": "y", "gyro_integration": "trapezoidal, uncalibrated",
            "sensor_width": sensor_width, "sensor_height": sensor_height,
            "column": fixed_column, "angular_bins": n_bins,
            "vertical_bins": vertical_bins, "event_polarities": 2,
            "min_events": 50, "min_cosine": 0.75, "min_top2_margin": 0.08,
            "first_turn_rule": "freeze map at gyro-integrated 2pi",
        },
        "observation": {
            "imu_samples": len(imu_t), "event_packets": packets,
            "total_event_camera_events": int(events_total),
            "events_at_fixed_column": center_column_total,
            "fixed_column_within_imu_interval": center_valid_time,
            "gyro_integrated_y_turns": turns,
            "first_turn_map_events": first_events,
            "later_revisit_events": revisit_events,
            "first_turn_coverage_bins": len(nonempty),
            "first_turn_coverage_total_bins": n_bins,
            "first_turn_min_events_per_bin": (int(first.sum(axis=(1, 2))[nonempty].min())
                                              if len(nonempty) else 0),
            "first_turn_map_sha256": hashlib.sha256(first.tobytes()).hexdigest(),
            "revisit_sector_count": len(tail_sectors),
        },
        "visual_retrieval_per_revisit_sector": observed,
        "overall_navigation_decision": "UNKNOWN",
        "why_navigation_unknown": (
            "No independently measured heading ground truth, gyroscope drift bound, "
            "repeated full revolutions, or multi-sector relocalization evidence; "
            "a visual match is at most a conventional candidate."
        ),
        "verification_boundary": "Original-sensor replay and parser cross-check, not flight or heading verification",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bag", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    report = replay_bag(options.bag, options.sha256)
    body = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if options.output:
        options.output.write_text(body)
    print(body)


if __name__ == "__main__":
    main()
