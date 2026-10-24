#!/usr/bin/env python3
"""Independent encoder-only offline scorer; never passes encoder to estimator.

Measures phase-relative errors without fitting an encoder offset on holdout.
The scorer cannot establish that the underlying encoder is a physical sensor.
"""
import bisect
import csv
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

def encoder_edges(path):
    with Path(path).open(newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames or not {"timestamp_ns", "unwrapped_count"}.issubset(r.fieldnames):
            raise ValueError("encoder columns missing")
        rows = [(int(x["timestamp_ns"]), int(x["unwrapped_count"])) for x in r]
    if len(rows) < 2 or any(a[0] >= b[0] or b[1] - a[1] != 1
                            for a, b in zip(rows, rows[1:])):
        raise ValueError("encoder source is not contiguous or monotone")
    return rows

def interp(rows, time):
    times = [r[0] for r in rows]
    i = bisect.bisect_right(times, time) - 1
    if i < 0 or i == len(rows) - 1:
        if time == times[-1]:
            return float(rows[-1][1])
        raise ValueError("estimator camera frame outside encoder time support")
    a, b = rows[i], rows[i + 1]
    return a[1] + (b[1] - a[1]) * (time - a[0]) / (b[0] - a[0])

def wrap(x):
    return (x + math.pi) % (2 * math.pi) - math.pi

def stats(values):
    if not values:
        raise ValueError("empty scoring class")
    z = sorted(abs(x) * 180 / math.pi for x in values)
    return {
        "circular_rmse_deg": math.sqrt(sum(x * x for x in z) / len(z)),
        "circular_median_abs_deg": statistics.median(z),
        "circular_p95_abs_deg": z[min(len(z)-1, math.ceil(.95*len(z))-1)],
        "samples": len(z)
    }

def score(output, encoder_path, pulses_per_revolution):
    if type(pulses_per_revolution) is not int or pulses_per_revolution <= 0:
        raise ValueError("invalid independently specified encoder resolution")
    if output.get("physical_navigation_authorized") is not False:
        raise ValueError("replay claims unsupported physical authority")
    if output.get("encoder_available_to_estimator") is not False:
        raise ValueError("estimator encoder-input admission invalid")
    edges = encoder_edges(encoder_path)
    start = output["firstturn_start_ns"]
    origin_count = interp(edges, start)
    if (edges[-1][1] - origin_count) < 5 * pulses_per_revolution:
        raise ValueError("fewer than five full encoder turns after first map origin")
    events = output.get("events")
    if not isinstance(events, list) or len(events) < 5:
        raise ValueError("insufficient held-out predictions")
    names = ("gyro_only_rad", "mathgraph_estimate_rad", "conventional_nearest_rad")
    traces = {key: [] for key in names}
    groups = {}
    unknown = 0
    requests = 0
    prev_t = start
    for e in events:
        t = e["timestamp_ns"]
        if type(t) is not int or t <= prev_t or t <= output["firstturn_end_ns"]:
            raise ValueError("noncausal or non-monotone prediction")
        prev_t = t
        rel_counts = interp(edges, t) - origin_count
        truth = 2 * math.pi * rel_counts / pulses_per_revolution
        turn = int(math.floor(rel_counts / pulses_per_revolution))
        if e.get("navigation_correction_authorized") is not False:
            raise ValueError("unsupported correction authorization")
        state = e.get("model_state")
        if state not in ("MODEL_SEPARATED", "UNKNOWN_NO_OBSERVATION",
                         "UNKNOWN_CONFLICT", "UNKNOWN_AMBIGUOUS"):
            raise ValueError("unsupported decision state")
        if state != "MODEL_SEPARATED":
            unknown += 1
        if e.get("requested_observation") is not None:
            requests += 1
        if (state == "MODEL_SEPARATED") != (len(e.get("compatible_bins", [])) == 1):
            raise ValueError("decision inconsistent with retained heading set")
        for name in names:
            value = e[name]
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("invalid numerical heading")
            err = wrap(value - truth)
            traces[name].append(err)
            groups.setdefault(turn, {}).setdefault(name, []).append(err)
    return {
        "state": "OFFLINE_MODEL_SCORING_ONLY_NO_PHYSICAL_PROVENANCE",
        "encoder_sha256": hashlib.sha256(Path(encoder_path).read_bytes()).hexdigest(),
        "encoder_complete_turns_from_origin": (edges[-1][1]-origin_count)//pulses_per_revolution,
        "heldout_frames": len(events),
        "unknown_fraction": unknown / len(events),
        "separating_observation_requests_not_automatically_acquired": requests,
        "overall": {key: stats(values) for key, values in traces.items()},
        "per_encoder_turn": {
            str(turn): {name: stats(values) for name, values in vals.items()}
            for turn, vals in sorted(groups.items())
        },
        "fairness": "Both estimators use identical camera, gyro, map and declared uncertainty; only this independent scorer reads encoder. No training, tuning or offset fitting on encoder holdout.",
        "physical_heading_correction_warranted": False
    }

def main():
    if len(sys.argv) != 5:
        raise SystemExit("usage: scorer estimator_output.json encoder.csv pulses_per_rev output.json")
    result = score(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2], int(sys.argv[3]))
    Path(sys.argv[4]).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k != "per_encoder_turn"}, indent=2))

if __name__ == "__main__":
    main()
