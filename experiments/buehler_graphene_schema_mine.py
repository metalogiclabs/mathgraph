#!/usr/bin/env python3
import json, re, hashlib
from pathlib import Path
import pandas as pd
from huggingface_hub import HfApi, hf_hub_download

OUT=Path("evidence/buehler-graphene-exact-v1")
OUT.mkdir(parents=True,exist_ok=True)
api=HfApi()
repos={
 "agent":("lamm-mit/graphene-agent-data","cb48eb13363bc81bfb4cdfe25bd163a192019cc3"),
 "u64":("lamm-mit/graphene-design-universe-64k","ef63e26782f9c82ca02f82c71e43f8b4c189b168"),
 "u256":("lamm-mit/graphene-design-universe-256k","84a5fece87926aac8181b27e6e287b32c07093a6"),
}
report={"schema":"mathgraph.buehler-graphene-schema-mine-v1","repos":{}}
text_ext={".md",".txt",".json",".csv",".yaml",".yml",".py"}
keywords=re.compile(r"(result|metric|summary|design|strength|fract|force|stress|strain|energy|density|slit|hier|vein|rebo|potential|validation|experiment|trajectory|mechanism|paper)",re.I)

for key,(repo,rev) in repos.items():
    print("\n###",key,repo,rev)
    entries=list(api.list_repo_tree(repo_id=repo, repo_type="dataset", revision=rev, recursive=True, expand=True))
    files=[]
    for e in entries:
        path=getattr(e,"path",None)
        size=getattr(e,"size",None)
        typ=e.__class__.__name__
        if typ=="RepoFile":
            files.append({"path":path,"size":size,"blob_id":getattr(e,"blob_id",None),
                          "lfs":str(getattr(e,"lfs",None)) if getattr(e,"lfs",None) else None})
    print("files",len(files),"bytes",sum((x["size"] or 0) for x in files))
    for x in files:
        if keywords.search(x["path"]):
            print("MATCH",x)
    rec={"file_count":len(files),"total_bytes":sum((x["size"] or 0) for x in files),
         "matched_paths":[x for x in files if keywords.search(x["path"])],
         "parquet":[],"small_text":[]}
    # Always inspect README and any small consequential text/data files.
    for x in files:
        p=x["path"]; sz=x["size"] or 0
        ext=Path(p).suffix.lower()
        wanted=(p=="README.md" or (keywords.search(p) and ext in text_ext and sz<=2_000_000))
        if not wanted: continue
        try:
            fp=hf_hub_download(repo_id=repo,repo_type="dataset",revision=rev,filename=p)
            b=Path(fp).read_bytes()
            sha=hashlib.sha256(b).hexdigest()
            text=b.decode("utf-8","replace")
            rec["small_text"].append({"path":p,"size":len(b),"sha256":sha,"preview":text[:20000]})
            print("\nTEXT",p,"sha256",sha,"\n",text[:12000])
        except Exception as ex:
            rec["small_text"].append({"path":p,"error":repr(ex)})
    # Inspect parquet schemas and the full 64k table; only schema/head for 256k if multiple/large.
    pq=[x for x in files if x["path"].lower().endswith(".parquet")]
    for x in pq:
        p=x["path"]; sz=x["size"] or 0
        if key=="u256" and sz>80_000_000:
            rec["parquet"].append({"path":p,"size":sz,"status":"SKIPPED_SIZE"})
            continue
        try:
            fp=hf_hub_download(repo_id=repo,repo_type="dataset",revision=rev,filename=p)
            df=pd.read_parquet(fp)
            info={"path":p,"size":sz,"rows":len(df),"columns":[str(c) for c in df.columns],
                  "dtypes":{str(c):str(df[c].dtype) for c in df.columns},
                  "head":json.loads(df.head(3).to_json(orient="records"))}
            rec["parquet"].append(info)
            print("\nPARQUET",p,"rows",len(df),"columns",list(df.columns))
            print(df.head(3).to_string(max_cols=100))
        except Exception as ex:
            rec["parquet"].append({"path":p,"size":sz,"error":repr(ex)})
            print("PARQUET ERROR",p,repr(ex))
    report["repos"][key]=rec

(OUT/"schema-mine.json").write_text(json.dumps(report,indent=2,sort_keys=True))
