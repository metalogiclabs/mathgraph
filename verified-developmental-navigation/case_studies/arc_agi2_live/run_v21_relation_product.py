import collections, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v20_supported_motifs as v20

# V21 tests the meta-residual suggested by V12->V20: spatial relation alone failed,
# symbolic relation alone fit demonstrations but did not generalize, and action-only
# completion did not repair it. Rather than invent a third unrelated ontology, compose
# the two retained relation languages: spatial grouping × symbolic composability.

def spatial_groups(g,path_color):
  bg,nodes=v20.detect(g); h,w=run_v2.v1.shape(g)
  owner={p:k for k,o in enumerate(nodes) for p in o['pts']}
  path={(i,j) for i in range(h) for j in range(w) if g[i][j]==path_color and (i,j) not in owner}
  unseen=set(path); adj=[set() for _ in nodes]
  while unseen:
    s=min(unseen);unseen.remove(s);stack=[s];cc={s}
    while stack:
      i,j=stack.pop()
      for di,dj in ((-1,0),(1,0),(0,-1),(0,1)):
        q=(i+di,j+dj)
        if q in unseen:unseen.remove(q);cc.add(q);stack.append(q)
    touch=set()
    for i,j in cc:
      for di,dj in ((-1,0),(1,0),(0,-1),(0,1)):
        q=(i+di,j+dj)
        if q in owner:touch.add(owner[q])
    for a in touch:
      for b in touch:
        if a!=b:adj[a].add(b)
  # connected components over nodes; isolated nodes remain singleton groups
  unseen=set(range(len(nodes))); groups=[]
  while unseen:
    r=min(unseen);unseen.remove(r);st=[r];grp={r}
    while st:
      a=st.pop()
      for b in adj[a]:
        if b in unseen:unseen.remove(b);grp.add(b);st.append(b)
    groups.append(sorted(grp,key=lambda k:nodes[k]['anchor']))
  return bg,nodes,groups

def symbolic_chains(nodes, group):
  by=collections.defaultdict(list)
  for k in group:by[nodes[k]['border']].append(k)
  succ={};indeg={k:0 for k in group}
  for k in group:
    qs=[q for q in by.get(nodes[k]['center'],[]) if q!=k]
    if len(qs)==1:succ[k]=qs[0];indeg[qs[0]]+=1
  roots=[k for k in group if indeg[k]==0];seen=set();chs=[]
  for r in sorted(roots,key=lambda k:nodes[k]['anchor']):
    ch=[];cur=r
    while cur not in seen:
      seen.add(cur);ch.append(cur)
      if cur not in succ:break
      cur=succ[cur]
    chs.append(ch)
  # any unresolved nodes are appended as singleton residuals; action policy decides tail.
  for k in group:
    if k not in seen:chs.append([k])
  return chs

def program(path_color,tail='delete'):
  def f(g):
    bg,nodes,groups=spatial_groups(g,path_color)
    if len(nodes)<2:return None
    z=[list(r) for r in g]
    for grp in groups:
      for ch in symbolic_chains(nodes,grp):
        k=0
        while k<len(ch):
          a=ch[k]
          if k+1<len(ch):
            b=ch[k+1]
            # only compose an actually symbolic-adjacent pair
            if nodes[a]['center']!=nodes[b]['border']:
              if tail=='delete':
                for p,q in nodes[a]['pts']:z[p][q]=bg
              k+=1;continue
            ci,cj=nodes[a]['center_pt'];z[ci][cj]=nodes[b]['center']
            for p,q in nodes[b]['pts']:z[p][q]=bg
            k+=2
          else:
            if tail=='delete':
              for p,q in nodes[a]['pts']:z[p][q]=bg
            k+=1
    return tuple(tuple(r) for r in z)
  return f

def candidates(task):
  colors=sorted({x for inp,_ in run_v2.v1.task_pairs(task) for row in inp for x in row if x!=0})
  for pc in colors:
    for tail in ('delete','keep'):
      yield f'product:path={pc}:tail={tail}',program(pc,tail)

def main():
  if len(sys.argv)!=2:raise SystemExit('usage run_v21_relation_product.py EVAL_DIR')
  tasks=run_v2.v1.load_tasks(sys.argv[1]);fits=[];solves=[];rows=[];total=0
  for tid,t in sorted(tasks.items()):
    fp=[];sp=[]
    for n,p in candidates(t):
      total+=1
      try:fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
      except Exception:fit=False
      if fit:
        fp.append(n)
        try:
          if run_v2.v1.task_solved(p,t):sp.append(n)
        except Exception:pass
    if fp:fits.append(tid)
    if sp:solves.append(tid)
    rows.append({'task':tid,'fit_programs':fp,'heldout_solved_programs':sp})
  result={'schema':'verified-developmental-navigation.arc-agi2-relation-product.v21','evidence_label':'KNOWN_WORLD_RETROSPECTIVE_REPAIR',
   'meta_move':'COMPOSE_REPRESENTATIONS: spatial grouping × symbolic equality, after each relation language alone exposed a different residual',
   'candidate_evaluations':total,'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,
   'trigger_task_solved':'d35bdbdc' in solves,'source_distinct_solved_ids':[x for x in solves if x!='d35bdbdc'],'rows':rows,
   'claim_boundary':'Known-world diagnostic on public evaluation data. Protected transfer is required before a recursive-improvement claim.'}
  out=HERE/'results_v21_relation_product';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
  print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
