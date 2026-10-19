#!/usr/bin/env python3
"""V2 equally-informed expert-authored rule baseline; intentionally independent implementation.

Has identical source/API visibility and 17 input seeds, same Python stdlib JSON
reader, but never imports/consumes candidate proposer or its output.
"""
import argparse,copy,hashlib,importlib,inspect,json,re,subprocess
from pathlib import Path
FIXTURES=["hello",b"hello","",b"",0,1,True,None,{"x-mg":"v-mg"},
          [("x-mg","v-mg")],[(b"x-mg",b"v-mg")],[(":method","GET")],
          [(b":method",b"GET")],
          [("x-mg","v-mg"),("x-other","2")],
          [(b"x-mg",b"v-mg"),(b"x-other",b"2")],
          {"x":[1,2],"z":True},2.5]
PAIRS=[("dumps","loads"),("encode","decode"),("packb","unpackb"),
       ("safe_dump","safe_load"),("serialize","deserialize")]

def can_accept_one(fun,method=False):
    try:
        fields=list(inspect.signature(fun).parameters.values())
    except (TypeError,ValueError):
        return False
    if method:
        if not fields or fields[0].name not in ("self","cls"):return False
        fields=fields[1:]
    need=[x for x in fields if x.default is inspect.Parameter.empty
          and x.kind not in (inspect.Parameter.VAR_POSITIONAL,inspect.Parameter.VAR_KEYWORD)]
    return (len(need)==1 and need[0].kind in
            (inspect.Parameter.POSITIONAL_ONLY,inspect.Parameter.POSITIONAL_OR_KEYWORD))

def no_required_init(cls):
    try: fields=list(inspect.signature(cls).parameters.values())
    except (TypeError,ValueError):return False
    for x in fields:
        if x.default is inspect.Parameter.empty and x.kind not in (
            inspect.Parameter.VAR_POSITIONAL,inspect.Parameter.VAR_KEYWORD):
            return False
    return True

def public_reversible(module):
    symbols=vars(module);r=[]
    for left,right in PAIRS:
        a,b=symbols.get(left),symbols.get(right)
        if (inspect.isfunction(a) and inspect.isfunction(b) and
            a.__module__.startswith(module.__name__) and b.__module__.startswith(module.__name__) and
            can_accept_one(a) and can_accept_one(b)):
            r.append(("function:"+left+"->"+right,left,right,False))
    for name,thing in sorted(symbols.items()):
        if not name.endswith("Encoder") or name.startswith("_") or not inspect.isclass(thing):
            continue
        decoder_name=name[:-7]+"Decoder";reverse=symbols.get(decoder_name)
        if not inspect.isclass(reverse):continue
        if not (thing.__module__.startswith(module.__name__) and
                reverse.__module__.startswith(module.__name__) and
                no_required_init(thing) and no_required_init(reverse)):continue
        if can_accept_one(getattr(thing,"encode",None),True) and can_accept_one(getattr(reverse,"decode",None),True):
            r.append(("class:"+name+".encode->"+decoder_name+".decode",thing,reverse,True))
    return sorted(r,key=lambda x:x[0])

def fresh(call):
    left,right,is_class=call
    return (left().encode,right().decode) if is_class else (left,right)

def strict_equal(a,b):
    return type(a) is type(b) and a==b

def assess(call,seeds):
    samples=[]
    for index,x in enumerate(seeds):
        row={"index":index,"encoder":"INELIGIBLE","strict":"UNKNOWN",
             "normal_form":"UNKNOWN","reference":"UNKNOWN","negative_json":"UNKNOWN"}
        encode,decode=fresh(call)
        try:wire=encode(copy.deepcopy(x))
        except Exception:
            samples.append(row);continue
        row["encoder"]="ACCEPTED"
        try:out=decode(wire)
        except Exception:
            row["strict"]="COUNTEREXAMPLE";samples.append(row);continue
        row["strict"]="MATCH" if strict_equal(out,x) else "COUNTEREXAMPLE"
        row["observed_fingerprint"]=hashlib.sha256(repr(out).encode()).hexdigest()
        try:
            encode2,decode2=fresh(call)
            out2=decode2(encode2(copy.deepcopy(out)))
            row["normal_form"]="MATCH" if strict_equal(out2,out) else "COUNTEREXAMPLE"
        except Exception:row["normal_form"]="UNSUPPORTED"
        try:reference=json.loads(wire)
        except (ValueError,TypeError,UnicodeError):
            samples.append(row);continue
        row["reference"]="MATCH" if strict_equal(reference,out) else "COUNTEREXAMPLE"
        row["reference_type"]=type(reference).__name__
        altered=(wire+"!") if isinstance(wire,str) else (wire+b"!" if isinstance(wire,(bytes,bytearray)) else None)
        if altered is not None:
            try:
                json.loads(altered)
                row["negative_json"]="COUNTEREXAMPLE"
            except (ValueError,UnicodeError):
                row["negative_json"]="REJECTED_MUTANT"
        samples.append(row)
    accepted=[x for x in samples if x["encoder"]=="ACCEPTED"]
    canonical=[x for x in accepted if x["normal_form"] in ("MATCH","COUNTEREXAMPLE")]
    parsed=[x for x in accepted if x["reference"] in ("MATCH","COUNTEREXAMPLE")]
    distinct={x["observed_fingerprint"] for x in parsed if "observed_fingerprint" in x}
    distinct_canonical={x["observed_fingerprint"] for x in canonical if "observed_fingerprint" in x}
    count_perturb=sum(x["negative_json"]=="REJECTED_MUTANT" for x in parsed)
    count_strict_bad=sum(x["strict"]!="MATCH" for x in accepted)
    count_can_bad=sum(x["normal_form"]=="COUNTEREXAMPLE" for x in canonical)
    count_ref_bad=sum(x["reference"]=="COUNTEREXAMPLE" for x in parsed)
    strict=("UNKNOWN_NO_ACCEPTED" if not accepted else "REJECTED_BOUNDED" if count_strict_bad else
            "WARRANTED_BOUNDED_FINITE")
    normal=("UNKNOWN_INSUFFICIENT_CANONICAL" if len(canonical)<3 or len(distinct_canonical)<2 else
            "REJECTED_BOUNDED" if count_can_bad else "WARRANTED_BOUNDED_FINITE")
    ref=("UNKNOWN_NO_INDEPENDENT_REFERENCE" if len(parsed)<3 or len(distinct)<2
         or not any(x.get("reference_type") in ("list","dict") for x in parsed) or count_perturb<2 else
         "REJECTED_BOUNDED" if count_ref_bad or any(x["negative_json"]=="COUNTEREXAMPLE" for x in parsed) else
         "WARRANTED_BOUNDED_JSON_SUBSET")
    return {"accepted":len(accepted),"strict_matches":len(accepted)-count_strict_bad,
            "strict_counterexamples":count_strict_bad,"canonical_supported":len(canonical),
            "canonical_counterexamples":count_can_bad,"reference_supported":len(parsed),
            "reference_counterexamples":count_ref_bad,"reference_distinct_outputs":len(distinct),
            "reference_has_container":any(x.get("reference_type") in ("list","dict") for x in parsed),
            "reference_perturbation_rejections":count_perturb,
            "strict_verdict":strict,"normal_form_verdict":normal,
            "reference_verdict":ref,"samples":samples}

def evaluate(module):
    decisions=[]
    for id, left,right,is_class in public_reversible(module):
        decisions.append({"id":id,**assess((left,right,is_class),FIXTURES)})
    return decisions

def main():
    cli=argparse.ArgumentParser()
    for v in ("module","checkout","source-sha","output"):cli.add_argument("--"+v,required=True)
    args=cli.parse_args()
    assert re.fullmatch("[0-9a-f]{40}",args.source_sha)
    root=Path(args.checkout).resolve()
    assert subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()==args.source_sha
    mod=importlib.import_module(args.module)
    assert Path(inspect.getfile(mod)).resolve().is_relative_to(root)
    result={"protocol":"EQUAL_INFO_EXPERT_RULE_V2","source_sha":args.source_sha,"module":args.module,
            "results":evaluate(mod),"oracle":"independently coded stdlib json.loads",
            "limitations":"Not a human/agent baseline; same fixed inputs and public API."}
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("EXPERT_RULE_V2_RESULTS",json.dumps([{k:v for k,v in item.items() if k!="samples"} for item in result["results"]],sort_keys=True))
if __name__=="__main__":main()
