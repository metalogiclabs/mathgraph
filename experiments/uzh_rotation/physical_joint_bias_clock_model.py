#!/usr/bin/env python3
"""Exploratory joint gyro bias / camera time-offset model; NO physical warrant.

Input optical phase is a SYNTHETIC sub-bin bearing abstraction (1/16 of a
64-bin circle). It is NOT recovered from raw camera columns. The continuous
gyro trace and the same sampled optical bearings are passed to every method.
No heading truth, encoder, true bias or true clock appears in an estimator.
"""
from __future__ import annotations
import argparse, json, math, random
from dataclasses import dataclass
import numpy as np

TAU=math.tau
SUBBIN=TAU/(64*16)
BIAS_GRID=np.round(np.linspace(-.030,.030,121),9)
CLOCK_GRID=np.round(np.linspace(-.040,.040,33),9)
TOLERANCE=.014
MAX_HEAD_RADIUS=.055
PRIOR_B=.030

def wrap(x):
    return (x+math.pi)%TAU-math.pi

def phase(t,mode):
    if mode=="steady": return 2*t
    return 2*t+.75/.65*(1-np.cos(.65*t))+.45/1.43*(1-np.cos(1.43*t))

@dataclass
class Capture:
    gyro_times:np.ndarray
    gyro_phase:np.ndarray
    camera_times:np.ndarray
    camera_bearing:np.ndarray
    true_camera_time_offset:float
    hidden_true_bias:float
    hidden_theta_at_camera_times:np.ndarray
    source:str
    condition:str

CONDITIONS=("steady","varying","varying_occlusion","varying_outliers",
            "varying_clock_shift","varying_drift","ambiguous_visual_dropout")

def make_capture(seed,condition):
    if condition not in CONDITIONS: raise ValueError(condition)
    rng=random.Random(73411+seed*131)
    mode="steady" if condition=="steady" else "varying"
    bias=.012 if seed%2==0 else -.008
    delta=-.0325 if condition=="varying_clock_shift" else .025
    gt=np.arange(-.10,20.251,.025)
    drift=.00065 if condition=="varying_drift" else 0.
    gyro=phase(gt,mode)+bias*gt+.5*drift*gt*gt
    ct=np.arange(.25,20.001,.10)
    visual=phase(ct+delta,mode)-phase(np.array([delta]),mode)[0]
    measured=np.array([v+rng.uniform(-.003,.003) for v in visual])
    measured=np.round(measured/SUBBIN)*SUBBIN
    if condition=="varying_occlusion": measured[(ct>=7)&(ct<10)]=np.nan
    if condition=="varying_outliers":
        # These events ARE on the frozen stride-8 acquisition timeline.
        for i in (48,96,144): measured[i]=wrap(measured[i]+1.60)
    if condition=="ambiguous_visual_dropout":
        # Abstract frontend withholding uncertain matches, not simulated
        # raw scene texture or proof of a real repeated-landmark detector.
        measured[(ct>=5)&(ct<13)]=np.nan
    return Capture(gt,gyro,ct,
        np.asarray([wrap(v) if math.isfinite(v) else np.nan for v in measured]),
        delta,bias,np.asarray(phase(ct,mode)),
        "SYNTHETIC_SUBBIN_VISUAL_PHASE_NOT_RAW_CAMERA",condition)

def unwrapped_visual(c):
    g=np.interp(c.camera_times,c.gyro_times,c.gyro_phase)
    y=np.array([v+TAU*round((p-v)/TAU) if math.isfinite(v) else np.nan
                for p,v in zip(g,c.camera_bearing)])
    # Requires actual gyro revolution-index error to be < pi;
    # never claimed as externally warranted on hardware.
    return g,y

def forward_components(c,ids):
    t=c.camera_times[ids]
    shifted=np.vstack([
        np.interp(t+d,c.gyro_times,c.gyro_phase)-
        np.interp(d,c.gyro_times,c.gyro_phase)
        for d in CLOCK_GRID
    ])
    return t,shifted

def joint_feasible(c,ids,tolerance=TOLERANCE,violation_budget=0):
    if not len(ids):return np.ones((len(CLOCK_GRID),len(BIAS_GRID)),dtype=bool)
    t,gshift=forward_components(c,ids)
    y=unwrapped_visual(c)[1][ids]
    residual=gshift[:,:,None]-t[None,:,None]*BIAS_GRID[None,None,:]-y[None,:,None]
    return np.sum(np.abs(residual)>tolerance+1e-10,axis=1)<=violation_budget

def ls_fit(c,ids,robust=False):
    if len(ids)<2:return 0.,0.
    t,p=forward_components(c,ids)
    y=unwrapped_visual(c)[1][ids]
    residual=p-y[None,:]
    b=np.clip(np.sum(residual*t,axis=1)/np.sum(t*t),-PRIOR_B,PRIOR_B)
    if robust:
        for _ in range(6):
            r=residual-b[:,None]*t
            weights=np.minimum(1.,.020/np.maximum(np.abs(r),1e-12))
            b=np.clip(np.sum(weights*residual*t,axis=1)/
                np.sum(weights*t*t,axis=1),-PRIOR_B,PRIOR_B)
        r=residual-b[:,None]*t
        losses=np.where(np.abs(r)<=.020,.5*r*r,.020*(np.abs(r)-.010))
    else:
        r=residual-b[:,None]*t
        losses=.5*r*r
    best=int(np.argmin(np.sum(losses,axis=1)))
    return float(b[best]),float(CLOCK_GRID[best])

def run_estimators(c,stride=8,mismatch_budget=0):
    g,_=unwrapped_visual(c)
    ids=[]
    records=[]
    feasible=np.ones((len(CLOCK_GRID),len(BIAS_GRID)),dtype=bool)
    bmid=clockmid=b_ls=b_huber=0.
    bounds=(-PRIOR_B,PRIOR_B)
    consistent=True
    for i,time in enumerate(c.camera_times):
        if math.isfinite(c.camera_bearing[i]) and i%stride==0:
            ids.append(i)
            # Same schedule and observations available to LS and Huber.
            feasible=joint_feasible(c,ids,violation_budget=mismatch_budget)
            if feasible.any():
                ds,bs=np.where(feasible)
                bounds=(float(BIAS_GRID[bs.min()]),float(BIAS_GRID[bs.max()]))
                bmid=(bounds[0]+bounds[1])/2
                clockmid=float(np.median(CLOCK_GRID[ds]))
                consistent=True
            else:
                # Never reinitialize secretly after contrary evidence.
                consistent=False
            b_ls,_=ls_fit(c,ids,robust=False)
            b_huber,_=ls_fit(c,ids,robust=True)
        radius=max(abs(bounds[0]-bmid),abs(bounds[1]-bmid))*time
        ds=np.where(feasible)[0]
        clock_span=float(np.ptp(CLOCK_GRID[ds])) if feasible.any() else float("nan")
        state=("UNKNOWN_NO_EVIDENCE" if len(ids)<2 else
               "UNKNOWN_CONFLICT" if not consistent else
               "UNKNOWN_WIDE_BIAS" if radius>MAX_HEAD_RADIUS else
               "MODEL_BIAS_BOUNDED_CLOCK_UNKNOWN" if clock_span>.020 else
               "MODEL_JOINT_BOUNDED")
        # Diagnostic bias-corrected heading. Never a flight actuator command.
        applied=bmid if state.startswith("MODEL_") else 0.
        records.append({
            "i":i,"t":round(float(time),5),"state":state,
            "mathgraph":float(g[i]-applied*time),
            "conventional_ls":float(g[i]-b_ls*time),
            "conventional_huber":float(g[i]-b_huber*time),
            "gyro":float(g[i]),"bias_midpoint":bmid,
            "bias_interval":list(bounds),
            "clock_span_seconds_if_model":clock_span,
            "candidate_clock_midpoint":clockmid,
            "head_bound_rad_if_model":float(radius),
            "physical_authority":False
        })
    return {"records":records,"camera_observations_used":len(ids),
            "sample_indices":ids,"final_state":records[-1]["state"],
            "front_end":"SYNTHETIC_SUBBIN_PHASE_REFERENCE_ASSUMED",
            "physical_authority":False}

def score(c,run):
    # Hidden truth is read ONLY by this separate scorer.
    truth=c.hidden_theta_at_camera_times
    rec=run["records"]
    keys=("gyro","mathgraph","conventional_ls","conventional_huber")
    rmse={key:float(np.sqrt(np.mean(np.rad2deg(
        np.asarray([r[key] for r in rec])-truth)**2))) for key in keys}
    states=[r["state"] for r in rec]
    holds=[r["bias_interval"][0]-1e-10<=c.hidden_true_bias<=
           r["bias_interval"][1]+1e-10 for r in rec
           if r["state"].startswith("MODEL_")]
    return {
        "scenario":c.condition,"rmse_unwrapped_deg":rmse,
        "camera_observations_used":run["camera_observations_used"],
        "decision_bounded_fraction":sum(s.startswith("MODEL_") for s in states)/len(states),
        "joint_clock_bounded_fraction":states.count("MODEL_JOINT_BOUNDED")/len(states),
        "decision_unknown_conflict_fraction":states.count("UNKNOWN_CONFLICT")/len(states),
        "claimed_bias_interval_contains_truth_on_bounded_steps":all(holds),
        "bounded_frames":len(holds),"physical_result":False,
        "hidden_truth_used_only_for_scoring":True
    }

def benchmark(seeds=8,stride=8):
    if not 1<=seeds<=64 or stride<1:raise ValueError("unsupported study bounds")
    cases=[]
    for condition in CONDITIONS:
        rows=[score((c:=make_capture(seed,condition)),
                    run_estimators(c,stride=stride))
              for seed in range(seeds)]
        keys=rows[0]["rmse_unwrapped_deg"]
        cases.append({
            "condition":condition,"seeds":seeds,
            "mean_unwrapped_rmse_deg":{
                key:round(float(np.mean([r["rmse_unwrapped_deg"][key] for r in rows])),5)
                for key in keys},
            "mean_bounded_fraction":round(float(np.mean(
                [r["decision_bounded_fraction"] for r in rows])),4),
            "mean_joint_clock_bounded_fraction":round(float(np.mean(
                [r["joint_clock_bounded_fraction"] for r in rows])),4),
            "mean_conflict_fraction":round(float(np.mean(
                [r["decision_unknown_conflict_fraction"] for r in rows])),4),
            "all_bounded_bias_intervals_contain_hidden_true_bias":all(
                r["claimed_bias_interval_contains_truth_on_bounded_steps"] for r in rows),
            "all_individual_seed_scores":rows})
    return {
        "boundary":"SYNTHETIC_PHASE_FRONTEND_NO_RAW_CAMERA_NO_PHYSICAL_CLOCK",
        "same_camera_and_gyro_for_all_compared_estimators":True,
        "same_fixed_acquisition_schedule_for_all_estimators":True,
        "synthetic_visual_bearing_quantization_degrees":float(np.rad2deg(SUBBIN)),
        "clock_joint_identifiable_on_steady_motion":False,
        "conditions":cases,"physical_heading_authorized":False
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--seeds",type=int,default=8)
    p.add_argument("--stride",type=int,default=8)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    result=benchmark(args.seeds,args.stride)
    with open(args.out,"w") as f:json.dump(result,f,indent=2)
    for c in result["conditions"]:
        print(c["condition"],c["mean_unwrapped_rmse_deg"],
              "joint_clock_bounded",c["mean_joint_clock_bounded_fraction"],
              "bias_interval_contains_truth",c["all_bounded_bias_intervals_contain_hidden_true_bias"])
    print("NO_RAW_CAMERA_OR_PHYSICAL_HEADING_CORRECTION_WARRANT")
