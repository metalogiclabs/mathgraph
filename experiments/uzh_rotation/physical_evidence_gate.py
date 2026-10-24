"""MathGraph five-revolution physical evidence gate: NAVIGATION role only.

Reads only navigation-side camera/gyro, decisions, and timing pulse evidence.
No encoder or ground-truth input exists in the command interface. This is a
source/causality/model-consistency auditor, not an on-device estimator.
External physical provenance and sensor-error bounds require separate review.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

VERSION="MGVC-PHYSICAL-1"
TWOPI=2*math.pi
TICKS=65536
BIN_TICKS=1024
ALLOWED_CAPTURE={"MAP_CAPTURE","FREEZE","MATCH","REQUEST","ESTIMATE","WITHDRAW"}
SHA_RE=re.compile(r"^[0-9a-f]{64}$")
CAPTURE_RE=re.compile(r"^[A-Za-z0-9_-]{8,80}$")


def fail(message):
    raise ValueError(message)


def strict_pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:fail("duplicate JSON object key: "+key)
        result[key]=value
    return result


def strict_json(path):
    with Path(path).open("r",encoding="utf-8") as stream:
        return json.load(stream,object_pairs_hook=strict_pairs,
                         parse_constant=lambda x:fail("non-finite JSON"))


def read_lines(path,max_bytes=200_000_000):
    path=Path(path)
    if path.stat().st_size>max_bytes:fail("input log exceeds supported 200MB limit")
    result=[]
    with path.open(encoding="utf-8") as f:
        for i,line in enumerate(f):
            if not line.strip():fail("blank input record")
            try:entry=json.loads(line,object_pairs_hook=strict_pairs,
                                  parse_constant=lambda x:fail("non-finite JSON"))
            except json.JSONDecodeError as e:fail(f"JSONL line {i+1}: {e}")
            if not isinstance(entry,dict):fail("record not a JSON object")
            if entry.get("seq")!=i or type(entry.get("seq")) is not int:
                fail("noncontiguous source sequence ID")
            t=entry.get("t_ns")
            if type(t) is not int or t<0:fail("invalid original timestamp nanoseconds")
            if result and t<=result[-1]["t_ns"]:fail("non-strict event timestamp")
            if any("encoder" in k.lower() or "truth" in k.lower() or k.startswith("gt_")
                   for k in entry):
                fail("forbidden encoder/ground-truth field in navigation log")
            result.append(entry)
    if not result:fail("empty source input")
    return result


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()


def check_manifest(folder,name,role,filenames):
    folder=Path(folder)
    if not folder.is_dir():fail("missing input bundle directory")
    m=strict_json(folder/name)
    if (m.get("schema")!=VERSION or m.get("role")!=role or
        m.get("mode") not in ("FIXTURE","PHYSICAL") or
        not isinstance(m.get("capture_id"),str) or
        not CAPTURE_RE.fullmatch(m["capture_id"])):
        fail("invalid capture manifest identity or role")
    if set(m.get("files",{}))!=set(filenames):
        fail("bundle must pin exactly the approved role-specific files")
    # Role containment: ensure encoder is physically absent from navigator job.
    if role=="NAVIGATION":
        for forbidden in ("encoder.jsonl","encoder_manifest.json","ground_truth.jsonl"):
            if (folder/forbidden).exists():fail("encoder file leaked into navigator bundle")
    for file in filenames:
        p=folder/file
        if not p.is_file() or p.is_symlink():fail("missing or symlinked captured source")
        item=m["files"][file]
        if (type(item) is not dict or not SHA_RE.fullmatch(str(item.get("sha256",""))) or
                type(item.get("bytes")) is not int or
                p.stat().st_size!=item["bytes"] or sha(p)!=item["sha256"]):
            fail("immutable source digest or size mismatch: "+file)
    return m


def camera_source(sensors):
    mapping={}
    last_w=None
    last_t=None
    angle=0.
    gyro_samples=0
    first_gyro_ns=None
    gyro_range=[]
    for e in sensors:
        if e.get("kind")=="GYRO":
            if set(e)!={"seq","t_ns","kind","omega_rad_s"}:fail("invalid gyro schema")
            w=e["omega_rad_s"]
            if type(w) not in (int,float) or not math.isfinite(w):fail("invalid gyro sample")
            if last_t is not None:
                angle+=(e["t_ns"]-last_t)*1e-9*last_w
            else:
                first_gyro_ns=e["t_ns"]
            last_t=e["t_ns"]
            last_w=float(w)
            gyro_samples+=1
            gyro_range.append(abs(float(w)))
        elif e.get("kind")=="COLUMN":
            if set(e)!={"seq","t_ns","kind","column_u16","status"}:
                fail("invalid camera column schema")
            if e["status"] not in ("OK","OCCLUDED"):
                fail("invalid camera status")
            val=e["column_u16"]
            if e["status"]=="OK":
                if type(val) is not int or not 0<=val<=65535:fail("invalid camera column")
            elif val is not None:fail("occluded camera fabricated a visual reading")
            mapping[e["seq"]]=e
        else:fail("unexpected sensor type")
        # Mid-sample step-hold gyro interpolation uses solely past readings.
        if last_t is not None:
            e["_causal_gyro_angle"]=angle+(e["t_ns"]-last_t)*1e-9*last_w
        else:
            e["_causal_gyro_angle"]=None
    if gyro_samples<2 or not mapping:fail("missing gyro sequence or camera readings")
    return mapping,max(gyro_range),first_gyro_ns


def timing_evidence(folder,manifest,sensors,max_measured_gyro):
    x=strict_json(Path(folder)/"timing.json")
    required={"capture_id","source","independent_reference",
              "nominal_skew_ns","error_bound_ns","witness_pairs",
              "calibrated_before_ns","valid_through_ns",
              "max_gyro_rad_s","integration_error_rad"}
    if set(x)!=required or x["capture_id"]!=manifest["capture_id"]:
        fail("timing certificate schema/identity mismatch")
    if x["source"]!="independent_reference_pulses" or x["independent_reference"] is not True:
        fail("no independent clock-pulse source evidence")
    for field in ("nominal_skew_ns","error_bound_ns","calibrated_before_ns","valid_through_ns"):
        if type(x[field]) is not int:fail("invalid timing integer: "+field)
    if (x["error_bound_ns"]<0 or x["calibrated_before_ns"]>=sensors[0]["t_ns"] or
            x["valid_through_ns"]<sensors[-1]["t_ns"]):
        fail("timing certificate absent, expired or after acquisition")
    pairs=x["witness_pairs"]
    if not isinstance(pairs,list) or len(pairs)<5:fail("insufficient independent pulse observations")
    prev=None
    for p in pairs:
        if (not isinstance(p,dict) or set(p)!={"camera_ns","gyro_ns"}
                or any(type(p[k]) is not int for k in ("camera_ns","gyro_ns"))):
            fail("invalid timing pulse pair")
        if prev is not None and p["camera_ns"]<=prev:fail("reordered timing reference pulses")
        prev=p["camera_ns"]
        if abs(p["camera_ns"]-p["gyro_ns"]-x["nominal_skew_ns"])>x["error_bound_ns"]:
            fail("declared timing error bound contradicted by witness")
    w=x["max_gyro_rad_s"]
    extra=x["integration_error_rad"]
    if (type(w) not in (int,float) or type(extra) not in (int,float) or
        not math.isfinite(w) or not math.isfinite(extra) or w<=0 or extra<0 or
        max_measured_gyro>w):
        fail("invalid or contradicted gyro bound")
    angular=float(w)*x["error_bound_ns"]*1e-9+float(extra)
    radius=int(math.ceil(angular/TWOPI*TICKS))+1
    return {"timing_claim":x,"minimum_source_phase_radius_u16":radius,
            "external_physical_bound_independently_authenticated":False,
            "timing_state":"CONSISTENT_WITH_DECLARED_PULSE_OBSERVATIONS_NOT_FUTURE_CERTIFIED"}


def single_bin(phase,radius):
    if type(phase) is not int or type(radius) is not int or not 0<=phase<=65535 or radius<0:
        fail("invalid fine phase angle")
    if radius>=512:return None
    a=((phase-radius)%TICKS)//BIN_TICKS
    b=((phase+radius)%TICKS)//BIN_TICKS
    return a if a==b else None


def map_digest(mapping,quarantined):
    body=json.dumps({"bins":{str(i):mapping[i] for i in sorted(mapping)},
                     "quarantined":sorted(quarantined)},
                    sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(body).hexdigest()


def allowed_after(hypotheses,step,column,mapping,maxerr=2,slip=1):
    if maxerr!=2 or slip!=1:fail("unsupported frozen finite camera uncertainty grammar")
    remaining=[]
    for h in hypotheses:
        possible=[(h+step+d)%64 for d in (-1,0,1)]
        # A map hole cannot be treated as contrary evidence.
        if any(p not in mapping for p in possible):
            remaining.append(h)
        elif min((column^mapping[p]).bit_count() for p in possible)<=maxerr:
            remaining.append(h)
    return remaining


def separates_pair(h,k,step,mapping):
    indices_h=[(h+step+d)%64 for d in (-1,0,1)]
    indices_k=[(k+step+d)%64 for d in (-1,0,1)]
    if any(i not in mapping for i in indices_h+indices_k):
        return False
    return min((mapping[i]^mapping[j]).bit_count()
               for i in indices_h for j in indices_k)>4


def inspect(bundle):
    m=check_manifest(bundle,"nav_manifest.json","NAVIGATION",
                     ("sensors.jsonl","decisions.jsonl","timing.json"))
    comparator=m.get("conventional_visual_baseline")
    if (not isinstance(comparator,dict) or
        set(comparator)!={"name","source_sensor_sha256","source_code_sha256",
                          "no_encoder_input","frozen_before_capture"} or
        not isinstance(comparator["name"],str) or not comparator["name"].strip() or
        comparator["source_sensor_sha256"]!=m["files"]["sensors.jsonl"]["sha256"] or
        not SHA_RE.fullmatch(str(comparator["source_code_sha256"])) or
        comparator["no_encoder_input"] is not True or
        comparator["frozen_before_capture"] is not True):
        fail("conventional vision+gyro baseline not pinned to identical sensor source")
    sensors=read_lines(Path(bundle)/"sensors.jsonl")
    camera,max_gyro,first_gyro=camera_source(sensors)
    bound=timing_evidence(bundle,m,sensors,max_gyro)
    decisions=read_lines(Path(bundle)/"decisions.jsonl")
    # No source GT or encoder input even accidentally.
    by_camera={v["seq"]:v for v in camera.values()}
    mapping={};quarantined=set();used_firstturn_cameras=set()
    pending={};last_match=None
    frozen=False; freeze_at=None
    samples=[]
    stats={"firstturn_captures":0,"firstturn_skipped_uncertain":0,
           "firstturn_quarantined":0,"visual_matches":0,"unknown_matches":0,
           "separating_requests":0,"requests_acquired":0,
           "warranted_estimates":0,"unknown_estimates":0,
           "occluded_columns":sum(c["status"]=="OCCLUDED" for c in camera.values())}
    previous_candidates=None
    last_decision_t=-1
    for d in decisions:
        kind=d.get("kind")
        if kind not in ALLOWED_CAPTURE:fail("unrecognized estimator evidence event")
        ts=d["t_ns"]
        if ts<=last_decision_t:fail("noncausal navigation trace timestamps")
        last_decision_t=ts
        if ts<sensors[0]["t_ns"] or ts>sensors[-1]["t_ns"]:
            fail("decision outside authenticated sensor time domain")
        if kind=="MAP_CAPTURE":
            if frozen:fail("map modified after first-turn freeze")
            cam=by_camera.get(d.get("camera_seq"))
            if not cam or cam["t_ns"]>ts:fail("map capture from missing/future camera")
            # All asserted first-turn phase bins must agree with a causal
            # integration of the gyro-only source; no encoder-oracle phase.
            if cam["seq"] in used_firstturn_cameras:
                fail("source camera observation reused to create map evidence")
            used_firstturn_cameras.add(cam["seq"])
            if cam["_causal_gyro_angle"] is None:
                fail("camera sample precedes authenticated gyro")
            rad=d.get("radius_u16")
            phase=d.get("phase_u16")
            if type(phase) is not int or not 0<=phase<TICKS:
                fail("invalid source reported camera phase")
            predicted=int(round((cam["_causal_gyro_angle"]%TWOPI)*TICKS/TWOPI))%TICKS
            shortest=min((predicted-phase)%TICKS,(phase-predicted)%TICKS)
            if shortest>rad+2:
                fail("reported firstturn source phase disagrees with causal gyro integral")
            if type(rad) is not int or rad<bound["minimum_source_phase_radius_u16"]:
                fail("unjustifiably tight reported source phase interval")
            idx=single_bin(phase,rad)
            if cam["status"]!="OK":idx=None
            # These are exact finite-model decisions, not sensor authority.
            disposition=d.get("disposition")
            if idx is None:
                if disposition!="UNKNOWN":fail("ambiguous firstturn index was accepted")
                stats["firstturn_skipped_uncertain"]+=1
            elif idx in quarantined:
                if disposition!="CONFLICT":fail("quarantined source bin reused")
            elif idx not in mapping:
                if disposition!="ACCEPTED":fail("firstturn valid new bin discarded or mislabeled")
                mapping[idx]=cam["column_u16"]
                stats["firstturn_captures"]+=1
            elif (mapping[idx]^cam["column_u16"]).bit_count()>2:
                if disposition!="CONFLICT":fail("first-turn contradictory duplicate accepted")
                del mapping[idx]
                quarantined.add(idx)
                stats["firstturn_quarantined"]+=1
            else:
                if disposition!="DUPLICATE":fail("consistent duplicate mislabeled")
        elif kind=="FREEZE":
            if frozen or not mapping:fail("empty, duplicate or unqualified reference freeze")
            gyro_prior=[s for s in sensors if s["t_ns"]<=ts and s["kind"]=="GYRO"]
            if not gyro_prior or abs(gyro_prior[-1]["_causal_gyro_angle"])<TWOPI:
                fail("first gyro-integrated revolution not completed at freeze")
            if d.get("map_sha256")!=map_digest(mapping,quarantined):
                fail("frozen map commitment changed")
            frozen=True;freeze_at=ts
        elif kind=="REQUEST":
            if not frozen:fail("future evidence request before map freeze")
            h=d.get("hypotheses")
            step=d.get("step_bins")
            if not (isinstance(h,list) and len(h)>=2 and h==sorted(set(h))
                    and all(type(x) is int and 0<=x<64 for x in h)
                    and type(step) is int and 0<=step<64):
                fail("invalid prospective heading-distinction request")
            has_witness=any(separates_pair(a,b,step,mapping)
                            for i,a in enumerate(h) for b in h[i+1:])
            if d.get("witness_predicted") is not has_witness:
                fail("unsupported claimed separating observation")
            pending[d["seq"]]={"time":ts,"step":step,"hypotheses":h,"witness":has_witness}
            if has_witness:stats["separating_requests"]+=1
        elif kind=="MATCH":
            if not frozen:fail("observed matching before map freeze")
            cam=by_camera.get(d.get("camera_seq"))
            if not cam or cam["t_ns"]>ts or cam["t_ns"]<=freeze_at:
                fail("match has no post-firstturn causal camera reading")
            if cam["status"]!="OK":fail("occluded column used as visual match")
            h=d.get("before");hafter=d.get("after");step=d.get("step_bins")
            if (not isinstance(h,list) or not h or
                h!=sorted(set(h)) or not all(type(x) is int and 0<=x<64 for x in h)
                or type(step) is not int or not 0<=step<64):
                fail("invalid candidate heading support")
            if previous_candidates is not None and h!=previous_candidates:
                fail("candidate support silently introduced or discarded")
            expected=allowed_after(h,step,cam["column_u16"],mapping)
            if hafter!=expected:fail("visual evidence cannot justify claimed candidate elimination")
            previous_candidates=expected
            stats["visual_matches"]+=1
            if len(expected)!=1:stats["unknown_matches"]+=1
            last_match={"t_ns":ts,"camera_seq":cam["seq"],
                        "candidates":expected,"step":step}
            if d.get("request_seq") is not None:
                rq=pending.pop(d["request_seq"],None)
                if not rq or not rq["witness"] or rq["step"]!=step or rq["time"]>=cam["t_ns"]:
                    fail("acquired witness not causally tied to a valid prior request")
                stats["requests_acquired"]+=1
        elif kind=="WITHDRAW":
            if d.get("reason") not in ("OCCLUSION","AMBIGUOUS","CONFLICT","TIMING","STALE"):
                fail("unsupported authority withdrawal reason")
            last_match=None
        elif kind=="ESTIMATE":
            fused=d.get("fused_heading_rad")
            comparator_heading=d.get("conventional_visual_heading_rad")
            corr=d.get("correction_delta_rad")
            auth=d.get("authority")
            if (type(fused) not in (int,float) or type(corr) not in (int,float)
                or type(comparator_heading) not in (int,float) or
                not math.isfinite(fused) or not math.isfinite(corr) or
                not math.isfinite(comparator_heading)
                or auth not in ("UNKNOWN","WARRANTED")):
                fail("invalid heading estimate")
            # Strictly causal gyro-only conventional baseline, ZOH held at last
            # seen original gyro sample. Its full calculation has no encoder.
            prev=[s for s in sensors if s["kind"]=="GYRO" and s["t_ns"]<=ts]
            if not prev:fail("heading estimate precedes first measured gyro")
            last_gyro=prev[-1]
            gyro=last_gyro["_causal_gyro_angle"]+(ts-last_gyro["t_ns"])*1e-9*last_gyro["omega_rad_s"]
            claimed=d.get("support_camera_seq")
            fresh=(last_match is not None and
                   len(last_match["candidates"])==1 and
                   last_match["camera_seq"]==claimed and
                   last_match["t_ns"]<=ts)
            # Occlusion or unmatched camera after the last validating
            # observation invalidates its claim for new corrections.
            if fresh:
                for c in by_camera.values():
                    if last_match["t_ns"]<c["t_ns"]<=ts:
                        fresh=False
                        break
            if auth=="WARRANTED":
                if not frozen or not fresh:
                    fail("applied visual correction unsupported by fresh unique evidence")
                stats["warranted_estimates"]+=1
            else:
                if abs(corr)>1e-12 or claimed is not None:
                    fail("UNKNOWN estimate claimed a fresh visual correction")
                stats["unknown_estimates"]+=1
            samples.append({"t_ns":ts,"gyro_heading_rad":gyro,
                            "conventional_visual_heading_rad":float(comparator_heading),
                            "fused_heading_rad":float(fused),
                            "authority":auth,
                            "correction_delta_rad":float(corr)})
        else:fail("invalid estimator event")
    if not frozen or not samples or not any(x["t_ns"]>freeze_at for x in samples):
        fail("missing actual firstturn freeze or postfirstturn output")
    return {
        "schema":VERSION,"capture_id":m["capture_id"],
        "capture_mode":m["mode"],"input_nav_manifest_sha256":sha(Path(bundle)/"nav_manifest.json"),
        "input_hashes":{n:m["files"][n]["sha256"] for n in m["files"]},
        "source_clock_claim":bound["timing_state"],
        "source_phase_minimum_radius_u16":bound["minimum_source_phase_radius_u16"],
        "physical_bound_independently_authenticated":False,
        "firstturn_map_frozen_sha256":map_digest(mapping,quarantined),
        "firstturn_freeze_t_ns":freeze_at,
        "firstturn_map_bins":len(mapping),
        "firstturn_quarantined_bins":sorted(quarantined),
        "role_isolation":"NAVIGATION_ONLY_NO_ENCODER_BYTES",
        "conventional_visual_baseline":{
            "name":comparator["name"],
            "source_sensor_sha256":comparator["source_sensor_sha256"],
            "source_code_sha256":comparator["source_code_sha256"],
            "identical_sensor_input_declared":True,
            "implementation_and_sensor_input_independently_attested":False},
        "policy_consistent_with_declared_finite_model":True,
        "physical_visual_heading_accuracy_verified":False,
        "navigation_samples":samples,"statistics":stats,
        "physical_acceptance":"UNKNOWN_PENDING_INDEPENDENT_ENCODER_AND_HARDWARE_ATTESTATION",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--navigation-bundle",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    try:r=inspect(args.navigation_bundle)
    except (ValueError,KeyError,TypeError,FileNotFoundError) as e:
        r={"schema":VERSION,"physical_acceptance":"REJECTED_INVALID_NAVIGATION_EVIDENCE",
           "error":str(e),"physical_visual_heading_accuracy_verified":False}
        args.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
        print("NAVIGATION_GATE_REJECTED",str(e))
        raise SystemExit(1)
    args.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print("NAVIGATION_EVIDENCE_BOUNDARY",json.dumps({k:r[k] for k in
          ("capture_id","firstturn_map_bins","statistics","physical_acceptance")},sort_keys=True))


if __name__=="__main__":
    main()
