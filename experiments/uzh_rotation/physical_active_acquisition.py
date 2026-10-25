#!/usr/bin/env python3
"""Finite-model active camera acquisition against equal-information continuous sensing.

An acquisition callback is the *only* way the policy obtains later columns.
Planning uses only the frozen first-turn map, gyro-consistent candidate bins,
and an assumed total Hamming error budget. This is not hardware acquisition,
not a physical clock-error certificate and not authorization to fly.
"""
import argparse
import json

from finite_witness_compass import (
    HORIZON, HYPOTHESES, NOISE_BUDGET,
    compile_minimum_witnesses, filter_hypotheses, generate_finite_trial,
)

KINDS = (
    ("breakable_clean", "breakable", ()),
    ("breakable_occlude_7", "breakable", (7,)),
    ("breakable_occlude_13", "breakable", (13,)),
    ("breakable_occlude_7_13", "breakable", (7, 13)),
    ("unbreakable_clean", "unbreakable", ()),
)

def active_policy(reference, initial_candidates, horizon, acquire,
                  noise_budget=NOISE_BUDGET):
    """Request one witness at a time and only then acquire its observation."""
    remaining = tuple(sorted(set(initial_candidates)))
    cursor = 1
    records = []
    plan_calls = 0
    while len(remaining) > 1 and cursor <= horizon:
        plan = compile_minimum_witnesses(
            reference, remaining, tuple(range(cursor, horizon + 1)), noise_budget
        )
        plan_calls += 1
        if plan.status != "SEPARATING_SET":
            return {"status": "UNKNOWN_OBSTRUCTION",
                    "candidates": list(remaining), "accepted_bin": None,
                    "requests": records, "sample_attempts": len(records),
                    "plan_calls": plan_calls, "resolution_step": None}
        step = plan.steps[0]
        if not cursor <= step <= horizon:
            raise AssertionError("compiler requested past/nonpermitted observation")
        # Request is fully chosen BEFORE accessing the sensor.
        request = {"step": step, "before": list(remaining),
                   "minimum_basis_size": plan.cost,
                   "planned_basis": list(plan.steps),
                   "witness_pair_coverage": plan.pair_coverage}
        observed = acquire(step)
        request["observed_column"] = observed
        if observed is not None:
            remaining = filter_hypotheses(reference, remaining, step,
                                           observed, noise_budget)
        request["after"] = list(remaining)
        records.append(request)
        if not remaining:
            return {"status": "CONFLICT", "candidates": [],
                    "accepted_bin": None, "requests": records,
                    "sample_attempts": len(records), "plan_calls": plan_calls,
                    "resolution_step": step}
        cursor = step + 1
    return {"status": "MODEL_UNIQUE" if len(remaining) == 1 else "UNKNOWN_OBSTRUCTION",
            "candidates": list(remaining),
            "accepted_bin": remaining[0] if len(remaining) == 1 else None,
            "requests": records, "sample_attempts": len(records),
            "plan_calls": plan_calls,
            "resolution_step": records[-1]["step"] if len(remaining) == 1 and records else None}

def continuous_policy(reference, initial_candidates, horizon, acquire,
                      noise_budget=NOISE_BUDGET):
    """Equally informed set-valued tracker, acquiring EVERY available time slot."""
    remaining = tuple(sorted(set(initial_candidates)))
    records = []
    for step in range(1, horizon + 1):
        observed = acquire(step)
        if observed is not None:
            remaining = filter_hypotheses(reference, remaining, step,
                                           observed, noise_budget)
        records.append({"step": step, "observed_column": observed,
                        "after": list(remaining)})
        if not remaining or len(remaining) == 1:
            break
    return {"status": "CONFLICT" if not remaining else
            "MODEL_UNIQUE" if len(remaining) == 1 else "UNKNOWN_AMBIGUOUS",
            "accepted_bin": remaining[0] if len(remaining) == 1 else None,
            "candidates": list(remaining), "readings": records,
            "sample_attempts": len(records),
            "resolution_step": records[-1]["step"] if len(remaining) == 1 and records else None}

def run_trial(seed, true_bin, kind, occluded, horizon=HORIZON):
    trial = generate_finite_trial(seed, true_bin=true_bin, kind=kind,
                                  occluded_steps=occluded, horizon=horizon)
    # The policy sees only these immutable first-turn references and a closure
    # that yields one column when the policy actually requests that step.
    def probe(step):
        if not 1 <= step <= horizon:
            raise ValueError("sensor request outside future trial horizon")
        return trial.columns[step]
    active = active_policy(trial.reference, HYPOTHESES, horizon, probe)
    continuous = continuous_policy(trial.reference, HYPOTHESES, horizon, probe)
    for outcome in (active, continuous):
        outcome["agrees_with_hidden_truth_if_unique"] = (
            outcome["accepted_bin"] == trial.true_bin
            if outcome["status"] == "MODEL_UNIQUE" else None
        )
    return {
        "seed": seed, "kind": kind, "true_bin_grader_only": trial.true_bin,
        "occluded_steps": list(occluded), "horizon": horizon,
        "firstturn_reference": list(trial.reference),
        "source_columns_grader_only": list(trial.columns),
        "initial_hypotheses": list(HYPOTHESES),
        "assumed_total_hamming_budget": NOISE_BUDGET,
        "active": active, "continuous": continuous,
    }

def experiment(seeds=32):
    if not 1 <= seeds <= 512:
        raise ValueError("unbounded seed census")
    cases = []
    for name, kind, occluded in KINDS:
        trials = [
            run_trial(seed, true_bin, kind, occluded)
            for seed in range(seeds) for true_bin in HYPOTHESES
        ]
        n = len(trials)
        active = [t["active"] for t in trials]
        baseline = [t["continuous"] for t in trials]
        assert all(a["agrees_with_hidden_truth_if_unique"] is not False
                   for a in active + baseline)
        cases.append({
            "case": name, "trials": n,
            "active_unique": sum(t["status"] == "MODEL_UNIQUE" for t in active),
            "continuous_unique": sum(t["status"] == "MODEL_UNIQUE" for t in baseline),
            "active_unknown": sum(t["status"].startswith("UNKNOWN") for t in active),
            "continuous_unknown": sum(t["status"].startswith("UNKNOWN") for t in baseline),
            "active_false_unique": sum(t["agrees_with_hidden_truth_if_unique"] is False for t in active),
            "continuous_false_unique": sum(t["agrees_with_hidden_truth_if_unique"] is False for t in baseline),
            "active_attempts": sum(t["sample_attempts"] for t in active),
            "continuous_attempts": sum(t["sample_attempts"] for t in baseline),
            "active_witness_acquisitions": sum(
                r["observed_column"] is not None for t in active for r in t["requests"]),
            "active_resolution_step_total": sum(
                t["resolution_step"] for t in active if t["resolution_step"] is not None),
            "continuous_resolution_step_total": sum(
                t["resolution_step"] for t in baseline if t["resolution_step"] is not None),
            "retained_trials_for_independent_audit": trials,
        })
    return {
        "boundary": "SYNTHETIC_FINITE_16BIT_GYRO_CANDIDATES_ASSUMED_NOISE_2",
        "physical_observations": 0,
        "hardware_acquisitions": 0,
        "observation_requests_physically_executed": False,
        "no_physical_heading_authority": True,
        "continuous_baseline_sees_identical_frozen_map_and_noise_budget": True,
        "cases": cases,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=32)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = experiment(a.seeds)
    with open(a.output, "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    for c in result["cases"]:
        print(c["case"], "trials", c["trials"], "identified",
              c["active_unique"], c["continuous_unique"], "camera attempts",
              c["active_attempts"], c["continuous_attempts"])
    print("NO_PHYSICAL_SENSOR_ACQUISITION=TRUE")

if __name__ == "__main__":
    main()
