#!/usr/bin/env python3
"""Freeze the first metadata-eligible repository: NO source URLs or file trees."""
import json, os, pathlib, sys, urllib.request
POOL = ["Verilean/sparkle", "Verified-zkEVM/ArkLib",
        "leanprover-community/iris-lean", "Stavan-Jain/QECLean",
        "lean-dojo/TorchLean"]
def get(endpoint):
    headers = {"Accept":"application/vnd.github+json", "User-Agent":"MathGraph-ThirdSource-MetadataLock-v1",
               "X-GitHub-Api-Version":"2022-11-28"}
    token=os.getenv("GH_TOKEN","")
    if token: headers["Authorization"]="Bearer "+token
    with urllib.request.urlopen(urllib.request.Request("https://api.github.com/"+endpoint,headers=headers),timeout=35) as f:
        return json.load(f)
def pick():
    rows=[]
    for name in POOL:
        try:
            d=get("repos/"+name)
            ok = (not d.get("private",True) and not d.get("archived",True)
                  and not d.get("disabled",True) and not d.get("fork",True)
                  and d.get("pushed_at","")>="2026-07-01T00:00:00Z"
                  and 0 < int(d.get("size",0)) <= 250000)
            row={"repository":name,"eligible":bool(ok),"metadata":{
                k:d.get(k) for k in ("full_name","private","archived","disabled","fork","pushed_at","size","default_branch")}}
            if ok:
                # Branch SHA: GitHub repository metadata, not source contents.
                b=get("repos/"+name+"/branches/"+d["default_branch"])
                row["selected_sha"]=b["commit"]["sha"]
            rows.append(row)
            if ok: return {"schema":"heldout.selection.metadata.v1","pool":POOL,
                "selection_rule":"FIRST_ELIGIBLE_NO_FALLTHROUGH","selected":row,"screen":rows}
        except Exception as ex:
            rows.append({"repository":name,"eligible":False,"metadata_error":type(ex).__name__+":"+str(ex)[:160]})
    return {"schema":"heldout.selection.metadata.v1","pool":POOL,
            "selected":None,"screen":rows,"status":"UNKNOWN_POOL"}
if __name__ == "__main__":
    output=pathlib.Path(sys.argv[1]); output.parent.mkdir(parents=True,exist_ok=True)
    record=pick()
    output.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    print(json.dumps(record,sort_keys=True))
    if record.get("selected") is None: sys.exit(3)
