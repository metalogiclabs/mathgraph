"""Source-qualify original UZH DAVIS shapes_rotation for genuinely repeated turns.

Read ONLY groundtruth.txt and archive directory metadata from original 150MB
text archive, never event/IMU bytes. First dataset qualification; fixed 20Hz
nearest-original-pose subsampling avoids treating 200Hz sensor jitter as a
direction reversal. All x/y/z body-coordinate axes evaluated, none selected
by visual outcome. No navigation correction is possible in this stage.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import zipfile

import numpy as np
from scipy.spatial.transform import Rotation

from evslam_reference_turns import independent_rotvecs

URL="https://files.ifi.uzh.ch/rpg/datasets/davis/shapes_rotation.zip"
SAMPLE_PERIOD_S=.05
REVERSAL_THRESHOLD_RAD=math.radians(.2)
TWO_PI=2*math.pi


def check_archive_members(archive):
    files=[]
    for file in archive.infolist():
        p=PurePosixPath(file.filename)
        if (p.is_absolute() or ".." in p.parts or "\\" in file.filename or
                file.filename.startswith("/")):
            raise ValueError("unsafe original archive member path")
        if not file.is_dir():
            files.append(file)
    gt=[a for a in files if a.filename.lower().split("/")[-1]=="groundtruth.txt"]
    if len(gt)!=1:
        raise ValueError("expected unique publisher groundtruth.txt")
    if gt[0].file_size<100 or gt[0].file_size>30*1024*1024:
        raise ValueError("source ground truth size inadmissible")
    return files,gt[0]


def downsample_original_pose(t,q,dt=SAMPLE_PERIOD_S):
    """Choose original pose stamps nearest each fixed 50ms nominal timestamp."""
    if not 0<dt<.2:
        raise ValueError("invalid frozen subsampling period")
    t=np.asarray(t)
    if t.ndim!=1 or len(t)<20 or np.any(np.diff(t)<=0):
        raise ValueError("invalid source chronology")
    grid=np.arange(float(t[0]),float(t[-1])+1e-9,dt)
    idx=np.searchsorted(t,grid)
    left=np.clip(idx-1,0,len(t)-1)
    right=np.clip(idx,0,len(t)-1)
    choose=np.where(abs(t[left]-grid)<=abs(t[right]-grid),left,right)
    choose=np.unique(choose)
    ts=t[choose]
    # Source pose gaps exceeding twice expected separation disqualify a
    # universal continuity claim; do not connect across unknown intervals.
    return ts,np.asarray(q)[choose]


def streak(changes,jitter=REVERSAL_THRESHOLD_RAD):
    direction=0
    run=0.
    longest=0.
    flips=0
    for value in changes:
        if abs(value)<=jitter:
            continue
        s=1 if value>0 else -1
        if direction and s!=direction:
            longest=max(longest,abs(run))
            run=0.
            flips+=1
        direction=s
        run+=float(value)
    longest=max(longest,abs(run))
    return longest/TWO_PI,flips


def qualify(gt):
    rows=np.asarray(gt,dtype=float)
    if rows.ndim!=2 or rows.shape[1]!=8 or len(rows)<100:
        raise ValueError("expected 8-column original mocap pose source")
    if not np.isfinite(rows).all():
        raise ValueError("nonfinite source pose")
    t=rows[:,0]
    q=rows[:,4:8]
    if np.any(np.diff(t)<=0) or np.any(np.abs(np.linalg.norm(q,axis=1)-1)>.02):
        raise ValueError("source monotonicity or quaternion norm invalid")
    ts,qs=downsample_original_pose(t,q)
    if len(ts)<40:
        raise ValueError("insufficient independent 20Hz poses")
    r=Rotation.from_quat(qs/np.linalg.norm(qs,axis=1)[:,None])
    manual=independent_rotvecs(qs)
    scipy=(r[:-1].inv()*r[1:]).as_rotvec()
    difference=float(np.max(np.linalg.norm(scipy-manual,axis=1)))
    if difference>1e-8:
        raise ValueError("independent relative orientation checks disagree")
    path=float(np.linalg.norm(scipy,axis=1).sum())
    steps=np.linalg.norm(scipy,axis=1)
    gap=float(np.diff(ts).max())
    alias=bool(gap>2*SAMPLE_PERIOD_S+1e-6 or np.max(steps)>=math.pi/2)
    axes={}
    for idx,name in enumerate("xyz"):
        length,flips=streak(scipy[:,idx])
        aligned=float(np.abs(scipy[:,idx]).sum()/max(path,1e-10))
        axes[name]={
            "longest_uninterrupted_projected_turns":length,
            "reversal_count_after_fixed_threshold":flips,
            "total_absolute_projected_turns":float(np.sum(np.abs(scipy[:,idx]))/TWO_PI),
            "net_projected_turns":float(np.sum(scipy[:,idx])/TWO_PI),
            "axis_fraction_of_3d_path":aligned,
            "qualifies_2_turns_90pct_axis":bool(length>=2 and aligned>=.9 and not alias),
        }
    return {
        "source_pose_count":len(t),
        "resampled_original_pose_count":len(ts),
        "duration_s":float(t[-1]-t[0]),
        "original_pose_median_interval_ms":float(np.median(np.diff(t))*1000),
        "resampled_median_interval_ms":float(np.median(np.diff(ts))*1000),
        "largest_resampled_gap_ms":gap*1000,
        "largest_so3_step_deg":float(np.degrees(steps.max())),
        "source_quaternion_independent_agreement_rad":difference,
        "total_3d_rotation_turns":path/TWO_PI,
        "per_body_axis":axes,
        "any_predeclared_axis_qualifies_2_turns":any(a["qualifies_2_turns_90pct_axis"] for a in axes.values()),
        "source_alias_or_gap_obstruction":alias,
        "sensor_event_values_read":False,
        "sensor_imu_values_read":False,
        "external_heading_truth_not_estimator_input":True,
        "navigation_heading_correction_authorized":False,
        "source_scope":"original UZH motion-capture poses, no camera/gyro acquisition",
    }


def sha256_file(path):
    sha=hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda:source.read(16*1024*1024),b""):
            sha.update(block)
    return sha.hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--zip",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    digest=sha256_file(args.zip)
    with zipfile.ZipFile(args.zip) as arc:
        files,ground=check_archive_members(arc)
        groundbytes=arc.read(ground)
        member_sha=hashlib.sha256(groundbytes).hexdigest()
        data=np.loadtxt(io.BytesIO(groundbytes),comments="#",dtype=float,ndmin=2)
        props=qualify(data)
    result={
        "source_publisher":"UZH Robotics and Perception Group DAVIS dataset",
        "source_url":URL,
        "source_archive_sha256_first_authenticated_receipt":digest,
        "source_archive_bytes":args.zip.stat().st_size,
        "source_gt_member":ground.filename,
        "source_gt_sha256":member_sha,
        "source_archive_file_entries":len(files),
        "selected_member_names":[item.filename for item in files
                                  if item.filename.lower().endswith(("events.txt","imu.txt","groundtruth.txt","calib.txt"))],
        "predeclared_geometry":"All xyz body axes, 50ms original-mocap sampling, >=720deg continuous, >=90% aligned",
        "motion":props,
        "result":("CANDIDATE_FOR_SEPARATE_REAL_EVENT_IMU_REPLAY"
                  if props["any_predeclared_axis_qualifies_2_turns"] else
                  "REJECTED_AS_CONTINUOUS_2_TURN_DATASET_IN_DECLARED_MODEL"),
        "external_camera_gyro_synchronization":"UNKNOWN",
        "source_external_ground_truth_authority":"publisher-described mocap, independently timestamped",
    }
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("UZH_SHAPES_ORIGINAL_MOTION_ADMISSION",json.dumps({
        "sha256":digest,"result":result["result"],
        "source_gt_count":props["source_pose_count"],
        "axes":props["per_body_axis"],
        "total_3d_turns":props["total_3d_rotation_turns"]},sort_keys=True))


if __name__=="__main__":
    main()
