"""Source-pinned EFRD lab1 independent mocap rotation qualification.

This is DATASET ADMISSION ONLY. The external reference is never an estimator
input. The reference frame world Z is fixed before viewing lab1 poses; no
post-hoc optimization of the best axis is permitted.
"""
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

ORIGINAL_SHA256="2fac73513203739df46fb085a4e67f8f41e7c2aa9ebfdd115d97b34a9929e484"

def digest(path):
    d=hashlib.sha256()
    with Path(path).open("rb") as f:
        for data in iter(lambda:f.read(16*1024*1024),b""):d.update(data)
    return d.hexdigest()

def quantify(stamps, q_xyzw, xyz, jitter_deg=.2):
    t=np.asarray(stamps,dtype=np.int64)
    q=np.asarray(q_xyzw,dtype=np.float64)
    p=np.asarray(xyz,dtype=np.float64)
    if t.ndim!=1 or len(t)<10 or q.shape!=(len(t),4) or p.shape!=(len(t),3):
        raise ValueError("invalid mocap pose shape")
    if not np.isfinite(q).all() or not np.isfinite(p).all():
        raise ValueError("nonfinite mocap position or quaternion")
    if np.any(np.diff(t)<=0):
        raise ValueError("duplicate/reversed source pose timestamps")
    norms=np.linalg.norm(q,axis=1)
    if np.any(abs(norms-1)>.05) or np.any(norms<1e-6):
        raise ValueError("source quaternion norm outside declared tolerance")
    rot=Rotation.from_quat(q/norms[:,None])
    mat=rot.as_matrix()
    yaw=np.unwrap(np.arctan2(mat[:,1,0],mat[:,0,0]))
    # Independent SciPy Euler extractor must agree except at gimbal.
    pitch=-np.arcsin(np.clip(mat[:,2,0],-1,1))
    gimbal=bool(np.any(abs(np.cos(pitch))<.05))
    euler=np.unwrap(rot.as_euler("ZYX",degrees=False)[:,0])
    if not gimbal and np.max(abs(yaw-euler))>1e-5:
        raise ValueError("independent yaw parameterizations disagree")
    increments=(rot[:-1].inv()*rot[1:]).magnitude()
    alias=bool(np.max(increments)>=math.pi/2)
    signs=np.diff(yaw)
    tol=math.radians(jitter_deg)
    longest=0.
    streak=0.
    prev=0
    reversals=0
    for d in signs:
        if abs(d)<=tol:continue
        direction=1 if d>0 else -1
        if prev and direction!=prev:
            longest=max(longest,abs(streak))
            streak=0.
            reversals+=1
        prev=direction
        streak+=float(d)
    longest=max(longest,abs(streak))
    translation_steps=np.linalg.norm(np.diff(p,axis=0),axis=1)
    return {
        "source_pose_count":int(len(t)),
        "duration_by_source_header_sec":float((int(t[-1])-int(t[0]))*1e-9),
        "world_z_yaw_excursion_turns":float(np.ptp(yaw)/(2*math.pi)),
        "world_z_net_yaw_turns":float((yaw[-1]-yaw[0])/(2*math.pi)),
        "world_z_longest_directional_yaw_turns":float(longest/(2*math.pi)),
        "independently_derived_yaw_max_disagreement_rad":float(np.max(abs(yaw-euler))),
        "total_3d_rotation_travel_turns":float(increments.sum()/(2*math.pi)),
        "directional_yaw_reversals":reversals,
        "max_pose_step_3d_deg":float(np.degrees(increments.max())),
        "median_source_pose_spacing_ms":float(np.median(np.diff(t))*1e-6),
        "max_translation_relative_start_m":float(np.max(np.linalg.norm(p-p[0],axis=1))),
        "translation_path_m":float(translation_steps.sum()),
        "near_world_z_yaw_gimbal":gimbal,
        "interpose_rotation_sampling_alias":alias,
        "world_z_two_turn_pose_qualification":bool(
            not gimbal and not alias and longest>=4*math.pi and
            np.ptp(yaw)>=4*math.pi),
        "source_axis":"world_Z, predeclared; physical drone/camera spin axis not authenticated",
        "estimator_saw_source_truth":False,
        "camera_gyro_time_alignment_verified":False,
        "heading_correction_permitted":False,
    }


def replay(path):
    from rosbags.highlevel import AnyReader
    source_sha=digest(path)
    if source_sha!=ORIGINAL_SHA256:
        raise ValueError("source bag hash mismatch")
    result={"original_bag_sha256":source_sha,
            "original_bag_bytes":Path(path).stat().st_size,
            "mocap_source_topic":"/vrpn_client_node/Rigid0/pose",
            "source_is_external_mocap":True,
            "source_pose_state":"UNKNOWN",
            "source_camera_imu_synchronization":"UNKNOWN",
            "scientific_result":"DATASET_MOTION_QUALIFICATION_ONLY",
            "navigation_correction_permitted":False,
            "lab2_unopened":True}
    with AnyReader([Path(path)]) as reader:
        con=[c for c in reader.connections if c.topic==result["mocap_source_topic"]
             and "PoseStamped" in c.msgtype]
        if len(con)!=1: 
            result["source_pose_state"]="UNKNOWN_NO_UNIQUE_EXTERNAL_POSE_STREAM"
            return result
        timestamps=[];quaternions=[];locations=[];receipts=[]
        for c,stamp,raw in reader.messages(connections=con):
            msg=reader.deserialize(raw,c.msgtype)
            h=msg.header.stamp
            if not 0<=int(h.nanosec)<10**9:
                result["source_pose_state"]="INVALID_HEADER_NANOSECONDS"
                return result
            timestamps.append(int(h.sec)*10**9+int(h.nanosec))
            receipts.append(int(stamp))
            x=msg.pose.orientation;y=msg.pose.position
            quaternions.append((x.x,x.y,x.z,x.w))
            locations.append((y.x,y.y,y.z))
    result["pose_messages_read"]=len(timestamps)
    result["header_receipt_equal_fraction"]=float(np.mean(np.array(
        timestamps,dtype=np.int64)==np.array(receipts,dtype=np.int64)))
    result["source_header_duplicate_count"]=int(np.sum(np.diff(timestamps)==0))
    result["source_header_reversal_count"]=int(np.sum(np.diff(timestamps)<0))
    try:
        metrics=quantify(timestamps,quaternions,locations)
        result["mocap_metrics"]=metrics
        result["source_pose_state"]=(
            "CANDIDATE_TWO_TURN_WORLD_Z_SOURCE_ONLY"
            if metrics["world_z_two_turn_pose_qualification"]
            else "REJECTED_FOR_PREDECLARED_TWO_TURN_WORLD_Z")
    except (ValueError,RuntimeError) as exc:
        result["source_pose_state"]="UNKNOWN_INVALID_MOCAP_TRAJECTORY"
        result["source_pose_error"]=str(exc)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bag",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    report=replay(a.bag)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("EFRD_INDEPENDENT_POSE_QUALIFICATION",json.dumps(report,sort_keys=True))
if __name__=="__main__":main()
