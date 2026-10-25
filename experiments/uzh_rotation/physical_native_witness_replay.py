#!/usr/bin/env python3
"""Bridge a frozen finite sensor model to the EXISTING MathGraph native C99 map.

Reuses finite_partial_map.c, finite_jitter_embedded.c, and their qualified
MGReferenceMap / MGPlan ABI. The bridge is a source-closed synthetic
differential experiment. It does NOT link into ArduPilot, schedule a physical
camera, or authorize drone navigation.
"""
import argparse
import ctypes
import json
from pathlib import Path
import tempfile

from audit_finite_partial_map import build_map, load_library, Plan
from finite_witness_compass import HYPOTHESES, generate_finite_trial
from physical_active_acquisition import active_policy, KINDS

def mask_to_bins(mask):
    return [16 * i for i in range(4) if mask & (1 << i)]

def native_follow(native, reference, columns, *, jitter=0, known=None,
                  noise_budget=2, potential=False):
    if not 0 <= jitter <= 3:
        raise ValueError("outside declared C99 timing-jitter grammar")
    horizon = len(columns) - 1
    if not 1 <= horizon <= 32:
        raise ValueError("invalid finite observation horizon")
    m = build_map(native, reference, range(64) if known is None else known)
    mask = 15
    cursor = 1
    events = []
    while mask.bit_count() > 1 and cursor <= horizon:
        plan = Plan()
        function = native.mg_sparse_next_probe if potential else native.mg_sparse_plan
        rc = function(ctypes.byref(m), mask, cursor, horizon,
                      noise_budget, jitter, ctypes.byref(plan))
        if rc != 0:
            raise AssertionError("valid frozen-map planner inputs rejected")
        if plan.status not in ((1, 5) if potential else (1,)):
            return {"status": "UNKNOWN_OBSTRUCTION", "accepted_bin": None,
                    "remaining": mask_to_bins(mask), "events": events,
                    "attempts": len(events), "resolution_step": None,
                    "terminal_plan_status": int(plan.status)}
        step = int(plan.first_step)
        if not cursor <= step <= horizon:
            raise AssertionError("native planner requested past observation")
        # Observation is retrieved only after a valid future step was requested.
        observed = columns[step]
        before = mask
        if observed is not None:
            mask = int(native.mg_sparse_filter(
                ctypes.byref(m), mask, step, observed, noise_budget, jitter))
        events.append({
            "step": step, "observed_column": observed, "before_mask": before,
            "after_mask": mask, "planner_status": int(plan.status),
            "minimum_basis_cost_if_guaranteed":
                int(plan.cost) if plan.status == 1 else None,
            "planned_steps_mask": int(plan.step_mask),
        })
        if mask == 0:
            return {"status": "CONFLICT", "accepted_bin": None,
                    "remaining": [], "events": events, "attempts": len(events),
                    "resolution_step": step, "terminal_plan_status": 0}
        if mask.bit_count() == 1:
            return {"status": "MODEL_UNIQUE",
                    "accepted_bin": 16 * (mask.bit_length() - 1),
                    "remaining": mask_to_bins(mask), "events": events,
                    "attempts": len(events), "resolution_step": step,
                    "terminal_plan_status": 1}
        cursor = step + 1
    return {"status": "UNKNOWN_OBSTRUCTION", "accepted_bin": None,
            "remaining": mask_to_bins(mask), "events": events,
            "attempts": len(events), "resolution_step": None,
            "terminal_plan_status": 3}

def experiment(seeds=32):
    if not 1 <= seeds <= 128:
        raise ValueError("unsupported finite experiment seed count")
    totals = []
    with tempfile.TemporaryDirectory() as tmp:
        native = load_library(Path(tmp) / "existing_mathgraph_map.so")
        for name, kind, occluded in KINDS:
            cases = []
            for seed in range(seeds):
                for true in HYPOTHESES:
                    t = generate_finite_trial(seed, true_bin=true, kind=kind,
                                              occluded_steps=occluded)
                    native0 = native_follow(native, t.reference, t.columns, jitter=0)
                    python0 = active_policy(
                        t.reference, HYPOTHESES, len(t.columns) - 1,
                        lambda step: t.columns[step])
                    if (native0["status"] != python0["status"] or
                        native0["remaining"] != python0["candidates"] or
                        native0["accepted_bin"] != python0["accepted_bin"] or
                        [x["step"] for x in native0["events"]] !=
                            [x["step"] for x in python0["requests"]]):
                        raise AssertionError("original C99 vs independent Python active policy differ")
                    if native0["status"] == "MODEL_UNIQUE" and native0["accepted_bin"] != true:
                        raise AssertionError("incorrect native bounded heading")
                    native1 = native_follow(native, t.reference, t.columns, jitter=1)
                    if native1["status"] == "MODEL_UNIQUE" and native1["accepted_bin"] != true:
                        raise AssertionError("unsafe native jitter-one heading")
                    cases.append((seed, true, native0, native1))
            totals.append({
                "condition": name, "trials": len(cases),
                "jitter_0_unique": sum(x[2]["status"]=="MODEL_UNIQUE" for x in cases),
                "jitter_1_unique": sum(x[3]["status"]=="MODEL_UNIQUE" for x in cases),
                "jitter_0_camera_attempts": sum(x[2]["attempts"] for x in cases),
                "jitter_1_camera_attempts": sum(x[3]["attempts"] for x in cases),
                "jitter_0_false_unique": 0, "jitter_1_false_unique": 0,
                "representative_traces": [
                    {"seed": x[0], "true_heading_grader_only": x[1],
                     "jitter_0": x[2], "jitter_1": x[3]} for x in cases[:2]
                ],
            })
    return {
        "source": "EXISTING_FINITE_PARTIAL_MAP_C99_NO_DUPLICATE_IMPLEMENTATION",
        "boundary": "FINITE_16BIT_ASSUMED_NOISE_AND_EXACT_PHASE_BIN",
        "native_vs_python_agreement_in_all_jitter0_trials": True,
        "jitter_1_is_an_assUMED_BOUND_NOT_A_MEASURED_CLOCK": True,
        "hardware_observation_acquisitions": 0,
        "physical_heading_authorized": False,
        "conditions": totals,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=32)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    result = experiment(args.seeds)
    Path(args.output).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    for x in result["conditions"]:
        print("NATIVE_WITNESS", x["condition"], "trials", x["trials"],
              "jitter_0_unique", x["jitter_0_unique"],
              "jitter_1_unique", x["jitter_1_unique"],
              "jitter_0_reads", x["jitter_0_camera_attempts"])
    print("NO_HARDWARE_NAVIGATION_AUTHORITY")

if __name__ == "__main__":
    main()
