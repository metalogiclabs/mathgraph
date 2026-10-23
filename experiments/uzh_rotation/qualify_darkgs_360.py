"""DARK-GS-Fusion source-pinned UAV yaw recording qualification.

This stage checks the publisher's original deposited 360.zip and opens ONLY
the original ROS2 /Darknav/pose values, never IMU or image payloads.

A dataset labelled "360" or a total rotation path > 1 revolution is not
evidence of two uninterrupted yaw revolutions. Author-declared /Darknav/pose
is a REFERENCE, but independent mocap/external pose provenance remains UNKNOWN
until documented, and it never enters a visual estimator or correction policy.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import zipfile

import numpy as np
from scipy.spatial.transform import Rotation

API="https://entrepot.recherche.data.gouv.fr/api/datasets/:persistentId/"
DATASET_ID="doi:10.57745/EV12AZ"
EXPECTED_NAME="360.zip"
PUBLISHED_MD5="2b6eb3220c82ecab96dc8a4d918464ed"
MIN_TURN=2.0
REVERSAL_TOL=math.radians(0.2)
TOPIC="/Darknav/pose"


def datafile_entry(meta,name=EXPECTED_NAME):
    versions=meta.get("data",{}).get("latestVersion",{})
    files=versions.get("files",[])
    matches=[e for e in files if e.get("dataFile",{}).get("filename")==name]
    if len(matches)!=1:
        raise ValueError("missing or duplicated exact original deposited source file")
    f=matches[0]["dataFile"]
    checksum=f.get("checksum") or {}
    md5=(checksum.get("value") if checksum.get("type","").upper()=="MD5" else None) or f.get("md5")
    if name==EXPECTED_NAME and str(md5).lower()!=PUBLISHED_MD5:
        raise ValueError("published original MD5 does not match pre-frozen expected digest")
    if not isinstance(f.get("id"),int) or f["id"]<=0:
        raise ValueError("invalid publisher datafile identity")
    return {"filename":name,"datafile_id":f["id"],"expected_md5":md5,
            "reported_bytes":f.get("filesize"),"source":"Dataverse API original deposit"}


def hashes(path):
    md5=hashlib.md5()
    sha=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""):
            md5.update(b);sha.update(b)
    return md5.hexdigest(),sha.hexdigest()


def validate_zip(members):
    seen=set()
    total=0
    for item in members:
        name=item.filename
        pieces=Path(name).parts
        if (not name or name.startswith("/") or "\\" in name or
                ".." in pieces or
                (item.external_attr>>16)&0o170000 in (stat.S_IFLNK,stat.S_IFCHR,stat.S_IFBLK)):
            raise ValueError("unsafe or ambiguous original archive member")
        if name in seen:raise ValueError("duplicate archive path")
        seen.add(name)
        total+=item.file_size
        if total>12*1024*1024*1024:
            raise ValueError("original archive declares excessive decompression")
    return total


def sign_run(values):
    run=best=0.0
    sign=0
    flips=0
    for step in values:
        if abs(float(step))<=REVERSAL_TOL:continue
        d=1 if step>0 else -1
        if sign and d!=sign:
            best=max(best,abs(run))
            run=0.
            flips+=1
        sign=d
        run+=float(step)
    return {"longest_turns":max(best,abs(run))/(2*math.pi),
            "net_turns":float(np.sum(values))/(2*math.pi),
            "reversals":flips,
            "absolute_total_projected_turns":float(np.sum(np.abs(values)))/(2*math.pi)}


def geometry(times,quaternions,positions):
    ts=np.asarray(times,dtype=np.int64)
    q=np.asarray(quaternions,dtype=float)
    xyz=np.asarray(positions,dtype=float)
    if len(ts)<20 or q.shape!=(len(ts),4) or xyz.shape!=(len(ts),3):
        raise ValueError("source pose insufficient or malformed")
    if not np.isfinite(q).all() or not np.isfinite(xyz).all():
        raise ValueError("nonfinite source pose")
    if np.any(np.diff(ts)<=0):
        raise ValueError("nonmonotonic source pose header clock")
    norm=np.linalg.norm(q,axis=1)
    if np.any(abs(norm-1)>0.02):raise ValueError("nonunit source orientation")
    rot=Rotation.from_quat(q/norm[:,None])
    delta=(rot[:-1].inv()*rot[1:]).as_rotvec()
    step=np.linalg.norm(delta,axis=1)
    mats=rot.as_matrix()
    yaw=np.unwrap(np.arctan2(mats[:,1,0],mats[:,0,0]))
    near_gimbal=bool(np.any(np.abs(mats[:,2,0])>0.995))
    yaw_run=sign_run(np.diff(yaw))
    paths=[sign_run(delta[:,i]) for i in range(3)]
    paths_sum=np.sum(step)
    fractions=[float(np.sum(np.abs(delta[:,i]))/max(paths_sum,1e-15)) for i in range(3)]
    dt=np.diff(ts)*1e-9
    sampled=(step.max()<math.pi/2 and dt.max()<=.25 and not near_gimbal)
    yaw_z=paths[2]
    admission=(sampled and yaw_run["longest_turns"]>=MIN_TURN and
               yaw_z["longest_turns"]>=MIN_TURN and fractions[2]>=.90)
    return {
      "n_original_publisher_pose_messages":int(len(ts)),
      "source_duration_header_s":float((int(ts[-1])-int(ts[0]))*1e-9),
      "median_pose_spacing_ms":float(np.median(dt)*1000),
      "largest_pose_spacing_ms":float(dt.max()*1000),
      "largest_original_pairwise_so3_step_deg":float(np.degrees(step.max())),
      "total_3d_rotation_travel_turns":float(paths_sum/(2*math.pi)),
      "world_z_yaw_unwrapped_excursion_turns":float(np.ptp(yaw)/(2*math.pi)),
      "world_z_yaw_directional":yaw_run,
      "body_axis_xyz_signed_runs":dict(zip("xyz",paths)),
      "body_axis_xyz_fraction_of_total_3d_path":dict(zip("xyz",fractions)),
      "near_world_z_yaw_singularity":near_gimbal,
      "pose_sampling_admission":sampled,
      "max_position_displacement_from_start_m":float(np.max(np.linalg.norm(xyz-xyz[0],axis=1))),
      "translation_path_m":float(np.sum(np.linalg.norm(np.diff(xyz,axis=0),axis=1))),
      "two_continuous_world_z_yaw_turns_qualified_in_source_model":bool(admission),
      "physical_unobserved_between_pose_motion_bounded":False,
      "source_ref_independently_authenticated_as_external_mocap":False,
      "visual_firstturn_map_built":False,
      "navigation_heading_correction_authorized":False,
    }


def walk_original_bag(root):
    metas=list(root.rglob("metadata.yaml"))
    if len(metas)!=1:
        return None,[str(x.relative_to(root)) for x in metas]
    return metas[0].parent,[str(x.relative_to(root)) for x in metas]


def extract_pose(msg):
    pose=getattr(msg,"pose",None)
    if pose is None:pose=getattr(msg,"transform",None)
    if hasattr(pose,"pose"):pose=pose.pose
    if pose is None:raise ValueError("publisher pose lacks parseable geometry")
    ori=getattr(pose,"orientation",None)
    pos=getattr(pose,"position",None)
    if ori is None or pos is None:
        raise ValueError("publisher pose structure differs from presumed PoseStamped/Odometry")
    stamp=getattr(getattr(msg,"header",None),"stamp",None)
    if stamp is None:raise ValueError("publisher pose lacks source-native header timestamp")
    ns=int(stamp.sec)*1_000_000_000+int(stamp.nanosec)
    if not 0<=int(stamp.nanosec)<1_000_000_000:
        raise ValueError("malformed source nanosecond field")
    return (ns,(ori.x,ori.y,ori.z,ori.w),(pos.x,pos.y,pos.z))


def inspect_bag(root,output):
    from rosbags.highlevel import AnyReader
    folder,candidates=walk_original_bag(root)
    output["original_rosbag_metadata_paths"]=candidates
    if folder is None:
        output["state"]="UNKNOWN_NO_UNIQUE_ROS2_METADATA_YAML"
        return
    with AnyReader([folder]) as reader:
        conn=[{"topic":c.topic,"msgtype":c.msgtype,"index_count":int(c.msgcount)}
              for c in reader.connections]
        output["source_topics"]=sorted(conn,key=lambda d:d["topic"])
        matching=[c for c in reader.connections if c.topic==TOPIC]
        output["camera_color_topic_present"]=any(c.topic=="/camera/color/image_raw/compressed" for c in reader.connections)
        output["filtered_imu_topic_present"]=any(c.topic=="/filtered_imu_xsens" for c in reader.connections)
        output["camera_or_imu_message_payloads_read"]=False
        if len(matching)!=1:
            output["state"]="UNKNOWN_NO_UNIQUE_PUBLISHER_REFERENCE_POSE"
            return
        ts=[];q=[];xyz=[]
        for c,_,raw in reader.messages(connections=matching):
            msg=reader.deserialize(raw,c.msgtype)
            time,quat,position=extract_pose(msg)
            ts.append(time);q.append(quat);xyz.append(position)
        try:
            motion=geometry(ts,q,xyz)
        except (ValueError,RuntimeError) as err:
            output["state"]="UNKNOWN_REFERENCE_MOTION_NOT_ADMISSIBLE"
            output["reason"]=str(err)
            return
        output["source_mocap_label_not_verified_as_external"]=True
        output["motion"]=motion
        output["state"]=(
          "CANDIDATE_SOURCE_2TURNS_REQUIRES_CAMERA_CLOCK_REPLAY"
          if motion["two_continuous_world_z_yaw_turns_qualified_in_source_model"]
          else "REJECTED_UNDER_TWO_TURN_WORLD_Z_SOURCE_MODEL"
        )


def run(output_path):
    import requests
    result={"dataset_doi":DATASET_ID,"repository":"DARK-GS-Fusion, Recherche Data Gouv",
            "author_published_md5":PUBLISHED_MD5,
            "requested_original_archive":EXPECTED_NAME,
            "heldout_360_2_not_opened":True,
            "any_camera_image_payload_processed":False,
            "any_imu_payload_processed":False,
            "reference_independent_external_mocap_proven":False,
            "heading_correction_authorized":False,
            "state":"UNKNOWN"}
    try:
        meta=requests.get(API,params={"persistentId":DATASET_ID},timeout=40)
        meta.raise_for_status()
        entry=datafile_entry(meta.json())
        result["publisher_record"]=entry
        path=Path(EXPECTED_NAME)
        api_url=f"https://entrepot.recherche.data.gouv.fr/api/access/datafile/{entry['datafile_id']}"
        with requests.get(api_url,stream=True,timeout=(30,100)) as stream:
            stream.raise_for_status()
            with path.open("wb") as f:
                for chunk in stream.iter_content(chunk_size=4*1024*1024):
                    if chunk:f.write(chunk)
        actual_md5,sha=hashes(path)
        result.update({"source_bytes":path.stat().st_size,
                       "source_sha256":sha,"source_md5":actual_md5})
        if actual_md5!=PUBLISHED_MD5:
            result["state"]="UNKNOWN_AUTHENTIC_SOURCE_MD5_MISMATCH"
        elif not zipfile.is_zipfile(path):
            result["state"]="UNKNOWN_NOT_ORIGINAL_ZIP"
        else:
            with zipfile.ZipFile(path) as arc:
                data=arc.infolist()
                uncompressed=validate_zip(data)
                result["archive_members"]=[
                    {"name":m.filename,"compressed_bytes":int(m.compress_size),
                     "original_bytes":int(m.file_size)}
                    for m in data[:75]]
                result["archive_member_count"]=len(data)
                result["archive_declared_uncompressed_bytes"]=uncompressed
                folder=Path("original_darkgs")
                folder.mkdir(exist_ok=True)
                arc.extractall(folder)
            inspect_bag(Path("original_darkgs"),result)
    except Exception as exc:
        result["state"]="UNKNOWN_AUTHENTIC_SOURCE_ADMISSION_FAILURE"
        result["failure"]=type(exc).__name__+": "+str(exc)[:900]
    output_path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("DARKGS_360_SOURCE_ADMISSION",json.dumps(result,sort_keys=True))
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    run(a.out)


if __name__=="__main__":
    main()
