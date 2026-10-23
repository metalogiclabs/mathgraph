"""Prospective EFRD lab2 pose admission with lab1-frozen qualification method.

Source identity previously SHA256-pinned without accessing pose values:
https://github.com/metalogiclabs/mathgraph/actions/runs/39878919187 .
Causal classifier and settings reused verbatim from previously verified lab1
qualifier experiments/uzh_rotation/qualify_efrd_mocap_pose.py. This adapter
must not alter that classifier or inspect event-camera observations.
"""
import argparse
import hashlib
import json
from pathlib import Path

from qualify_efrd_mocap_pose import quantify

LAB2_SHA256 = "69fd0fb8fafcf01cde467904d54baa90b98d5c85cb22bd15034770be3f8ed7c1"
LAB2_BYTES = 1394913640
LAB2_TOPIC = "/vrpn_client_node/Rigid0/pose"
FROZEN_QUALIFIER_BLOB = "b1ec80c906abb04d79f769d1493cde5403145449"


def replay(file):
    from rosbags.highlevel import AnyReader
    path=Path(file)
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(16*1024*1024),b""):
            digest.update(chunk)
    if digest.hexdigest()!=LAB2_SHA256 or path.stat().st_size!=LAB2_BYTES:
        raise ValueError("Lab2 original-source hash or byte count mismatch")
    result={
        "source":"EFRD original author lab2.bag",
        "source_sha256":digest.hexdigest(),
        "source_bytes":path.stat().st_size,
        "source_identity_pinned_before_pose_access":True,
        "identity_pin":"https://github.com/metalogiclabs/mathgraph/actions/runs/39878919187",
        "classifier_origin":"lab1-frozen qualify_efrd_mocap_pose.quantify",
        "classifier_blob_sha":FROZEN_QUALIFIER_BLOB,
        "source_pose_header_used_not_rosbag_global_duration":True,
        "mocap_reference_only_for_offline_admission":True,
        "camera_event_values_not_opened":True,
        "estimator_received_ground_truth":False,
        "navigation_correction_authorized":False,
        "state":"UNKNOWN",
    }
    with AnyReader([path]) as reader:
        matches=[c for c in reader.connections if c.topic==LAB2_TOPIC
                 and "PoseStamped" in c.msgtype]
        if len(matches)!=1:
            result["state"]="UNKNOWN_NO_UNIQUE_MOCAP"
            return result
        stamps=[];q=[];xyz=[]
        for c,_,raw in reader.messages(connections=matches):
            m=reader.deserialize(raw,c.msgtype)
            h=m.header.stamp
            if h.nanosec<0 or h.nanosec>=1000000000:
                result["state"]="UNKNOWN_BAD_ORIGINAL_TIMESTAMPS"
                return result
            stamps.append(int(h.sec)*1000000000+int(h.nanosec))
            o=m.pose.orientation
            p=m.pose.position
            q.append((o.x,o.y,o.z,o.w))
            xyz.append((p.x,p.y,p.z))
    result["source_pose_count"]=len(stamps)
    if len(stamps)!=5904:
        result["state"]="UNKNOWN_POSE_COUNT_CHANGED_FROM_PINNED_SOURCE_INDEX"
        return result
    try:
        metric=quantify(stamps,q,xyz)
    except (ValueError,RuntimeError) as error:
        result["state"]="UNKNOWN_INVALID_POSE_SEQUENCE"
        result["error"]=str(error)
        return result
    result["metrics"]=metric
    result["state"]=(
      "CANDIDATE_FOR_SEPARATE_CAMERA_IMU_COLUMN_QUALIFICATION"
      if metric["world_z_two_turn_pose_qualification"]
      else "REJECTED_FOR_FROZEN_WORLD_Z_TWO_TURN_REQUIREMENT"
    )
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--bag",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    report=replay(args.bag)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("EFRD_LAB2_FROZEN_MOTION",json.dumps(report,sort_keys=True))

if __name__=="__main__":main()
