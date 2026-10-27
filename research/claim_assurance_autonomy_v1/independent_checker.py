#!/usr/bin/env python3
"""MathGraph independent autonomous-source-to-claim adjudicator, bounded.

No imports from native producer execute.py or the target rover code. This
checker reads separately retained source code, author tests and native output.
Verdicts apply to *selected documented claim/test identity*, not flight safety.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

REPO="nasa-jpl/osr-rover-code"
PIN="7aaf18512c9e8a997931f0caae28b63c8c6e9a78"
CODE="ROS/osr_control/osr_control/kinematics.py"
TEST="ROS/osr_control/test/test_kinematics.py"
CODE_BLOB="38e35e5823111808177d78427a1595d27d0ebe00"
TEST_BLOB="5860abcdd690f4c62f912e79ebfdd84d0817b4ae"
CLAIM_ID="OSR_KINEMATICS_WHEEL_SPEED_BOUND"
TEST_ID="test_body_speed_keeps_every_wheel_within_max_vel"
REVERSE_ID="test_body_speed_for_radius_clamps_reverse"
UNRELATED_ID="test_twist_to_radius_infinite_when_no_yaw"
METHOD="RoverKinematics.body_speed_for_radius"
EXPECT_GUARD="return math.copysign(limited, commanded_linear_x)"
DIMS=(0.177,0.310,0.274,0.253,0.075)
RPM=223.0

class Inconsistent(Exception): pass
class Missing(Exception): pass

def sha(data:bytes)->str: return hashlib.sha256(data).hexdigest()
def ensure(x, reason):
    if not x: raise Inconsistent(reason)
def text(p:Path)->str:
    if not p.is_file(): raise Missing("MISSING_REQUIRED_EVIDENCE:"+p.name)
    return p.read_text(encoding="utf-8")
def checkout_sha(root:Path)->str:
    return subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
def gitblob(root:Path,p:str)->str:
    return subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD:"+p],text=True).strip()

def extract_author_intent(root:Path)->dict:
    src=text(root/CODE); tests=text(root/TEST)
    impl=ast.parse(src); testast=ast.parse(tests)
    k=next((t for t in impl.body if isinstance(t,ast.ClassDef) and
            t.name=="RoverKinematics"),None)
    ensure(k is not None,"MISSING_AUTHENTIC_IMPLEMENTATION_CLASS")
    methods={x.name:x for x in k.body if isinstance(x,ast.FunctionDef)}
    ensure("body_speed_for_radius" in methods and
           "calculate_drive_velocities" in methods,
           "MISSING_AUTHENTIC_KINEMATICS_METHOD")
    doc=ast.get_docstring(methods["body_speed_for_radius"]) or ""
    ensure("every drive wheel stays within max_vel" in doc,
           "CLAIM_NOT_IN_AUTHOR_SOURCE_DOCSTRING")
    fn={x.name:x for x in testast.body if isinstance(x,ast.FunctionDef)}
    for name in (TEST_ID,REVERSE_ID,UNRELATED_ID):
        ensure(name in fn,"MISSING_AUTHORED_TEST_ID:"+name)
    selected=ast.get_source_segment(tests,fn[TEST_ID]) or ""
    ensure(all(x in selected for x in (
        "kin.body_speed_for_radius(", "kin.calculate_drive_velocities(",
        "assert fastest == pytest.approx(kin.max_vel)")),
        "CLAIM_TEST_HAS_NO_FULL_SPEED_BOUND_CHECK")
    implpart=ast.get_source_segment(src,methods["body_speed_for_radius"]) or ""
    ensure(implpart.count(EXPECT_GUARD)==1,"SOURCE_SPEED_CLAMP_MISSING")
    return {"claim_author":"upstream source docstring",
            "requirement_method":METHOD,"test_id":TEST_ID,
            "test_sha256":sha(selected.encode()),"implementation_sha256":sha(implpart.encode())}

def validate_finite(o:dict):
    dims=DIMS; d1,d2,d3,d4,wheel_radius=dims
    maxv=wheel_radius*RPM/60.0*2.0*math.pi
    ensure(o.get("cases")==70,"GRID_SIZE_CHANGED")
    ensure(math.isclose(o.get("max_vel_mps",float("nan")),maxv,
                        rel_tol=1e-12,abs_tol=1e-12),"MAX_VEL_REF_CHANGED")
    rows=o.get("measurements")
    ensure(isinstance(rows,list) and len(rows)==70,"MISSING_RAW_GRID_RECORDS")
    digest=sha(json.dumps(rows,sort_keys=True,separators=(",",":")).encode())
    ensure(digest==o.get("grid_sha256"),"MEASUREMENT_DIGEST_BAD")
    radii=(-6.39,-3.0,-1.0,-0.6,-0.45,0.45,0.6,1.0,3.0,6.39)
    speeds=(-10.,-1.,-0.4,0.,0.4,1.,10.)
    expected={(r,s) for r in radii for s in speeds}
    used=set()
    for row in rows:
        radius,cmd=row.get("radius"),row.get("commanded")
        ensure((radius,cmd) in expected and (radius,cmd) not in used,
               "GRID_CASE_FORGED_OR_DUPLICATE")
        used.add((radius,cmd))
        out=row.get("limited"); wheel=row.get("max_wheel")
        ensure(isinstance(out,(int,float)) and isinstance(wheel,(int,float))
               and math.isfinite(out) and math.isfinite(wheel),
               "NONFINITE_WHEEL_OBSERVATION")
        r=abs(radius)
        geometric=max(math.hypot(r+d1,d3),r+d4)
        independent_cap=r/geometric*maxv
        expected_speed=0. if cmd==0. else math.copysign(min(abs(cmd),independent_cap),cmd)
        ensure(math.isclose(out,expected_speed,abs_tol=1e-10,rel_tol=1e-10),
               "INDEPENDENT_CLAMP_BOUND_CHANGED")
        ensure(wheel<=maxv+1e-10,"AUTHENTIC_WHEEL_LIMIT_EXCEEDED")
        # A separate geometric radius bound, not imported production logic.
        theoretical_max=abs(out)*geometric/r
        ensure(math.isclose(wheel,theoretical_max,rel_tol=1e-9,abs_tol=1e-9),
               "MEASURED_WHEEL_GEOMETRY_DISAGREES")
    ensure(used==expected,"GRID_INCOMPLETE")

def validate_native(n:dict,folder:Path,root:Path)->dict:
    ensure(n.get("protocol")=="MATHGRAPH_AUTONOMOUS_CLAIM_TRANSFER_V1",
           "UNRECOGNIZED_NATIVE_EVIDENCE")
    ensure(n.get("external_repository")==REPO and n.get("source_sha")==PIN,
           "SOURCE_IDENTITY_MISMATCH")
    ensure(n.get("source_blob_git")==CODE_BLOB and
           n.get("test_blob_git")==TEST_BLOB,"SOURCE_BLOB_ID_MISMATCH")
    ensure(gitblob(root,CODE)==CODE_BLOB and gitblob(root,TEST)==TEST_BLOB,
           "CHECKOUT_BLOBS_DIFFER")
    ensure(n.get("source_sha256")==sha((root/CODE).read_bytes()) and
           n.get("test_sha256")==sha((root/TEST).read_bytes()),
           "SOURCE_BYTES_NOT_FROM_PIN")
    verified=extract_author_intent(root)
    actual=n.get("source_test_alignment") or {}
    ensure(actual.get("test_id")==TEST_ID and
           actual.get("test_anchor_sha256")==verified["test_sha256"] and
           actual.get("implementation_anchor_sha256")==verified["implementation_sha256"],
           "NATIVE_REPORT_MISATTRIBUTES_TEST_OR_METHOD")
    for key in ("real_author_test_run","protected_author_test_run"):
        item=n.get(key) or {}
        ensure(item.get("passed") is True and item.get("exit")==0,
               "NATIVE_AUTHOR_TEST_NOT_GREEN:"+key)
        data=text(folder/item.get("log","")).encode()
        ensure(sha(data)==item.get("log_sha256"),"AUTHOR_TEST_LOG_TAMPERED:"+key)
        ensure(re.search(rb"\b[0-9]+ passed\b",data) is not None,
               "NO_AUTHENTIC_PYTEST_PASS:"+key)
    mutant=n.get("induced_local_mutation") or {}
    ensure(mutant.get("original_protected_case_failed") is True and
           mutant.get("passed") is False and mutant.get("exit")!=0,
           "INDUCED_FAULT_NOT_DETECTED")
    mutlog=text(folder/mutant.get("log","")).encode()
    ensure(sha(mutlog)==mutant.get("log_sha256") and
           b"FAILED" in mutlog and TEST_ID.encode() in mutlog,
           "MUTANT_TEST_LOG_INVALID")
    ensure(EXPECT_GUARD in text(root/CODE) and
           "return commanded_linear_x" in text(folder/"mutation.diff.txt"),
           "MUTATION_NOT_CAUSAL")
    validate_finite(n.get("finite_independent_geometry_oracle") or {})
    return verified

def verdict(record:dict|None, root:Path, folder:Path, claim:dict)->dict:
    """Claim-specific permission. UNKNOWN never permits generalized use."""
    if record is None:
        return {"verdict":"WITHDRAWN","reason":"MISSING_NATIVE_REPORT"}
    if claim.get("source_sha")!=PIN or record.get("source_sha")!=PIN:
        return {"verdict":"WITHDRAWN","reason":"STALE_SOURCE_REVISION"}
    if claim.get("evidence_test_id")!=TEST_ID:
        return {"verdict":"MISMATCH","reason":"WRONG_TEST_ATTRIBUTED_TO_REQUIREMENT"}
    if claim.get("claim_id")!=CLAIM_ID:
        return {"verdict":"UNKNOWN","reason":"CLAIM_NOT_BOUND_TO_SOURCE_TEST"}
    if claim.get("scope")!="BOUNDED_AUTHOR_TEST_AND_FINITE_GEOMETRY":
        return {"verdict":"UNKNOWN","reason":"STRONGER_SAFETY_OR_FLIGHT_CLAIM_UNTESTED"}
    try:
        checked=validate_native(record,folder,root)
    except Missing as exc:
        return {"verdict":"WITHDRAWN","reason":str(exc)}
    except (Inconsistent,ValueError,TypeError) as exc:
        return {"verdict":"REJECTED_EVIDENCE","reason":str(exc)}
    return {"verdict":"WARRANTED_BOUNDED","reason":"EXACT_SOURCE_TEST_AND_FINITE_GEOMETRY_REPLAY",
            "test_anchor_sha256":checked["test_sha256"],
            "scope":"software-level named tests and measured finite grid only"}

def run(root:Path,folder:Path)->dict:
    ensure(checkout_sha(root)==PIN,"UPSTREAM_CHECKOUT_NOT_PINNED")
    record=json.loads(text(folder/"native-observation.json"))
    good={"claim_id":CLAIM_ID,"source_sha":PIN,
          "evidence_test_id":TEST_ID,
          "scope":"BOUNDED_AUTHOR_TEST_AND_FINITE_GEOMETRY"}
    positive=verdict(record,root,folder,good)
    ensure(positive["verdict"]=="WARRANTED_BOUNDED","POSITIVE_NOT_WARRANTED:"+str(positive))
    # These are claims against *authentic* source/results, with one changed
    # premise at a time. They test the checker, not extra JPL rover bugs.
    probes=[
       ("wrong_test_attribution",{**good,"evidence_test_id":UNRELATED_ID},
        "MISMATCH"),
       ("too_broad_flight_safety_claim",
        {**good,"scope":"FLIGHT_HARDWARE_END_TO_END_SAFETY"},"UNKNOWN"),
       ("stale_source_revision",{**good,"source_sha":"0"*40},"WITHDRAWN"),
       ("different_requirement_id",{**good,"claim_id":"E_STOP_PREVENTS_DRIVE"},
        "UNKNOWN"),
       ("withheld_native_report",good,"WITHDRAWN"),
    ]
    decisions=[]
    for name,claim,want in probes:
        got=verdict(None if name=="withheld_native_report" else record,root,folder,claim)
        ensure(got["verdict"]==want,"NEGATIVE_PROBE_NOT_FAIL_CLOSED:"+name+":"+str(got))
        decisions.append({"case":name,"verdict":got["verdict"],"reason":got["reason"]})
    altered=copy.deepcopy(record)
    altered["induced_local_mutation"]["exit"]=0
    d=verdict(altered,root,folder,good)
    ensure(d["verdict"]=="REJECTED_EVIDENCE","COUNTERFEIT_MUTANT_PASS_NOT_REJECTED")
    decisions.append({"case":"forged_mutant_exit_success",**d})
    altered=copy.deepcopy(record)
    altered["finite_independent_geometry_oracle"]["measurements"][0]["max_wheel"]*=10
    d=verdict(altered,root,folder,good)
    ensure(d["verdict"]=="REJECTED_EVIDENCE","FORGED_WHEEL_SPEED_NOT_REJECTED")
    decisions.append({"case":"forged_native_wheel_measurement",**d})
    altered=copy.deepcopy(record)
    altered["test_blob_git"]="f"*40
    d=verdict(altered,root,folder,good)
    ensure(d["verdict"]=="REJECTED_EVIDENCE","WRONG_TEST_BLOB_NOT_REJECTED")
    decisions.append({"case":"wrong_test_blob_identity",**d})
    # An unaugmented pytest exit code is a comparison baseline, not a fully
    # informed reviewer. It is unchanged under a wrong attribution.
    conventional={"name":"unaugmented_original_pytest_ci_exit_only",
                  "correct_claim":"GREEN", "wrong_target_claim":"GREEN",
                  "comparison_scope":"no source-to-claim binding at all",
                  "fair_expert_baseline_compared":False}
    result={"protocol":"MATHGRAPH_AUTONOMOUS_CLAIM_ASSURANCE_V1",
            "evidence_repo":f"{REPO}@{PIN}",
            "documented_claim_id":CLAIM_ID,
            "source":CODE,"author_test":TEST,
            "original_native_controls_pass":True,
            "selected_positive":positive,
            "adversarial_claim_and_evidence_controls":decisions,
            "adversarial_count":len(decisions),
            "authentic_original_test_baseline":conventional,
            "scientific_limits":[
                "This is a public educational JPL Open Source Rover, not Endurance mission flight software.",
                "The requirement is sourced from a code docstring and original unit tests, not a signed mission assurance requirement.",
                "No certified safety case, motor hardware/ROS execution, real-time liveness, proof for all real input values or end-to-end NASA approval.",
                "A fully informed conventional reviewer may detect all these mismatches; added commercial value is not independently measured.",
                "Failures of locally mutated implementations are induced controls, not reported defects in JPL upstream."],
            "upstream_write":False,"external_contact":False,
            "release_permission":"NOT_AUTHORIZED"}
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--checkout",type=Path,required=True)
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    result=run(a.checkout,a.evidence)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("MATHGRAPH_ROVER_CLAIM_ASSURANCE_BOUNDED_WARRANTED",
          json.dumps({"original":result["selected_positive"]["verdict"],
              "negative":result["adversarial_count"],
              "actual_source":result["evidence_repo"],
              "authority":"software test + finite observation only"},sort_keys=True))
if __name__=="__main__":
    main()
