import collections
import importlib.util
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v1", HERE / "run.py")
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)

NEW_BASE = v1.FAMILIES + ["component_extract", "separator_tile", "concat_symmetry"]
EXTENSION = "structural_then_recolor"


def connected_components(g, color, diag=False):
    h, w = v1.shape(g)
    unseen = {(i, j) for i in range(h) for j in range(w) if g[i][j] == color}
    comps = []
    dirs = [(-1,0),(1,0),(0,-1),(0,1)]
    if diag:
        dirs += [(-1,-1),(-1,1),(1,-1),(1,1)]
    while unseen:
        seed = min(unseen)
        stack = [seed]
        unseen.remove(seed)
        comp = {seed}
        while stack:
            i, j = stack.pop()
            for di, dj in dirs:
                q = (i+di, j+dj)
                if q in unseen:
                    unseen.remove(q); comp.add(q); stack.append(q)
        comps.append(comp)
    return comps


def crop_points(g, pts):
    if not pts:
        return None
    rs = [i for i,j in pts]; cs = [j for i,j in pts]
    a,b,c,d = min(rs),max(rs),min(cs),max(cs)
    return tuple(tuple(g[i][j] for j in range(c,d+1)) for i in range(a,b+1))


def component_programs(pairs):
    cs = sorted(set().union(*(v1.colors(i) for i,_ in pairs)))
    ans = []
    for c in cs:
        for diag in (False, True):
            for mode in ("largest", "smallest", "first", "last"):
                def f(g, c=c, diag=diag, mode=mode):
                    comps = connected_components(g, c, diag)
                    if not comps: return None
                    if mode == "largest": comp = max(comps, key=lambda z:(len(z), -min(z)[0], -min(z)[1]))
                    elif mode == "smallest": comp = min(comps, key=lambda z:(len(z), min(z)[0], min(z)[1]))
                    elif mode == "first": comp = min(comps, key=lambda z:min(z))
                    else: comp = max(comps, key=lambda z:min(z))
                    return crop_points(g, comp)
                ans.append((f"component:{c}:{8 if diag else 4}:{mode}", f))
    return ans


def split_tiles(g):
    h,w = v1.shape(g)
    solid_rows = [i for i,r in enumerate(g) if len(set(r)) == 1]
    solid_cols = [j for j in range(w) if len({g[i][j] for i in range(h)}) == 1]
    def spans(n, cuts):
        cuts = sorted(set(cuts))
        out=[]; s=0
        for c in cuts:
            if s < c: out.append((s,c))
            s=c+1
        if s<n: out.append((s,n))
        return out
    rs = spans(h, solid_rows); cs = spans(w, solid_cols)
    tiles=[]
    for a,b in rs:
        for c,d in cs:
            if a<b and c<d:
                tiles.append(tuple(tuple(g[i][j] for j in range(c,d)) for i in range(a,b)))
    return tiles


def separator_programs(pairs):
    maxn = max([len(split_tiles(i)) for i,_ in pairs] + [0])
    ans=[]
    for k in range(min(maxn, 25)):
        def f(g,k=k):
            ts=split_tiles(g)
            return ts[k] if k < len(ts) else None
        ans.append((f"separator_tile:{k}", f))
    return ans


def hcat(a,b):
    if len(a)!=len(b): return None
    return tuple(tuple(x for x in ra)+tuple(x for x in rb) for ra,rb in zip(a,b))


def vcat(a,b):
    if (a and b) and len(a[0])!=len(b[0]): return None
    return tuple(a)+tuple(b)


def concat_programs(pairs):
    ans=[]
    for name,fn in v1.GEOMS:
        for side in ("h_lr","h_rl","v_tb","v_bt"):
            def f(g,fn=fn,side=side):
                z=fn(g)
                if side=="h_lr": return hcat(g,z)
                if side=="h_rl": return hcat(z,g)
                if side=="v_tb": return vcat(g,z)
                return vcat(z,g)
            ans.append((f"concat:{side}:{name}",f))
    return ans


def programs(family,pairs):
    if family in v1.FAMILIES:
        return v1.candidate_programs(family,pairs)
    if family=="component_extract": return component_programs(pairs)
    if family=="separator_tile": return separator_programs(pairs)
    if family=="concat_symmetry": return concat_programs(pairs)
    if family==EXTENSION:
        ans=[]
        structural=[]
        # Base structural languages, excluding direct recolor to avoid duplicate identity recolor.
        for fam in ["geom","crop_color","crop_nonbg","scale_cells","tile_grid","downsample_uniform","component_extract","separator_tile","concat_symmetry"]:
            structural.extend((fam,name,p) for name,p in programs(fam,pairs))
        for fam,name,p in structural:
            m=v1.infer_recolor(pairs,pre=p)
            if m is not None:
                ans.append((f"{fam}/{name}+recolor:{repr(sorted(m.items()))}",v1.recolor_program(m,pre=p)))
        return ans
    raise KeyError(family)


def first_fit(task,family):
    pairs=v1.task_pairs(task); tried=0
    for name,p in programs(family,pairs):
        tried+=1
        if v1.exact_on_pairs(p,pairs): return name,p,tried
    return None,None,tried


def family_success(task,fam):
    _,p,_=first_fit(task,fam)
    return bool(p and v1.task_solved(p,task))


def train_router(tasks):
    gok=collections.Counter(); gseen=collections.Counter(); sok=collections.defaultdict(collections.Counter); sseen=collections.defaultdict(collections.Counter)
    solved_ids=collections.defaultdict(list)
    for tid,task in sorted(tasks.items()):
        sig=v1.signature(task)
        for fam in NEW_BASE:
            gseen[fam]+=1; sseen[sig][fam]+=1
            if family_success(task,fam):
                gok[fam]+=1; sok[sig][fam]+=1; solved_ids[fam].append(tid)
    def grate(f): return (gok[f]+1)/(gseen[f]+2)
    global_order=sorted(NEW_BASE,key=lambda f:(-grate(f),NEW_BASE.index(f)))
    orders={}
    for sig in sseen:
        def score(f):
            return (sok[sig][f]+4*grate(f))/(sseen[sig][f]+4)
        orders[sig]=sorted(NEW_BASE,key=lambda f:(-score(f),global_order.index(f)))
    return global_order,orders,dict(gok),dict(gseen),{k:v for k,v in solved_ids.items()}


def solve(task,order,extend=False):
    pairs=v1.task_pairs(task); tried=0
    for fam in order:
        for name,p in programs(fam,pairs):
            tried+=1
            if v1.exact_on_pairs(p,pairs):
                return fam,name,p,tried,False
    if extend:
        for name,p in programs(EXTENSION,pairs):
            tried+=1
            if v1.exact_on_pairs(p,pairs):
                return EXTENSION,name,p,tried,True
    return None,None,None,tried,False


def arm(tasks,order_fn,extend=False):
    rows=[]
    for tid,task in sorted(tasks.items()):
        fam,name,p,tried,used=solve(task,order_fn(task),extend)
        rows.append({"task":tid,"solved":bool(p and v1.task_solved(p,task)),"fit_found":p is not None,"candidate_evaluations":tried,"family":fam,"program":name,"extension_used":used})
    return rows


def summary(rows):
    c=[r["candidate_evaluations"] for r in rows]
    return {"tasks":len(rows),"solved":sum(r["solved"] for r in rows),"fit_found":sum(r["fit_found"] for r in rows),"total_candidate_evaluations":sum(c),"mean_candidate_evaluations":sum(c)/len(c),"median_candidate_evaluations":statistics.median(c),"extension_used":sum(r["extension_used"] for r in rows),"extension_solved":sum(r["extension_used"] and r["solved"] for r in rows)}


def main():
    if len(sys.argv)!=3: raise SystemExit("usage run_v2.py TRAIN_DIR EVAL_DIR")
    train=v1.load_tasks(sys.argv[1]); ev=v1.load_tasks(sys.argv[2])
    order,orders,gok,gseen,train_solved=train_router(train)
    G=arm(ev,lambda t:order,False)
    V=arm(ev,lambda t:orders.get(v1.signature(t),order),False)
    E=arm(ev,lambda t:orders.get(v1.signature(t),order),True)
    gb={r['task']:r for r in G}; vb={r['task']:r for r in V}; eb={r['task']:r for r in E}
    common=[t for t in gb if gb[t]['solved'] and vb[t]['solved']]
    cg=sum(gb[t]['candidate_evaluations'] for t in common); cv=sum(vb[t]['candidate_evaluations'] for t in common)
    new=[t for t in eb if eb[t]['solved'] and not vb[t]['solved']]
    lost=[t for t in eb if vb[t]['solved'] and not eb[t]['solved']]
    SG,SV,SE=summary(G),summary(V),summary(E)
    result={
      "schema":"verified-developmental-navigation.arc-agi2-live.v2",
      "source":{"repository":"arcprize/ARC-AGI-2","commit":"f3283f727488ad98fe575ea6a5ac981e4a188e49","training_tasks":len(train),"evaluation_tasks":len(ev)},
      "residual_from_v1":"No frozen base or geometry+recolor candidate fit all demonstrations for any of 120 evaluation tasks; representation/language expansion required.",
      "base_families":NEW_BASE,"extension_family":EXTENSION,"global_learned_order":order,"signature_count":len(orders),
      "training_family_exact_solve_counts":gok,"training_solved_task_ids":train_solved,
      "global":SG,"vdn_base":SV,"vdn_with_extension":SE,
      "common_solved":{"count":len(common),"global_total_candidate_evaluations":cg,"vdn_total_candidate_evaluations":cv,"ratio_global_over_vdn":cg/cv if cv else None},
      "newly_solved_by_extension":new,"lost_by_extension":lost,
      "navigation_advantage":SV['solved']>=SG['solved'] and cv<cg,
      "developmental_phase_change":bool(new) and not lost,
      "rows":{"global":G,"vdn_base":V,"vdn_with_extension":E}
    }
    out=HERE/'results_v2'; out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','training_solved_task_ids')},indent=2,sort_keys=True))
    print('NAVIGATION_ADVANTAGE',result['navigation_advantage'])
    print('DEVELOPMENTAL_PHASE_CHANGE',result['developmental_phase_change'])

if __name__=='__main__': main()
