"""Retrospective source-alternative ECRot gyro audit; no physical-heading claim."""
import argparse, hashlib, itertools, json, math
from fractions import Fraction
from pathlib import Path
SHA="3d8e3284670c94b52919228c2a133586e8e592c07f3a6e1e127fee6acd747455"
NANO=10**9
TWO_PI_LOW=Fraction.from_float(math.nextafter(2*math.pi,-math.inf))
TWO_PI_HIGH=Fraction.from_float(math.nextafter(2*math.pi,math.inf))

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(16*1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def group_source(samples):
    groups=[]
    for stamp,bag,rate,raw in samples:
        if not isinstance(stamp,int) or not isinstance(bag,int) or not isinstance(raw,bytes) or not math.isfinite(float(rate)):
            raise ValueError("invalid source observation")
        if groups and stamp<groups[-1]["t"]:
            raise ValueError("backward source timestamp")
        if groups and stamp==groups[-1]["t"]:
            g=groups[-1]
            g["rates"].append(Fraction.from_float(float(rate)))
            g["bags"].add(bag)
            g["hashes"].add(hashlib.sha256(raw).hexdigest())
        else:
            groups.append({"t":stamp,"rates":[Fraction.from_float(float(rate))],
                           "bags":{bag},"hashes":{hashlib.sha256(raw).hexdigest()}})
    if len(groups)<2:
        raise ValueError("insufficient unique timestamps")
    return groups

def interval_oracle(groups):
    lo=hi=Fraction(0)
    maximum=Fraction(0)
    for left,right in zip(groups,groups[1:]):
        dt=right["t"]-left["t"]
        if dt<=0: raise ValueError("non-increasing unique timestamps")
        k=Fraction(dt,2*NANO)
        lo+=k*(min(left["rates"])+min(right["rates"]))
        hi+=k*(max(left["rates"])+max(right["rates"]))
        maximum=max(maximum,abs(lo),abs(hi))
    return {"final_low":lo,"final_high":hi,"max_abs_prefix":maximum}

def explicit_oracle(groups,max_combinations=128):
    opts=[g["rates"] for g in groups]
    ambiguities=[i for i,o in enumerate(opts) if len(o)>1]
    count=math.prod(len(opts[i]) for i in ambiguities)
    if count>max_combinations:
        return {"status":"TOO_MANY_ALTERNATIVES","count":count}
    baseline=[o[0] for o in opts]
    finals=[]
    high=Fraction(0)
    for choices in itertools.product(*(opts[i] for i in ambiguities)):
        rates=list(baseline)
        for i,v in zip(ambiguities,choices): rates[i]=v
        s=Fraction(0)
        for k in range(len(groups)-1):
            dt=groups[k+1]["t"]-groups[k]["t"]
            s+=(rates[k]+rates[k+1])*Fraction(dt,2*NANO)
            high=max(high,abs(s))
        finals.append(s)
    return {"status":"EXHAUSTIVE","count":count,"final_low":min(finals),
            "final_high":max(finals),"max_abs_prefix":high}

def summarize(groups):
    bound=interval_oracle(groups)
    independent=explicit_oracle(groups)
    if independent["status"]=="EXHAUSTIVE":
        for k in ("final_low","final_high","max_abs_prefix"):
            if bound[k]!=independent[k]:
                raise AssertionError("exact enumerator disagrees: "+k)
    duplicate=[{"source_index":i,"timestamp_ns":g["t"],"messages":len(g["rates"]),
                "distinct_rate_values":len(set(g["rates"])),
                "distinct_serializations":len(g["hashes"]),
                "distinct_bag_timestamps":len(g["bags"]),
                "low_rate_y":float(min(g["rates"])),"high_rate_y":float(max(g["rates"]))}
               for i,g in enumerate(groups) if len(g["rates"])>1]
    peak=bound["max_abs_prefix"]
    if peak<TWO_PI_LOW:
        status="NO_FULL_TURN_IN_ANY_RECORDED_SOURCE_CHOICE"
    elif bound["final_low"]>TWO_PI_HIGH or bound["final_high"]< -TWO_PI_HIGH:
        status="ELIGIBLE_FOR_SEPARATE_VISUAL_REPLAY_ONLY"
    else:
        status="UNKNOWN_CROSSING_OR_DIRECTION"
    return {"status":status,
            "source_imu_messages":sum(len(g["rates"]) for g in groups),
            "unique_imu_stamps":len(groups),
            "duplicate_groups":duplicate,
            "source_choice_count":independent["count"],
            "independent_exact_agreement":independent["status"]=="EXHAUSTIVE",
            "independent_oracle_status":independent["status"],
            "net_signed_y_turns_low":float(bound["final_low"]/(2*math.pi)),
            "net_signed_y_turns_high":float(bound["final_high"]/(2*math.pi)),
            "max_abs_y_prefix_turns":float(peak/(2*math.pi)),
            "max_abs_y_prefix_radians":float(peak),
            "not_a_physical_angular_error_bound":True,
            "reference_map_populated":False,
            "navigation_authorized":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bag",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    digest=sha256(args.bag)
    if digest!=SHA: raise ValueError("source checksum mismatch")
    from rosbags.highlevel import AnyReader
    rows=[]
    with AnyReader([args.bag]) as reader:
        con=[c for c in reader.connections if c.topic=="/dvs/imu"]
        if len(con)!=1: raise ValueError("unexpected IMU connections")
        for c,receipt_ns,raw in reader.messages(connections=con):
            m=reader.deserialize(raw,c.msgtype)
            stamp=m.header.stamp
            if not 0<=stamp.nanosec<NANO: raise ValueError("invalid nanoseconds")
            rows.append((int(stamp.sec)*NANO+int(stamp.nanosec),
                         int(receipt_ns),float(m.angular_velocity.y),bytes(raw)))
    audit=summarize(group_source(rows))
    report={"source":"ECRot Brandenburg original ROS1 bag, exposed second scene",
            "source_sha256":digest,"audit":audit,
            "physical_yaw_ground_truth":"UNAVAILABLE",
            "gyro_to_camera_time_bound":"UNVERIFIED",
            "boundary":"finite recorded-source alternatives, exact rational gyro integration, not physical motion proof",
            "navigation_decision":"UNKNOWN; correction withheld"}
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("BRANDENBURG_SETVALUED",json.dumps(audit,sort_keys=True))
if __name__=="__main__": main()
