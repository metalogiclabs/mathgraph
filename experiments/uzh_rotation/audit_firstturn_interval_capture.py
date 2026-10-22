#!/usr/bin/env python3
"""External finite audit of bounded first-turn camera/gyro source assignment.

This is a synthetic sensor-envelope experiment. The first-turn camera sequence
and all alleged timing bounds are generated before any future heading is used.
Both navigation consumers receive EXACTLY the same frozen reference map.
"""

import argparse
import ctypes
import json
from pathlib import Path
import random
import subprocess
import tempfile

from audit_finite_partial_map import Map, Plan, follow
from finite_witness_jitter import HYPOTHESES, generate_jitter_trial


ROOT = Path(__file__).parent
CONDITIONS = {
    "honest_r3_1x": {"density": 1, "radius": 3, "lie": False},
    "honest_r3_2x": {"density": 2, "radius": 3, "lie": False},
    "honest_r3_4x": {"density": 4, "radius": 3, "lie": False},
    "honest_r7_4x": {"density": 4, "radius": 7, "lie": False},
    "honest_r8_4x": {"density": 4, "radius": 8, "lie": False},
    "lied_r3_4x": {"density": 4, "radius": 3, "lie": True},
}


def load_gate(path):
    subprocess.run([
        "gcc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-O2",
        "-fPIC", "-shared", str(ROOT / "firstturn_interval_capture.c"),
        str(ROOT / "finite_partial_map.c"),
        str(ROOT / "finite_jitter_embedded.c"), "-o", str(path),
    ], check=True, capture_output=True, text=True)
    native = ctypes.CDLL(str(path))
    native.mg_map_init.argtypes = [ctypes.POINTER(Map)]
    native.mg_map_freeze.argtypes = [ctypes.POINTER(Map)]
    native.mg_map_capture.argtypes = [ctypes.POINTER(Map),
                                      ctypes.c_uint8, ctypes.c_uint16]
    native.mg_map_capture.restype = ctypes.c_int
    native.mg_firstturn_capture_interval.argtypes = [ctypes.POINTER(Map),
        ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint16]
    native.mg_firstturn_capture_interval.restype = ctypes.c_int
    # Same C functions and ctypes signatures as the frozen v5 grader.
    for name in ("mg_sparse_plan", "mg_sparse_next_probe"):
        func = getattr(native, name)
        func.argtypes = [ctypes.POINTER(Map), ctypes.c_uint8, ctypes.c_uint8,
                         ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8,
                         ctypes.POINTER(Plan)]
        func.restype = ctypes.c_int
    native.mg_sparse_filter.argtypes = [ctypes.POINTER(Map), ctypes.c_uint8,
        ctypes.c_uint8, ctypes.c_uint16, ctypes.c_uint8, ctypes.c_uint8]
    native.mg_sparse_filter.restype = ctypes.c_uint8
    return native


def generate_stream(physical_source, seed, condition):
    """Rows: (true_camera_phase, gyro_reported_phase, noisy_column).

    Truth is available only to the external grader and synthetic generator.
    There is deliberately no future heading input to this function.
    """
    params = CONDITIONS[condition]
    rng = random.Random(211003 * seed + sum(map(ord, condition)) * 71)
    rows = []
    for bin_idx in range(64):
        phases = sorted(rng.randrange(16) for _ in range(params["density"]))
        for local_phase in phases:
            physical_phase = 16 * bin_idx + local_phase
            if params["lie"]:
                deviation = rng.choice((-16, 16)) + rng.randrange(-3, 4)
            else:
                deviation = rng.randrange(-params["radius"], params["radius"] + 1)
            gyro_phase = (physical_phase + deviation) % 1024
            column = physical_source[bin_idx] ^ (1 << rng.randrange(16))
            rows.append((physical_phase, gyro_phase, column))
    return tuple(rows)


def build_maps(native, stream, declared_radius):
    """Feed only observed gyro phase and camera column into map writers."""
    gated, nearest = Map(), Map()
    native.mg_map_init(ctypes.byref(gated))
    native.mg_map_init(ctypes.byref(nearest))
    diagnostics = {"captured": 0, "confirm": 0, "quarantined": 0,
                   "deferred": 0, "nearest_quarantined": 0}
    for _, estimate, column in stream:
        result = native.mg_firstturn_capture_interval(
            ctypes.byref(gated), estimate, declared_radius, column)
        if result not in (0, 1, 2, -2):
            raise AssertionError(("gate invalid", estimate, result))
        diagnostics[{0:"captured",1:"confirm",2:"deferred",-2:"quarantined"}[result]] += 1
        naive = native.mg_map_capture(ctypes.byref(nearest),
                                      estimate // 16, column)
        if naive == -2: diagnostics["nearest_quarantined"] += 1
        elif naive not in (0, 1): raise AssertionError(("nearest invalid", naive))
    if native.mg_map_freeze(ctypes.byref(gated)) != 0:
        raise AssertionError("unable to freeze bounded map")
    if native.mg_map_freeze(ctypes.byref(nearest)) != 0:
        raise AssertionError("unable to freeze nearest-bin map")
    return gated, nearest, diagnostics


def validity(physical_source, stream, declared_radius, record):
    source_bound = all(min((est - actual) % 1024,
                           (actual - est) % 1024) <= declared_radius
                       for actual, est, _ in stream)
    map_fidelity = all(
        (record.columns[i] ^ physical_source[i]).bit_count() <= 1
        for i in range(64) if record.seen[i // 8] & (1 << (i % 8))
    )
    return source_bound, map_fidelity


def protected_failure(policy, label):
    """Only consumers of the source-bound map carry the safety obligation.

    A nearest-bin comparator intentionally rejects that source boundary. Its
    false correction is a NEGATIVE CONTROL, not a counterexample to a gate it
    never used. Preserve it in the per-trial trace and comparator totals.
    """
    return policy in ("active", "continuous") and label in ("false", "conflict")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    totals = {name: {"trials": 0, "bound_kept": 0, "map_fidelity": 0,
        "gated_coverage": 0, "nearest_coverage": 0, "gated_deferred": 0,
        "active_correct": 0, "active_false": 0, "active_unknown": 0,
        "active_conflict": 0, "continuous_correct": 0, "continuous_false": 0,
        "continuous_unknown": 0, "continuous_conflict": 0,
        "nearest_continuous_correct": 0, "nearest_continuous_false": 0,
        "nearest_continuous_unknown": 0, "nearest_continuous_conflict": 0,
        "active_reads": 0, "continuous_reads": 0,
        "nearest_continuous_reads": 0} for name in CONDITIONS}
    violations = []
    with tempfile.TemporaryDirectory(prefix="mathgraph-firstturn-safe-") as td:
        native = load_gate(Path(td) / "libgate.so")
        for seed in args.seeds:
            base = generate_jitter_trial(seed, 0, "wide")
            for condition, parameters in CONDITIONS.items():
                stream = generate_stream(base.physical_source, seed, condition)
                bounded, naive, stats = build_maps(native, stream, parameters["radius"])
                src_ok, fidelity = validity(base.physical_source, stream,
                                            parameters["radius"], bounded)
                if not parameters["lie"] and (not src_ok or not fidelity):
                    violations.append((seed, condition, "honest map source violation"))
                (args.out / f"source_{seed}_{condition}.json").write_text(
                    json.dumps({"seed": seed, "condition": condition,
                        "boundary": "SYNTHETIC_DECLARED_GYRO_PHASE_INTERVAL",
                        "source_physical_grader_only": base.physical_source,
                        "first_turn_rows_physical_phase_grader_only": stream,
                        "declared_radius": parameters["radius"],
                        "source_bound_holds_grader_only": src_ok,
                        "frozen_map_has_source_fidelity_grader_only": fidelity,
                        "count_gated": int(bounded.count),
                        "count_nearest": int(naive.count),
                        "diagnostics": stats}, indent=2) + "\n")
                for heading in HYPOTHESES:
                    future = generate_jitter_trial(seed, heading, "wide")
                    if future.physical_source != base.physical_source:
                        raise AssertionError("future heading changed source")
                    outcomes = {"active": follow(native, bounded, future.columns, "active"),
                        "continuous": follow(native, bounded, future.columns, "continuous"),
                        "nearest_continuous": follow(native, naive,
                                                      future.columns, "continuous")}
                    row = totals[condition]
                    row["trials"] += 1
                    row["bound_kept"] += int(src_ok)
                    row["map_fidelity"] += int(fidelity)
                    row["gated_coverage"] += int(bounded.count)
                    row["nearest_coverage"] += int(naive.count)
                    row["gated_deferred"] += stats["deferred"]
                    for policy, result in outcomes.items():
                        status = result["status"]
                        if status == "AUTHORIZED":
                            label = "correct" if result["accepted_bin"] == heading else "false"
                        else:
                            label = "conflict" if status == "CONFLICT" else "unknown"
                        row[f"{policy}_{label}"] += 1
                        row[f"{policy}_reads"] += len(result["reads"])
                        if not parameters["lie"] and protected_failure(policy, label):
                            violations.append((seed, heading, condition, policy,
                                               "honest source false correction", result))
                    (args.out / f"heading_{seed}_{heading}_{condition}.json").write_text(
                        json.dumps({"seed": seed, "heading_truth_grader_only": heading,
                            "condition": condition, "map_fidelity_grader_only": fidelity,
                            "source_bound_grader_only": src_ok, "outcomes": outcomes},
                            indent=2) + "\n")
    result = {"seeds": args.seeds, "conditions": totals, "failures": violations,
        "scope": ["Development or separately frozen synthetic seeds only",
                  "Source angular error bound externally declared, not calibrated",
                  "Both active and conventional continuous use same gated map",
                  "Lying source bound is an intentional negative control",
                  "Correct heading is relative to generated first-turn physical frame",
                  "No aircraft hardware or real line-camera validation"]}
    (args.out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print("FIRSTTURN_BOUND_SUMMARY", json.dumps(totals))
    print("FIRSTTURN_BOUND_VIOLATIONS", len(violations))
    if violations:
        raise SystemExit("HONEST_DECLARED_SOURCE_BOUND_VIOLATION")


if __name__ == "__main__":
    main()
