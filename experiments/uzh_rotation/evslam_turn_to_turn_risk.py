"""EvSLAM repeated-heading parallax and view-drift risk from published poses.

Only offline dataset suitability. No camera descriptors or gyro-based heading
estimator are used, and no phase/time alignment is exposed to navigation
code. The datasets were already inspected: retrospective, not blind.
"""
import argparse,json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from evslam_reference_turns import (
    SOURCE_BLOBS,UPSTREAM_COMMIT,independent_rotvecs,read_original_gt,
)

TWO_PI=2*math.pi
PHASE_BINS=16
MIN_MATCHES_PER_COMPLETE_LATER_TURN=8


def pose_at_phase(phase,poses,quaternions,target):
    """First increasing crossing only; no monotone-clipping of reversals."""
    eligible=np.flatnonzero((phase[:-1]<=target) & (phase[1:]>=target) &
                             (phase[1:]>phase[:-1]))
    if not len(eligible):
        return None
    i=int(eligible[0])
    f=float((target-phase[i])/(phase[i+1]-phase[i]))
    position=(1-f)*poses[i]+f*poses[i+1]
    a=np.asarray(quaternions[i],dtype=float)
    b=np.asarray(quaternions[i+1],dtype=float)
    a=a/np.linalg.norm(a)
    b=b/np.linalg.norm(b)
    cos=float(np.dot(a,b))
    if cos<0:
        cos=-cos
        b=-b
    cos=np.clip(cos,-1,1)
    if cos>.999999:
        interp=(1-f)*a+f*b
        interp=interp/np.linalg.norm(interp)
    else:
        omega=math.acos(cos)
        interp=(a*math.sin((1-f)*omega)+b*math.sin(f*omega))/math.sin(omega)
    return (position, Rotation.from_quat(interp), float(f))


def measure_pose_revisit(gt,phase_bins=PHASE_BINS):
    g=np.asarray(gt,dtype=float)
    if g.ndim!=2 or g.shape[1]!=11 or len(g)<30:
        raise ValueError("invalid source pose data")
    times=g[:,0]
    if np.any(np.diff(times)<=0):
        raise ValueError("non-increasing source GT time")
    q=g[:,4:8]
    if np.max(np.abs(np.linalg.norm(q,axis=1)-1))>1e-3:
        raise ValueError("invalid orientation norm")
    rotvec=independent_rotvecs(q)
    # Body-Y source projection; this is not a certified physical gyro angle.
    sign=1 if np.sum(rotvec[:,1])>=0 else -1
    phase=np.r_[0.,np.cumsum(sign*rotvec[:,1])]
    if phase_bins<4 or phase_bins>64:
        raise ValueError("unsupported finite angular grammar")
    total=float(phase[-1]/TWO_PI)
    complete=int(math.floor(float(np.max(phase))/TWO_PI + 1e-8))
    p=g[:,1:4]
    matches=[]
    for turn in range(1,max(complete,1)):
        dists=[];angles=[];delay=[];n=0
        for b in range(phase_bins):
            unit=b/phase_bins
            initial=pose_at_phase(phase,p,q,unit*TWO_PI)
            later=pose_at_phase(phase,p,q,(turn+unit)*TWO_PI)
            if initial is None or later is None:
                continue
            pos1,rot1,_=initial
            pos2,rot2,_=later
            # Physical displacement between nominal same-phase positions.
            dists.append(float(np.linalg.norm(pos2-pos1)))
            angles.append(float(np.degrees((rot1.inv()*rot2).magnitude())))
            n+=1
        if n>=MIN_MATCHES_PER_COMPLETE_LATER_TURN:
            matches.append({
                "later_turn_index":turn,
                "phase_bins_compared":n,
                "distance_median_m":float(np.median(dists)),
                "distance_p90_m":float(np.percentile(dists,90)),
                "distance_max_m":float(np.max(dists)),
                "orientation_difference_median_deg":float(np.median(angles)),
                "orientation_difference_p90_deg":float(np.percentile(angles,90)),
                "orientation_difference_max_deg":float(np.max(angles)),
            })
    return {
        "body_y_projected_net_turns":total,
        "body_y_projected_max_turns":float(np.max(phase)/TWO_PI),
        "projected_phase_has_reversals":bool(np.any(np.diff(phase)<0)),
        "phase_bins_per_revolution":phase_bins,
        "initial_reference_turn":0,
        "later_full_turns_measured":len(matches),
        "per_turn_later":matches,
        "visual_scene_stationarity_verified":False,
        "camera_field_of_view_overlap_verified":False,
        "independent_camera_to_drone_extrinsics_verified":False,
        "pose_is_not_single_column_sensor_observation":True,
        "no_camera_or_imu_samples_read":True,
        "navigation_correction_authorized":False,
        "status":"RETROSPECTIVE_REFERENCE_ONLY; not a visual-compass benchmark",
        "scope":"matched projected body-Y phase, not full scene correspondence",
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-dir",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    result={
        "publisher":"NAIL-HNU/EvSLAM_Dataset",
        "pinned_source_commit":UPSTREAM_COMMIT,
        "source_blobs":SOURCE_BLOBS,
        "source_access_obstructions":[
            "drone_rot_norm original raw bag Drive quota at Actions 39934255115",
            "drone_rot_fast original raw bag Drive quota at Actions 39934784749",
        ],
        "analyses":{},
        "evaluation_only":True,
    }
    for name in SOURCE_BLOBS:
        data=read_original_gt(args.source_dir/f"{name}_gt.txt")
        measurement=measure_pose_revisit(data)
        result["analyses"][name]=measurement
        print("EVSLAM_REVISIT_SCENE_RISK",name,json.dumps(measurement,sort_keys=True))
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")

if __name__=="__main__":
    main()
