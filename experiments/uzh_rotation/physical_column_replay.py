#!/usr/bin/env python3
"""Causal, encoder-blind 16-bit column replay with a first-turn frozen map.

Uses the same 64 angular bins, 16-bit Hamming descriptors and bounded
candidate filtering as finite_witness_compass.py / DARK-GS. It is a
source-driven *model* experiment; a verified physical timing/gyro error bound,
drone-scale hardware and true multi-turn capture are NOT supplied here.

Run:
  python physical_column_replay.py --build-map camera.csv gyro.csv map.json
  python physical_column_replay.py camera.csv gyro.csv map.json
Second command emits estimator output JSON to stdout for Docker isolation.
"""
import bisect
import csv
import json
import math
import sys
from pathlib import Path

BINS = 64
BITS = 16
TWO_PI = math.tau
MAX_IMU_EXTRAPOLATION_NS = 20_000_000


def rows(path, required):
    with Path(path).open(newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or not set(required).issubset(reader.fieldnames):
            raise ValueError("source CSV missing required fields")
        result = list(reader)
    if len(result) < 2:
        raise ValueError("source has fewer than two records")
    times = [int(row["timestamp_ns"]) for row in result]
    if min(times) < 0 or any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError("source timestamps not strictly monotone")
    return result, times


class Gyro:
    def __init__(self, path):
        data, self.times = rows(path, ("timestamp_ns", "gyro_z_rad_s"))
        self.rates = [float(d["gyro_z_rad_s"]) for d in data]
        if not all(math.isfinite(w) for w in self.rates):
            raise ValueError("nonfinite gyro")
        self.cumulative = [0.0]
        for i in range(1, len(data)):
            dt = (self.times[i] - self.times[i - 1]) * 1e-9
            self.cumulative.append(self.cumulative[-1] +
                0.5 * dt * (self.rates[i - 1] + self.rates[i]))
        self.peak = max(abs(w) for w in self.rates)

    def phase(self, stamp):
        i = bisect.bisect_right(self.times, stamp) - 1
        if i < 0 or stamp - self.times[i] > MAX_IMU_EXTRAPOLATION_NS:
            raise ValueError("camera outside bounded causal gyro window")
        return self.cumulative[i] + self.rates[i] * (stamp - self.times[i]) * 1e-9


def camera(path):
    data, times = rows(path, ("timestamp_ns", "bits16", "usable"))
    columns = []
    for row, t in zip(data, times):
        bits, usable = int(row["bits16"]), int(row["usable"])
        if not 0 <= bits < (1 << BITS) or usable not in (0, 1):
            raise ValueError("invalid binary camera column")
        columns.append((t, bits if usable else None))
    return columns


def phase_bin(angle):
    return int(math.floor((angle % TWO_PI) * BINS / TWO_PI)) % BINS


def wrapped(angle):
    return (angle + math.pi) % TWO_PI - math.pi


def build_map(columns, gyro, *, timing_error_ns=0,
              gyro_rate_bound=0.012, firstturn_phase_bound=0.08,
              noise_budget=2):
    """Map only from first gyro-measured turn; no encoder or future images."""
    if any(x < 0 for x in (timing_error_ns, gyro_rate_bound,
                          firstturn_phase_bound, noise_budget)):
        raise ValueError("negative assumed uncertainty")
    origin = gyro.phase(columns[0][0])
    signature = [None] * BINS
    quarantined = set()
    end = None
    for stamp, bits in columns:
        relative = gyro.phase(stamp) - origin
        if relative >= TWO_PI:
            end = stamp
            break
        if relative < 0:
            raise ValueError("gyro phase reversed during first turn")
        if bits is None:
            continue
        cell = phase_bin(relative)
        if signature[cell] is None:
            signature[cell] = bits
        elif (signature[cell] ^ bits).bit_count() > noise_budget:
            quarantined.add(cell)
    if end is None:
        raise ValueError("no completed first gyro-integrated revolution")
    for cell in quarantined:
        signature[cell] = None
    if sum(b is not None for b in signature) < 16:
        raise ValueError("insufficient frozen firstturn map coverage")
    return {
        "model": "CAUSAL_FIRSTTURN_16BIT_64BIN_UNCERTIFIED_PHYSICAL",
        "firstturn_start_ns": columns[0][0],
        "firstturn_end_ns": end,
        "signatures": signature,
        "quarantined_bins": sorted(quarantined),
        "noise_budget": int(noise_budget),
        "timing_error_bound_ns": int(timing_error_ns),
        "gyro_rate_error_bound_rad_s": float(gyro_rate_bound),
        "firstturn_phase_error_bound_rad": float(firstturn_phase_bound),
        "physical_error_bounds_independently_certified": False,
        "encoder_used_in_map": False,
    }


def validate_map(m):
    if m.get("model") != "CAUSAL_FIRSTTURN_16BIT_64BIN_UNCERTIFIED_PHYSICAL":
        raise ValueError("wrong or unverifiable first-turn map")
    signature = m["signatures"]
    if len(signature) != BINS or any(
        x is not None and (type(x) is not int or not 0 <= x < 1 << BITS)
        for x in signature
    ):
        raise ValueError("invalid frozen descriptor map")
    if not (type(m["noise_budget"]) is int and 0 <= m["noise_budget"] <= 2):
        raise ValueError("invalid source noise assumption")
    if m.get("encoder_used_in_map") is not False:
        raise ValueError("encoder map contamination")
    for key in ("timing_error_bound_ns", "gyro_rate_error_bound_rad_s",
                "firstturn_phase_error_bound_rad"):
        value = m[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("invalid assumed uncertainty parameter")
    if type(m["firstturn_start_ns"]) is not int or type(m["firstturn_end_ns"]) is not int:
        raise ValueError("invalid firstturn times")
    if m["firstturn_end_ns"] <= m["firstturn_start_ns"]:
        raise ValueError("noncausal frozen map")
    # This adapter has no authenticated physical-source authority interface.
    if m.get("physical_error_bounds_independently_certified") is not False:
        raise ValueError("unsupported physical authority declaration")


def separation_request(signatures, candidates, budget):
    """Suggest a future angular step; does not look ahead at new observations."""
    if len(candidates) < 2:
        return None
    best = None
    for step in range(1, 17):
        compared = 0
        separated = 0
        for i, a in enumerate(candidates):
            for b in candidates[i + 1:]:
                x = signatures[(a + step) % BINS]
                y = signatures[(b + step) % BINS]
                if x is None or y is None:
                    continue
                compared += 1
                separated += int((x ^ y).bit_count() > 2 * budget)
        if compared and separated:
            key = (separated, -step)
            if best is None or key > best[0]:
                best = (key, step, separated, compared)
    return None if best is None else {
        "relative_bin_step": best[1], "separated_pairs": best[2],
        "compared_pairs": best[3], "status": "REQUEST_ONLY_NOT_ACQUIRED"
    }


def replay(columns, gyro, frozen):
    validate_map(frozen)
    if columns[0][0] != frozen["firstturn_start_ns"]:
        raise ValueError("different camera origin than frozen map")
    if columns[-1][0] <= frozen["firstturn_end_ns"]:
        raise ValueError("no post-firstturn camera observations")
    origin = gyro.phase(columns[0][0])
    signature = frozen["signatures"]
    radius0 = frozen["firstturn_phase_error_bound_rad"]
    bias = frozen["gyro_rate_error_bound_rad_s"]
    clock_ns = frozen["timing_error_bound_ns"]
    budget = frozen["noise_budget"]
    events = []
    for stamp, bits in columns:
        if stamp <= frozen["firstturn_end_ns"]:
            continue
        g = gyro.phase(stamp) - origin
        elapsed = (stamp - columns[0][0]) * 1e-9
        radius = radius0 + elapsed * bias + gyro.peak * clock_ns * 1e-9
        # Discretization cushion preserves any candidate bin intersecting bound.
        candidates = [i for i in range(BINS) if signature[i] is not None
                      and abs(wrapped((i + 0.5) * TWO_PI / BINS - g))
                      <= radius + math.pi / BINS]
        compatible = ([] if bits is None else [
            i for i in candidates if (signature[i] ^ bits).bit_count() <= budget
        ])
        baseline_bin = (min(candidates,
            key=lambda i: ((signature[i] ^ bits).bit_count(),
                abs(wrapped((i + 0.5) * TWO_PI / BINS - g))))
            if bits is not None and candidates else None)
        baseline = (g + wrapped((baseline_bin + 0.5) * TWO_PI / BINS - g)
                    if baseline_bin is not None else g)
        unique = len(compatible) == 1
        estimate = (g + wrapped((compatible[0] + 0.5) * TWO_PI / BINS - g)
                    if unique else g)
        events.append({
            "timestamp_ns": stamp, "gyro_only_rad": g,
            "mathgraph_estimate_rad": estimate,
            "conventional_nearest_rad": baseline,
            "model_state": ("MODEL_SEPARATED" if unique else
                "UNKNOWN_NO_OBSERVATION" if bits is None else
                "UNKNOWN_CONFLICT" if len(compatible) == 0 else
                "UNKNOWN_AMBIGUOUS"),
            "navigation_correction_authorized": False,
            "candidate_bins": candidates,
            "compatible_bins": compatible,
            "model_witness_bin": compatible[0] if unique else None,
            "requested_observation": (None if unique else
                separation_request(signature, compatible or candidates, budget)),
            "assumed_heading_error_radius_rad": radius,
        })
    return {
        "boundary": "MODEL_ONLY_UNCERTIFIED_PHYSICAL_ERROR_BOUNDS",
        "firstturn_start_ns": frozen["firstturn_start_ns"],
        "firstturn_end_ns": frozen["firstturn_end_ns"],
        "frozen_map_bin_count": sum(s is not None for s in signature),
        "encoder_available_to_estimator": False,
        "physical_navigation_authorized": False,
        "events": events,
    }


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--print-map":
        columns, gyro = camera(sys.argv[2]), Gyro(sys.argv[3])
        frozen = build_map(columns, gyro, gyro_rate_bound=0.03,
                           firstturn_phase_bound=0.08)
        print(json.dumps(frozen, sort_keys=True, allow_nan=False))
        return
    if len(sys.argv) == 5 and sys.argv[1] == "--build-map":
        columns, gyro = camera(sys.argv[2]), Gyro(sys.argv[3])
        Path(sys.argv[4]).write_text(json.dumps(build_map(columns, gyro),
                                      indent=2, sort_keys=True) + "\n")
        return
    if len(sys.argv) != 4:
        raise SystemExit("usage: estimator camera.csv gyro.csv frozen_map.json")
    columns, gyro = camera(sys.argv[1]), Gyro(sys.argv[2])
    result = replay(columns, gyro, json.loads(Path(sys.argv[3]).read_text()))
    print(json.dumps(result, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
