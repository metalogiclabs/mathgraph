"""EvSLAM original-source camera/IMU time-shift sensitivity to first-turn binning.

This is OFFLINE reference-motion sensitivity using piecewise-linear body-Y
phase interpolation at publisher 10Hz pose times, not real camera event
timestamps or an independently certified timing-error interval.

A nominal Kalibr timeshift is NOT a physical uncertainty guarantee. The
hypothetical +/- |timeshift_cam_imu| scenario tests firstturn phase-bin
fragility only. Do not claim sensor safety or navigation correction.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
import yaml

from evslam_reference_turns import (
    SOURCE_BLOBS,UPSTREAM_COMMIT,independent_rotvecs,read_original_gt,
)

CALIB_SHA256 = "2aee1692299ae519251e921c087503263e187a3e79cf6c341a31b97bd87a2b72"
IMU_SHA256 = "561da3630bce3f7dfd27b7ad134441f5053abaccadfa9cb89771ae8493ac051a"
CALIB_ORIGINAL_DRIVE_ID = "1ZeQokirC1dyB9is8bmm8gCKejxv2V7rD"
IMU_ORIGINAL_DRIVE_ID = "16XWYmUw6NPwe9jD_r5nUKnS4N-0uwJdQ"
TWO_PI = 2*math.pi
BINS = 64
TICKS = 1024


def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def admit_calibrations(cam_path,imu_path):
    if sha256_file(cam_path)!=CALIB_SHA256:
        raise ValueError("original publisher camera calibration SHA256 mismatch")
    if sha256_file(imu_path)!=IMU_SHA256:
        raise ValueError("original publisher IMU calibration SHA256 mismatch")
    with Path(cam_path).open() as f: camera=yaml.safe_load(f)
    with Path(imu_path).open() as f: imu=yaml.safe_load(f)
    cam=camera["cam0"]
    ins=cam["intrinsics"]
    if (cam.get("camera_model")!="pinhole" or
        cam.get("resolution")!=[640,480] or
        len(ins)!=4 or abs(ins[0]-431.7934202019396)>1e-9 or
        not np.all(np.isfinite(ins))):
        raise ValueError("unexpected source camera geometry")
    shift=float(cam["timeshift_cam_imu"])
    if (not math.isfinite(shift) or
        abs(shift-(-0.0025859877860685437))>1e-12):
        raise ValueError("unexpected nominal camera-to-IMU shift")
    tci=np.asarray(cam["T_cam_imu"],dtype=float)
    if tci.shape!=(4,4) or not np.all(np.isfinite(tci)):
        raise ValueError("invalid source camera extrinsics")
    R=tci[:3,:3]
    if (np.max(np.abs(R.T@R-np.eye(3)))>1e-3 or
        abs(np.linalg.det(R)-1)>1e-3):
        raise ValueError("nonrigid camera-to-IMU transform")
    raw_imu=imu["imu0"]
    if (raw_imu.get("rostopic")!="/dvxplorer_left/imu" or
        float(raw_imu.get("update_rate",0))!=400):
        raise ValueError("unexpected source IMU settings")
    return {
        "camera_calibration_original_sha256":CALIB_SHA256,
        "imu_calibration_original_sha256":IMU_SHA256,
        "camera_intrinsics":list(ins),
        "camera_resolution":cam["resolution"],
        "camera_imu_nominal_shift_s":shift,
        "sensitivity_halfwidth_s":abs(shift),
        "camera_imu_extrinsics":tci.tolist(),
        "camera_pixel_column_from_intrinsics":320,
        "gyroscope_nominal_update_hz":400,
        "gyroscope_noise_density_rad_per_s_sqrt_hz":float(raw_imu["gyroscope_noise_density"]),
        "nominal_shift_is_verified_error_bound":False,
        "camera_to_reference_pose_frame_confirmed":False,
        "camera_event_timestamps_acquired":False,
    }


def body_y_phase(gt):
    gt=np.asarray(gt,dtype=float)
    if gt.ndim!=2 or gt.shape[1]!=11 or len(gt)<20:
        raise ValueError("invalid source GT matrix")
    t=gt[:,0]
    q=gt[:,4:8]
    if not np.isfinite(gt).all() or np.any(np.diff(t)<=0):
        raise ValueError("invalid source GT chronology")
    if np.max(np.abs(np.linalg.norm(q,axis=1)-1))>1e-3:
        raise ValueError("source quaternion norm invalid")
    R=Rotation.from_quat(q/np.linalg.norm(q,axis=1)[:,None])
    scipy=(R[:-1].inv()*R[1:]).as_rotvec()
    manual=independent_rotvecs(q)
    discrepancy=float(np.max(np.linalg.norm(scipy-manual,axis=1)))
    if discrepancy>1e-8:
        raise ValueError("independent body-frame quaternion method disagrees")
    sign=1 if scipy[:,1].sum()>=0 else -1
    phase=np.r_[0.,np.cumsum(sign*scipy[:,1])]
    return t,phase,scipy,discrepancy


def interval_membership(t,phase,center,halfwidth):
    """All knots inside the hypothetical time interval also count."""
    left=center-halfwidth
    right=center+halfwidth
    if left<t[0] or right>t[-1]:
        return None
    mask=(t>left)&(t<right)
    values=np.r_[np.interp(left,t,phase), phase[mask], np.interp(right,t,phase)]
    return float(np.min(values)),float(np.max(values))


def tick_guard(phase,halfwidth_ticks):
    """Mirrors C99 adapter acceptance rule, not a separate oracle proof."""
    if halfwidth_ticks>=8:
        return False
    estimate=int(math.floor((phase % TWO_PI)/TWO_PI*TICKS))%TICKS
    low=(estimate-halfwidth_ticks)%TICKS
    high=(estimate+halfwidth_ticks)%TICKS
    return low//16==high//16


def sensitivity(gt,halfwidth,fx=431.7934202019396):
    t,phase,delta,independent_error=body_y_phase(gt)
    if not 0<=halfwidth<.08 or not math.isfinite(halfwidth):
        raise ValueError("invalid declared hypothetical halfwidth")
    steps=np.diff(t)
    rates=np.abs(delta[:,1]/steps)
    shift_deg=np.degrees(rates*halfwidth)
    shift_pixels=fx*np.tan(rates*halfwidth)
    shifts_ticks=rates*halfwidth*TICKS/TWO_PI
    first=[]
    refused=plus=minus=guardref=accepted=0
    bins_nominal=set()
    bins_guard=set()
    example=[]
    for i,time in enumerate(t):
        if not 0<=phase[i]<TWO_PI:
            continue
        limits=interval_membership(t,phase,float(time),halfwidth)
        if limits is None:
            continue
        lo,hi=limits
        if lo<0 or hi>=TWO_PI:  # first-turn-only qualification
            continue
        nominal=int(math.floor(phase[i]*BINS/TWO_PI))
        minbin=int(math.floor(lo*BINS/TWO_PI))
        maxbin=int(math.floor(hi*BINS/TWO_PI))
        bins_nominal.add(nominal)
        first.append(i)
        if minbin!=maxbin:
            refused+=1
            if len(example)<12:
                example.append({"t_s":float(time),"nominal_bin":nominal,
                                "earliest_bin":minbin,"latest_bin":maxbin})
        if minbin!=nominal:minus+=1
        if maxbin!=nominal:plus+=1
        radius=int(math.ceil(max(abs(lo-phase[i]),abs(hi-phase[i]))*TICKS/TWO_PI))+1
        good=tick_guard(phase[i],radius)
        if not good:guardref+=1
        else:
            accepted+=1
            bins_guard.add(nominal)
            # Model-conditional negative check. This is not measured fidelity.
            if minbin!=nominal or maxbin!=nominal:
                raise AssertionError("C-compatible tick guard admitted bin crossing")
    def quantiles(a):
        return {
            "p50":float(np.percentile(a,50)),
            "p90":float(np.percentile(a,90)),
            "max":float(np.max(a)),
        }
    return {
        "pose_samples":int(len(t)),
        "pose_interval_count":int(len(steps)),
        "original_pose_duration_s":float(t[-1]-t[0]),
        "independent_relative_rotvec_max_disagreement_rad":independent_error,
        "body_y_projected_signed_turns":float(abs(phase[-1])/TWO_PI),
        "absolute_projected_y_rate_rad_per_s":quantiles(rates),
        "hypothetical_clock_offset_shift_deg":quantiles(shift_deg),
        "ideal_pinhole_horizontal_pixel_equivalent_at_center":quantiles(shift_pixels),
        "hypothetical_phase_ticks_per_1024_turn":quantiles(shifts_ticks),
        "first_turn_source_pose_samples_with_two_sided_support":len(first),
        "first_turn_nominal_64bin_coverage_at_gt_10hz":len(bins_nominal),
        "first_turn_two_sided_time_interval_crosses_angular_bin":refused,
        "first_turn_negative_time_offset_bin_mismatches":minus,
        "first_turn_positive_time_offset_bin_mismatches":plus,
        "C99_compatible_conservative_tick_guard_refusals":guardref,
        "C99_compatible_conservative_tick_guard_accepted":accepted,
        "C99_compatible_accepted_gt_bin_coverage":len(bins_guard),
        "crossing_cases":example,
        "not_a_calibrated_angle_error_bound":True,
        "not_actual_camera_event_samples":True,
        "firstturn_c_guard_source_unchanged":True,
        "navigation_correction_authorized":False,
        "interpretation":"piecewise-linear 10Hz reference pose model with hypothetical +/- nominal timing shift, not measured sensor error",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-dir",type=Path,required=True)
    p.add_argument("--calib",type=Path,required=True)
    p.add_argument("--imu-calib",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    calib=admit_calibrations(args.calib,args.imu_calib)
    result={
        "publisher":"NAIL-HNU/EvSLAM_Dataset",
        "pinned_publisher_revision":UPSTREAM_COMMIT,
        "source_blob_ids":SOURCE_BLOBS,
        "calibration":calib,
        "interpretation":"nominal calibration offset used as hypothetical signed sensitivity range only",
        "camera_event_and_gyro_sources":"NOT_ACQUIRED",
        "experiment":"FIRSTTURN_POSE_CLOCK_SENSITIVITY",
        "trajectories":{},
    }
    for name in SOURCE_BLOBS:
        gt=read_original_gt(args.source_dir/(name+"_gt.txt"))
        result["trajectories"][name]=sensitivity(gt,calib["sensitivity_halfwidth_s"],calib["camera_intrinsics"][0])
        s=result["trajectories"][name]
        print("EVSLAM_CLOCK_SENSITIVITY",name,json.dumps({
            "max_phase_shift_deg":s["hypothetical_clock_offset_shift_deg"]["max"],
            "max_center_pixel_equivalent":s["ideal_pinhole_horizontal_pixel_equivalent_at_center"]["max"],
            "gt_first_turn_samples":s["first_turn_source_pose_samples_with_two_sided_support"],
            "interval_bin_crossings":s["first_turn_two_sided_time_interval_crosses_angular_bin"],
            "source_pose_guard_refusals":s["C99_compatible_conservative_tick_guard_refusals"],
        },sort_keys=True))
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")


if __name__=="__main__":
    main()
