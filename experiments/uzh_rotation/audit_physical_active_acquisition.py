#!/usr/bin/env python3
"""Independent exact audit of finite active camera acquisition traces.

Does NOT call the planner or its filtering functions. Every advertised
acquisition is replayed from the original synthetic source; all never-requested
frames are inaccessible in the policy trace. Scope is finite synthetic only.
"""
import argparse
import itertools
import json
from pathlib import Path

HYPOTHESES = (0, 16, 32, 48)
MAP_BINS = 64

def pairs(candidates):
    return [(a, b) for i, a in enumerate(candidates) for b in candidates[i+1:]]

def signature_filter(reference, current, step, observed, budget):
    return [h for h in current
            if (reference[(h + step) % MAP_BINS] ^ observed).bit_count() <= budget]

def covered_pairs(reference, current, steps, budget):
    return {
        (a, b) for a, b in pairs(current)
        if any(
            (reference[(a + step) % MAP_BINS] ^
             reference[(b + step) % MAP_BINS]).bit_count() > 2 * budget
            for step in steps
        )
    }

def exact_minimum_basis_size(reference, current, start, horizon, budget):
    """Independent exhaustive subset oracle for <= four initial candidates.

    Distinct from compiler's dynamic-programming pair-coverage implementation.
    No partial qualification when the bounded search horizon is inadequate.
    """
    allpairs = set(pairs(current))
    if not allpairs:
        return 0
    available = list(range(start, horizon + 1))
    if covered_pairs(reference, current, available, budget) != allpairs:
        return None
    # At most one witness for each candidate pair can be necessary.
    bound = min(len(allpairs), len(available))
    for size in range(1, bound + 1):
        for steps in itertools.combinations(available, size):
            if covered_pairs(reference, current, steps, budget) == allpairs:
                return size
    raise AssertionError("independent finite cover should exist")

def audit_trial(t):
    reference = t["firstturn_reference"]
    original = t["source_columns_grader_only"]
    truth = t["true_bin_grader_only"]
    horizon = t["horizon"]
    budget = t["assumed_total_hamming_budget"]
    if (len(reference) != MAP_BINS or len(original) != horizon + 1 or
        tuple(t["initial_hypotheses"]) != HYPOTHESES or
        not 0 <= truth < MAP_BINS or budget != 2):
        raise ValueError("invalid finite trial boundary")
    if truth not in t["initial_hypotheses"]:
        raise ValueError("true heading not in declared prior candidate set")
    seen = set()
    candidates = t["initial_hypotheses"][:]
    previous = 0
    for request in t["active"]["requests"]:
        step = request["step"]
        if not previous < step <= horizon or step in seen:
            raise ValueError("noncausal or duplicate camera request")
        if request["before"] != candidates:
            raise ValueError("active policy claimed a false prior")
        planned = request["planned_basis"]
        if (not planned or planned[0] != step or
            any(s < step or s > horizon for s in planned) or
            planned != sorted(set(planned))):
            raise ValueError("planned witness basis invalid")
        full = set(pairs(candidates))
        if covered_pairs(reference, candidates, planned, budget) != full:
            raise ValueError("requested witness set is not separating")
        if len(planned) != exact_minimum_basis_size(
                reference, candidates, previous + 1, horizon, budget):
            raise ValueError("planned witness basis is not exactly minimum")
        observed = original[step]
        if request["observed_column"] != observed:
            raise ValueError("camera observation was forged or not acquired")
        if observed is not None:
            candidates = signature_filter(reference, candidates, step,
                                          observed, budget)
        if request["after"] != candidates:
            raise ValueError("unobserved or unjustified candidate elimination")
        seen.add(step)
        previous = step
    active = t["active"]
    if active["sample_attempts"] != len(seen) or active["candidates"] != candidates:
        raise ValueError("active sampling or candidate count manipulated")
    if active["status"] == "MODEL_UNIQUE":
        if len(candidates) != 1 or active["accepted_bin"] != candidates[0]:
            raise ValueError("invalid unique correction")
        if candidates[0] != truth:
            raise ValueError("false correction relative to hidden synthetic truth")
        if active["resolution_step"] != previous:
            raise ValueError("incorrect active decision timestamp")
    elif active["status"] == "UNKNOWN_OBSTRUCTION":
        if len(candidates) <= 1 or active["accepted_bin"] is not None:
            raise ValueError("false UNKNOWN disposition")
        if exact_minimum_basis_size(reference, candidates, previous + 1,
                                    horizon, budget) is not None:
            raise ValueError("false obstruction: separating continuation remains")
    elif active["status"] == "CONFLICT":
        if candidates or active["accepted_bin"] is not None:
            raise ValueError("invalid conflict result")
    else:
        raise ValueError("unsupported active status")

    baseline = t["continuous"]
    c = t["initial_hypotheses"][:]
    for index, rec in enumerate(baseline["readings"], 1):
        if rec["step"] != index or rec["observed_column"] != original[index]:
            raise ValueError("conventional sensor access differs from original source")
        if original[index] is not None:
            c = signature_filter(reference, c, index, original[index], budget)
        if rec["after"] != c:
            raise ValueError("conventional baseline processed wrong candidates")
    if (baseline["sample_attempts"] != len(baseline["readings"]) or
        baseline["candidates"] != c or
        baseline["accepted_bin"] != (c[0] if len(c) == 1 else None)):
        raise ValueError("baseline final trace manipulated")
    if len(c) == 1 and c[0] != truth:
        raise ValueError("conventional tracker false correction")
    if baseline["status"] == "MODEL_UNIQUE":
        if len(c) != 1 or baseline["resolution_step"] != len(baseline["readings"]):
            raise ValueError("baseline accepted without unique evidence")
    elif baseline["status"].startswith("UNKNOWN"):
        if len(c) <= 1 or len(baseline["readings"]) != horizon:
            raise ValueError("baseline unknown without exhausting horizon")
    elif baseline["status"] == "CONFLICT":
        if c:
            raise ValueError("baseline spurious conflict")
    else:
        raise ValueError("unsupported baseline state")
    if active["status"] == "MODEL_UNIQUE" and baseline["status"] != "MODEL_UNIQUE":
        raise ValueError("continuous equal-information tracker lost an available witness")
    if (active["status"] == "MODEL_UNIQUE" and
        baseline["resolution_step"] > active["resolution_step"]):
        raise ValueError("continuous tracker failed to identify by active resolution")
    return {"active_unique": int(active["status"] == "MODEL_UNIQUE"),
            "continuous_unique": int(baseline["status"] == "MODEL_UNIQUE"),
            "active_unknown": int(active["status"].startswith("UNKNOWN")),
            "continuous_unknown": int(baseline["status"].startswith("UNKNOWN")),
            "active_attempts": len(seen),
            "continuous_attempts": len(baseline["readings"]),
            "active_witness_acquisitions": sum(
                q["observed_column"] is not None for q in active["requests"])}

def audit_experiment(result):
    if (result.get("physical_observations") != 0 or
        result.get("hardware_acquisitions") != 0 or
        result.get("observation_requests_physically_executed") is not False or
        result.get("no_physical_heading_authority") is not True):
        raise ValueError("model claims unsupported physical demonstration")
    checked = 0
    for case in result["cases"]:
        stats = [audit_trial(t) for t in case["retained_trials_for_independent_audit"]]
        checked += len(stats)
        for key in ("active_unique", "continuous_unique", "active_unknown",
                    "continuous_unknown", "active_attempts",
                    "continuous_attempts", "active_witness_acquisitions"):
            if sum(row[key] for row in stats) != case[key]:
                raise ValueError("synthetic aggregate mismatch: " + case["case"] + "/" + key)
        if case["trials"] != len(stats):
            raise ValueError("trial count forged")
        if case["active_false_unique"] or case["continuous_false_unique"]:
            raise ValueError("incorrect heading inference promoted")
    return {
        "scope": "INDEPENDENT_EXHAUSTIVE_FINITE_TRACE_AUDIT_ONLY",
        "status": "WARRANTED_WITHIN_FROZEN_SYNTHETIC_GRAMMAR",
        "trial_traces_replayed": checked,
        "physical_validation": "UNKNOWN",
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("report_json")
    p.add_argument("--output", required=True)
    a = p.parse_args()
    result = audit_experiment(json.loads(Path(a.report_json).read_text()))
    Path(a.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__":
    main()
