"""Paired L4YAML/FRET semantic-assurance mechanics on exact pinned source observations.
The same two tests and original six-field Boundary Warrant machinery are used.
Known cases, not blind discovery. Conventional script has equal inputs and may tie.
No human adjudicator or operational owner permission is asserted.
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from dataclasses import asdict
from itertools import combinations
from pathlib import Path

YAML_P = {
    "1_000":"str","1000":"int","0x":"str","0":"int",
    "1.":"float","1.0":"float","true":"bool","hello":"str",
    "0x3A":"int","null":"null",".inf":"float","yes":"str"
}
FRET_SHA="cf0f913cc15c41705e803593297e89cd6056b839"
R2U2_SHA="2875a1dfc0b8cb27c4c4f14bece6b95c3afff91a"
L4_ORIGINAL="4f31fef1f18e48b2204322b9a257b905340768c6"
L4_REPAIRED="d8f9865f222f75a15ffbd766837d340ba627d12a"

def h(data):
    return hashlib.sha256(data).hexdigest()
def digest(*files):
    return h(b"\0".join(Path(f).read_bytes() for f in files))
def parse_tags(path):
    out={}
    for row in Path(path).read_text().splitlines():
        if not row.strip(): continue
        name,sep,value=row.partition("\t")
        if not sep or name in out or value not in ("str","int","float","null","bool"):
            raise ValueError("INVALID_LEAN_OBSERVATION:"+repr(row))
        out[name]=value
    if set(out)!=set(YAML_P): raise ValueError("YAML_DOMAIN_MISMATCH")
    return out
def consequence_pairs(p,q):
    names=sorted(p)
    return sorted((a,b) for a,b in combinations(names,2)
                  if q[a]==q[b] and p[a]!=p[b])
def mg_diagnosis(p,q,actual):
    if set(q)!=set(p) or set(actual)!=set(p):
        raise ValueError("DOMAIN_MISMATCH")
    lost=consequence_pairs(p,q)
    mismatches=sorted(k for k in p if actual[k]!=p[k])
    result=("REPRESENTATION_INSUFFICIENT" if lost
            else "DECODER_FIDELITY_FAILURE" if mismatches
            else "BOTH_PASS_FINITE_X")
    return {"class":result,"witness_pairs":[list(x) for x in lost],
            "pointwise_mismatches":mismatches}
def conventional_diagnosis(p,q,actual):
    # Fully informed standard direct pairwise/pointwise script. No MG function calls.
    bad=[]
    for i,a in enumerate(sorted(p)):
        for b in sorted(p)[i+1:]:
            if q[a]==q[b] and p[a]!=p[b]:
                bad.append([a,b])
    wrong=[s for s in sorted(p) if p[s]!=actual[s]]
    return {
        "class":"REPRESENTATION_INSUFFICIENT" if bad else
                ("DECODER_FIDELITY_FAILURE" if wrong else "BOTH_PASS_FINITE_X"),
        "witness_pairs":bad,"pointwise_mismatches":wrong
    }
def rocket_observations(path):
    root=Path(path)
    raw=json.loads((root/"native-result.json").read_text())
    if raw.get("source_pins")!={"fret":FRET_SHA,"r2u2":R2U2_SHA}:
        raise ValueError("ROCKET_UPSTREAM_REVISIONS_NOT_PINNED")
    if raw.get("source_formula")!="(BOOST -> (F[0,7] COAST))":
        raise ValueError("FRET_SOURCE_FORMULA_CHANGED")
    if raw.get("comparison_formula")!="(BOOST -> (F[1,7] COAST))":
        raise ValueError("CHALLENGER_FORMULA_CHANGED")
    if raw.get("overall")!="UNKNOWN" or raw.get("auto_repair")!="DENIED":
        raise ValueError("INBAND_AUTHORITY_PROMOTION")
    for variant in ("source","challenger"):
        for ext,expected in (("c2po",raw["source_sha256"][variant]),
                             ("map",raw["map_sha256"]),
                             ("bin",raw["binary_sha256"][variant])):
            if digest(root/(variant+"."+ext)) != expected:
                raise ValueError("ACTUAL_NATIVE_ARTIFACT_CHANGED:"+variant+"."+ext)
    source_p={}
    source_d={}
    challenger_d={}
    trace_sets={}
    for case in ("simultaneous","next_tick","no_coast","no_boost"):
        x=json.loads((root/(case+".json")).read_text())
        if len(x)!=8 or any(set(v)!={"BOOST","COAST"} or
                            v["BOOST"] not in (0,1) or v["COAST"] not in (0,1)
                            for v in x):
            raise ValueError("INVALID_ROCKET_TRACE")
        trace_sets[case]=x
        for t in range(8):
            key=f"{case}:{t}"
            source_p[key]=(not bool(x[t]["BOOST"])) or any(
                bool(x[j]["COAST"]) for j in range(t,min(7,t+7)+1))
    for rec in raw["observations"]:
        case,variant=rec["scenario"],rec["variant"]
        if case not in trace_sets or variant not in ("source","challenger"):
            raise ValueError("UNEXPECTED_SCENARIO_OR_VARIANT")
        if len(rec["native"])!=8 or len(rec["oracle"])!=8:
            raise ValueError("INCOMPLETE_NATIVE_VERDICTS")
        target=source_d if variant=="source" else challenger_d
        for t,v in enumerate(rec["native"]):
            key=f"{case}:{t}"
            if key in target or not isinstance(v,bool): raise ValueError("DUPLICATE_VERDICT")
            target[key]=v
    if set(source_p)!=set(source_d) or set(source_p)!=set(challenger_d):
        raise ValueError("WRONG_NATIVE_CENSUS")
    # q = full inputs and temporal point, so the observation has sufficient
    # information for P on X, independently of which decoder is used.
    q={f"{case}:{t}":(t,tuple((x["BOOST"],x["COAST"])
                            for x in trace_sets[case]))
       for case in trace_sets for t in range(8)}
    if any(v!=expected for k,v in q.items() for k2,expected in ((k,q[k]),)):
        raise AssertionError("UNREACHABLE")
    return source_p,q,source_d,challenger_d,raw
def warrant_admission(repaired,rocket,verified):
    from mathgraph_check.boundary_warrant import (
        Subject, Obligation, Relation, Verification, Conclusion,
        BoundaryWarrant, Dependency, required_dependencies, scope_identity,
        admitted_route, resolve_boundaries
    )
    from mathgraph_check.warrant_resolution import Receipt
    def make(suffix,repo,sha,source_file,policy,evidence_files):
        source_digest=digest(source_file)
        sub=Subject(repo,sha,source_digest)
        obligation=Obligation("pilot:"+suffix,
            "A previously frozen, independently published bounded requirement",
            "PUBLIC_SOURCE_AUTHOR_NOT_MISSION_OWNER",h(("pilot:obligation:"+suffix).encode()))
        relation=Relation("source_to_observation_fidelity",
            "Native outputs agree with independently frozen P on finite X",
            (("domain","FINITE_FROZEN"),("human_approval","NOT_RUN")))
        ver=Verification("native","paired-assessor-v1:"+suffix,
            h(("pilot:assessor:"+policy).encode()),(),
            "paired:receipt:"+suffix)
        deps=required_dependencies(sub,obligation,relation,ver)+(
            Dependency("evidence","evidence:"+suffix,digest(*evidence_files)),)
        w=BoundaryWarrant(sub,obligation,relation,ver,
                          Conclusion("SUPPORTED",("exact pinned native case",
                                                  "not external owner authorization")),deps)
        receipt=Receipt(ver.receipt_id,ver.method,scope_identity(w))
        return w,receipt
    y=make("yaml","nasa-jpl/L4YAML",L4_REPAIRED,
           repaired/"L4YAML.Schema.Schema.lean","yaml-core-tag",
           [repaired/"observations.tsv",repaired/"L4YAML.Schema.Schema.lean"])
    f=make("fret","NASA-SW-VnV/fret",FRET_SHA,
           rocket/"source.c2po","fret-rocketrun",
           [rocket/"native-result.json",rocket/"source.c2po",
            rocket/"source.map",rocket/"source.bin"])
    items=[y,f]
    current={d.key:d.sha256 for w,receipt in items for d in w.dependencies}
    before=resolve_boundaries(items,current)
    ids=[admitted_route(w,r)[0].id for w,r in items]
    assert all(v.startswith("WARRANTED_BOUNDED") for v in before.states.values())
    controls=[]
    for i,role in ((0,"source"),(0,"obligation"),(1,"evidence"),(1,"verifier")):
        w,_=items[i]
        key=next(d.key for d in w.dependencies if d.role==role)
        changed=dict(current)
        changed[key]="e"*64 if current[key]!="e"*64 else "f"*64
        after=resolve_boundaries(items,changed)
        assert after.states[ids[i]] in ("STALE","UNKNOWN"),after.states
        assert after.states[ids[1-i]]==before.states[ids[1-i]]
        controls.append({"case":f"{['yaml','fret'][i]}:{role}",
                         "affected":after.states[ids[i]],
                         "other_preserved":True})
    # A caller-supplied 'owner_approved' cannot create a new legitimate
    # trusted receipt: no owner has signed a permission grant.
    return {"states":dict(before.states),"controls":controls,
            "no_owner_authorization":"UNKNOWN","auto_repair":"DENIED"}

def main():
    p=argparse.ArgumentParser()
    for item in ("yaml_original","yaml_repaired","fret","boundary"):
        p.add_argument("--"+item.replace("_","-"),required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    repaired=Path(a.yaml_repaired)
    sys.path.insert(0,str(Path(a.boundary).resolve()))
    old=parse_tags(Path(a.yaml_original)/"observations.tsv")
    fixed=parse_tags(repaired/"observations.tsv")
    ycases={
        "original":mg_diagnosis(YAML_P,old,old),
        "repaired":mg_diagnosis(YAML_P,fixed,fixed)
    }
    pd,q,ds,dc,manifest=rocket_observations(a.fret)
    rcases={
        "original_source":mg_diagnosis(pd,q,ds),
        "constructed_challenger":mg_diagnosis(pd,q,dc)
    }
    results={}
    for domain,cases,truth,qs,vals in (
        ("L4YAML",ycases,YAML_P,{"original":old,"repaired":fixed},
         {"original":old,"repaired":fixed}),
        ("FRET_R2U2",rcases,pd,
         {"original_source":q,"constructed_challenger":q},
         {"original_source":ds,"constructed_challenger":dc})):
        results[domain]={}
        for case,observed in cases.items():
            control=conventional_diagnosis(truth,qs[case],vals[case])
            assert control==observed,("STRONG_SCRIPT_TIE_BROKEN",domain,case)
            results[domain][case]={"diagnosis":observed,
                "conventional_script":"TIE_EXACT_WITNESS_SET"}
    assert ycases["original"]["class"]=="REPRESENTATION_INSUFFICIENT",ycases
    assert ycases["repaired"]["class"]=="BOTH_PASS_FINITE_X",ycases
    assert rcases["original_source"]["class"]=="BOTH_PASS_FINITE_X",rcases
    assert rcases["constructed_challenger"]["class"]=="DECODER_FIDELITY_FAILURE",rcases
    results["admission"]=warrant_admission(repaired,Path(a.fret),results)
    results["status"]="WARRANTED_BOUNDED_NATIVE_MECHANICS_ONLY"
    results["source_authority"]={
        "l4_original":L4_ORIGINAL,"l4_repaired":L4_REPAIRED,
        "fret":FRET_SHA,"r2u2":R2U2_SHA,
        "yaml_P":"YAML 1.2.2 §10.3.2 Core Schema plain scalar",
        "rocket_P":"published FRETish [0,7], not owner mission"}
    results["external_human_oracle_adjudicator"]="NOT_RUN"
    results["external_human_conventional_reviewer"]="NOT_RUN"
    results["commercial_or_discovery_superiority"]="UNKNOWN"
    results["owner_action_permission"]="NOT_AUTHORIZED"
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(results,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
       "yaml_old_errors":len(ycases["original"]["pointwise_mismatches"]),
       "yaml_rep_errors":len(ycases["repaired"]["pointwise_mismatches"]),
       "fret_source_errors":len(rcases["original_source"]["pointwise_mismatches"]),
       "fret_challenger_errors":len(rcases["constructed_challenger"]["pointwise_mismatches"]),
       "script_baselines":"TIE_4_OF_4",
       "selective_controls":len(results["admission"]["controls"]),
       "human_comparison":"NOT_RUN"},sort_keys=True))
if __name__=="__main__":main()
