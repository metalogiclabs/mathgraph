import json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v13_symbolic_composition as v13


def spatial_adj(g,nodes,path_color,conn8=False,touch8=False):
    h,w=run_v2.v1.shape(g); node_owner={p:k for k,o in enumerate(nodes) for p in o['pts']}
    path={(i,j) for i in range(h) for j in range(w) if g[i][j]==path_color and (i,j) not in node_owner}
    cdirs=[(-1,0),(1,0),(0,-1),(0,1)] + ([(-1,-1),(-1,1),(1,-1),(1,1)] if conn8 else [])
    tdirs=[(-1,0),(1,0),(0,-1),(0,1)] + ([(-1,-1),(-1,1),(1,-1),(1,1)] if touch8 else [])
    unseen=set(path); adj=[set() for _ in nodes]
    while unseen:
        s=min(unseen); unseen.remove(s); st=[s]; cc={s}
        while st:
            i,j=st.pop()
            for di,dj in cdirs:
                q=(i+di,j+dj)
                if q in unseen: unseen.remove(q);cc.add(q);st.append(q)
        touch=set()
        for i,j in cc:
            for di,dj in tdirs:
                q=(i+di,j+dj)
                if q in node_owner:touch.add(node_owner[q])
        for a in touch:
            adj[a]|=(touch-{a})
    return adj


def program(path_color,conn8,touch8,orientation):
    def f(g):
        bg,nodes,succ,indeg,roots=v13.symbolic_graph(g)
        if len(nodes)<2:return None
        adj=spatial_adj(g,nodes,path_color,conn8,touch8)
        selected=[]
        for a,b in succ.items():
            if b in adj[a]: selected.append((a,b))
        if not selected:return None
        # spatial components should specify disjoint composition pairs
        used=set(); pairs=[]
        for a,b in sorted(selected,key=lambda ab:nodes[ab[0]]['anchor']):
            if a in used or b in used: continue
            used|={a,b};pairs.append((a,b))
        out=[list(r) for r in g]
        keep=set()
        for a,b in pairs:
            if orientation=='source':
                k,drop=a,b; val=nodes[b]['center']
            else:
                k,drop=b,a; val=nodes[a]['border']
            ci,cj=nodes[k]['center_pt'];out[ci][cj]=val;keep.add(k)
            for i,j in nodes[drop]['pts']:out[i][j]=bg
        for k,o in enumerate(nodes):
            if k not in keep and k not in {x for p in pairs for x in p}:
                for i,j in o['pts']:out[i][j]=bg
        return tuple(tuple(r) for r in out)
    return f


def candidates(task):
    colors=sorted({x for inp,_ in run_v2.v1.task_pairs(task) for r in inp for x in r if x!=0})
    for c in colors:
      for conn8 in (False,True):
       for touch8 in (False,True):
        for orient in ('source','target'):
            yield f'hybrid:path={c}:conn={8 if conn8 else 4}:touch={8 if touch8 else 4}:keep={orient}',program(c,conn8,touch8,orient)


def main():
    tasks=run_v2.v1.load_tasks(sys.argv[1]);fits=[];solves=[];rows=[];total=0
    for tid,t in sorted(tasks.items()):
      found=None;tried=0
      for name,p in candidates(t):
        tried+=1;total+=1
        try:fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
        except Exception:fit=False
        if fit:
          try:solved=run_v2.v1.task_solved(p,t)
          except Exception:solved=False
          found=(name,solved);break
      if found:
        name,solved=found;fits.append(tid)
        if solved:solves.append(tid)
        rows.append({'task':tid,'fit':True,'heldout_solved':solved,'program':name,'candidate_evaluations':tried})
      else:rows.append({'task':tid,'fit':False,'heldout_solved':False,'program':None,'candidate_evaluations':tried})
    result={'schema':'verified-developmental-navigation.arc-agi2-hybrid-topology.v20','source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
      'meta_loop':{'v19':'Simple 4-connected path intersection gave 0 fits.','meta_check':'Before rejecting the hybrid theory, test adequacy of its operationalization: path connectivity (4/8), node-touch connectivity (4/8), and which endpoint carries the composed relation. This is a bounded implementation-equivalence separator, not a new representation.','criterion':'If any topology restores d35bdbdc, retain hybrid relation and localize topology. If none does, reject this bounded hybrid family.'},
      'declared_language':{'symbolic':'center(A)==border(B)','path_component_connectivity':[4,8],'path_to_node_touch':[4,8],'retained_endpoint':['source','target']},
      'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,'candidate_evaluations':total,'restores_d35':'d35bdbdc' in fits,'strict_heldout_gain_over_v13':bool(solves),'rows':rows}
    out=HERE/'results_v20_hybrid_topology';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
