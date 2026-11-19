"""Real #282 artifact bytes -> original #261 BoundaryWarrant resolver (research-only)."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import copy, hashlib, json, os

from mathgraph_check.boundary_warrant import (
    Subject, Obligation, Relation, Verification, Conclusion, Dependency,
    BoundaryWarrant, required_dependencies, scope_identity, admitted_route, resolve_boundaries
)
from mathgraph_check.warrant_resolution import Receipt

PR_SHA="2b0e21e94e64ca54ff35c1d4572c60b3b6049720"
SPEC={"source":"61cdfdb56da7463f3fb220381649c011efb6d0a5177a841255540186f2b3ea15",
      "challenger":"cc16408a46782573397b8d6f06857fb011651adac90d1c8a9379213c9aef7100"}
MAP="dc8649dfeefbccd35f1df8afbf25f8e14b10cc0ff97551b8b6aa79724f79ea2f"
E=Path(os.environ.get("EVIDENCE_DIR","rocket-evidence"))
Q=Path(os.environ.get("QUAL_DIR","rocket-qualification"))
SOURCE=Path(os.environ.get("SOURCE_FILE","pinned-rocket-source.mjs"))
POLICY=b"MathGraph rocket native finite witness, advisory only, no owner grant; v0.1"
H=lambda b: hashlib.sha256(b).hexdigest()

def original_files():
    data={}
    for p in E.iterdir():
        if p.is_file(): data[p.name]=p.read_bytes()
    for p in Q.iterdir():
        if p.is_file(): data[p.name]=p.read_bytes()
    if SOURCE.is_file(): data["__source_code__"]=SOURCE.read_bytes()
    return data

def qualified_source(data):
    native=json.loads(data["native-result.json"])
    separate=json.loads(data["independent-qualification.json"])
    assert native["source_pins"]=={
        "fret":"cf0f913cc15c41705e803593297e89cd6056b839",
        "r2u2":"2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a"}
    assert native["source_sha256"]==SPEC
    assert native["map_sha256"]==MAP
    assert native["native_oracle_positions"]==64
    assert native["overall"]=="UNKNOWN" and native["auto_repair"]=="DENIED"
    assert native["repair_authority"]=="UNKNOWN"
    assert separate["overall"]=="UNKNOWN" and separate["repair"]=="DENIED"
    assert separate["permission"]=="ADVISORY_ONLY" and separate["positions"]==64
    assert separate["artifact_sha256"]==native["binary_sha256"]
    assert separate["monitor_sha256"]==native["monitor_executable_sha256"]
    assert not any(x in native for x in ("owner_approved","operator","authorized","semantic_truth"))
    assert len(native["observations"])==8
    for v in SPEC:
        assert H(data[v+".c2po"])==SPEC[v]
        assert H(data[v+".map"])==MAP
        assert H(data[v+".bin"])==native["binary_sha256"][v]
    assert "__source_code__" in data
    return native

def case_receipt(data, variant, scenario):
    subject=Subject("metalogiclabs/mathgraph",PR_SHA,H(data["__source_code__"]))
    obligation=Obligation(
        id="rocket-finite:"+variant+":"+scenario,
        statement="Finite archived native verdict agrees with declared rocket source truth table; no mission grant",
        authority="STUDY_DECLARATION_NOT_OPERATIONAL_OWNER",
        authority_sha256=H(data["source-declaration.json"]))
    rel=Relation(kind="native_finite_correspondence",
                 statement="Bounded archived oracle agreement, exact source/map/binary and named scenario",
                 parameters=(("scenario",scenario),("variant",variant)))
    ver=Verification(method="native",verifier_id="rocket-pr282-ci:"+variant+":"+scenario,
                     policy_sha256=H(POLICY),
                     assumptions=("four complete 8-tick scenarios, source/verification pinned",
                                  "no owner consent, no automatic repair"),
                     receipt_id="rocket-native-44611662927:"+variant+":"+scenario)
    evid_names=(variant+".c2po",variant+".map",variant+".bin",
                scenario+".csv",scenario+".json","source-declaration.json",
                "native-result.json","independent-qualification.json")
    dependencies=required_dependencies(subject,obligation,rel,ver)+tuple(
        Dependency("evidence","actual:"+n,H(data[n])) for n in evid_names)
    warrant=BoundaryWarrant(subject,obligation,rel,ver,
        Conclusion("SUPPORTED",("exact original archived finite case only",
                                "no independently ratified owner requirement",
                                "no new native execution in this integration job")),
        dependencies)
    receipt=Receipt(ver.receipt_id,"native",scope_identity(warrant))
    admitted_route(warrant,receipt)
    return warrant,receipt

def live_dependencies(data,policy,admitted):
    current={}
    for warrant,_ in admitted:
        subj=replace(warrant.subject,source_sha256=H(data["__source_code__"]))
        obl=replace(warrant.obligation,authority_sha256=H(data["source-declaration.json"]))
        ver=replace(warrant.verification,policy_sha256=H(policy))
        for dep in required_dependencies(subj,obl,warrant.relation,ver):
            if dep.key in current:
                assert current[dep.key]==dep.sha256
            current[dep.key]=dep.sha256
        for dep in warrant.dependencies:
            if dep.role=="evidence":
                current[dep.key]=H(data[dep.key[len("actual:"):]])
    return current

def verdict(data,policy,admitted):
    result=resolve_boundaries(admitted,live_dependencies(data,policy,admitted))
    keys=[admitted_route(w,r)[0].id for w,r in admitted]
    return [result.states[k] for k in keys]

def conventional(data,policy,admitted):
    # Fully informed byte/dependency checklist: same evidence, no restricted capability.
    current=live_dependencies(data,policy,admitted)
    return ["WARRANTED_BOUNDED_NATIVE" if all(
        current.get(dep.key)==dep.sha256 for dep in w.dependencies)
        else "UNKNOWN" for w,_ in admitted]

def main():
    data=original_files()
    qualified_source(data)
    admitted=[case_receipt(data,"source","simultaneous"),
              case_receipt(data,"challenger","next_tick")]
    good="WARRANTED_BOUNDED_NATIVE";bad="UNKNOWN"
    variants={}
    variants["original"]=(data,POLICY,[good,good])
    src=copy.deepcopy(data);src["source.bin"]+=b"\0"
    variants["source_binary_changed"]=(src,POLICY,[bad,good])
    b=copy.deepcopy(data);b["challenger.c2po"]+=b"\n--changed\n"
    variants["challenger_spec_changed"]=(b,POLICY,[good,bad])
    c=copy.deepcopy(data);c["__source_code__"]+=b"\n// changed upstream source\n"
    variants["source_code_changed_stale_metadata"]=(c,POLICY,[bad,bad])
    d=copy.deepcopy(data);d["source-declaration.json"]+=b"\n"
    variants["obligation_changed"]=(d,POLICY,[bad,bad])
    e=copy.deepcopy(data);e["next_tick.csv"]=e["next_tick.csv"].replace(b"1,0",b"1,1",1)
    variants["trace_changed"]=(e,POLICY,[good,bad])
    variants["policy_changed"]=(data,POLICY+b" changed",[bad,bad])
    variants["restoration"]=(data,POLICY,[good,good])
    observed={}
    for name,(snapshot,policy,expected) in variants.items():
        actual=verdict(snapshot,policy,admitted)
        comparator=conventional(snapshot,policy,admitted)
        assert actual==expected,(name,actual,expected)
        assert comparator==actual,(name,comparator,actual)
        observed[name]=actual
    tampered=copy.deepcopy(data)
    d=json.loads(tampered["native-result.json"])
    d["owner_approved"]=True
    tampered["native-result.json"]=json.dumps(d).encode()
    try:
        qualified_source(tampered)
    except AssertionError:
        observed["forged_inband_owner_approval"]="REFUSED"
    else:
        raise AssertionError("in-band owner authority was accepted")
    print(json.dumps({"status":"WARRANTED_BOUNDED_INTEGRATION_MECHANICS",
          "source":"#261 original resolver @ 1b06e7fb",
          "evidence":"#282 original 2-job artifacts @ 2b0e21e",
          "cases":observed,"baseline":"EQUAL_INFORMATION_TIE",
          "native_reexecution_this_job":False,
          "external_owner_grant":"UNKNOWN",
          "repair_permission":"DENIED"},sort_keys=True))

if __name__=="__main__": main()
