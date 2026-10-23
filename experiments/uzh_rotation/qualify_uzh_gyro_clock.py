"""Original UZH DAVIS camera gyroscope vs independent mocap timing diagnostic.

This is real sensor evidence on shapes_rotation (NOT 2 full revolutions).
Train-only choice of lag from original IMU and independent mocap motion;
second-half holdout frozen before evaluation. This DOES NOT certify a hard
physical clock error bound or a phase warrant for a different device.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

SOURCE_ARCHIVE_SHA = "56aade6bf53dcf73e8fe40905ccac8385cd7606bc9a85103bf2c9f9045117551"
IMU_SHA = "d209e3e203970f64efdb0ed28de900e4554a0ae0aedb9f7bb388cd528849bbd5"
GT_SHA = "bb62c320a51c1be412e17065eb86cfffa9041841290d439c23e447f1991aabdb"
CAM_SHA = "ab797c55a990c03656fbddac2473d3eace2a22f87fea4ca3b0497862b50545cd"
SOURCE_URL = "https://files.ifi.uzh.ch/rpg/datasets/davis/shapes_rotation.zip"
WINDOW_S = 0.100
MAX_LAG_S = 0.050
LAG_STEP_S = 0.001
PEAK_RUNNER_SEPARATION_S = 0.005
MIN_SPLIT_SAMPLES = 100


def source_sha(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as src:
        for block in iter(lambda:src.read(16*1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def read_sources(path):
    if source_sha(path)!=SOURCE_ARCHIVE_SHA:
        raise ValueError("original archive changed from independently admitted UZH source")
    with zipfile.ZipFile(path) as z:
        allfiles=[n for n in z.namelist() if not n.endswith("/")]
        arrays={}
        for name,expected_sha in [
            ("imu.txt",IMU_SHA),("groundtruth.txt",GT_SHA),("calib.txt",CAM_SHA)]:
            matches=[n for n in allfiles if n.split("/")[-1].lower()==name]
            if len(matches)!=1:
                raise ValueError("missing or duplicate original member "+name)
            raw=z.read(matches[0])
            if hashlib.sha256(raw).hexdigest()!=expected_sha:
                raise ValueError("original UZH member changed "+name)
            arrays[name]=np.loadtxt(io.BytesIO(raw),dtype=np.float64,ndmin=2)
    return arrays


def pearson(a,b):
    a=np.asarray(a,dtype=np.float64)
    b=np.asarray(b,dtype=np.float64)
    if (len(a)<MIN_SPLIT_SAMPLES or b.shape!=a.shape or
            not np.all(np.isfinite(a)) or not np.all(np.isfinite(b))):
        return None
    x=a-a.mean();y=b-b.mean()
    den=float(np.linalg.norm(x)*np.linalg.norm(y))
    return None if den<1e-12 else float((x@y)/den)


def evaluate(imu,gt):
    imu=np.asarray(imu,dtype=np.float64)
    gt=np.asarray(gt,dtype=np.float64)
    if (imu.ndim!=2 or imu.shape[1]!=7 or len(imu)<500 or
            gt.ndim!=2 or gt.shape[1]!=8 or len(gt)<200 or
            not np.isfinite(imu).all() or not np.isfinite(gt).all()):
        raise ValueError("source gyro/groundtruth schema or finite values invalid")
    ti=imu[:,0];tg=gt[:,0]
    if np.any(np.diff(ti)<=0) or np.any(np.diff(tg)<=0):
        raise ValueError("source header clock not strictly monotone")
    quats=gt[:,4:8]
    norms=np.linalg.norm(quats,axis=1)
    if np.any(np.abs(norms-1)>0.02):
        raise ValueError("mocap source quaternion norm unreliable")
    rotation=Rotation.from_quat(quats/norms[:,None])
    slerp=Slerp(tg,rotation)
    # Fixed 100ms window endpoints. The time origin is independent
    # of any source value, and the same intervals serve both baselines.
    left=max(float(ti[0]),float(tg[0]))+MAX_LAG_S+WINDOW_S
    right=min(float(ti[-1]),float(tg[-1]))-MAX_LAG_S-WINDOW_S
    if right-left<20:
        raise ValueError("insufficient overlapping source motion")
    start=math.ceil(left/WINDOW_S)*WINDOW_S
    endpoints=start+np.arange(int(math.floor((right-start)/WINDOW_S))+0,dtype=float)*WINDOW_S
    ends=endpoints+WINDOW_S
    if len(endpoints)<2*MIN_SPLIT_SAMPLES:
        raise ValueError("insufficient complete time windows")
    truth=(slerp(endpoints).inv()*slerp(ends)).magnitude()/WINDOW_S
    # Original IMU wx wy wz are in radians per second, per publisher.
    speed=np.linalg.norm(imu[:,4:7],axis=1)
    cumulative=np.r_[0.,np.cumsum((speed[1:]+speed[:-1])*np.diff(ti)*0.5)]
    def sampled_gyro(lag):
        return (np.interp(ends+lag,ti,cumulative)-
                np.interp(endpoints+lag,ti,cumulative))/WINDOW_S

    N=len(endpoints)
    train=np.arange(N//2)
    held=np.arange(N//2,N)
    lags=np.arange(-50,51,dtype=np.int64)*LAG_STEP_S
    valid=[]
    for lag in lags:
        a=sampled_gyro(float(lag))
        c=pearson(truth[train],a[train])
        if c is not None:
            valid.append((float(lag),c))
    if not valid:
        return {"status":"UNKNOWN_NO_IDENTIFIABLE_CLOCK",
                "imu_count":len(imu),"mocap_count":len(gt),
                "navigation_correction_authorized":False}
    valid.sort(key=lambda p:(-p[1],abs(p[0]),p[0]))
    chosen,top=valid[0]
    runner=next((x for x in valid[1:]
                if abs(x[0]-chosen)>PEAK_RUNNER_SEPARATION_S),None)
    spread=top-runner[1] if runner else None

    source_gyro=sampled_gyro(chosen)
    baseline=sampled_gyro(0.)
    train_res=np.abs(truth[train]-source_gyro[train])
    held_res=np.abs(truth[held]-source_gyro[held])
    zero_res=np.abs(truth[held]-baseline[held])
    frozen_train_max=float(np.max(train_res))
    h_corr=pearson(truth[held],source_gyro[held])
    h_zero=pearson(truth[held],baseline[held])
    evidence=(h_corr is not None and h_zero is not None and
              top>=0.65 and h_corr>=0.65 and
              h_corr-h_zero>=0.03 and spread is not None and spread>=0.02)
    state=("CANDIDATE_WITHIN_UZH_SOURCE_CLOCK_CONSISTENCY"
           if evidence else "UNKNOWN_SOURCE_CLOCK_NOT_IDENTIFIABLE_STRONGLY")
    def quantile(a):
        return {
            "median":float(np.median(a)),
            "p95":float(np.percentile(a,95)),
            "p99":float(np.percentile(a,99)),
            "maximum":float(np.max(a)),
        }
    return {
        "status":state,
        "imu_count":len(imu),"mocap_count":len(gt),
        "imu_median_sample_period_ms":float(np.median(np.diff(ti))*1000),
        "mocap_median_sample_period_ms":float(np.median(np.diff(tg))*1000),
        "original_duration_sec":float(min(ti[-1],tg[-1])-max(ti[0],tg[0])),
        "angular_speed_evaluation_method":"mocap geodesic SO3 100ms; raw gyro 3-axis integrated norm",
        "chronological_training_windows":len(train),
        "chronological_validation_windows":len(held),
        "candidate_lags_tested":len(valid),
        "lag_grid_milliseconds":[-50,50,1],
        "lag_sign":"sample gyro at mocap reference time + fitted lag",
        "frozen_training_selected_lag_ms":float(chosen*1000),
        "training_selected_lag_correlation":top,
        "training_runner_outside_5ms":None if runner is None else {
            "lag_ms":runner[0]*1000,"correlation":runner[1]},
        "train_peak_separation":spread,
        "training_zero_lag_correlation":pearson(truth[train],baseline[train]),
        "validation_selected_lag_correlation":h_corr,
        "validation_zero_lag_correlation":h_zero,
        "validation_selected_lag_magnitude_error_rad_s":quantile(held_res),
        "validation_zero_lag_magnitude_error_rad_s":quantile(zero_res),
        "training_selected_lag_magnitude_error_rad_s":quantile(train_res),
        "validation_cases_exceeding_train_max_magnitude_error":
            int(np.count_nonzero(held_res>frozen_train_max+1e-12)),
        "validation_exceedance_fraction":
            float(np.mean(held_res>frozen_train_max+1e-12)),
        "validation_influenced_training_choice":False,
        "mocap_truth_used_in_navigation_estimator":False,
        "camera_event_samples_processed":False,
        "this_source_qualifies_continuous_two_turns":False,
        "timing_bound_independently_certified":False,
        "gyro_orientation_phase_bound_certified":False,
        "physical_sensor_error_bound":"UNKNOWN",
        "other_device_transfer":"NOT_ESTABLISHED",
        "heading_correction_authorized":False,
        "calibration_model_limit":"source real gyro vs mocap uses only scalar speed magnitude; no gyro bias, extrinsic phase, between-sample dynamics or physical clock jitter bound",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--zip",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    data=read_sources(args.zip)
    result=evaluate(data["imu.txt"],data["groundtruth.txt"])
    report={"source_original_archive_sha256":SOURCE_ARCHIVE_SHA,
            "source_url":SOURCE_URL,
            "source_original_imu_sha256":IMU_SHA,
            "source_original_gt_sha256":GT_SHA,
            "source_calibration_sha256":CAM_SHA,
            "experiment":"real sensor clock-vs-independent-mocap qualification, not compass",
            "result":result}
    args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("UZH_REAL_GYRO_VS_MOCAP_CLOCK",json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()
