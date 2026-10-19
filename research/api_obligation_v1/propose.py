#!/usr/bin/env python3
"""V1 frozen API-surface relation proposer. No per-repository semantic adapters."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import re
import subprocess

PAIR_NAMES=(("encode","decode"),("compress","decompress"),("dump","load"),
            ("dumps","loads"),("escape","unescape"),("pack","unpack"),
            ("serialize","deserialize"))
SEEDS=(
    "hello", b"hello", "", b"", 0, 1, {"x-mg":"v-mg"},
    [("x-mg","v-mg")], [(b"x-mg",b"v-mg")],
    [(":method","GET")], [(b":method",b"GET")],
    [("x-mg","v-mg"),("x-other","2")],
    [(b"x-mg",b"v-mg"),(b"x-other",b"2")],
)

def _signature_ok(callable_, method=False):
    try: sig=inspect.signature(callable_)
    except (TypeError, ValueError): return False
    params=list(sig.parameters.values())
    if method:
        if not params or params[0].name not in ("self","cls"): return False
        params=params[1:]
    mandatory=[p for p in params if p.default is inspect.Parameter.empty and
               p.kind not in (inspect.Parameter.VAR_POSITIONAL,inspect.Parameter.VAR_KEYWORD)]
    return len(mandatory)==1 and mandatory[0].kind in (
        inspect.Parameter.POSITIONAL_ONLY,inspect.Parameter.POSITIONAL_OR_KEYWORD)

def _ctor_ok(cls):
    try: sig=inspect.signature(cls)
    except (ValueError,TypeError): return False
    return all(p.default is not inspect.Parameter.empty or p.kind in
               (inspect.Parameter.VAR_POSITIONAL,inspect.Parameter.VAR_KEYWORD)
               for p in sig.parameters.values())

def discover(module):
    """Return deterministic public class and function signature matches."""
    members=vars(module)
    root=module.__name__
    results=[]
    for a,b in PAIR_NAMES:
        f=members.get(a);g=members.get(b)
        if (inspect.isfunction(f) and inspect.isfunction(g) and
            f.__module__.startswith(root) and g.__module__.startswith(root) and
            _signature_ok(f) and _signature_ok(g)):
            results.append({"id":f"function:{a}->{b}","kind":"function","a":a,"b":b})
    for name,cls in sorted(members.items()):
        if (not isinstance(name,str) or name.startswith("_") or not
            name.endswith("Encoder") or not inspect.isclass(cls) or not
            cls.__module__.startswith(root) or not _ctor_ok(cls)):
            continue
        peer=name[:-len("Encoder")]+"Decoder"
        other=members.get(peer)
        if (not inspect.isclass(other) or not other.__module__.startswith(root)
            or not _ctor_ok(other)): continue
        f=getattr(cls,"encode",None);g=getattr(other,"decode",None)
        if not (callable(f) and callable(g) and _signature_ok(f,True)
                and _signature_ok(g,True)): continue
        results.append({"id":f"class:{name}.encode->{peer}.decode",
                        "kind":"class","a":name,"b":peer})
    return sorted(results,key=lambda r:r["id"])

def _pair(module,c):
    if c["kind"]=="class":
        left=getattr(module,c["a"])()
        right=getattr(module,c["b"])()
        return left.encode,right.decode
    return getattr(module,c["a"]),getattr(module,c["b"])

def evaluate(module,c):
    records=[]
    for i,s in enumerate(SEEDS):
        encode,decode=_pair(module,c)
        entry={"index":i,"seed_type":type(s).__qualname__,
               "seed_sha256":hashlib.sha256(repr(s).encode()).hexdigest()}
        try: wire=encode(copy.deepcopy(s))
        except Exception as exc:
            entry.update({"result":"INELIGIBLE_ENCODER","error_type":type(exc).__name__})
            records.append(entry);continue
        entry["wire_type"]=type(wire).__qualname__
        try:
            out=decode(wire)
            entry["output_type"]=type(out).__qualname__
            entry["result"]=("MATCH" if type(out) is type(s) and out==s else
                             "COUNTEREXAMPLE")
            if entry["result"]=="COUNTEREXAMPLE":
                entry["output_repr"]=repr(out)[:350]
        except Exception as exc:
            entry.update({"result":"COUNTEREXAMPLE","error_type":type(exc).__name__})
        records.append(entry)
    accepted=[r for r in records if r["result"]!="INELIGIBLE_ENCODER"]
    wrong=[r for r in accepted if r["result"]!="MATCH"]
    status=("UNKNOWN_NO_APPLICABILITY" if not accepted else
            "REJECTED_BOUNDED" if wrong else "WARRANTED_BOUNDED_FINITE")
    return {"id":c["id"],"relation":"strict type/value equality of decode(encode(x)) and x",
            "accepted":len(accepted),"counterexamples":len(wrong),
            "status":status,"samples":records}

def run(module):
    candidates=discover(module)
    return {"source_surface":module.__name__,"grammar":"API_OBLIGATION_V1",
            "candidate_count":len(candidates),"results":[evaluate(module,c) for c in candidates],
            "overall":"UNKNOWN_NO_RELATION_FAMILY" if not candidates else "OBSERVED_BOUNDED"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--module",required=True);p.add_argument("--checkout",required=True)
    p.add_argument("--source-sha",required=True);p.add_argument("--output",required=True)
    a=p.parse_args()
    assert re.fullmatch("[0-9a-f]{40}",a.source_sha)
    root=Path(a.checkout).resolve()
    got=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    assert got==a.source_sha, "SOURCE_SHA_MISMATCH"
    module=importlib.import_module(a.module)
    loaded=Path(inspect.getfile(module)).resolve()
    assert loaded.is_relative_to(root),f"IMPORT_OUTSIDE_PINNED_CHECKOUT {loaded}"
    result=run(module)
    result.update({"selected_sha":got,"loaded_module_path":str(loaded.relative_to(root)),
                   "source_sha_authority":"checked out repository Git HEAD"})
    path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("FROZEN_PROPOSER_RESULT",json.dumps({"overall":result["overall"],
          "candidates":result["candidate_count"],"verdicts":{r["id"]:r["status"]
          for r in result["results"]}},sort_keys=True))

if __name__=="__main__":main()
