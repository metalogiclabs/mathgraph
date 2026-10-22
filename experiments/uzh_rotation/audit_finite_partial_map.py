#!/usr/bin/env python3
"""First-turn source-coverage stress and fair continuous-baseline C replay."""

import argparse
import ctypes
import json
from pathlib import Path
import random
import subprocess
import tempfile

from finite_witness_jitter import HYPOTHESES, generate_jitter_trial


ROOT=Path(__file__).parent


class Map(ctypes.Structure):
    _fields_=[("columns",ctypes.c_uint16*64),("seen",ctypes.c_uint8*8),
              ("quarantined",ctypes.c_uint8*8),("count",ctypes.c_uint8),
              ("frozen",ctypes.c_uint8)]


class Plan(ctypes.Structure):
    _fields_=[("step_mask",ctypes.c_uint32),("pair_checks",ctypes.c_uint16),
              ("cost",ctypes.c_uint8),("first_step",ctypes.c_uint8),
              ("status",ctypes.c_uint8)]


def load_library(path):
    subprocess.run(["gcc","-std=c99","-Wall","-Wextra","-Werror",
        "-O2","-fPIC","-shared",str(ROOT/"finite_partial_map.c"),
        str(ROOT/"finite_jitter_embedded.c"),"-o",str(path)],check=True)
    native=ctypes.CDLL(str(path))
    native.mg_map_init.argtypes=[ctypes.POINTER(Map)]
    native.mg_map_capture.argtypes=[ctypes.POINTER(Map),ctypes.c_uint8,
                                    ctypes.c_uint16]
    native.mg_map_capture.restype=ctypes.c_int
    native.mg_map_freeze.argtypes=[ctypes.POINTER(Map)]
    native.mg_map_freeze.restype=ctypes.c_int
    native.mg_sparse_plan.argtypes=[ctypes.POINTER(Map),ctypes.c_uint8,
        ctypes.c_uint8,ctypes.c_uint8,ctypes.c_uint8,ctypes.c_uint8,
        ctypes.POINTER(Plan)]
    native.mg_sparse_plan.restype=ctypes.c_int
    native.mg_sparse_next_probe.argtypes=[ctypes.POINTER(Map),ctypes.c_uint8,
        ctypes.c_uint8,ctypes.c_uint8,ctypes.c_uint8,ctypes.c_uint8,
        ctypes.POINTER(Plan)]
    native.mg_sparse_next_probe.restype=ctypes.c_int
    native.mg_sparse_filter.argtypes=[ctypes.POINTER(Map),ctypes.c_uint8,
        ctypes.c_uint8,ctypes.c_uint16,ctypes.c_uint8,ctypes.c_uint8]
    native.mg_sparse_filter.restype=ctypes.c_uint8
    return native


def coverage(seed, heading, condition):
    rng=random.Random(99173*seed + heading*217 + len(condition))
    if condition=="full": return set(range(64))
    if condition=="one_hole0": return set(range(64))-{0}
    if condition=="missing_first_cue":
        return {i for i in range(64) if i%16 not in (6,7,8)}
    if condition=="conflicting_repeat7": return set(range(64))
    holes={"random_3":3,"random_6":6,"random_12":12}[condition]
    return set(range(64))-set(rng.sample(range(64),holes))


def build_map(native, trial, bins, contradictory_repeat=False):
    m=Map()
    native.mg_map_init(ctypes.byref(m))
    for index in sorted(bins):
        if native.mg_map_capture(ctypes.byref(m),index,trial.reference[index])!=0:
            raise AssertionError("First-turn map acquisition failed")
    if contradictory_repeat:
        if native.mg_map_capture(ctypes.byref(m),7,
                                  trial.reference[7] ^ 65535)!=-2:
            raise AssertionError("Failed to quarantine conflicting duplicate")
    if native.mg_map_freeze(ctypes.byref(m))!=0:
        raise AssertionError("Map not frozen")
    return m


def follow(native, m, columns, policy):
    support=15
    reads=[]
    attempts=[]
    checks=0
    status="UNKNOWN"
    accepted=None
    plan_log=[]
    if policy in ("guaranteed","active"):
        start=1
        while start<len(columns):
            compiled=Plan()
            planner=(native.mg_sparse_plan if policy=="guaranteed"
                     else native.mg_sparse_next_probe)
            rc=planner(ctypes.byref(m),support,start,
                       len(columns)-1,2,1,ctypes.byref(compiled))
            if rc!=0: raise AssertionError("Sparse planner invalid under legal input")
            checks+=int(compiled.pair_checks)
            if compiled.status not in ((1,) if policy=="guaranteed" else (1,5)):
                plan_log.append({"from":start,"status":int(compiled.status),
                                 "pair_checks":int(compiled.pair_checks)})
                break
            step=int(compiled.first_step)
            attempts.append(step)
            plan_log.append({"from":start,"next":step,"mask":int(compiled.step_mask),
                             "cost":int(compiled.cost),"status":int(compiled.status),
                             "pair_checks":int(compiled.pair_checks)})
            if columns[step] is not None:
                reads.append(step)
                support=native.mg_sparse_filter(ctypes.byref(m),support,step,
                                                 columns[step],2,1)
                if support==0:
                    status="CONFLICT"
                    break
                if support.bit_count()==1:
                    status="AUTHORIZED"
                    accepted=(support.bit_length()-1)*16
                    break
            start=step+1
    else:
        for step in range(1,len(columns)):
            if columns[step] is None: continue
            attempts.append(step)
            reads.append(step)
            support=native.mg_sparse_filter(ctypes.byref(m),support,step,
                                             columns[step],2,1)
            if support==0:
                status="CONFLICT"
                break
            if support.bit_count()==1:
                status="AUTHORIZED"
                accepted=(support.bit_length()-1)*16
                break
    return {"status":status,"accepted_bin":accepted,"reads":reads,
            "attempts":attempts,"pair_checks":checks,
            "final_mask":int(support),"plans":plan_log}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seeds",nargs="+",type=int,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    conditions=("full","one_hole0","random_3","random_6",
                "random_12","missing_first_cue","conflicting_repeat7")
    totals={name:{"trials":0,"planned_correct":0,"planned_unknown":0,
                  "active_correct":0,"active_unknown":0,
                  "continuous_correct":0,"continuous_unknown":0,
                  "false_corrections":0,"planned_reads":0,"active_reads":0,
                  "continuous_reads":0,"active_pair_checks":0,
                  "map_columns":0} for name in conditions}
    failures=[]
    with tempfile.TemporaryDirectory(prefix="mathgraph-map-coverage-") as folder:
        native=load_library(Path(folder)/"libpartial.so")
        for seed in args.seeds:
            for heading in HYPOTHESES:
                trial=generate_jitter_trial(seed,heading,"wide")
                for condition in conditions:
                    bins=coverage(seed,heading,condition)
                    m=build_map(native,trial,bins,condition=="conflicting_repeat7")
                    planned=follow(native,m,trial.columns,"guaranteed")
                    active=follow(native,m,trial.columns,"active")
                    continuous=follow(native,m,trial.columns,"continuous")
                    grade={"true_heading_grader_only":heading,
                           "reference_bins_observed":int(m.count),
                           "quarantined_7":bool(m.quarantined[0] & (1<<7)),
                           "first_turn_map_bound_for_all_seen":all(
                              (m.columns[i]^trial.physical_source[i]).bit_count()<=1
                              for i in range(64) if m.seen[i//8] & (1<<(i%8))),
                           "future_measurement_bounds":all(
                              c is None or (c ^ trial.physical_source[
                                  (heading+step+trial.timing_offsets[step])%64]
                              ).bit_count()<=1
                              for step,c in enumerate(trial.columns))}
                    if not grade["first_turn_map_bound_for_all_seen"] or not grade["future_measurement_bounds"]:
                        failures.append((seed,heading,condition,"source model violated"))
                    results=[planned,active,continuous]
                    for result in results:
                        if result["status"]=="CONFLICT" or (
                            result["status"]=="AUTHORIZED" and
                            result["accepted_bin"]!=heading):
                            failures.append((seed,heading,condition,"incorrect correction",result))
                    t=totals[condition]
                    t["trials"]+=1
                    t["map_columns"]+=int(m.count)
                    for prefix,result in (("planned",planned),("active",active),
                                          ("continuous",continuous)):
                        if result["status"]=="AUTHORIZED": t[prefix+"_correct"]+=1
                        if result["status"]=="UNKNOWN": t[prefix+"_unknown"]+=1
                        t[prefix+"_reads"]+=len(result["reads"])
                    t["active_pair_checks"]+=active["pair_checks"]
                    record={"boundary":"SYNTHETIC_EXACT_FIRST_TURN_BIN_ASSIGNMENT_ASSUMED",
                            "seed":seed,"condition":condition,
                            "reference":trial.reference,"future_columns":trial.columns,
                            "gyro_timing_slip_grader_only":trial.timing_offsets,
                            "physical_source_grader_only":trial.physical_source,
                            "observed_first_turn_bins":sorted(bins),
                            "seen_bitset":list(m.seen),
                            "quarantined_bitset":list(m.quarantined),
                            "grade":grade,"planned":planned,"active":active,
                            "continuous":continuous}
                    (args.out/f"{seed}_{heading}_{condition}.json").write_text(
                        json.dumps(record,indent=2)+"\n")
                    print("MAP_COVERAGE",seed,heading,condition,"coverage",m.count,
                          "planned",planned["status"],planned["reads"],
                          "active",active["status"],active["reads"],
                          "continuous",continuous["status"],len(continuous["reads"]))
    summary={"seeds":args.seeds,"conditions":totals,"failures":failures,
             "limitations":["first-turn angular bin comes from gyro without measured assignment error",
                            "source fidelity assumed; later scene-swap can still fool both",
                            "failure to plan with partial map is UNKNOWN, not impossibility of environment"]}
    (args.out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("MAP_SUMMARY",json.dumps(totals),"failures",len(failures))
    if failures: raise SystemExit("INCORRECT_CONSEQUENTIAL_MAP_DECISION")


if __name__=="__main__":
    main()
