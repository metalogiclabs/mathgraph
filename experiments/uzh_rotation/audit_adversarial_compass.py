#!/usr/bin/env python3
"""Independent event/metric replay of adversarial-compass JSON traces.

This does NOT import the estimator or its grader. It replays each accepted
correction, re-computes target risk and circular heading errors from recorded
truth, and rejects inconsistent summaries. It cannot validate scene physics.
"""

import argparse
import json
from pathlib import Path

import numpy as np


def audit_run(result: dict) -> int:
    assert result["evidence_class"] == "SYNTHETIC_CONTROLLED"
    raw = result["audit_trace"]
    truth = np.asarray(raw["truth"], dtype=float)
    observed = np.asarray(raw["observed"], dtype=bool)
    gyro = np.asarray(raw["gyro_deltas"], dtype=float)
    n = len(truth)
    end = int(result["training_end"])
    assert n == result["samples"] == len(observed) == len(gyro)
    assert 0 < end < n
    assert 0 <= result["map_coverage"] <= 1
    assert set(result["methods"]) == {"gyro_only", "matched_filter", "robust", "evidence_aware"}

    gaps = []
    start = None
    for i in range(end, n + 1):
        missing = i < n and not observed[i]
        if missing and start is None:
            start = i
        if not missing and start is not None:
            gaps.append((start, i))
            start = None
    blackout = max(gaps, key=lambda v: v[1] - v[0]) if gaps else None
    assert (tuple(result["blackout"]) if result["blackout"] else None) == blackout

    for method, metrics in result["methods"].items():
        trace = raw["methods"][method]
        heading = np.asarray(trace["heading"], dtype=float)
        authority = np.asarray(trace["authority"], dtype=bool)
        events = trace["events"]
        assert len(heading) == len(authority) == n
        assert np.isfinite(heading).all()
        assert np.isfinite(truth).all()
        assert not np.any(authority[:end])
        assert not np.any(authority[~observed])
        assert method != "gyro_only" or not events
        by_index = {int(e["index"]): e for e in events}
        assert len(by_index) == len(events)  # no duplicate acceptances

        last_event = -100000
        wrong = harmful = 0
        for i in range(n):
            expected_before = (heading[i - 1] if i else 0.0) + gyro[i]
            if i in by_index:
                event = by_index[i]
                assert i >= end and observed[i]
                assert abs(event["before"] - expected_before) < 1e-8
                assert abs(event["after"] - heading[i]) < 1e-8
                target_error = abs((event["target"] - truth[i] + np.pi) % (2*np.pi) - np.pi)
                before_error = abs((event["before"] - truth[i] + np.pi) % (2*np.pi) - np.pi)
                after_error = abs((event["after"] - truth[i] + np.pi) % (2*np.pi) - np.pi)
                wrong += target_error > np.deg2rad(10)
                harmful += after_error > before_error + np.deg2rad(5)
                last_event = i
            else:
                assert abs(heading[i] - expected_before) < 1e-8
            if authority[i]:
                assert i - last_event <= 90

        err = (heading[end:] - truth[end:] + np.pi) % (2*np.pi) - np.pi
        unwrapped = heading[end:] - truth[end:]
        recomputed = {
            "heading_rmse_deg": float(np.sqrt(np.mean(err**2)) * 180 / np.pi),
            "max_heading_error_deg": float(np.max(np.abs(err)) * 180 / np.pi),
            "unwrapped_rmse_deg": float(np.sqrt(np.mean(unwrapped**2)) * 180 / np.pi),
            "heading_available_fraction": float(np.mean(authority[end:])),
        }
        for key, value in recomputed.items():
            assert abs(metrics[key] - value) < 1e-8, (method, key, metrics[key], value)
        assert metrics["accepted_corrections"] == len(events)
        assert metrics["incorrect_accepted_corrections"] == int(wrong)
        assert metrics["harmful_accepted_corrections"] == int(harmful)
        recovery = None
        if blackout:
            for i in range(blackout[1], n - 29):
                err30 = (heading[i:i+30] - truth[i:i+30] + np.pi) % (2*np.pi) - np.pi
                if authority[i] and np.all(np.abs(err30) <= np.deg2rad(5)):
                    recovery = i - blackout[1]
                    break
        assert metrics["recovery_samples"] == recovery
    return len(result["methods"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path, nargs="+")
    args = parser.parse_args()
    for path in args.results:
        result = json.loads(path.read_text())
        num = audit_run(result)
        print(f"AUDIT PASS {path.name}: {num} independent method replays")


if __name__ == "__main__":
    main()
