"""Retrospective, source-pinned Brandenburg IMU transfer audit (V2).

Original ECRot source did not meet the previous frozen v1 replay preconditions.
No gyro-based heading label is treated as independent truth. Observed duplicate
timestamps may be removed only if the entire original serialized IMU message
and its bag receipt time are identical; different data at one time is UNKNOWN.
No camera map is constructed before one actual gyro-estimated full turn.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np

SOURCE_SHA256 = "3d8e3284670c94b52919228c2a133586e8e592c07f3a6e1e127fee6acd747455"


def source_hash(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda:source.read(16*1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def qualify_imu(records):
    """Accept (stamp_ns,bag_ns,raw_serialized_bytes,(wx,wy,wz)) in source order."""
    rows=list(records)
    base={"original_imu_messages":len(rows), "exact_retransmissions":0,
          "clock_collisions":0,"clock_reversals":0,
          "examples":[],"status":"UNKNOWN", "gyro_y_turns":None,
          "estimated_map_turn_complete":False,
          "first_turn_map_populated":False,
          "heading_correction_authorized":False,
          "basis":"source header nanoseconds and uncalibrated y gyro, not heading truth"}
    unique=[]
    for i,row in enumerate(rows):
        stamp,bag,raw,angular=row
        if (not isinstance(stamp,int) or not isinstance(bag,int) or
            not isinstance(raw,bytes) or len(angular)!=3 or
            any(not math.isfinite(float(v)) for v in angular)):
            base["status"]="INVALID_SOURCE_RECORD"
            base["examples"].append({"index":i,"issue":"nonfinite or malformed"})
            return base
        if unique:
            last=unique[-1]
            if stamp < last[0]:
                base["clock_reversals"]+=1
                base["examples"].append({"index":i,"issue":"time reversed",
                                         "ns_delta":stamp-last[0]})
                base["status"]="INVALID_IMU_CHRONOLOGY"
                return base
            if stamp == last[0]:
                if bag == last[1] and raw == last[2]:
                    base["exact_retransmissions"]+=1
                    continue
                base["clock_collisions"]+=1
                base["examples"].append({
                    "index":i,"issue":"same header time with different source identity",
                    "same_bag_time":bag==last[1],
                    "same_raw_bytes":raw==last[2]})
                base["status"]="AMBIGUOUS_IMU_TIMESTAMP"
                return base
        unique.append(row)
    base["unique_imu_samples"]=len(unique)
    if len(unique)<2:
        base["status"]="INSUFFICIENT_IMU"
        return base
    stamps=np.array([r[0]-unique[0][0] for r in unique],dtype=np.int64)
    rates=np.array([r[3] for r in unique],dtype=np.float64)
    dt=np.diff(stamps).astype(np.float64)*1e-9
    if not np.all(dt>0):
        base["status"]="INVALID_IMU_CHRONOLOGY"
        return base
    # This is a relative gyro phase, not an accurate absolute yaw measurement.
    signed=float(np.sum((rates[:-1,1]+rates[1:,1])*0.5*dt))
    total=float(np.sum(np.abs((rates[:-1,1]+rates[1:,1])*0.5*dt)))
    base["gyro_y_turns"]=signed/(2*math.pi)
    base["absolute_gyro_y_travel_turns"]=total/(2*math.pi)
    base["median_imu_period_ms"]=float(np.median(dt)*1000)
    # This is a necessary condition for a subsequent column-map replay, not a
    # sufficient criterion for source timing accuracy or visual relocalization.
    base["estimated_map_turn_complete"]=abs(signed)>=2*math.pi
    if not base["estimated_map_turn_complete"]:
        base["status"]="INSUFFICIENT_FIRST_REVOLUTION"
        return base
    base["status"]="ELIGIBLE_FOR_SEPARATE_VISUAL_REPLAY_ONLY"
    return base


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--bag",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    digest=source_hash(args.bag)
    if digest!=SOURCE_SHA256:
        raise ValueError("ECRot original Brandenburg source SHA256 mismatch")
    from rosbags.highlevel import AnyReader
    with AnyReader([args.bag]) as reader:
        con=[c for c in reader.connections if c.topic=="/dvs/imu"]
        if len(con)!=1 or sum(c.topic=="/dvs/events" for c in reader.connections)!=1:
            raise ValueError("expected exactly one IMU and EventArray source")
        rows=[]
        for connection,timestamp,raw in reader.messages(connections=con):
            msg=reader.deserialize(raw,connection.msgtype)
            stamp=msg.header.stamp
            if stamp.nanosec<0 or stamp.nanosec>=1000000000:
                raise ValueError("invalid source nanoseconds")
            header_ns=int(stamp.sec)*1000000000+int(stamp.nanosec)
            w=msg.angular_velocity
            rows.append((header_ns,int(timestamp),bytes(raw),(w.x,w.y,w.z)))
    audit=qualify_imu(rows)
    report={
        "research_state":"REJECTED for continuous two-turn visual replay; diagnostic is retrospective",
        "dataset":"ECRot original Brandenburg Gate /dvs/imu and /dvs/events",
        "source_sha256":digest,
        "original_v1_freeze":"62ddc79389f2f39c7a8782d8b378d9d95ca5a068",
        "independent_source_pin_run":"https://github.com/metalogiclabs/mathgraph/actions/runs/39870666780",
        "predeclared_gyro_axis":"y",
        "source_recorder_clock_verified_as_camera_clock":False,
        "raw_event_source_untouched":True,
        "imap":audit,
        "heading_truth":"UNAVAILABLE",
        "visual_relocalization":"NOT TESTED: insufficient admitted acquisition evidence",
        "navigation_authorization":"UNKNOWN; no correction",
        "epistemic_boundary":"retrospective source qualification, not flight or multi-turn line-camera validation",
    }
    args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("BRANDENBURG_REPLAY",json.dumps(audit,sort_keys=True))
    if audit["status"] not in ("INSUFFICIENT_FIRST_REVOLUTION","AMBIGUOUS_IMU_TIMESTAMP"):
        raise SystemExit("Unexpected second-scene admission change; inspect preserved report")
if __name__=="__main__":
    main()
