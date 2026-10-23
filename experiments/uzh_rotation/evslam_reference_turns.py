"""EvSLAM source-authentic drone turn qualification, evaluation poses only.

This script inspects published independent-reference QUATERNIONS to qualify
a dataset, never feeds them to a visual estimator or confidence decision.
All three sensor/body axes are evaluated and reported; no axis is selected
or optimized after seeing validation scores. It is an exposed real-data
qualification, NOT an unseen-navigation holdout.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

UPSTREAM = "https://github.com/NAIL-HNU/EvSLAM_Dataset"
UPSTREAM_COMMIT = "f116a9fe305f3ad8b1a379e1bb52becfc87654dc"
SOURCE_BLOBS = {
    "drone_rot_norm": {
        "gt": "809d83df4063376d0ee50f62095131e1d8940c00",
        "ref": "34a8c16d23a4418a0f206fe615898276bc61008d",
        "raw_bag_drive_id": "1NNUZgkzpyR321AFeI1j5Uv2DKV8E_W3u",
    },
    "drone_rot_fast": {
        "gt": "47a1bd5b54c0843d2535af42ebff0529950a5a6f",
        "ref": "b6c74a7e9167cf8750bc3f33b277b23a76181f21",
        "raw_bag_drive_id": "1t4viDrRV40_uOS3Tfh9-jMbGKgHorTI1",
    },
}
MIN_TWO_TURNS = 2.0
MAX_SAMPLE_STEP_RAD = math.pi/2
JITTER_RAD = math.radians(.2)
MIN_AXIS_ABS_ALIGNMENT = 0.90


def _manual_product(a,b):
    x,y,z,w=a
    X,Y,Z,W=b
    return np.array([w*X+x*W+y*Z-z*Y,
                     w*Y-x*Z+y*W+z*X,
                     w*Z+x*Y-y*X+z*W,
                     w*W-x*X-y*Y-z*Z],dtype=float)


def independent_rotvecs(q):
    """Manually compute q_previous.inverse * q_next for each sample."""
    data=np.asarray(q,dtype=float)
    result=np.empty((len(data)-1,3),dtype=float)
    for i in range(len(data)-1):
        a=data[i];b=data[i+1]
        denom=float(a@a)
        inv=np.array([-a[0],-a[1],-a[2],a[3]])/denom
        dq=_manual_product(inv,b)
        dq/=np.linalg.norm(dq)
        if dq[3]<0:
            dq=-dq
        norm=float(np.linalg.norm(dq[:3]))
        angle=2*math.atan2(norm,float(dq[3]))
        result[i]=dq[:3]*(angle/norm) if norm>1e-12 else [0,0,0]
    return result


def longest_directional(steps, threshold_rad=JITTER_RAD):
    best=run=0.
    direction=0
    reversals=0
    for d in steps:
        if abs(float(d))<=threshold_rad:
            continue
        newdir=1 if d>0 else -1
        if direction and newdir!=direction:
            best=max(best,abs(run))
            run=0.
            reversals+=1
        direction=newdir
        run+=float(d)
    return {"longest_turns":max(best,abs(run))/(2*math.pi),
            "reversals":reversals,
            "net_turns":float(np.sum(steps))/(2*math.pi),
            "total_abs_projection_turns":float(np.sum(np.abs(steps)))/(2*math.pi)}


def turn_crossing_time(times,projected_steps):
    """Evaluation-only first gyro-independent full reference turn crossing."""
    accum=0.
    trend=0
    streak_start=0
    crossing=None
    turns=[]
    for i,d in enumerate(projected_steps):
        if abs(float(d))<=JITTER_RAD:
            continue
        sign=1 if d>0 else -1
        if trend and sign!=trend:
            accum=0.
            streak_start=i
        trend=sign
        before=abs(accum)
        accum+=float(d)
        after=abs(accum)
        if int(math.floor(after/(2*math.pi)))>int(math.floor(before/(2*math.pi))):
            target=(int(math.floor(before/(2*math.pi)))+1)*2*math.pi
            frac=min(max((target-before)/(after-before),0.),1.)
            turns.append(float(times[i]+frac*(times[i+1]-times[i])))
    return turns


def read_original_gt(path):
    gt=np.loadtxt(path,dtype=float,ndmin=2)
    if gt.ndim!=2 or gt.shape[1]!=11 or len(gt)<20 or not np.isfinite(gt).all():
        raise ValueError("Expected source GT Nx11 finite rows")
    if not np.all(np.diff(gt[:,0])>0):
        raise ValueError("GT source timestamp is not strictly increasing")
    q=gt[:,4:8]
    if np.any(np.abs(np.linalg.norm(q,axis=1)-1)>0.001):
        raise ValueError("GT quaternion norm not supported")
    return gt


def analyze(gt,reference_times,sequence):
    if sequence not in SOURCE_BLOBS:
        raise ValueError("source sequence not preregistered")
    gt=np.asarray(gt,dtype=float)
    if (gt.ndim!=2 or gt.shape[1]!=11 or len(gt)<20 or
            not np.isfinite(gt).all() or
            not np.all(np.diff(gt[:,0])>0)):
        raise ValueError("source trajectory invalid")
    q=gt[:,4:8]
    norms=np.linalg.norm(q,axis=1)
    if np.any(abs(norms-1)>0.001):
        raise ValueError("source quaternion invalid")
    pose=Rotation.from_quat(q/norms[:,None])
    relative=pose[:-1].inv()*pose[1:]
    scipy_steps=relative.as_rotvec()
    manual_steps=independent_rotvecs(q)
    difference=float(np.max(np.linalg.norm(manual_steps-scipy_steps,axis=1)))
    if difference>1e-8:
        raise AssertionError("Independent quaternion relative rotations disagree")
    mag=np.linalg.norm(scipy_steps,axis=1)
    dt=np.diff(gt[:,0])
    spacing_max=float(dt.max())
    alias=bool(np.any(mag>=MAX_SAMPLE_STEP_RAD) or spacing_max>0.25)
    reference_times=np.asarray(reference_times,dtype=float)
    if (reference_times.ndim!=1 or not np.isfinite(reference_times).all() or
            not np.all(np.diff(reference_times)>0)):
        raise ValueError("invalid source reference timestamps")
    # Match only timestamp ID, not pose values; no GT enters an estimator.
    nearest=np.searchsorted(reference_times,gt[:,0],side="left")
    nearest=np.clip(nearest,0,len(reference_times)-1)
    prev=np.clip(nearest-1,0,len(reference_times)-1)
    dist=np.minimum(abs(reference_times[nearest]-gt[:,0]),
                    abs(reference_times[prev]-gt[:,0]))
    matched=int(np.count_nonzero(dist<=.001))
    path=float(mag.sum())
    axes={}
    for axis,name in enumerate("xyz"):
        l=longest_directional(scipy_steps[:,axis])
        frac=float(np.abs(scipy_steps[:,axis]).sum()/max(path,1e-15))
        l["fraction_of_3d_path_aligned_with_axis"]=frac
        l["reference_turn_boundary_times_s"]=turn_crossing_time(gt[:,0],scipy_steps[:,axis])
        l["qualified_2_turns_in_recorded_pose_model"]=bool(
            l["longest_turns"]>=MIN_TWO_TURNS and
            frac>=MIN_AXIS_ABS_ALIGNMENT and not alias)
        axes[name]=l
    position=gt[:,1:4]
    translate=np.linalg.norm(np.diff(position,axis=0),axis=1)
    return {
        "source_sequence":sequence,
        "source_type":"Published evaluation ground truth, with MoCap described by authors",
        "source_git_revision":UPSTREAM_COMMIT,
        "gt_samples":int(len(gt)),
        "reference_timestamp_samples":int(len(reference_times)),
        "reference_pose_timestamps_matched_1ms":matched,
        "ref_pose_alignment_fraction":matched/len(gt),
        "original_time_start_s":float(gt[0,0]),
        "original_time_end_s":float(gt[-1,0]),
        "duration_s":float(gt[-1,0]-gt[0,0]),
        "largest_pose_dt_s":spacing_max,
        "largest_3d_step_degrees":float(np.degrees(mag.max())),
        "total_3d_rotation_travel_turns":path/(2*math.pi),
        "independent_quaternion_derivations_max_rad_difference":difference,
        "axis_results":axes,
        "longest_projected_yaw_body_y_turns":axes["y"]["longest_turns"],
        "max_translation_from_start_m":float(np.max(np.linalg.norm(position-position[0],axis=1))),
        "translation_path_m":float(translate.sum()),
        "source_pairwise_sampling_admissible":not alias,
        "recorded_body_y_2plus_revolutions_candidate":axes["y"]["qualified_2_turns_in_recorded_pose_model"],
        "insufficient_revolution_count_for_navigation":"UNKNOWN; gyro and camera not checked",
        "physical_camera_to_body_axis_calibrated":False,
        "camera_imu_temporal_alignment_verified":False,
        "unseen_motion_between_100ms_pose_samples_bounded":False,
        "first_revolution_visual_map_built":False,
        "later_turn_camera_recognition_tested":False,
        "navigation_correction_permitted":False,
        "epistemic_state":"CANDIDATE_TRAJECTORY_QUALIFIED_ONLY",
        "source_limit":"3D translation and visibility may change; pose qualification is not repeatable appearance",
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-dir",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    out={"source_repo":UPSTREAM,"source_revision":UPSTREAM_COMMIT,
         "verified_blob_identities":SOURCE_BLOBS,
         "method":"body quaternion relative log; independent SciPy vs manual SO3; all xyz axes reported",
         "scope":"source trajectory admission; no raw camera/IMU decoded",
         "qualifications":{}}
    for sequence in SOURCE_BLOBS:
        gt=read_original_gt(args.source_dir/f"{sequence}_gt.txt")
        ref=np.loadtxt(args.source_dir/f"{sequence}_ref_time.txt",ndmin=1)
        out["qualifications"][sequence]=analyze(gt,ref,sequence)
        res=out["qualifications"][sequence]
        print("EVSLAM_ROTATION_REFERENCE",sequence,json.dumps({
            "samples":res["gt_samples"],
            "continuous_body_y_turns":res["longest_projected_yaw_body_y_turns"],
            "total_3d_turns":res["total_3d_rotation_travel_turns"],
            "axis_y_alignment":res["axis_results"]["y"]["fraction_of_3d_path_aligned_with_axis"],
            "qualified_reference_candidate":res["recorded_body_y_2plus_revolutions_candidate"],
            "translation_m":res["translation_path_m"],
        },sort_keys=True))
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")


if __name__=="__main__":
    main()
