#!/usr/bin/env python3
"""Independent external grader for frozen C99 compass, not an aircraft loop.

The C planner gets only observed map columns, a finite candidate mask and past
measurements. Physical source, actual heading and camera slip go exclusively to
this external grader. Preserve every negative and UNKNOWN in JSON, even if a
holdout fails. Development self-test: --seeds 5 11 19 23.
"""

import argparse
import ctypes
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import tempfile

from finite_witness_jitter import (
    HYPOTHESES, generate_jitter_trial, run_jitter_acquired,
    run_jitter_continuous,
)


ROOT = Path(__file__).parent


class Plan(ctypes.Structure):
    _fields_ = [("step_mask", ctypes.c_uint32),
                ("pair_checks", ctypes.c_uint16),
                ("cost", ctypes.c_uint8),
                ("first_step", ctypes.c_uint8),
                ("status", ctypes.c_uint8)]


def load_c_library(path: Path):
    subprocess.run(["gcc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-O2",
                    "-fPIC", "-shared", str(ROOT / "finite_jitter_embedded.c"),
                    "-o", str(path)], check=True)
    library = ctypes.CDLL(str(path))
    library.mg_plan.argtypes = [ctypes.POINTER(ctypes.c_uint16),
        ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8,
        ctypes.c_uint8, ctypes.POINTER(Plan)]
    library.mg_plan.restype = ctypes.c_int
    library.mg_filter.argtypes = [ctypes.POINTER(ctypes.c_uint16),
        ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint16,
        ctypes.c_uint8, ctypes.c_uint8]
    library.mg_filter.restype = ctypes.c_uint8
    return library


def run_c(library, reference, columns):
    """Online: no truth, original scene, offsets or future captures in plan."""
    map_buffer = (ctypes.c_uint16 * 64)(*reference)
    support_mask = 15
    start = 1
    records = []
    pair_checks = 0
    attempted = []
    acquired = []
    status = "UNKNOWN_OBSTRUCTION"
    accepted_bin = None
    decision_step = None
    while start < len(columns):
        plan = Plan()
        if library.mg_plan(map_buffer, support_mask, start,
                           len(columns) - 1, 2, 1, ctypes.byref(plan)) != 0:
            raise AssertionError("Native planner rejected legal inputs")
        pair_checks += plan.pair_checks
        if plan.status != 1:
            records.append({"step": start, "plan_status": int(plan.status),
                            "action": "WITHHOLD", "pair_checks": int(plan.pair_checks)})
            break
        future = int(plan.first_step)
        if future < start or future >= len(columns):
            raise AssertionError("Planner returned invalid future observation")
        attempted.append(future)
        measurement = columns[future]
        entry = {"step": future, "planned_steps_mask": int(plan.step_mask),
                 "plan_cost": int(plan.cost), "pair_checks": int(plan.pair_checks),
                 "before_mask": int(support_mask)}
        if measurement is None:
            entry["action"] = "MISSING_REPLAN"
        else:
            acquired.append(future)
            support_mask = library.mg_filter(map_buffer, support_mask,
                                             future, measurement, 2, 1)
            entry.update({"action": "FILTER", "observation": measurement,
                          "after_mask": int(support_mask)})
            if support_mask == 0:
                status, decision_step = "CONFLICT", future
            elif support_mask.bit_count() == 1:
                status, decision_step = "AUTHORIZED", future
                accepted_bin = (support_mask.bit_length() - 1) * 16
        records.append(entry)
        if status != "UNKNOWN_OBSTRUCTION":
            break
        start = future + 1
    return {"status": status, "accepted_bin": accepted_bin,
            "candidate_bins": [16 * i for i in range(4) if support_mask & (1 << i)],
            "attempted_steps": attempted, "acquired_steps": acquired,
            "pair_checks": pair_checks, "decision_step": decision_step,
            "trace": records}


def external_grade(trial, c_outcome, reference=None, columns=None):
    """Inspect source identity and true yaw after C has finished deciding."""
    reference = trial.reference if reference is None else reference
    columns = trial.columns if columns is None else columns
    map_bound = all((a ^ b).bit_count() <= 1 for a, b in
                    zip(reference, trial.physical_source))
    camera_bound = all(value is None or (value ^ trial.physical_source[
        (trial.true_bin + step + trial.timing_offsets[step]) % 64]).bit_count() <= 1
        for step, value in enumerate(columns))
    slip_bound = all(abs(delta) <= 1 for delta in trial.timing_offsets)
    authorized = c_outcome["status"] == "AUTHORIZED"
    return {"first_turn_source_bound": map_bound,
            "later_camera_source_bound": camera_bound,
            "timing_slip_bound": slip_bound,
            "false_accepted_heading": authorized and
                c_outcome["accepted_bin"] != trial.true_bin}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    problems = []
    totals = {"ordinary": 0, "warranted_corrections": 0,
              "obstructions": 0, "missing_recoveries": 0,
              "scene_identity_negative_controls": 0,
              "negative_false_corrections": 0}
    with tempfile.TemporaryDirectory(prefix="mathgraph-embedded-audit-") as temp:
        native = load_c_library(Path(temp) / "finite_jitter_embedded.so")
        for seed in args.seeds:
            for actual in HYPOTHESES:
                for kind, absent in (("wide", ()), ("wide", (7,)),
                                     ("narrow", ()), ("unbreakable", ())):
                    label = "missing7" if absent else kind
                    trial = generate_jitter_trial(seed, actual, kind, absent)
                    result = run_c(native, trial.reference, trial.columns)
                    python_plan = run_jitter_acquired(trial.reference,
                                                      HYPOTHESES, trial.columns)
                    conventional = run_jitter_continuous(trial.reference,
                                                          HYPOTHESES, trial.columns)
                    grade = external_grade(trial, result)
                    expected_match = (result["status"] == python_plan.status and
                                      result["accepted_bin"] == python_plan.accepted_bin and
                                      result["attempted_steps"] == list(python_plan.attempted_steps) and
                                      result["acquired_steps"] == list(python_plan.acquired_steps) and
                                      result["pair_checks"] == python_plan.pair_checks and
                                      result["decision_step"] == python_plan.decision_step)
                    intended_status = ("AUTHORIZED" if label in ("wide", "missing7")
                                       else "UNKNOWN_OBSTRUCTION")
                    eligible = all((grade["first_turn_source_bound"],
                                    grade["later_camera_source_bound"],
                                    grade["timing_slip_bound"]))
                    valid = (eligible and expected_match and
                             result["status"] == intended_status and
                             not grade["false_accepted_heading"] and
                             (result["accepted_bin"] == actual if
                              intended_status == "AUTHORIZED" else True))
                    record = {"boundary": "SYNTHETIC_ASSUMED_FINITE_CAMERA_AND_GYRO_BOUNDS",
                              "seed": seed, "actual_bin_grader_only": actual,
                              "condition": label, "physical_source_grader_only": trial.physical_source,
                              "reference": trial.reference, "columns": trial.columns,
                              "slips_grader_only": trial.timing_offsets,
                              "missing": trial.occluded_steps,
                              "c": result, "python_independent_runtime": asdict(python_plan),
                              "conventional": asdict(conventional), "grade": grade,
                              "exact_c_python_agreement": expected_match,
                              "passes_declared_condition": valid}
                    file = args.output / f"{seed}_{actual}_{label}.json"
                    file.write_text(json.dumps(record, indent=2) + "\n")
                    totals["ordinary"] += 1
                    if result["status"] == "AUTHORIZED": totals["warranted_corrections"] += 1
                    if result["status"] == "UNKNOWN_OBSTRUCTION": totals["obstructions"] += 1
                    if absent and result["status"] == "AUTHORIZED": totals["missing_recoveries"] += 1
                    if not valid: problems.append((seed, actual, label, record["grade"], result))
                    print("C_HOLDOUT", seed, actual, label, result["status"],
                          result["accepted_bin"], result["acquired_steps"],
                          "compares", result["pair_checks"],
                          "conventional_reads", len(conventional.acquired_steps),
                          "valid", valid)

                # Explicitly break scene fidelity: later columns look like an
                # alternate heading, though external physical heading did not
                # change. False confident authority is a FAILURE MODE, not a
                # valid correction and not part of ordinary success counts.
                base = generate_jitter_trial(seed, actual, "wide")
                alternate = (actual + 16) % 64
                masquerade = generate_jitter_trial(seed, alternate, "wide")
                assert masquerade.reference == base.reference
                faked = run_c(native, base.reference, masquerade.columns)
                negative_grade = external_grade(base, faked,
                                                columns=masquerade.columns)
                totals["scene_identity_negative_controls"] += 1
                if negative_grade["false_accepted_heading"]:
                    totals["negative_false_corrections"] += 1
                negative_record = {"boundary": "NEGATIVE_SOURCE_FIDELITY_VIOLATED",
                    "seed": seed, "actual_bin_grader_only": actual,
                    "masquerade_bin_grader_only": alternate,
                    "reference": base.reference, "columns": masquerade.columns,
                    "result": faked, "grade": negative_grade}
                (args.output / f"{seed}_{actual}_source_swap_NEGATIVE.json").write_text(
                    json.dumps(negative_record, indent=2) + "\n")
                print("C_SOURCE_SWAP_NEGATIVE", seed, actual, alternate,
                      faked["status"], faked["accepted_bin"],
                      "false_authority", negative_grade["false_accepted_heading"])
    summary = {"totals": totals, "violations": problems,
               "holdout_seeds": args.seeds,
               "source_fidelity_limitation": "Explicit negative control; source swaps may fool both methods"}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("C_HOLDOUT_SUMMARY", json.dumps(totals), "violations", len(problems))
    if problems:
        raise SystemExit("UNEXPECTED_OR_INCORRECT_FINITE_COMPASS_OUTCOME")


if __name__ == "__main__":
    main()
