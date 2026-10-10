#!/usr/bin/env python3
"""VDN V25: verifier-guided *representation* refinement, not search priority.

Source development: ConceptARC 160 source tasks (corpus/).
Untouched protected evaluation: the 16 separately authored MinimalTasks.
The protected directory is not checked out until a source-trained feature
selection policy has been frozen and source receipt hashed.

Feature families are explicitly supplied and FINITE; selecting one is not
unrestricted predicate invention. Training can reveal a cell-colour quotient
obstruction; a typed relational feature splits its equivalence class. A new
feature set is admitted only when its induced deterministic input/output map
passes BOTH source demonstrations and independent source task test examples.

Target task parameter maps may be learned from its demonstration examples;
protected target test output pixels are never used until after ALL arms freeze.
"""
from __future__ import annotations
import argparse,collections,hashlib,itertools,json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v23_generator_feedback as v23
import run_v5_retention as v5

PIN="0e67da6af879e4bad3d7cd3c196e8d551b445725"
FEATS=("color","position","edge","same_neighbours","nonzero_neighbours",
       "component_size","component_boundary","component_enclosed",
       "component_border","row_load","col_load","nonzero_bbox")
EXTRAS=FEATS[1:]
BUDGET=48


def dump(obj,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")


def hash_obj(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def norm_grid(g):
    return tuple(tuple(v for v in row) for row in g)


def grid_features(g):
    """Explicit typed finite feature interface; no test labels or metadata."""
    h,w=len(g),len(g[0]); comps={};seen=set()
    nr=[sum(x!=0 for x in r) for r in g]
    nc=[sum(g[i][j]!=0 for i in range(h)) for j in range(w)]
    pts=[(i,j) for i in range(h) for j in range(w) if g[i][j]!=0]
    if pts: bounds=(min(i for i,j in pts),max(i for i,j in pts),
                    min(j for i,j in pts),max(j for i,j in pts))
    else:bounds=(0,-1,0,-1)
    for i in range(h):
        for j in range(w):
            if (i,j) in seen:continue
            col=g[i][j];todo=[(i,j)];seen.add((i,j));cells=[]
            while todo:
                x,y=todo.pop();cells.append((x,y))
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    xx,yy=x+dx,y+dy
                    if 0<=xx<h and 0<=yy<w and (xx,yy) not in seen and g[xx][yy]==col:
                        seen.add((xx,yy));todo.append((xx,yy))
            border=collections.Counter()
            for x,y in cells:
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    xx,yy=x+dx,y+dy
                    if 0<=xx<h and 0<=yy<w and g[xx][yy]!=col:
                        border[g[xx][yy]]+=1
            touch=any(x in (0,h-1) or y in (0,w-1) for x,y in cells)
            outborder=(border.most_common(1)[0][0] if border else -1)
            for coord in cells:
                comps[coord]=(len(cells),touch,outborder)
    feats={}
    for i in range(h):
        for j in range(w):
            ns=[g[ii][jj] for ii,jj in ((i+1,j),(i-1,j),(i,j+1),(i,j-1))
                if 0<=ii<h and 0<=jj<w]
            size,touch,border=comps[(i,j)]
            bbox=(int(bounds[0]<=i<=bounds[1]),int(bounds[2]<=j<=bounds[3]))
            feats[i,j]={
              "color":g[i][j],
              "position":((0 if i==0 else 2 if i==h-1 else 1),
                          (0 if j==0 else 2 if j==w-1 else 1)),
              "edge":int(i in (0,h-1) or j in (0,w-1)),
              "same_neighbours":min(4,sum(x==g[i][j] for x in ns)),
              "nonzero_neighbours":min(4,sum(x!=0 for x in ns)),
              "component_size":(0 if size==1 else 1 if size<=3 else 2 if size<=9 else 3),
              "component_boundary":int(touch),
              "component_enclosed":int(not touch),
              "component_border":border,
              "row_load":min(4,nr[i]),
              "col_load":min(4,nc[j]),
              "nonzero_bbox":bbox,
            }
    return feats


def samples(pairs):
    """Precompute deterministic source observation signatures once."""
    out=[]
    for pair in pairs:
        g=norm_grid(pair["input"])
        y=norm_grid(pair["output"])
        if not g or not g[0] or len(g)!=len(y) or len(g[0])!=len(y[0]):
            return None
        fs=grid_features(g)
        out.extend((fs[i,j],y[i][j],g[i][j])
                   for i in range(len(g)) for j in range(len(g[0])))
    return out


def fit(data,features):
    if data is None:return None
    mapping={}
    for f,target,_ in data:
        key=tuple(f[n] for n in features)
        if key in mapping and mapping[key]!=target:return None
        mapping[key]=target
    return mapping


def apply(g,features,mapping):
    g=norm_grid(g);fs=grid_features(g)
    return tuple(tuple(mapping.get(tuple(fs[i,j][x] for x in features),g[i][j])
                       for j in range(len(g[0]))) for i in range(len(g)))


def tests_exact(task,features,mapping):
    return all(apply(t["input"],features,mapping)==norm_grid(t["output"])
               for t in task["test"])


def feature_universe():
    # Color alone is the old-world scalar semantic observation.
    yield ("color",)
    # Admissible representation refinements: one or two new typed distinctions.
    for n in (1,2):
        for subset in itertools.combinations(EXTRAS,n):
            yield ("color",)+subset


def task_data(task):
    return samples(task["train"])


def source_train(root):
    all_tasks={}
    for p in sorted(Path(root).glob("*/*.json")):
        d=json.loads(p.read_text())
        if "train" in d and "test" in d:
            all_tasks[p.stem]=d
    assert len(all_tasks)==160
    universe=list(feature_universe())
    assert len(universe)==1+len(EXTRAS)+len(EXTRAS)*(len(EXTRAS)-1)//2
    source_cost=0
    winning=collections.Counter()
    baseline=0
    examples=[]
    old_color_inadequacy=0
    for tid,task in all_tasks.items():
        d=task_data(task)
        if d is None:continue
        old=fit(d,("color",))
        if old is None:
            old_color_inadequacy+=1
        elif tests_exact(task,("color",),old):
            baseline+=1
        hits=[]
        for fs in universe:
            source_cost+=1
            m=fit(d,fs)
            if m is not None and tests_exact(task,fs,m):
                hits.append(fs)
        # The verifier may admit several same-cost feature refinements.
        # Carry ALL source-qualified alternatives forward, not only one choice.
        new=[x for x in hits if x!=("color",)]
        if new and old is None or (new and old is not None and not tests_exact(task,("color",),old)):
            best_len=min(map(len,new))
            minima=[x for x in new if len(x)==best_len]
            for x in minima:winning[x]+=1
            examples.append({"source_task":tid,"admitted_feature_sets":[list(x) for x in minima]})
    candidates=[(list(fs),n) for fs,n in sorted(winning.items(),
                                  key=lambda z:(-z[1],len(z[0]),z[0]))]
    policy={"schema":"vdn.minimal-relational-representation.v25",
            "source_pin":PIN,
            "source_count":len(all_tasks),
            "source_oracle_checks":source_cost,
            "source_color_only_exact_tasks":baseline,
            "source_old_colour_insufficient":old_color_inadequacy,
            "learned_feature_sets":candidates,
            "source_witnesses":examples,
            "finite_candidate_universe":len(universe),
            "target_loaded_before_freeze":False,
            "protected_outputs_seen_before_freeze":False,
            "claim_boundary":"selected typed feature sets from a designer-supplied bounded grammar, not arbitrary predicate invention"}
    return policy


def target_tasks(root):
    ts={}
    for p in sorted(Path(root).glob("*Minimal.json")):
        t=json.loads(p.read_text())
        assert "train" in t and "test" in t
        ts[p.stem]=t
    assert len(ts)==16,len(ts)
    return ts


def attempt(task,arm,policy,budget=BUDGET):
    start=time.perf_counter()
    data=task_data(task)
    if data is None:
        return {"found":False,"checks":0,"choices":0,"program":None,
                "wall":time.perf_counter()-start}
    if arm=="color_only":
        search=[("color",)]
    elif arm=="learned_relation":
        search=[tuple(row[0]) for row in policy["learned_feature_sets"]]
        search+=list(feature_universe())
    elif arm=="no_meta":
        search=list(feature_universe())
    elif arm=="permuted_meta":
        learned=[tuple(row[0]) for row in policy["learned_feature_sets"]]
        # Break rank association deterministically without consulting target.
        learned=list(reversed(learned))
        search=learned+list(feature_universe())
    else:raise ValueError(arm)
    seen=set();checks=0;choice=None;mapping=None
    for feat in search:
        if feat in seen:continue
        seen.add(feat)
        if checks>=budget:break
        checks+=1
        m=fit(data,feat)
        if m is not None:
            choice=feat;mapping=m;break
    return {"found":choice is not None,"checks":checks,"choices":len(seen),
            "program":(choice,mapping) if choice is not None else None,
            "wall":time.perf_counter()-start}


def target_score(policy,target_dir,out,budget=BUDGET):
    ts=target_tasks(target_dir)
    arms=("color_only","no_meta","permuted_meta","learned_relation")
    selected={}
    for arm in arms:
        selected[arm]={tid:attempt(task,arm,policy,budget)
                       for tid,task in sorted(ts.items())}
    # Freeze all candidate choices before protected test outputs are read.
    frozen={a:{tid:{"found":r["found"],"checks":r["checks"],
                    "features":list(r["program"][0]) if r["found"] else None}
               for tid,r in rows.items()} for a,rows in selected.items()}
    dump(frozen,out/"target_choices_frozen.json")
    scored={}
    for arm,rs in selected.items():
        rows=[]
        for tid,r in rs.items():
            ok=bool(r["found"] and tests_exact(ts[tid],*r["program"]))
            rows.append({"id":tid,"fit":r["found"],"checks":r["checks"],
                         "features":list(r["program"][0]) if r["found"] else None,
                         "protected_solved":ok})
        scored[arm]=rows
    by={arm:{z["id"]:z for z in rows} for arm,rows in scored.items()}
    gains=sorted(tid for tid in ts if by["learned_relation"][tid]["protected_solved"]
                 and not by["color_only"][tid]["protected_solved"])
    strict=sorted(tid for tid in ts if by["learned_relation"][tid]["protected_solved"]
                  and not by["no_meta"][tid]["protected_solved"])
    controls=sorted(tid for tid in ts if by["learned_relation"][tid]["protected_solved"]
                    and not by["permuted_meta"][tid]["protected_solved"])
    regressions=sorted(tid for tid in ts if by["color_only"][tid]["protected_solved"]
                       and not by["learned_relation"][tid]["protected_solved"])
    totals={arm:{"tasks":16,"solved":sum(x["protected_solved"] for x in rows),
                 "demonstration_fits":sum(x["fit"] for x in rows),
                 "candidate_checks":sum(x["checks"] for x in rows)}
            for arm,rows in scored.items()}
    result={"schema":"vdn.conceptarc.minimal-feature-transfer.v25",
            "source":policy["source_pin"],
            "source_train_tasks":policy["source_count"],
            "target_tasks":len(ts),
            "target_type":"ConceptARC MinimalTasks, source-distinct attention checks",
            "policy_sha256":hash_obj(policy),
            "source_training_checks":policy["source_oracle_checks"],
            "arms":totals,"new_relational_witness_ids":gains,
            "new_over_strong_stateless_ids":strict,
            "meta_order_ablation_ids":controls,
            "old_retention_regressions":regressions,
            "claims":{
                "new_typed_relational_observation_heldout_gain":
                    "WARRANTED_BOUNDED" if gains and not regressions else "UNKNOWN",
                "strict_advantage_over_strong_stateless":
                    "WARRANTED_BOUNDED" if strict and controls else "UNKNOWN",
                "fully_autonomous_representation_invention":"UNKNOWN",
                "multi_generation_recursive_compounding":"UNKNOWN",
                "total_amortized_economic_gain":"UNKNOWN"},
            "protected_rows":scored}
    dump(result,out/"result.json")
    print(json.dumps({k:v for k,v in result.items() if k!="protected_rows"},indent=2))
    assert len(ts)==16
    assert all(x["candidate_checks"]<=16*budget for x in totals.values())


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=("source","protected"),required=True)
    p.add_argument("--corpus",type=Path)
    p.add_argument("--minimal",type=Path)
    p.add_argument("--policy",type=Path,required=True)
    p.add_argument("--out",type=Path)
    p.add_argument("--budget",type=int,default=BUDGET)
    a=p.parse_args()
    if a.mode=="source":
        assert a.corpus is not None
        pol=source_train(a.corpus)
        dump(pol,a.policy)
        print(json.dumps({"source_trained":pol["source_count"],
                          "new_feature_witnesses":len(pol["source_witnesses"]),
                          "learned_feature_sets":pol["learned_feature_sets"][:10],
                          "policy_digest":hash_obj(pol)},indent=2))
    else:
        assert a.minimal is not None and a.out is not None
        pol=json.loads(a.policy.read_text())
        assert pol["schema"]=="vdn.minimal-relational-representation.v25"
        assert not pol["protected_outputs_seen_before_freeze"]
        target_score(pol,a.minimal,a.out,a.budget)

if __name__=="__main__":
    main()
