#!/usr/bin/env python3
"""V2 source-neutral reversible-API obligation proposer with independent JSON oracle."""
from __future__ import annotations
import argparse,copy,hashlib,importlib,inspect,json,re,subprocess
from pathlib import Path

FUNCTION_PAIRS=(("dumps","loads"),("encode","decode"),("packb","unpackb"),
                ("safe_dump","safe_load"),("serialize","deserialize"))
SEEDS=("hello",b"hello","",b"",0,1,True,None,{"x-mg":"v-mg"},
       [("x-mg","v-mg")],[(b"x-mg",b"v-mg")],[(":method","GET")],
       [(b":method",b"GET")],[("x-mg","v-mg"),("x-other","2")],
       [(b"x-mg",b"v-mg"),(b"x-other",b"2")],
       {"x":[1,2],"z":True},2.5)

def one_payload(fun,unbound=False):
    try: params=list(inspect.signature(fun).parameters.values())
    except (TypeError,ValueError):return False
    if unbound:
        if not params or params[0].name not in ("self","cls"):return False
        params=params[1:]
    needed=[p for p in params if p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_KEYWORD,
                               inspect.Parameter.VAR_POSITIONAL)]
    return len(needed)==1 and needed[0].kind in (
        inspect.Parameter.POSITIONAL_ONLY,inspect.Parameter.POSITIONAL_OR_KEYWORD)

def no_required_ctor(cls):
    try: params=inspect.signature(cls).parameters.values()
    except (ValueError,TypeError):return False
    return all(p.default is not inspect.Parameter.empty or p.kind in
               (inspect.Parameter.VAR_POSITIONAL,inspect.Parameter.VAR_KEYWORD)
               for p in params)

def discover(mod):
    items=vars(mod); prefix=mod.__name__;out=[]
    for a,b in FUNCTION_PAIRS:
        f,g=items.get(a),items.get(b)
        if (inspect.isfunction(f) and inspect.isfunction(g)
            and f.__module__.startswith(prefix) and g.__module__.startswith(prefix)
            and one_payload(f) and one_payload(g)):
            out.append({"id":"function:"+a+"->"+b,"kind":"function","a":a,"b":b})
    for name,cls in sorted(items.items()):
        if not isinstance(name,str) or name.startswith("_") or not name.endswith("Encoder"):
            continue
        if not inspect.isclass(cls) or not cls.__module__.startswith(prefix) or not no_required_ctor(cls):
            continue
        peer_name=name[:-len("Encoder")]+"Decoder";peer=items.get(peer_name)
        if not inspect.isclass(peer) or not peer.__module__.startswith(prefix) or not no_required_ctor(peer):
            continue
        if one_payload(getattr(cls,"encode",None),True) and one_payload(getattr(peer,"decode",None),True):
            out.append({"id":"class:"+name+".encode->"+peer_name+".decode",
                        "kind":"class","a":name,"b":peer_name})
    return sorted(out,key=lambda x:x["id"])

def functions(mod,pair):
    if pair["kind"]=="class":
        return getattr(mod,pair["a"])().encode,getattr(mod,pair["b"])().decode
    return getattr(mod,pair["a"]),getattr(mod,pair["b"])

def typename(value):return type(value).__name__
def eq(a,b):return type(a) is type(b) and a==b
def identity(value):return typename(value)+":"+repr(value)[:800]

def check_one(mod,pair,seed,n):
    entry={"index":n,"seed_type":typename(seed),"seed_sha256":hashlib.sha256(repr(seed).encode()).hexdigest(),
           "encoder":"INELIGIBLE","strict":"UNKNOWN","normal_form":"UNKNOWN",
           "reference":"UNKNOWN","negative_json":"UNKNOWN"}
    encoder,decoder=functions(mod,pair)
    try: wire=encoder(copy.deepcopy(seed))
    except Exception as error:
        entry["encoder_error"]=type(error).__name__
        return entry
    entry["encoder"]="ACCEPTED";entry["wire_type"]=typename(wire)
    entry["wire_sha256"]=hashlib.sha256(repr(wire).encode()).hexdigest()
    try: observed=decoder(wire)
    except Exception as error:
        entry["strict"]="COUNTEREXAMPLE"
        entry["decoder_error"]=type(error).__name__
        return entry
    entry["strict"]="MATCH" if eq(observed,seed) else "COUNTEREXAMPLE"
    entry["output_type"]=typename(observed)
    entry["output_sha256"]=hashlib.sha256(repr(observed).encode()).hexdigest()
    try:
        fresh_encoder,fresh_decoder=functions(mod,pair)
        stabilized=fresh_decoder(fresh_encoder(copy.deepcopy(observed)))
        entry["normal_form"]="MATCH" if eq(stabilized,observed) else "COUNTEREXAMPLE"
    except Exception as error:
        entry["normal_form"]="UNSUPPORTED"
        entry["normal_form_error"]=type(error).__name__
    try:
        parsed=json.loads(wire)
    except (TypeError,ValueError,UnicodeError):
        return entry
    entry["reference"]="MATCH" if eq(parsed,observed) else "COUNTEREXAMPLE"
    entry["reference_type"]=typename(parsed)
    try:
        perturb=(wire+"!") if isinstance(wire,str) else (wire+b"!" if isinstance(wire,(bytes,bytearray)) else None)
        if perturb is not None:
            try:json.loads(perturb);entry["negative_json"]="COUNTEREXAMPLE"
            except (ValueError,UnicodeError):entry["negative_json"]="REJECTED_MUTANT"
    except (TypeError,ValueError):
        entry["negative_json"]="UNKNOWN"
    return entry

def classify(rows):
    accepted=[r for r in rows if r["encoder"]=="ACCEPTED"]
    strict_fail=[r for r in accepted if r["strict"]!="MATCH"]
    stable=[r for r in accepted if r["normal_form"] in ("MATCH","COUNTEREXAMPLE")]
    stable_fails=[r for r in stable if r["normal_form"]!="MATCH"]
    refs=[r for r in accepted if r["reference"] in ("MATCH","COUNTEREXAMPLE")]
    ref_fails=[r for r in refs if r["reference"]!="MATCH"]
    outputs={r.get("output_sha256") for r in refs if r.get("output_sha256")}
    structured=any(r.get("reference_type") in ("list","dict") for r in refs)
    negative=sum(r["negative_json"]=="REJECTED_MUTANT" for r in refs)
    strict=("UNKNOWN_NO_ACCEPTED" if not accepted else
            "REJECTED_BOUNDED" if strict_fail else "WARRANTED_BOUNDED_FINITE")
    normal=("UNKNOWN_INSUFFICIENT_CANONICAL" if len(stable)<3 or len(set(r.get("output_sha256") for r in stable))<2 else
            "REJECTED_BOUNDED" if stable_fails else "WARRANTED_BOUNDED_FINITE")
    reference=("UNKNOWN_NO_INDEPENDENT_REFERENCE" if len(refs)<3 or len(outputs)<2 or not structured or negative<2 else
               "REJECTED_BOUNDED" if ref_fails or any(r["negative_json"]=="COUNTEREXAMPLE" for r in refs) else
               "WARRANTED_BOUNDED_JSON_SUBSET")
    return {"accepted":len(accepted),"strict_matches":len(accepted)-len(strict_fail),
            "strict_counterexamples":len(strict_fail),
            "canonical_supported":len(stable),"canonical_counterexamples":len(stable_fails),
            "reference_supported":len(refs),"reference_counterexamples":len(ref_fails),
            "reference_distinct_outputs":len(outputs),"reference_has_container":structured,
            "reference_perturbation_rejections":negative,
            "strict_verdict":strict,"normal_form_verdict":normal,
            "reference_verdict":reference}

def inspect_api(mod):
    proposed=[]
    for pair in discover(mod):
        samples=[check_one(mod,pair,seed,n) for n,seed in enumerate(SEEDS)]
        proposed.append({"id":pair["id"],"relation_family":"reversible public API",
                         "samples":samples,**classify(samples)})
    return {"protocol":"API_MEANING_V2","pair_count":len(proposed),"results":proposed}

def main():
    p=argparse.ArgumentParser()
    for arg in ("module","checkout","source-sha","output"):p.add_argument("--"+arg,required=True)
    a=p.parse_args()
    assert re.fullmatch(r"[0-9a-f]{40}",a.source_sha)
    folder=Path(a.checkout).resolve()
    assert subprocess.check_output(["git","-C",str(folder),"rev-parse","HEAD"],text=True).strip()==a.source_sha
    mod=importlib.import_module(a.module)
    modfile=Path(inspect.getfile(mod)).resolve()
    assert modfile.is_relative_to(folder),f"IMPORT_NOT_FROM_SOURCE {modfile}"
    result=inspect_api(mod)
    result.update({"source_sha":a.source_sha,"module":a.module,"native_module_path":str(modfile.relative_to(folder)),
                   "independent_oracle":"Python 3 stdlib json.loads","interpretation_scope":"JSON parsed subsets only",
                   "higher_level_intent":"UNKNOWN", "human_agent_advantage":"UNKNOWN"})
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("API_MEANING_V2_PROPOSALS",json.dumps([{k:v for k,v in item.items() if k!="samples"} for item in result["results"]],sort_keys=True))
if __name__=="__main__":main()
