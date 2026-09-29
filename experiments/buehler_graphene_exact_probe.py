#!/usr/bin/env python3
import json, urllib.parse, urllib.request
from pathlib import Path

OUT=Path("evidence/buehler-graphene-exact-v1")
OUT.mkdir(parents=True,exist_ok=True)

REPOS={
 "agent":"lamm-mit/graphene-agent-data",
 "u64":"lamm-mit/graphene-design-universe-64k",
 "u256":"lamm-mit/graphene-design-universe-256k",
}
PINS={
 "agent":"cb48eb13363bc81bfb4cdfe25bd163a192019cc3",
 "u64":"ef63e26782f9c82ca02f82c71e43f8b4c189b168",
 "u256":"84a5fece87926aac8181b27e6e287b32c07093a6",
}

def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"MathGraph-Crystal/1"})
    with urllib.request.urlopen(req,timeout=60) as r:
        return r.read()

def api_json(url):
    return json.loads(get(url))

def tree(repo,rev):
    # HF tree endpoint can paginate; recurse from root.
    enc=urllib.parse.quote(repo,safe="/")
    url=f"https://huggingface.co/api/datasets/{enc}/tree/{rev}?recursive=true&expand=true"
    return api_json(url)

res={"schema":"mathgraph.buehler-graphene-exact-probe-v1","repos":{}}
for key,repo in REPOS.items():
    meta=api_json("https://huggingface.co/api/datasets/"+urllib.parse.quote(repo,safe="/"))
    try:
        tr=tree(repo,PINS[key])
    except Exception as e:
        tr={"error":repr(e)}
    files=[]
    if isinstance(tr,list):
        for x in tr:
            files.append({
                "path":x.get("path"),
                "type":x.get("type"),
                "size":x.get("size"),
                "oid":x.get("oid"),
                "lfs":x.get("lfs"),
            })
    res["repos"][key]={
        "id":repo,"pin":PINS[key],
        "meta_sha":meta.get("sha"),
        "lastModified":meta.get("lastModified"),
        "tags":meta.get("tags"),
        "cardData":meta.get("cardData"),
        "siblings":[s.get("rfilename") for s in meta.get("siblings",[])],
        "tree_count":len(files),
        "files":files,
        "tree_error":tr.get("error") if isinstance(tr,dict) else None,
    }

(OUT/"probe.json").write_text(json.dumps(res,indent=2,sort_keys=True))
for key,r in res["repos"].items():
    print("\\n==",key,r["id"],r["pin"],"tree",r["tree_count"])
    print("cardData=",json.dumps(r["cardData"],sort_keys=True)[:4000])
    for f in r["files"][:250]:
        print(f)
