#!/usr/bin/env python3
"""16-bit camera-column joint bias/clock/drift study. SYNTHETIC ONLY.

First-turn reference comes from camera and gyro source records, not an
invented sub-bin phase detector. The scorer alone sees hidden headings.
No physical clock certificate, encoder or flight authority is provided.
"""
from dataclasses import dataclass
import csv
import json
import math
from pathlib import Path
import numpy as np

TAU=math.tau
BINS=64
ANGULAR_BIN=TAU/BINS
BIAS=np.linspace(-.020,.020,41)
CLOCK=np.linspace(-.040,.040,17)
DRIFT=np.array([-.0008,-.0004,0.,.0004,.0008])
POPCOUNT=np.fromiter((n.bit_count() for n in range(65536)),dtype=np.uint8,count=65536)
SCENARIOS=("steady","varying","clock_shift","drift","occlusion","alias","outliers")

@dataclass
class Source:
    gyro_ns:np.ndarray
    gyro_rate:np.ndarray
    camera_ns:np.ndarray
    camera_bits:np.ndarray  # -1 is missing; all other values must be 0..65535

@dataclass
class Truth:
    heading_rad:np.ndarray
    bias_rad_s:float
    drift_rad_s2:float
    offset_s:float

def phi(t,mode):
    t=np.asarray(t,dtype=float)
    return 2*t if mode=="steady" else 2*t+.75/.65*(1-np.cos(.65*t))+.45/1.43*(1-np.cos(1.43*t))

def omega(t,mode):
    t=np.asarray(t,dtype=float)
    return 2+np.zeros_like(t) if mode=="steady" else 2+.75*np.sin(.65*t)+.45*np.sin(1.43*t)

def make_fixture(seed,scenario):
    if scenario not in SCENARIOS or not 0<=seed<1024:
        raise ValueError("unsupported synthetic fixture")
    rng=np.random.default_rng(82511+seed)
    mode="steady" if scenario=="steady" else "varying"
    bias=.006 if seed%2==0 else -.008
    drift=.0004 if scenario=="drift" else 0.
    offset=-.03 if scenario=="clock_shift" else .025
    gyro_t=np.arange(-.1,20.25,.01)
    camera_t=np.arange(0,20,.03)
    visual_phase=phi(camera_t+offset,mode)-float(phi([offset],mode)[0])
    panorama=[int(x) for x in rng.integers(0,65536,64)]
    if scenario=="alias":
        panorama=panorama[:16]*4
    cells=np.floor(np.mod(visual_phase,TAU)/ANGULAR_BIN).astype(int)%BINS
    observed=np.asarray([panorama[k] for k in cells],dtype=np.uint16)
    flip=np.left_shift(np.uint16(1),rng.integers(0,16,len(camera_t)).astype(np.uint16))
    observed=np.bitwise_xor(observed,flip).astype(np.int32)
    if scenario=="occlusion":
        observed[(camera_t>7)&(camera_t<10)]=-1
    if scenario=="outliers":
        for i in (204,336,468):
            observed[i]=int(rng.integers(0,65536))
    shift=100_000_000
    nav=Source(np.rint(gyro_t*1e9).astype(np.int64)+shift,
        omega(gyro_t,mode)+bias+drift*gyro_t,
        np.rint(camera_t*1e9).astype(np.int64)+shift,observed)
    hidden=Truth(np.asarray(phi(camera_t,mode)),bias,drift,offset)
    return nav,hidden

def validate_source(src):
    for stamps in (src.camera_ns,src.gyro_ns):
        if len(stamps)<10 or np.any(stamps<0) or np.any(np.diff(stamps)<=0):
            raise ValueError("timestamps missing, negative or nonmonotonic")
    if len(src.camera_ns)!=len(src.camera_bits) or len(src.gyro_ns)!=len(src.gyro_rate):
        raise ValueError("sensor length mismatch")
    if np.any((src.camera_bits < -1)|(src.camera_bits>=65536)):
        raise ValueError("invalid 16-bit camera source")
    if not np.isfinite(src.gyro_rate).all():
        raise ValueError("non-finite gyro source")
    if np.min(src.camera_ns)<np.min(src.gyro_ns) or np.max(src.camera_ns)>np.max(src.gyro_ns):
        raise ValueError("camera outside gyro support")

def integrated(src):
    steps=np.diff(src.gyro_ns)*1e-9*(src.gyro_rate[:-1]+src.gyro_rate[1:])*.5
    return np.r_[0.,np.cumsum(steps)]

MAX_GYRO_AGE_NS=20_000_000

def past_only_gyro_phase(src,cumulative,stamps):
    """Integrate only gyro packets available at each requested timestamp."""
    stamps=np.asarray(stamps,dtype=np.int64)
    last=np.searchsorted(src.gyro_ns,stamps,side="right")-1
    if np.any(last<0):
        raise ValueError("camera before first gyro packet")
    age=stamps-src.gyro_ns[last]
    if np.any(age<0) or np.any(age>MAX_GYRO_AGE_NS):
        raise ValueError("stale gyro source: causal phase unavailable")
    return cumulative[last]+src.gyro_rate[last]*age*1e-9

def read_navigation_csv(camera_path,gyro_path):
    """Read exact camera/gyro CSVs from canonical NAVIGATION-only adapter."""
    with open(camera_path,newline="") as file:
        reader=csv.DictReader(file)
        if not reader.fieldnames or not {"timestamp_ns","bits16","usable"}<=set(reader.fieldnames):
            raise ValueError("missing camera CSV columns")
        cameras=list(reader)
    with open(gyro_path,newline="") as file:
        reader=csv.DictReader(file)
        if not reader.fieldnames or not {"timestamp_ns","gyro_z_rad_s"}<=set(reader.fieldnames):
            raise ValueError("missing gyro CSV columns")
        gyros=list(reader)
    if len(cameras)<10 or len(gyros)<10:
        raise ValueError("insufficient source samples")
    if any(row["usable"] not in ("0","1") for row in cameras):
        raise ValueError("invalid camera usability")
    source=Source(
        np.asarray([int(row["timestamp_ns"]) for row in gyros],dtype=np.int64),
        np.asarray([float(row["gyro_z_rad_s"]) for row in gyros]),
        np.asarray([int(row["timestamp_ns"]) for row in cameras],dtype=np.int64),
        np.asarray([int(row["bits16"]) if row["usable"]=="1" else -1 for row in cameras],dtype=np.int32))
    validate_source(source)
    return source

def map_from_source(src):
    validate_source(src)
    g=integrated(src)
    camera_g=past_only_gyro_phase(src,g,src.camera_ns)
    first=np.nonzero((camera_g-camera_g[0])>=TAU)[0]
    if len(first)==0:
        raise ValueError("no first measured gyro revolution")
    end=int(first[0])
    signature=np.zeros(BINS,dtype=np.uint16)
    present=np.zeros(BINS,dtype=bool)
    quarantined=np.zeros(BINS,dtype=bool)
    for i in range(end):
        if src.camera_bits[i]==-1:
            continue
        k=int(math.floor(((camera_g[i]-camera_g[0])%TAU)/ANGULAR_BIN))%BINS
        if not present[k] and not quarantined[k]:
            signature[k]=int(src.camera_bits[i]);present[k]=True
        elif present[k] and POPCOUNT[int(signature[k]^src.camera_bits[i])]>2:
            present[k]=False;quarantined[k]=True
    if present.sum()<16:
        raise ValueError("insufficient firstturn coverage")
    return {"signatures":signature,"present":present,
            "quarantined":quarantined,"frozen_at_camera_index":end,
            "gyro_integral":g,"hardware_authority":False}

def model_candidate_step(src,frozen,frame,jitter=1):
    if not 0<=jitter<=3 or src.camera_bits[frame]<0:
        raise ValueError("missing observation or invalid assumed jitter")
    t=(src.camera_ns[frame]-src.camera_ns[0])*1e-9
    timeline=src.gyro_ns*1e-9
    base=src.camera_ns[0]*1e-9
    g=frozen["gyro_integral"]
    shifted=np.asarray([
        past_only_gyro_phase(src,g,[int(src.camera_ns[frame]+round(delta*1e9))])[0]-
        past_only_gyro_phase(src,g,[int(src.camera_ns[0]+round(delta*1e9))])[0]
        for delta in CLOCK])
    predicted=shifted[:,None,None]-t*BIAS[None,:,None]-.5*t*t*DRIFT[None,None,:]
    bins=np.floor(np.mod(predicted,TAU)/ANGULAR_BIN).astype(int)%BINS
    bits=int(src.camera_bits[frame])
    present=frozen["present"];signature=frozen["signatures"]
    compatible=np.zeros_like(bins,dtype=bool)
    missing=np.zeros_like(bins,dtype=bool)
    cost=np.full_like(bins,16,dtype=np.int16)
    for delta in range(-jitter,jitter+1):
        cell=(bins+delta)%BINS
        valid=present[cell]
        hamming=POPCOUNT[np.bitwise_xor(signature[cell],np.uint16(bits))].astype(np.int16)
        compatible|=valid & (hamming<=2)
        missing|=~valid
        cost=np.minimum(cost,np.where(valid,hamming,16))
    # A missing map bin cannot eliminate a heading hypothesis.
    compatible|=missing
    return compatible,np.where(missing,2,cost)

def replay(src,*,stride=12,jitter=1,outlier_budget=1,
           robustness_budget=3,width_limit_rad=.07):
    frozen=map_from_source(src)
    shape=(len(CLOCK),len(BIAS),len(DRIFT))
    failures=np.zeros(shape,dtype=np.int16)
    robust_loss=np.zeros(shape,dtype=float)
    bg=np.broadcast_to(BIAS[None,:,None],shape)
    dg=np.broadcast_to(DRIFT[None,None,:],shape)
    g=past_only_gyro_phase(src,frozen["gyro_integral"],src.camera_ns)
    g=g-g[0]
    end=frozen["frozen_at_camera_index"]
    events=[];reads=[]
    for i in range(end,len(src.camera_ns)):
        acquired=(i%stride==0 and src.camera_bits[i]!=-1)
        if acquired:
            reads.append(i)
            matching,cost=model_candidate_step(src,frozen,i,jitter=jitter)
            failures+=(~matching).astype(np.int16)
            # Conventional capped-Hamming grid estimator sees the same pixels.
            robust_loss+=np.minimum(cost,4)**2
        t=(src.camera_ns[i]-src.camera_ns[0])*1e-9
        candidates=failures<=outlier_budget
        if candidates.any():
            phases=g[i]-bg[candidates]*t-.5*dg[candidates]*t*t
            lo,hi=float(np.min(phases)),float(np.max(phases))
            midpoint=(lo+hi)*.5
            width=hi-lo
        else:
            midpoint=float(g[i]);width=None;lo=hi=None
        stress_set=failures<=max(robustness_budget,outlier_budget)
        if stress_set.any():
            phases=g[i]-bg[stress_set]*t-.5*dg[stress_set]*t*t
            stress_width=float(np.max(phases)-np.min(phases))
        else:
            stress_width=None
        state=("UNKNOWN_INSUFFICIENT" if len(reads)<3 else
               "UNKNOWN_CONFLICT" if not candidates.any() else
               "UNKNOWN_TOO_WIDE" if width>width_limit_rad else
               "UNKNOWN_OUTLIER_SENSITIVITY" if stress_width is None or
                 stress_width>width_limit_rad else
               "MODEL_INTERVAL_NARROW")
        regularizer=.005*(bg/.020)**2+.003*(dg/.0008)**2
        flat=int(np.argmin(robust_loss+regularizer))
        _,bidx,didx=np.unravel_index(flat,shape)
        robust=g[i]-BIAS[bidx]*t-.5*DRIFT[didx]*t*t
        events.append({
            "camera_index":int(i),"timestamp_ns":int(src.camera_ns[i]),
            "gyro_clock_decision_not_before_ns":int(src.camera_ns[i]+round(float(max(CLOCK))*1e9)),
            "model_state":state,"diagnostic_midpoint_rad":float(midpoint),
            "conventional_capped_hamming_rad":float(robust),
            "gyro_only_rad":float(g[i]),"interval_min_rad":lo,
            "interval_max_rad":hi,"interval_width_rad":width,
            "sensitivity_width_rad":stress_width,
            "feasible_parameter_count":int(candidates.sum()),
            "source_camera_observation_acquired":bool(acquired),
            "navigation_correction_authorized":False})
    return {"scope":"SOURCE_NATIVE_16BIT_SYNTHETIC_NO_PHYSICAL_METROLOGY",
            "physical_navigation_authorized":False,
            "firstturn_end_camera_index":end,
            "frozen_firstturn_bins":int(frozen["present"].sum()),
            "firstturn_quarantined_bins":int(frozen["quarantined"].sum()),
            "camera_acquisition_indices":reads,
            "assumed_outlier_budget":outlier_budget,
            "assumed_jitter_bins":jitter,
            "sensitivity_budget":robustness_budget,
            "retrospective_analysis_only":True,
            "events":events}

def grade(nav,truth,output):
    # Independent synthetic grader: hidden truth is NOT passed into replay.
    true=truth.heading_rad-truth.heading_rad[0]
    indexes=[e["camera_index"] for e in output["events"]]
    actual=true[indexes]
    def rmse(key):
        error=np.asarray([r[key] for r in output["events"]])-actual
        return float(np.rad2deg(np.sqrt(np.mean(error*error))))
    narrow=[r for r in output["events"] if r["model_state"]=="MODEL_INTERVAL_NARROW"]
    wrong=sum(not r["interval_min_rad"]-1e-10<=true[r["camera_index"]]<=
                 r["interval_max_rad"]+1e-10 for r in narrow)
    # Post-hoc risk/coverage diagnostics only. Thresholds are NOT tuned
    # into a flight policy. The hidden synthetic grader alone sees truth.
    frontier={}
    for width in (.07,.10,.20,.30,.50):
        eligible=[e for e in output["events"] if
                  e["interval_width_rad"] is not None and
                  e["sensitivity_width_rad"] is not None and
                  e["interval_width_rad"]<=width and
                  e["sensitivity_width_rad"]<=width]
        false=sum(not (e["interval_min_rad"]-1e-10<=true[e["camera_index"]]<=
                       e["interval_max_rad"]+1e-10) for e in eligible)
        frontier[f"{width:.2f}"]={
            "eligible_frames":len(eligible),
            "false_intervals_grader_only":int(false),
            "fraction_of_scored_frames":len(eligible)/len(indexes)}
    return {"gyro_rmse_deg":rmse("gyro_only_rad"),
            "mathgraph_diagnostic_rmse_deg":rmse("diagnostic_midpoint_rad"),
            "conventional_capped_hamming_rmse_deg":rmse("conventional_capped_hamming_rad"),
            "model_narrow_fraction":len(narrow)/len(indexes),
            "model_narrow_frames":len(narrow),
            "false_model_narrow_frames_grader_only":int(wrong),
            "retrospective_risk_coverage_only":frontier,
            "firstturn_truth_revolutions_grader_only":
                float(true[output["firstturn_end_camera_index"]]/TAU),
            "hardware_warrant":False}

def benchmark(seeds=8):
    if not 1<=seeds<=64:
        raise ValueError("study seeds outside bounds")
    rows=[]
    for case in SCENARIOS:
        scores=[]
        for seed in range(seeds):
            source,hidden=make_fixture(seed,case)
            scores.append(grade(source,hidden,replay(source)))
        labels=("gyro_rmse_deg","mathgraph_diagnostic_rmse_deg",
                "conventional_capped_hamming_rmse_deg","model_narrow_fraction",
                "false_model_narrow_frames_grader_only")
        means={k:round(float(np.mean([s[k] for s in scores])),4) for k in labels}
        frontier={key:{
            "eligible_frames":sum(row["retrospective_risk_coverage_only"][key]["eligible_frames"] for row in scores),
            "false_intervals_grader_only":sum(row["retrospective_risk_coverage_only"][key]["false_intervals_grader_only"] for row in scores)}
            for key in scores[0]["retrospective_risk_coverage_only"]}
        rows.append({"condition":case,"trials":seeds,"mean":means,
                     "posthoc_threshold_frontier":frontier,
                     "seed_scores":scores})
    return {"boundary":"ACTUAL_SYNTHETIC_16BIT_COLUMNS_NOT_IDEALIZED_OPTICAL_PHASE",
            "same_gyro_and_source_columns_for_both_estimation_methods":True,
            "hidden_truth_excluded_from_estimators":True,
            "real_sensors_tested":False,"physical_navigation_authorized":False,
            "scenarios":rows}

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--seeds",type=int,default=8)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    result=benchmark(args.seeds)
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n")
    for item in result["scenarios"]:
        print("SOURCE_NATIVE_FINITE",item["condition"],item["mean"])
    print("NO_PHYSICAL_NAVIGATION_WARRANT")
