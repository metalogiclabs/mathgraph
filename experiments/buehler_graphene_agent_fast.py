#!/usr/bin/env python3
import json,re,hashlib
from pathlib import Path
import numpy as np
from huggingface_hub import HfApi,hf_hub_download

REPO="lamm-mit/graphene-agent-data"
REV="cb48eb13363bc81bfb4cdfe25bd163a192019cc3"
OUT=Path("evidence/buehler-graphene-fast-v1"); OUT.mkdir(parents=True,exist_ok=True)
api=HfApi()
files=[]
for e in api.list_repo_tree(repo_id=REPO,repo_type="dataset",revision=REV,recursive=True,expand=True):
    if e.__class__.__name__=="RepoFile":
        files.append({"path":e.path,"size":e.size,"blob_id":getattr(e,"blob_id",None)})
print("FILE_COUNT",len(files),"TOTAL_BYTES",sum((x["size"] or 0) for x in files))
npzs=[x for x in files if x["path"].endswith(".npz")]
print("NPZ_COUNT",len(npzs),"NPZ_TOTAL_BYTES",sum((x["size"] or 0) for x in npzs))
print("NPZ_SMALLEST",sorted(npzs,key=lambda x:x["size"] or 10**30)[:20])
print("NPZ_LARGEST",sorted(npzs,key=lambda x:x["size"] or 0,reverse=True)[:10])

def dl(path):
    return Path(hf_hub_download(repo_id=REPO,repo_type="dataset",revision=REV,filename=path))

# Read authoritative README / captions / JSON experiment descriptors.
text_paths=["README.md","movies/README.md","movies/captions.json",
            "movies/M01_baselines_pristine_vs_precrack.json",
            "movies/M02_slit_angle_series.json",
            "movies/M03_tip_overlap_control.json",
            "movies/M04_hierarchy_vs_alignment.json",
            "movies/M05_alignment_sweep_single_level.json",
            "movies/M06_disorder_and_gradients_are_costs.json",
            "movies/M07_flaw_halo.json",
            "movies/M08_fracture_modes_progressive_vs_avalanche.json",
            "movies/M09_closeup_en_echelon_linking.json",
            "movies/M10_closeup_aligned_hierarchy.json"]
texts={}
refs=set()
for p in text_paths:
    try:
        fp=dl(p); b=fp.read_bytes(); s=b.decode("utf-8","replace")
        texts[p]={"sha256":hashlib.sha256(b).hexdigest(),"size":len(b),"text":s}
        print("\n===== TEXT",p,"=====\n",s[:30000])
        refs.update(re.findall(r"run_\d{8}_\d{6}_[0-9a-f]+(?:\.npz)?",s))
    except Exception as ex:
        texts[p]={"error":repr(ex)}
print("REFERENCED_RUN_IDS",sorted(refs))

# Inspect referenced trajectories if resolvable; otherwise the 6 smallest as schema probes.
path_by_stem={Path(x["path"]).stem:x["path"] for x in npzs}
chosen=[]
for r in sorted(refs):
    stem=Path(r).stem
    if stem in path_by_stem: chosen.append(path_by_stem[stem])
if not chosen:
    chosen=[x["path"] for x in sorted(npzs,key=lambda x:x["size"] or 10**30)[:6]]
chosen=list(dict.fromkeys(chosen))[:20]
print("CHOSEN_NPZ",chosen)
traj={}
for p in chosen:
    try:
        fp=dl(p)
        z=np.load(fp,allow_pickle=True)
        rec={}
        for k in z.files:
            a=z[k]
            info={"dtype":str(a.dtype),"shape":list(a.shape)}
            if a.size<=30:
                try: info["value"]=a.tolist()
                except Exception: info["repr"]=repr(a)
            elif a.dtype.kind in "fiu":
                try:
                    info.update({"min":float(np.nanmin(a)),"max":float(np.nanmax(a)),
                                 "first":np.asarray(a).reshape(-1)[:5].tolist(),
                                 "last":np.asarray(a).reshape(-1)[-5:].tolist()})
                except Exception: pass
            elif a.dtype==object and a.size<=100:
                try: info["object_repr"]=repr(a.tolist())[:10000]
                except Exception: pass
            rec[k]=info
        traj[p]=rec
        print("\n===== NPZ",p,"=====")
        print(json.dumps(rec,indent=2)[:30000])
    except Exception as ex:
        traj[p]={"error":repr(ex)}
        print("NPZ ERROR",p,repr(ex))
out={"schema":"mathgraph.buehler-graphene-fast-v1","source":{"repo":REPO,"revision":REV},
     "file_count":len(files),"npz_count":len(npzs),"npz_total_bytes":sum((x["size"] or 0) for x in npzs),
     "npz_files":npzs,"texts":texts,"refs":sorted(refs),"chosen_npz":chosen,"trajectories":traj}
(OUT/"fast.json").write_text(json.dumps(out,indent=2,sort_keys=True))
