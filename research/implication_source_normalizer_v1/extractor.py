#!/usr/bin/env python3
"""Conservative ACSL source-only implication/conjunction normalizer.

Recognizes five explicitly bounded logical proof patterns, not arbitrary ACSL.
Constructs obligations from the preconditions and postconditions ONLY.
No generated Rust is read. Unrecognized constructs abstain.
"""
import json,re,subprocess
from pathlib import Path
from itertools import product

HERE=Path(__file__).resolve().parent
MANIFEST=HERE/"FROZEN_MANIFEST.json"
def manifest():return json.loads(MANIFEST.read_text())
def source_contract(text):
    matches=re.findall(r"/\*@([\s\S]*?)\*/",text)
    if not matches:return ""
    return " ".join(matches[0].split())
def satisfies(flat,patterns):
    return all(re.search(pattern,flat) for pattern in patterns)
def classify(text):
    flat=source_contract(text)
    if not flat:return {"status":"UNKNOWN_UNSUPPORTED_CONTRACT","reason":"NO_ACSL"}
    rules=[
       ("SCALAR_PAIR_MAX",[
        r"ensures\s+\\result\s*==\s*x\s*\|\|\s*\\result\s*==\s*y\s*;",
        r"ensures\s+\\result\s*>=\s*x\s*&&\s*\\result\s*>=\s*y\s*;"]),
       ("QUANTIFIED_ARRAY_MAX",[
        r"requires\s+n\s*>\s*0\s*;",
        r"ensures\s+\\forall\s+integer\s+k\s*;\s*0\s*<=\s*k\s*<\s*n\s*==>\s*\\result\s*>=\s*a\[k\]\s*;",
        r"ensures\s+\\exists\s+integer\s+k\s*;\s*0\s*<=\s*k\s*<\s*n\s*&&\s*\\result\s*==\s*a\[k\]\s*;"]),
       ("ALL_EVEN_BOOLEAN",[
        r"requires\s+n\s*>\s*0\s*;",
        r"behavior\s+all_even:\s*assumes\s+\\forall\s+integer\s+k\s*;\s*0\s*<=\s*k\s*<\s*n\s*==>\s*a\[k\]\s*%\s*2\s*==\s*0\s*;\s*ensures\s+\\result\s*==\s*1\s*;",
        r"behavior\s+all_not_even:\s*assumes\s+\\exists\s+integer\s+k\s*;\s*0\s*<=\s*k\s*<\s*n\s*&&\s*a\[k\]\s*%\s*2\s*!=\s*0\s*;\s*ensures\s+\\result\s*==\s*0\s*;"]),
       ("EVEN_INDEX_ZERO_ONLY",[
        r"requires\s+n\s*>\s*0\s*;",
        r"ensures\s+\\forall\s+integer\s+k\s*;\s*\(\s*0\s*<=\s*k\s*<\s*n\s*\)\s*&&\s*\(\s*k\s*%\s*2\s*==\s*0\s*\)\s*==>\s*\(\s*a\[k\]\s*==\s*0\s*\)\s*;"]),
       ("INDEX_DOUBLE_GUARDED",[
        r"requires\s+n\s*>\s*0\s*;",
        r"requires\s+\\forall\s+integer\s+k\s*;\s*0\s*<=\s*k\s*<\s*n\s*==>\s*a\[k\]\s*==\s*k\s*&&\s*2\s*\*\s*k\s*<=\s*INT_MAX\s*;",
        r"ensures\s+\\forall\s+integer\s+k\s*;\s*0\s*<=\s*k\s*<\s*n\s*==>\s*a\[k\]\s*==\s*2\s*\*\s*k\s*;"]),
    ]
    matched=[name for name,patterns in rules if satisfies(flat,patterns)]
    if len(matched)!=1:return {"status":"UNKNOWN_UNSUPPORTED_CONTRACT","reason":"AMBIGUOUS_OR_UNRECOGNIZED_FORMULA","matched_rules":matched}
    kind=matched[0]
    # The partial frame: no assigns in replace_evens; never silently
    # demand preservation of unspecified odd-indexed array positions.
    return {"status":"SOURCE_CONTRACT_RECOGNIZED","family":kind,"partial_spec":kind=="EVEN_INDEX_ZERO_ONLY",
            "array_input":kind!="SCALAR_PAIR_MAX",
            "mutates_array":kind in ("EVEN_INDEX_ZERO_ONLY","INDEX_DOUBLE_GUARDED"),
            "obligation_count":len(dict(rules)[kind]),"source_only":True}
def all_cases(family):
    conf=manifest()["domain"]
    vals=tuple(conf["values"])
    if family=="SCALAR_PAIR_MAX":
        yield from product(conf["pair_values"],repeat=2)
    elif family=="INDEX_DOUBLE_GUARDED":
        for n in range(1,conf["array_double_max_length"]+1):yield tuple(range(n))
    elif family in ("QUANTIFIED_ARRAY_MAX","ALL_EVEN_BOOLEAN","EVEN_INDEX_ZERO_ONLY"):
        for n in range(1,conf["array_max_length"]+1):
            yield from product(vals,repeat=n)
    else:raise ValueError("UNRECOGNIZED_CASE_GENERATOR")
def probes(family):
    samples={
      "SCALAR_PAIR_MAX":[(-3,-2),(2,-1),(0,0)],
      "QUANTIFIED_ARRAY_MAX":[(-2,2),(2,-2),(-1,-1)],
      "ALL_EVEN_BOOLEAN":[(-2,0),(0,1),(-1,)],
      "EVEN_INDEX_ZERO_ONLY":[(1,2,-1,0),(-2,),(-1,2,1)],
      "INDEX_DOUBLE_GUARDED":[(0,1,2,3),(0,),(0,1,2,3,4)]}
    if family not in samples:raise ValueError("UNSUPPORTED_PROBE_FAMILY")
    return samples[family]
def authorized(family,before,after,result):
    if family=="SCALAR_PAIR_MAX":
        return result==max(before) and after is None
    if family=="QUANTIFIED_ARRAY_MAX":
        return result==max(before) and after==before
    if family=="ALL_EVEN_BOOLEAN":
        return result==int(all(x%2==0 for x in before)) and after==before
    if family=="EVEN_INDEX_ZERO_ONLY":
        # No source contract frame guarantee for the odd indices.
        return after is not None and len(after)==len(before) and all(after[i]==0 for i in range(0,len(before),2))
    if family=="INDEX_DOUBLE_GUARDED":
        return after==tuple(2*i for i in range(len(before)))
    raise ValueError("NOT_AUTHORIZED")
def git_blob(root,path):
    return subprocess.run(["git","-C",str(root),"hash-object",path],capture_output=True,text=True,check=True).stdout.strip()
def packet(root):
    root=Path(root);items=[]
    for entry in manifest()["cases"]:
        if git_blob(root,entry["source"])!=entry["blob"]:raise ValueError("SOURCE_BYTES_CHANGED:"+entry["source"])
        spec=classify((root/entry["source"]).read_text())
        item={**entry,**spec}
        if spec["status"]=="SOURCE_CONTRACT_RECOGNIZED":
            item["probe_inputs"]=[list(x) for x in probes(spec["family"])]
            item["finite_domain_size"]=sum(1 for _ in all_cases(spec["family"]))
        items.append(item)
    return {"protocol":"IMPLICATION_AWARE_SOURCE_ONLY_V1","source_only":True,
        "source_revision":manifest()["source_revision"],"cases":items}
