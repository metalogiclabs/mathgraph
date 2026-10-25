#!/usr/bin/env python3
"""Independent expert-authored conventional reversible-API rule baseline V1.

Reads the same public API/source checkout and the same finite fixtures as the
frozen proposer. It does NOT import the proposer or consume its decisions.
Not an independent hired expert or an LLM coding-agent comparison.
"""
import argparse,copy,hashlib,importlib,inspect,json,re,subprocess
from pathlib import Path

VALUES=["hello",b"hello","",b"",0,1,{"x-mg":"v-mg"},
        [("x-mg","v-mg")],[(b"x-mg",b"v-mg")],
        [(":method","GET")],[(b":method",b"GET")],
        [("x-mg","v-mg"),("x-other","2")],
        [(b"x-mg",b"v-mg"),(b"x-other",b"2")]]
CONVENTIONAL=[("encode","decode"),("compress","decompress"),
              ("dump","load"),("dumps","loads"),("escape","unescape"),
              ("pack","unpack"),("serialize","deserialize")]

def one_payload(fun,instance=False):
    try: ps=list(inspect.signature(fun).parameters.values())
    except (TypeError,ValueError):return False
    if instance:
        if not ps or ps[0].name not in ("self","cls"):return False
        ps=ps[1:]
    required=[x for x in ps if x.default is inspect.Parameter.empty
              and x.kind not in (inspect.Parameter.VAR_KEYWORD,
                                  inspect.Parameter.VAR_POSITIONAL)]
    return len(required)==1 and required[0].kind in (
        inspect.Parameter.POSITIONAL_ONLY,inspect.Parameter.POSITIONAL_OR_KEYWORD)

def constructible(cls):
    try:ps=inspect.signature(cls).parameters.values()
    except (TypeError,ValueError):return False
    return all(x.default is not inspect.Parameter.empty or x.kind in
               (inspect.Parameter.VAR_POSITIONAL,inspect.Parameter.VAR_KEYWORD)
               for x in ps)

def enumerate_expert(mod):
    exported=vars(mod)
    found=[]
    for a,b in CONVENTIONAL:
        left=exported.get(a);right=exported.get(b)
        if (inspect.isfunction(left) and inspect.isfunction(right) and
            left.__module__.startswith(mod.__name__) and
            right.__module__.startswith(mod.__name__) and
            one_payload(left) and one_payload(right)):
            found.append(("function:"+a+"->"+b,left,right))
    for name,cls in sorted(exported.items()):
        if not name.endswith("Encoder") or name.startswith("_") or not inspect.isclass(cls):continue
        dname=name[:-7]+"Decoder";peer=exported.get(dname)
        if not inspect.isclass(peer):continue
        if not (cls.__module__.startswith(mod.__name__) and
                peer.__module__.startswith(mod.__name__) and
                constructible(cls) and constructible(peer)):continue
        x=getattr(cls,"encode",None);y=getattr(peer,"decode",None)
        if x and y and one_payload(x,True) and one_payload(y,True):
            found.append(("class:"+name+".encode->"+dname+".decode",cls,peer))
    return sorted(found,key=lambda v:v[0])

def judge(mod):
    records=[]
    for id,a,b in enumerate_expert(mod):
        samples=[]
        class_pair=id.startswith("class:")
        for n,value in enumerate(VALUES):
            entry={"index":n,"result":"UNKNOWN"}
            try:
                first=a().encode if class_pair else a
                second=b().decode if class_pair else b
                serialized=first(copy.deepcopy(value))
            except Exception as exc:
                entry={"index":n,"result":"INELIGIBLE_ENCODER","error_type":type(exc).__name__}
                samples.append(entry);continue
            try:
                observed=second(serialized)
                entry["result"]=("MATCH" if type(observed) is type(value)
                                 and observed==value else "COUNTEREXAMPLE")
            except Exception as exc:
                entry.update({"result":"COUNTEREXAMPLE","error_type":type(exc).__name__})
            samples.append(entry)
        valid=[x for x in samples if x["result"]!="INELIGIBLE_ENCODER"]
        wrong=[x for x in valid if x["result"]=="COUNTEREXAMPLE"]
        status=("UNKNOWN_NO_APPLICABILITY" if not valid else
                "REJECTED_BOUNDED" if wrong else "WARRANTED_BOUNDED_FINITE")
        docs={"left":bool(inspect.getdoc(a)),"right":bool(inspect.getdoc(b))}
        records.append({"id":id,"status":status,"accepted":len(valid),
                        "counterexamples":len(wrong),"samples":samples,
                        "docs_available":docs})
    return records

def main():
    p=argparse.ArgumentParser()
    for name in ("module","checkout","source-sha","output"):p.add_argument("--"+name,required=True)
    a=p.parse_args()
    assert re.fullmatch("[0-9a-f]{40}",a.source_sha)
    source=Path(a.checkout).resolve()
    assert subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],text=True).strip()==a.source_sha
    mod=importlib.import_module(a.module)
    assert Path(inspect.getfile(mod)).resolve().is_relative_to(source)
    results=judge(mod)
    report={"protocol":"INFORMED_EXPERT_RULE_BASELINE_V1","selected_sha":a.source_sha,
            "native_API_input":a.module,"independent_from_proposer":True,
            "results":results,
            "limitations":"Expert-authored automated rule, not actual independent human reviewer."}
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("EXPERT_RULE_BASELINE",json.dumps({r["id"]:r["status"] for r in results},sort_keys=True))

if __name__=="__main__":main()
