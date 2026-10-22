#!/usr/bin/env python3
"""Adversarial first-revolution gyro bin misassignment (external grader only).

This deliberately VIOLATES v5's exact first-turn map-index assumption.
Compare three equally informed consumers of the same corrupted map and later
columns. A passing script never converts failures outside the bound to proof.
"""

import argparse
import ctypes
import json
from pathlib import Path
import random
import tempfile

from audit_finite_partial_map import Map, load_library, follow
from finite_witness_jitter import HYPOTHESES, generate_jitter_trial


CONDITIONS=("exact_control","constant_plus1","constant_minus1",
            "alternating_plusminus1","independent_plusminus1",
            "cue_concentrated_plusminus1","independent_plusminus2")


def assigned_offsets(seed, condition):
    # Same first-revolution disturbance for all later heading hypotheses.
    # Do not let a future outcome determine the observations used to build map.
    rng=random.Random(110917*seed+len(condition)*101)
    if condition=="exact_control": return (0,)*64
    if condition=="constant_plus1": return (1,)*64
    if condition=="constant_minus1": return (-1,)*64
    if condition=="alternating_plusminus1":
        return tuple(1 if i%2==0 else -1 for i in range(64))
    if condition=="independent_plusminus1":
        return tuple(rng.randrange(-1,2) for _ in range(64))
    if condition=="cue_concentrated_plusminus1":
        return tuple(rng.choice((-1,1)) if i%16 in (6,7,8,12,13,14)
                     else 0 for i in range(64))
    if condition=="independent_plusminus2":
        return tuple(rng.randrange(-2,3) for _ in range(64))
    raise ValueError(condition)


def first_revolution_samples(trial, seed, condition):
    offsets=assigned_offsets(seed,condition)
    rng=random.Random(2010013*seed+len(condition)*1021)
    samples=tuple(trial.physical_source[(i+offsets[i])%64] ^
                  (1<<rng.randrange(16)) for i in range(64))
    if not all((samples[i]^trial.physical_source[(i+offsets[i])%64]).bit_count()==1
               for i in range(64)):
        raise AssertionError("First-turn physical one-bit generator invariant")
    return samples,offsets


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seeds",type=int,nargs="+",required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    summary={condition:{"cases":0,"exact_map_bound":0,
             "guaranteed_correct":0,"guaranteed_unknown":0,"guaranteed_conflict":0,"guaranteed_false":0,
             "active_correct":0,"active_unknown":0,"active_conflict":0,"active_false":0,
             "continuous_correct":0,"continuous_unknown":0,"continuous_conflict":0,"continuous_false":0,
             "active_reads":0,"continuous_reads":0} for condition in CONDITIONS}
    with tempfile.TemporaryDirectory(prefix="mathgraph-firstturn-index-") as temp:
        native=load_library(Path(temp)/"libfirstturn.so")
        for seed in args.seeds:
            for heading in HYPOTHESES:
                trial=generate_jitter_trial(seed,heading,"wide")
                for condition in CONDITIONS:
                    columns,offsets=first_revolution_samples(trial,seed,condition)
                    m=Map()
                    native.mg_map_init(ctypes.byref(m))
                    for i,value in enumerate(columns):
                        if native.mg_map_capture(ctypes.byref(m),i,value)!=0:
                            raise AssertionError("Initial map failed to acquire")
                    native.mg_map_freeze(ctypes.byref(m))
                    outcomes={policy:follow(native,m,trial.columns,policy)
                              for policy in ("guaranteed","active","continuous")}
                    map_bound=all((columns[i]^trial.physical_source[i]).bit_count()<=1
                                  for i in range(64))
                    if condition=="exact_control" and not map_bound:
                        raise AssertionError("Exact-index control violated map boundary")
                    row=summary[condition]
                    row["cases"]+=1
                    row["exact_map_bound"]+=int(map_bound)
                    for method,outcome in outcomes.items():
                        status=outcome["status"]
                        if status=="AUTHORIZED":
                            key="correct" if outcome["accepted_bin"]==heading else "false"
                        else:
                            key="conflict" if status=="CONFLICT" else "unknown"
                        row[method+"_"+key]+=1
                    row["active_reads"]+=len(outcomes["active"]["reads"])
                    row["continuous_reads"]+=len(outcomes["continuous"]["reads"])
                    record={"boundary":"NEGATIVE_OUTSIDE_FIRST_TURN_ANGULAR_INDEX_BOUND",
                        "seed":seed,"condition":condition,
                        "true_heading_grader_only":heading,
                        "true_scene_grader_only":trial.physical_source,
                        "firstturn_index_error_grader_only":offsets,
                        "firstturn_samples":columns,
                        "future_samples":trial.columns,
                        "future_slips_grader_only":trial.timing_offsets,
                        "firstturn_exact_index_bound_holds":map_bound,
                        "outcomes":outcomes}
                    (args.out/f"{seed}_{heading}_{condition}.json").write_text(
                        json.dumps(record,indent=2)+"\n")
                    print("FIRSTTURN_GYRO_JITTER",seed,heading,condition,
                          "source_bound",map_bound,"planned",outcomes["guaranteed"]["status"],
                          outcomes["guaranteed"]["accepted_bin"],
                          "active",outcomes["active"]["status"],
                          outcomes["active"]["accepted_bin"],
                          "continuous",outcomes["continuous"]["status"],
                          outcomes["continuous"]["accepted_bin"])
    record={"seeds":args.seeds,"conditions":summary,
        "epistemic_boundary":"All nonzero first-turn index errors violate frozen-index premise",
        "verdict":"adversarial sensitivity, not validated sensor tolerance"}
    (args.out/"summary.json").write_text(json.dumps(record,indent=2)+"\n")
    print("FIRSTTURN_JITTER_SUMMARY",json.dumps(summary))
    control=summary["exact_control"]
    if control["active_correct"]!=control["cases"] or control["continuous_correct"]!=control["cases"]:
        raise SystemExit("FIRSTTURN_CONTROL_FAILED")


if __name__=="__main__":
    main()
