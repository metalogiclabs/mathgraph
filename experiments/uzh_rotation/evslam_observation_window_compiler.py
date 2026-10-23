"""Source-pose-only observation-window compiler for MathGraph visual compass.

An independently authenticated clock error bound is NOT yet available; the
publisher's nominal camera-IMU shift is used only as a hypothetical sensitivity
halfwidth. Ground-truth pose phase is an OFFLINE oracle for feasibility, never a
camera/gyro estimator input or an online acquisition schedule.

All windows are calculated from the exact piecewise-linear interpolation of
the 10-Hz GT projected body-Y phase: sample-hidden rotations are NOT bounded.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from evslam_source_phase_clock import (
    admit_calibrations, body_y_phase, read_original_gt, SOURCE_BLOBS,
    UPSTREAM_COMMIT, TWO_PI,
)

BINS = 64
BIN_RAD = TWO_PI/BINS
CLOCK_SCENARIOS_S = (0.0,0.0005,0.001,0.0025859877860685437,
                     0.005,0.01,0.015,0.02,0.025,0.03)
COMPARE_RATES_HZ = (10,20,25,30,40,50,100,400)


def first_complete_projected_turn(times, phase):
    """Truncate at FIRST upward crossing of 2pi, never splice later turns."""
    times=np.asarray(times,dtype=float)
    phase=np.asarray(phase,dtype=float)
    if (times.ndim!=1 or times.size<2 or phase.shape!=times.shape or
        not np.isfinite(times).all() or not np.isfinite(phase).all() or
        not np.all(np.diff(times)>0)):
        raise ValueError("invalid original pose time/phase")
    crosses=np.flatnonzero((phase[:-1]<TWO_PI)&(phase[1:]>=TWO_PI))
    if crosses.size==0:
        return None
    i=int(crosses[0])
    fraction=(TWO_PI-phase[i])/(phase[i+1]-phase[i])
    boundary=times[i]+fraction*(times[i+1]-times[i])
    return np.r_[times[:i+1],boundary],np.r_[phase[:i+1],TWO_PI]


def bin_occupancy_windows(times, phase, bins=BINS):
    """Finite exact knot/boundary crossing decomposition of piecewise phase.

    A maximal open time interval belongs to a unique bin only if every
    interpolated phase inside it belongs to that bin. Both reversing and
    stationary source trajectories are permitted; never monotonic-clip.
    """
    times=np.asarray(times,dtype=float)
    phase=np.asarray(phase,dtype=float)
    if times.ndim!=1 or len(times)<2 or phase.shape!=times.shape or not (2<=bins<=256):
        raise ValueError("invalid occupancy input")
    if not np.all(np.isfinite(times)) or not np.all(np.isfinite(phase)) or not np.all(np.diff(times)>0):
        raise ValueError("invalid occupancy chronology")
    width=TWO_PI/bins
    segments=[]
    for j in range(len(times)-1):
        t0,t1=float(times[j]),float(times[j+1])
        p0,p1=float(phase[j]),float(phase[j+1])
        breaks=[t0,t1]
        if p0!=p1:
            minp,maxp=min(p0,p1),max(p0,p1)
            bottom=max(0,int(math.floor(minp/width)))
            top=min(bins,int(math.ceil(maxp/width)))
            for k in range(bottom,top+1):
                boundary=k*width
                if minp<boundary<maxp:
                    f=(boundary-p0)/(p1-p0)
                    breaks.append(t0+f*(t1-t0))
        breaks.sort()
        for a,b in zip(breaks[:-1],breaks[1:]):
            if b-a<=1e-10:
                continue
            mid=(a+b)*.5
            pmid=p0+(p1-p0)*(mid-t0)/(t1-t0)
            if pmid<0 or pmid>=TWO_PI:
                continue
            index=min(int(math.floor(pmid/width)),bins-1)
            if segments and segments[-1][0]==index and abs(segments[-1][2]-a)<=1e-8:
                segments[-1]=(index,segments[-1][1],b)
            else:
                segments.append((index,a,b))
    bins_map={i:[] for i in range(bins)}
    for index,a,b in segments:
        bins_map[index].append((a,b))
    return bins_map


def compile_observation_windows(times,phase,clock_halfwidth_s,
                                bins=BINS,rate_options=COMPARE_RATES_HZ):
    """Conditional possibility/obstruction within the declared finite model.

    For a connected source-phase occupancy window (a,b), all phase values
    within [t-d,t+d] remain in that bin when a+d < t < b-d. The source
    phase model does NOT certify that this clock halfwidth is physical.
    """
    if (not math.isfinite(clock_halfwidth_s) or clock_halfwidth_s<0):
        raise ValueError("invalid timing halfwidth")
    first=first_complete_projected_turn(times,phase)
    if first is None:
        return {"state":"BOUNDED_NO_FIRST_COMPLETE_TURN",
                "all_bins_has_capture_window":False,
                "navigation_authorized":False,
                "source_timing_bound_authenticated":False}
    t,p=first
    windows=bin_occupancy_windows(t,p,bins)
    results={}
    for idx in range(bins):
        candidates=[]
        for left,right in windows[idx]:
            start=left+clock_halfwidth_s
            end=right-clock_halfwidth_s
            # Open interval. Zero duration cannot guarantee an observation.
            if end-start>1e-10:
                candidates.append((start,end,left,right))
        if candidates:
            # Prefer widest usable window; earliest ties, then lower bound.
            start,end,raw_left,raw_right=sorted(
                candidates,key=lambda x:(-(x[1]-x[0]),x[0]))[0]
            results[str(idx)]={
                "uninterrupted_admissible_window_s":end-start,
                "first_observable_s":float(start),
                "last_observable_s":float(end),
                "offline_GT_oracle_midpoint_s":float((start+end)/2),
                "original_phase_occupancy_duration_s":float(raw_right-raw_left),
                "source_disjoint_occupancy_interval_count":len(windows[idx]),
            }
    count=len(results)
    widths=[row["uninterrupted_admissible_window_s"] for row in results.values()]
    shortest=min(widths) if widths else 0.
    critical=min((max(b-a for a,b in windows[i])/2 if windows[i] else 0.
                  for i in range(bins)),default=0.)
    guarantee={str(rate):int(sum(
            row["uninterrupted_admissible_window_s"]>1/float(rate)
            for row in results.values())) for rate in rate_options}
    state=("MODEL_64_BIN_CAPTURE_WINDOWS_EXIST" if count==bins
           else "BOUNDED_MISSING_SOURCE_PHASE_WINDOWS")
    return {
        "state":state,
        "all_bins_has_capture_window":count==bins,
        "first_complete_turn_timestamp_s":float(t[-1]),
        "source_start_timestamp_s":float(t[0]),
        "source_first_turn_duration_s":float(t[-1]-t[0]),
        "declared_clock_halfwidth_s":clock_halfwidth_s,
        "phase_grammar_bins":bins,
        "bins_with_positive_clock_robust_window":count,
        "bins_without_clock_robust_window":[x for x in range(bins) if str(x) not in results],
        "longest_available_window_per_bin":results,
        "shortest_required_window_s":shortest,
        "hypothetical_source_window_clock_halfwidth_ceiling_s":critical,
        "cadence_hz_strictly_above_required_for_all_phase_offsets":(
            int(math.floor(1/shortest))+1 if count==bins and shortest>0 else None),
        "minimum_bins_guaranteed_at_uniform_rate_hz":guarantee,
        "timing_source_is_real_GT_piecewise_interpolated":True,
        "source_timing_bound_authenticated":False,
        "timestamp_locations_chosen_with_offline_GT_not_online_sensor":True,
        "no_camera_or_IMU_readings_acquired":True,
        "source_scene_columns_known":False,
        "navigation_authorized":False,
        "visual_recognition_verified":False,
        "physical_sampling_requirements_certified":False,
        "interpretation":"Offline continuous GT interpolation yields conditional time windows, not evidence camera observations exist at them",
    }


def evaluate_original(gt,halfwidth):
    t,p,_,delta=body_y_phase(gt)
    result=compile_observation_windows(t,p,halfwidth)
    result["independent_body_quaternion_agreement_rad"]=delta
    return result


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--gt-dir",type=Path,required=True)
    a.add_argument("--camera-calib",type=Path,required=True)
    a.add_argument("--imu-calib",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    args=a.parse_args()
    calib=admit_calibrations(args.camera_calib,args.imu_calib)
    nominal=abs(calib["camera_imu_nominal_shift_s"])
    out={"publisher":"NAIL-HNU/EvSLAM_Dataset",
         "upstream_source_revision":UPSTREAM_COMMIT,
         "source_git_blob_ids":SOURCE_BLOBS,
         "calibration_sha256":[calib["camera_calibration_original_sha256"],
                                calib["imu_calibration_original_sha256"]],
         "source_error_bound_authenticated":False,
         "hypothetical_halfwidth_source":"ABSOLUTE_VALUE_OF_NOMINAL_KALIBR_SHIFT_NOT_ERROR_BOUND",
         "no_camera_or_IMU_events_acquired":True,
         "original_author_raw_bags_blocked_by_quota":True,
         "not_online_navigation":True,
         "experiment":"NECESSITY_COMPILED_OFFLINE_SOURCE_PHASE_CAPTURE_WINDOWS",
         "sequences":{}}
    for name in SOURCE_BLOBS:
        gt=read_original_gt(args.gt_dir/(name+"_gt.txt"))
        data=evaluate_original(gt,nominal)
        series={str(s):evaluate_original(gt,s) for s in CLOCK_SCENARIOS_S}
        # avoid repeating 64 individual per-bin detailed rows in every scenario
        out["sequences"][name]={"nominal_hypothetical_sensitivity":data,
          "hypothetical_timing_sweep":{
            s:{k:v for k,v in d.items()
               if k not in ("longest_available_window_per_bin",)}
            for s,d in series.items()}}
        print("SOURCE_GT_CAPTURE_WINDOW_COMPILER",name,json.dumps({
          "state":data["state"],
          "conditional_bins":data["bins_with_positive_clock_robust_window"],
          "min_safe_window_ms":round(data["shortest_required_window_s"]*1000,4),
          "clock_halfwidth_ceiling_ms":round(data["hypothetical_source_window_clock_halfwidth_ceiling_s"]*1000,4),
          "uniform_rate_hz_strictly_above":data["cadence_hz_strictly_above_required_for_all_phase_offsets"],
          "bins_guaranteed_at_400hz":data["minimum_bins_guaranteed_at_uniform_rate_hz"]["400"],
          "bins_guaranteed_at_10hz":data["minimum_bins_guaranteed_at_uniform_rate_hz"]["10"],
        },sort_keys=True))
    args.out.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")


if __name__=="__main__":main()
