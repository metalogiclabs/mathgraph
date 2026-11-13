import collections, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v8_object_relational as v8

# V18 is RETROSPECTIVE/KNOWN_WORLD with respect to d35bdbdc: V17 plus the
# heldout diagnostic revealed that fixed 3x3-ring parsing itself fails on one
# test case. The representation repair is therefore derived from that residual.
# We test whether the abstraction transfers beyond the trigger task.

def detect_motifs(g):
    bg=v8.mode_color(g); h,w=run_v2.v1.shape(g); cand=[]
    for i in range(1,h-1):
      for j in range(1,w-1):
        card=[g[i-1][j],g[i+1][j],g[i][j-1],g[i][j+1]]
        if len(set(card))!=1: continue
        b=card[0]; c=g[i][j]
        if b==bg or c==b: continue
        pts={(i,j),(i-1,j),(i+1,j),(i,j-1),(i,j+1)}
        # If all four diagonals agree with the carrier, the motif is a full ring.
        diag={(i-1,j-1),(i-1,j+1),(i+1,j-1),(i+1,j+1)}
        if all(g[a][q]==b for a,q in diag): pts |= diag
        cand.append({'center_pt':(i,j),'anchor':min(pts),'pts':pts,'border':b,'center':c})
    # deterministic non-overlap; prefer larger motifs (ring before cross)
    cand.sort(key=lambda o:(-len(o['pts']),o['anchor']))
    out=[]; used=set()
    for o in cand:
      if not(o['pts'] & used): out.append(o); used |= o['pts']
    return bg,out

def chains(g, unique=True):
    bg,nodes=detect_motifs(g); by_border=collections.defaultdict(list)
    for k,o in enumerate(nodes): by_border[o['border']].append(k)
    succ={}; indeg=[0]*len(nodes)
    for k,o in enumerate(nodes):
      qs=[q for q in by_border.get(o['center'],[]) if q!=k]
      if unique and len(qs)!=1: continue
      if not qs: continue
      q=min(qs,key=lambda z:nodes[z]['anchor'])
      succ[k]=q; indeg[q]+=1
    roots=[k for k,d in enumerate(indeg) if d==0]
    seen=set(); chs=[]
    for r in sorted(roots,key=lambda k:nodes[k]['anchor']):
      ch=[]; cur=r
      while cur not in seen:
        seen.add(cur); ch.append(cur)
        if cur not in succ: break
        cur=succ[cur]
      chs.append(ch)
    if len(nodes)<2 or len(seen)!=len(nodes): return None
    return bg,nodes,chs

def program(tail='delete',unique=True):
  def f(g):
    q=chains(g,unique)
    if q is None:return None
    bg,nodes,chs=q; z=[list(r) for r in g]
    for ch in chs:
      k=0
      while k<len(ch):
        a=ch[k]
        if k+1<len(ch):
          b=ch[k+1]; ci,cj=nodes[a]['center_pt']; z[ci][cj]=nodes[b]['center']
          for p,q in nodes[b]['pts']: z[p][q]=bg
          k+=2
        else:
          if tail=='delete':
            for p,q in nodes[a]['pts']: z[p][q]=bg
          k+=1
    return tuple(tuple(r) for r in z)
  return f

def main():
  if len(sys.argv)!=2: raise SystemExit('usage run_v18_symbolic_motif.py EVAL_DIR')
  tasks=run_v2.v1.load_tasks(sys.argv[1]); variants=[]
  for unique in (True,False):
    for tail in ('delete','keep'): variants.append((f'motif:{"unique" if unique else "first"}:{tail}',program(tail,unique)))
  fits=[]; solves=[]; rows=[]; total=0
  for tid,t in sorted(tasks.items()):
    fp=[]; sp=[]
    for n,p in variants:
      total+=1
      try: fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
      except Exception: fit=False
      if fit:
        fp.append(n)
        try:
          if run_v2.v1.task_solved(p,t): sp.append(n)
        except Exception: pass
    if fp: fits.append(tid)
    if sp: solves.append(tid)
    rows.append({'task':tid,'fit_programs':fp,'heldout_solved_programs':sp})
  result={
    'schema':'verified-developmental-navigation.arc-agi2-symbolic-motif.v18',
    'evidence_label':'KNOWN_WORLD_RETROSPECTIVE_REPAIR',
    'source':{'repository':'arcprize/ARC-AGI-2','commit':'f3283f727488ad98fe575ea6a5ac981e4a188e49','evaluation_tasks':len(tasks)},
    'residual':'V17 exhausted eight action policies while d35bdbdc test[0] did not parse under the fixed 3x3-ring ontology. Therefore the next change is representation-level, not another chain action.',
    'representation_change':'Replace fixed 3x3 uniform-border glyph by a centered motif: four cardinal carrier cells of one color around a distinct payload; include matching diagonals when present. This subsumes square rings and crosses.',
    'variants':[n for n,_ in variants],'candidate_evaluations':total,
    'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,
    'trigger_task_solved':'d35bdbdc' in solves,
    'source_distinct_solved_ids':[x for x in solves if x!='d35bdbdc'],
    'rows':rows,
    'claim_boundary':'Retrospective repair on public ARC-AGI-2 evaluation data. Any trigger-task solve is diagnostic, not protected evidence. Source-distinct gains are transfer candidates requiring a new protected split.'
  }
  out=HERE/'results_v18_symbolic_motif'; out.mkdir(exist_ok=True)
  (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
  print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
