"""Source-authoritative EFRD camera-IMU duplicate-timestamp audit.

Preserves all source observations; does not choose a conflicting same-time
rate by comparing to external motion capture. Min/max norm curves are
retrospective diagnostics, NOT guaranteed physical angular-speed bounds.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from qualify_efrd_timing import (
    SOURCE_SHA256, MOCAP_TOPIC, sha256_file, source_time_ns,
    mocap_angular_speed, frozen_offset_split,
)


def classify_timed_imu(records):
    """Source ordered (timestamp_ns, bag_receipt_ns, raw, xyz) observations.

    Exact duplicate means bytes AND receipt time agree. Any other same-time
    record is a recorded conflict. Retain all rates and source identities.
    """
    groups = []
    for i, (time, bag_receipt, raw, w) in enumerate(records):
        xyz = np.asarray(w, dtype=float)
        if (not isinstance(time,int) or not isinstance(bag_receipt,int) or
                not isinstance(raw, bytes) or len(raw)==0 or xyz.shape!=(3,) or
                not np.all(np.isfinite(xyz))):
            raise ValueError("invalid original source record")
        speed = float(np.linalg.norm(xyz))
        if groups and time < groups[-1]["time"]:
            raise ValueError("reverse source chronology")
        item={"rate":speed,"raw_sha":hashlib.sha256(raw).hexdigest(),
              "receipt":bag_receipt,"index":i}
        if groups and time == groups[-1]["time"]:
            groups[-1]["observations"].append(item)
        else:
            groups.append({"time":time,"observations":[item]})
    if len(groups)<2:
        raise ValueError("insufficient unique camera IMU timestamps")
    exact=conflicting=0
    conflicts=[]
    low=[];high=[];times=[]
    for g in groups:
        all_rates=[entry["rate"] for entry in g["observations"]]
        first=g["observations"][0]
        for observation in g["observations"][1:]:
            if (observation["raw_sha"]==first["raw_sha"] and
                    observation["receipt"]==first["receipt"]):
                exact+=1
            else:
                conflicting+=1
        if len(g["observations"])>1:
            conflicts.append({
                "timestamp_ns":g["time"],
                "observations":len(g["observations"]),
                "distinct_raw_sha":len({v["raw_sha"] for v in g["observations"]}),
                "distinct_receipt_time":len({v["receipt"] for v in g["observations"]}),
                "speed_min_rad_s":min(all_rates),
                "speed_max_rad_s":max(all_rates),
                "speed_spread_rad_s":max(all_rates)-min(all_rates),
                "source_indices":[v["index"] for v in g["observations"]],
            })
        times.append(g["time"])
        low.append(min(all_rates))
        high.append(max(all_rates))
    return {
        "state":("CONFLICTING_OR_UNVERIFIED_TIMESTAMP_COLLISIONS"
                 if conflicting else "EXACT_RETRANSMISSIONS_ONLY"),
        "original_messages":sum(len(g["observations"]) for g in groups),
        "unique_timestamps":len(groups),
        "same_time_extra_observations":exact+conflicting,
        "byte_identical_same_receipt_extras":exact,
        "conflicting_same_time_extras":conflicting,
        "duplicate_groups":conflicts,
        "timestamp_ns":np.asarray(times,dtype=np.int64),
        "min_speed":np.asarray(low,dtype=float),
        "max_speed":np.asarray(high,dtype=float),
        "all_source_alternatives_retained":True,
        "not_a_physical_angular_error_bound":True,
        "navigation_correction_authorized":False,
    }


def audit_original(path):
    from rosbags.highlevel import AnyReader

    p=Path(path)
    digest=sha256_file(p)
    if digest != SOURCE_SHA256:
        raise ValueError("Original lab1 source SHA256 mismatch")
    with AnyReader([p]) as reader:
        mc=[c for c in reader.connections if c.topic==MOCAP_TOPIC]
        gg=[c for c in reader.connections if c.topic=="/dvs/imu"]
        if len(mc)!=1 or len(gg)!=1:
            raise ValueError("missing unique mocap or camera gyro stream")
        pt=[];qq=[]
        for c,_,raw in reader.messages(connections=mc):
            msg=reader.deserialize(raw,c.msgtype)
            h=source_time_ns(msg.header.stamp)
            o=msg.pose.orientation
            pt.append(h)
            qq.append([o.x,o.y,o.z,o.w])
        reference_t,reference_speed=mocap_angular_speed(pt,qq)
        rows=[]
        for c,receipt_ns,raw in reader.messages(connections=gg):
            msg=reader.deserialize(raw,c.msgtype)
            w=msg.angular_velocity
            rows.append((source_time_ns(msg.header.stamp),int(receipt_ns),bytes(raw),
                         [w.x,w.y,w.z]))
    grouped=classify_timed_imu(rows)
    timing={}
    for name in ("min","max"):
        speeds=grouped["min_speed"] if name=="min" else grouped["max_speed"]
        timing[name]=frozen_offset_split(
            reference_t,reference_speed,grouped["timestamp_ns"],speeds)
    duplicate_detail=grouped["duplicate_groups"]
    return {
        "original_source_sha256":digest,
        "original_source_bytes":p.stat().st_size,
        "mocap_pose_count":len(pt),
        "camera_gyro_source_state":grouped["state"],
        "camera_imu_count":grouped["original_messages"],
        "unique_gyro_times":grouped["unique_timestamps"],
        "same_time_extra_observations":grouped["same_time_extra_observations"],
        "byte_identical_same_receipt_extras":grouped["byte_identical_same_receipt_extras"],
        "conflicting_same_time_extras":grouped["conflicting_same_time_extras"],
        "duplicate_group_details":duplicate_detail,
        "min_max_source_choice_lag_diagnostics":timing,
        "max_disagreement_speed_rad_s":max((x["speed_spread_rad_s"] for x in duplicate_detail),default=0),
        "source_boundaries":{
            "min_max_are_not_exhaustive_correlation_bounds":True,
            "mocap_used_only_to_diagnose_timing":True,
            "gyro_values_not_selected_using_mocap":True,
            "source_is_previously_exposed":True,
            "lab2_sensor_values_unopened":True,
            "camera_events_not_decoded":True,
            "physical_angular_error_bound":"UNKNOWN",
            "navigation_correction_authorized":False
        },
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bag",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=audit_original(args.bag)
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("EFRD_CAMERA_IMU_COLLISION_AUDIT",json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
