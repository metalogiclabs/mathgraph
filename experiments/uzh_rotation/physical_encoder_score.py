"""Independent OPTICAL ENCODER referee for MathGraph physical evidence.

A separate process/job receives only a navigation-audit output and encoder
bundle. Navigation-audit has no encoder API or path, preventing use of ground
truth for estimation. Encoder interpolation and gyro/fused error scoring are
recomputed here from immutable referenced records. This does not by itself
authenticate physical capture or guarantee a future timing-error bound.
"""
import argparse
import bisect
import json
import math
from pathlib import Path

from physical_evidence_gate import (
    VERSION,check_manifest,sha,strict_json,fail,
)

TWOPI=2*math.pi


def encoder_records(bundle,manifest):
    p=Path(bundle)/"encoder.jsonl"
    xs=[]
    for i,line in enumerate(p.read_text(encoding="utf-8").splitlines()):
        try:d=json.loads(line,parse_constant=lambda _:fail("nonfinite encoder data"))
        except json.JSONDecodeError as e:fail(str(e))
        if (not isinstance(d,dict) or set(d)!={"seq","t_ns","ticks_unwrapped"} or
                d["seq"]!=i or type(d["t_ns"]) is not int or
                type(d["ticks_unwrapped"]) is not int):
            fail("invalid optical encoder schema")
        if xs and d["t_ns"]<=xs[-1]["t_ns"]:
            fail("optical encoder clock is not strictly increasing")
        xs.append(d)
    if len(xs)<12:fail("insufficient independent encoder sample coverage")
    cpr=manifest.get("counts_per_revolution")
    if type(cpr) is not int or cpr<16:
        fail("encoder counts-per-revolution not calibrated")
    diffs=[xs[i+1]["ticks_unwrapped"]-xs[i]["ticks_unwrapped"]
           for i in range(len(xs)-1)]
    direction=1 if xs[-1]["ticks_unwrapped"]>xs[0]["ticks_unwrapped"] else -1
    if any(direction*step<0 for step in diffs):
        fail("encoder-referenced physical turn reversal or source misordering")
    return xs,cpr,direction


def sync_claim(bundle,manifest,records):
    sync=manifest.get("encoder_to_navigation_clock")
    if (not isinstance(sync,dict) or
        set(sync)!={"offset_ns","bound_ns","independent_reference",
                    "source","pulse_pairs","max_interpolation_gap_ns"}):
        fail("missing independent encoder-to-navigation clock source")
    for k in ("offset_ns","bound_ns","max_interpolation_gap_ns"):
        if type(sync[k]) is not int:fail("invalid encoder time calibration")
    if (sync["bound_ns"]<0 or sync["max_interpolation_gap_ns"]<=0 or
        sync["source"]!="independent_reference_pulses" or
        sync["independent_reference"] is not True or
        not isinstance(sync["pulse_pairs"],list) or len(sync["pulse_pairs"])<5):
        fail("encoder clock calibration source is insufficient")
    for pair in sync["pulse_pairs"]:
        if (not isinstance(pair,dict) or set(pair)!={"encoder_ns","navigation_ns"} or
            any(type(pair[k]) is not int for k in pair)):
            fail("invalid encoder timing reference pulse")
        residual=pair["encoder_ns"]+sync["offset_ns"]-pair["navigation_ns"]
        if abs(residual)>sync["bound_ns"]:
            fail("timing sync pulse contradicts asserted encoder offset bound")
    transformed=[x["t_ns"]+sync["offset_ns"] for x in records]
    return transformed,sync


def interp_encoder(t,ts,values,max_gap):
    i=bisect.bisect_left(ts,t)
    if i<len(ts) and ts[i]==t:return float(values[i])
    if i<=0 or i>=len(ts):return None
    if ts[i]-ts[i-1]>max_gap:return None
    frac=(t-ts[i-1])/(ts[i]-ts[i-1])
    return (1-frac)*values[i-1]+frac*values[i]


def rmse(errors):
    return math.sqrt(sum(x*x for x in errors)/len(errors)) if errors else None


def score(nav_audit_path,encoder_bundle):
    nav=strict_json(nav_audit_path)
    if (nav.get("schema")!=VERSION or
        nav.get("role_isolation")!="NAVIGATION_ONLY_NO_ENCODER_BYTES" or
        nav.get("policy_consistent_with_declared_finite_model") is not True or
        nav.get("physical_visual_heading_accuracy_verified") is not False):
        fail("unauthenticated, tampered or unsafe navigation-audit input")
    m=check_manifest(encoder_bundle,"encoder_manifest.json","ENCODER",("encoder.jsonl",))
    if (m["capture_id"]!=nav["capture_id"] or m["mode"]!=nav["capture_mode"]
        or m.get("navigation_manifest_sha256")!=nav["input_nav_manifest_sha256"]):
        fail("cross-role capture identity or original sensor manifest mismatch")
    enc,cpr,direction=encoder_records(encoder_bundle,m)
    times,cal=sync_claim(encoder_bundle,m,enc)
    counts=[x["ticks_unwrapped"] for x in enc]
    recorded_turns=direction*(counts[-1]-counts[0])/cpr
    # No scoring alignment is sent back to navigation.
    nav_samples=nav.get("navigation_samples",[])
    if not isinstance(nav_samples,list) or len(nav_samples)<2:
        fail("no substantive navigation heading timeline")
    if nav_samples[0]["t_ns"]<times[0] or nav_samples[-1]["t_ns"]>times[-1]:
        fail("encoder recording does not enclose independent navigator window")
    start=nav_samples[0]
    zero=interp_encoder(start["t_ns"],times,counts,
                        cal["max_interpolation_gap_ns"])
    if zero is None:fail("missing independent encoder gauge anchor")
    # Physical revolution numbers start at ENCODER CAPTURE, not at the first
    # navigation estimate (which may arrive in the middle of revolution one).
    reference_start_tick=counts[0]
    freeze_tick=interp_encoder(nav["firstturn_freeze_t_ns"],times,counts,
                               cal["max_interpolation_gap_ns"])
    freeze_turns=(direction*(freeze_tick-reference_start_tick)/cpr
                  if freeze_tick is not None else None)
    true_firstturn_freeze=(freeze_turns is not None and 1.<=freeze_turns<2.)
    gyro_zero=float(start["gyro_heading_rad"])
    fused_zero=float(start["fused_heading_rad"])
    result_by_rev={}
    excluded=0
    for e in nav_samples:
        t=e["t_ns"]
        reference=interp_encoder(t,times,counts,
                                 cal["max_interpolation_gap_ns"])
        if reference is None:
            excluded+=1
            continue
        ref_rad=(reference-zero)/cpr*TWOPI
        physical_turns=direction*(reference-reference_start_tick)/cpr
        revolution=math.floor(physical_turns)+1
        if revolution not in (2,3,4,5):
            continue
        # Evaluate unwrapped heading displacement in the same reference
        # gauge. This catches multiple-turn slips rather than only modulo 2pi.
        true_delta=ref_rad
        gyro_delta=float(e["gyro_heading_rad"])-gyro_zero
        fused_delta=float(e["fused_heading_rad"])-fused_zero
        if not math.isfinite(gyro_delta) or not math.isfinite(fused_delta):
            fail("non-finite navigator heading")
        group=result_by_rev.setdefault(revolution,{"gyro_errors_deg":[],
                                                   "fused_errors_deg":[],
                                                   "warranted":0,"unknown":0})
        group["gyro_errors_deg"].append(math.degrees(gyro_delta-true_delta))
        group["fused_errors_deg"].append(math.degrees(fused_delta-true_delta))
        group["warranted" if e["authority"]=="WARRANTED" else "unknown"]+=1
    rows={}
    for r in (2,3,4,5):
        x=result_by_rev.get(r)
        rows[str(r)]={
           "samples":len(x["gyro_errors_deg"]) if x else 0,
           "gyro_only_rmse_unwrapped_deg":rmse(x["gyro_errors_deg"]) if x else None,
           "fused_rmse_unwrapped_deg":rmse(x["fused_errors_deg"]) if x else None,
           "warranted_samples":x["warranted"] if x else 0,
           "unknown_samples":x["unknown"] if x else 0,
        }
    all_gyro=[e for x in result_by_rev.values() for e in x["gyro_errors_deg"]]
    all_fused=[e for x in result_by_rev.values() for e in x["fused_errors_deg"]]
    gyro_score=rmse(all_gyro)
    fused_score=rmse(all_fused)
    complete=recorded_turns>=5 and all(rows[str(r)]["samples"]>0 for r in range(2,6))
    reduced=(gyro_score is not None and fused_score is not None
             and fused_score<gyro_score)
    stats=nav["statistics"]
    tests={
        "five_complete_encoder_revolutions":bool(recorded_turns>=5),
        "all_later_revolutions_scored":all(rows[str(r)]["samples"]>0 for r in range(2,6)),
        "gyro_drift_reduced_vs_same_source_gyro_only":bool(reduced),
        "first_turn_map_frozen":nav["firstturn_map_bins"]>0,
        "first_turn_freeze_not_early_or_in_later_turns":true_firstturn_freeze,
        "sensor_ambiguity_was_observed":stats["unknown_matches"]>0,
        "at_least_one_requested_separating_observation_acquired":stats["requests_acquired"]>0,
        "occlusion_was_present":stats["occluded_columns"]>0,
        "timing_pulse_evidence_present":True,
        "all_navigator_estimates_have_bracketed_encoder_truth":excluded==0,
        "timing_bound_independently_physically_certified":False,
        "on_device_encoder_isolation_independently_attested":False,
    }
    if m["mode"]=="FIXTURE":
        verdict="FIXTURE_ONLY_NOT_PHYSICAL_VALIDATION"
    elif complete and all(tests.values()):
        # Should remain unreachable until a separately implemented external
        # hardware/clock attestation verifier exists.
        verdict="CANDIDATE_REQUIRE_INDEPENDENT_HARDWARE_ATTESTATION"
    else:
        verdict="PHYSICAL_CRITERIA_UNMET_OR_UNATTESTED"
    return {
        "schema":VERSION,
        "capture_id":nav["capture_id"],
        "mode":m["mode"],
        "role_separation":"ENCODER_READS_NAVIGATION_VERDICT_ONLY",
        "nav_verdict_sha256":sha(nav_audit_path),
        "source_nav_manifest_sha256":nav["input_nav_manifest_sha256"],
        "original_encoder_sha256":m["files"]["encoder.jsonl"]["sha256"],
        "optical_encoder_ticks_per_rev":cpr,
        "encoder_turns_at_source_firstturn_freeze":freeze_turns,
        "revolutions_indexed_from_encoder_capture_start":True,
        "heading_displacement_gauge_first_navigation_estimate":True,
        "recorded_total_optical_turns":recorded_turns,
        "physical_encoder_source_samples":len(enc),
        "encoder_interpolation_missing_samples":excluded,
        "per_revolution":rows,
        "gyro_only_rmse_unwrapped_deg":gyro_score,
        "visual_fused_rmse_unwrapped_deg":fused_score,
        "observed_improvement_over_gyro_only":bool(reduced),
        "acceptance_tests":tests,
        "independent_score_reproducible_from_immutable_logs":True,
        "hardware_and_future_bound_attestation":"NOT_IMPLEMENTED",
        "physical_acceptance":verdict,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--nav-verdict",type=Path,required=True)
    p.add_argument("--encoder-bundle",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    try:r=score(args.nav_verdict,args.encoder_bundle)
    except (ValueError,KeyError,TypeError,FileNotFoundError) as e:
        args.out.write_text(json.dumps(
            {"schema":VERSION,"physical_acceptance":"REJECTED_INVALID_ENCODER_EVIDENCE",
             "error":str(e)},indent=2,sort_keys=True)+"\n")
        print("ENCODER_REFEREE_REJECTED",str(e))
        raise SystemExit(1)
    args.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print("ENCODER_REFEREE",json.dumps({k:r[k] for k in
          ("capture_id","recorded_total_optical_turns","gyro_only_rmse_unwrapped_deg",
           "visual_fused_rmse_unwrapped_deg","physical_acceptance")},sort_keys=True))


if __name__=="__main__":
    main()
