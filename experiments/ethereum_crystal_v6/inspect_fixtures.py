#!/usr/bin/env python3
"""Inspect generated EELS fixtures for realized BAL data.

This is intentionally schema-discovery first. It refuses to infer an ingestion
schema before seeing the actual serialized fixtures.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from collections import Counter

root=Path(sys.argv[1])
files=sorted(root.rglob("*.json"))
if not files:
    raise SystemExit("NO_JSON_FIXTURES")

keys=Counter()
bal_hits=[]
def walk(x,path=()):
    if isinstance(x,dict):
        for k,v in x.items():
            lk=k.lower()
            if "access" in lk or "bal"==lk or "blockaccess" in lk:
                keys[k]+=1
                bal_hits.append((".".join(path+(k,)), type(v).__name__))
            walk(v,path+(k,))
    elif isinstance(x,list):
        for i,v in enumerate(x):
            walk(v,path+(str(i),))

parsed=0
for f in files:
    try:
        obj=json.loads(f.read_text())
    except Exception:
        continue
    parsed+=1
    walk(obj,(f.name,))

print("EELS_FIXTURE_SCHEMA_DISCOVERY")
print(f"json_files={len(files)} parsed={parsed}")
print("access_like_keys="+",".join(f"{k}:{n}" for k,n in sorted(keys.items())))
print("sample_paths="+("|".join(f"{p}:{t}" for p,t in bal_hits[:20]) if bal_hits else "-"))
if parsed==0:
    raise SystemExit("NO_PARSEABLE_FIXTURES")
if not bal_hits:
    raise SystemExit("NO_SERIALIZED_ACCESS_SURFACE_FOUND")
print("EELS_FIXTURE_BAL_SURFACE=FOUND")
