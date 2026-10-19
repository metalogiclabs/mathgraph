#!/usr/bin/env python3
"""Independent expert-authored conventional rule baseline.

Same input metadata and root initializer bytes as V2 proposer; independently
implemented static export census, different precommitted name ordering. This
is NOT a recruited expert or evidence of human-expert performance.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

SERIALIZERS=("dumps","encode","serialize")
PARSERS=("loads","decode","parse")
PARSER={"toml":"tomllib.loads","json":"json.loads"}


def infer_format(repo, description):
    tokens=re.findall("[a-z0-9]+",(repo+" "+(description or "")).lower())
    present=set(k for k in PARSER
                if k in tokens or k in repo.lower().split("/")[-1])
    return next(iter(present)) if len(present)==1 else None


def surface(data):
    tree=ast.parse(data.decode("utf-8"))
    imports=set()
    members=set()
    declared=None
    assignments=[]
    for item in tree.body:
        if isinstance(item, (ast.FunctionDef,ast.AsyncFunctionDef)):
            members.add(item.name)
        if isinstance(item,ast.Import):
            for name in item.names:
                imports.add(name.asname or name.name.split(".")[0])
        if isinstance(item,ast.ImportFrom):
            for name in item.names:
                if name.name=="*":
                    continue
                n=name.asname or name.name
                imports.add(n)
                members.add(n)
        if isinstance(item,(ast.Assign,ast.AnnAssign)):
            targets=item.targets if isinstance(item,ast.Assign) else [item.target]
            for target in targets:
                if not isinstance(target,ast.Name):
                    continue
                if target.id=="__all__":
                    v=item.value
                    if isinstance(v,(ast.List,ast.Tuple)):
                        names=[n.value for n in v.elts
                               if isinstance(n,ast.Constant) and isinstance(n.value,str)]
                        if len(names)==len(v.elts):
                            declared=set(names)
                else:
                    assignments.append((target.id,item.value))
    for name,value in assignments:
        if name.startswith("_"):
            continue
        parts=[]
        while isinstance(value,ast.Attribute):
            parts.append(value.attr)
            value=value.value
        if isinstance(value,ast.Name) and value.id in imports and 1<=len(parts)<=2:
            members.add(name)
    members={x for x in members if not x.startswith("_")}
    if declared is not None:
        members.intersection_update(declared)
    return sorted(members)


def expert_rules(metadata, path):
    raw=path.read_bytes()
    fmt=infer_format(metadata["repository"],metadata.get("description"))
    members=surface(raw)
    result={
        "arm":"expert",
        "repository":metadata["repository"],
        "source_sha":metadata["source_sha"],
        "api_sha256":hashlib.sha256(raw).hexdigest(),
        "public_symbols":members,
        "format":fmt,
        "status":"UNKNOWN_NO_SUPPORTED_RELATION",
        "obligations":[],
        "authority":"separately authored expert cookbook using identical public source initializer and metadata",
    }
    if fmt is None:
        return result
    writer=next((s for s in SERIALIZERS if s in members),None)
    reader=next((s for s in PARSERS if s in members),None)
    if writer is None:
        return result
    result["status"]="CANDIDATE_PENDING_INDEPENDENT_NATIVE_VERIFICATION"
    result["obligations"].append({
        "id":"external-semantics",
        "writer":writer,"reader":None,
        "relation":"independent_parse(writer(mapping)) == mapping",
        "oracle":PARSER[fmt],
        "domain":"predeclared JSON/TOML-compatible mappings",
    })
    if reader:
        result["obligations"].append({
            "id":"native-roundtrip",
            "writer":writer,"reader":reader,
            "relation":"reader(writer(mapping)) == mapping",
            "oracle":"original public reader, not independent",
            "domain":"predeclared JSON/TOML-compatible mappings",
        })
    return result


def main():
    a=argparse.ArgumentParser()
    for name in ("metadata","api","output"):
        a.add_argument("--"+name,required=True,type=Path)
    x=a.parse_args()
    md=json.loads(x.metadata.read_text())
    assert re.fullmatch(r"[a-f0-9]{40}",md["source_sha"])
    result=expert_rules(md,x.api)
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("V2_EXPERT_REFERENCE_API_PROPOSAL",result["status"],
          [s["id"] for s in result["obligations"]])


if __name__=="__main__":
    main()
