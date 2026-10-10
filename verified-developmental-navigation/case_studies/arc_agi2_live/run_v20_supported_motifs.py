import collections, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2
import run_v12_scene_graph as v12
import run_v8_object_relational as v8

# Residual from V18/V19: a naive union of ring and cross detectors destroys the
# training fit by admitting incidental crosses. Repair: preserve exact V13 ring
# nodes, and admit a cross only when it participates in the same symbolic key
# relation as an already admitted ring; if a grid has no rings, require crosses
# to support each other by key equality. This changes the ontology admission
# rule, not the action rule.

def cross_candidates(g,bg):
  h,w=run_v2.v1.shape(g); out=[]
  for i in range(1,h-1):
    for j in range(1,w-1):
      c=g[i][j]; ns=[g[i-1][j],g[i+1][j],g[i][j-1],g[i][j+1]]
      if len(set(ns))!=1 or ns[0]==bg or c==ns[0]:continue
      b=ns[0]; ds=[g[i-1][j-1],g[i-1][j+1],g[i+1][j-1],g[i+1][j+1]]
      if any(x==b for x in ds):continue
      pts={(i,j),(i-1,j),(i+1,j),(i,j-1),(i,j+1)}
      out.append({'center_pt':(i,j),'anchor':min(pts),'pts':pts,'border':b,'center':c,'kind':'cross'})
  return out

def detect(g):
  bg,rings=v12.detect_nodes(g)
  for o in rings:o['kind']='ring'
  crosses=cross_candidates(g,bg)
  if rings:
    rb={o['border'] for o in rings}; rc={o['center'] for o in rings}
    crosses=[o for o in crosses if o['center'] in rb or o['border'] in rc]
  else:
    cb={o['border'] for o in crosses}; cc={o['center'] for o in crosses}
    crosses=[o for o in crosses if o['center'] in cb or o['border'] in cc]
  cand=list(rings)+crosses; cand.sort(key=lambda o:(0 if o['kind']=='ring' else 1,o['anchor']))
  out=[];used=set()
  for o in cand:
    if not(o['pts']&used):out.append(o);used|=o['pts']
  return bg,out

def chains(g):
  bg,nodes=detect(g);by=collections.defaultdict(list)
  for k,o in enumerate(nodes):by[o['border']].append(k)
  succ={};indeg=[0]*len(nodes)
  for k,o in enumerate(nodes):
    qs=[q for q in by.get(o['center'],[]) if q!=k]
    if len(qs)==1:succ[k]=qs[0];indeg[qs[0]]+=1
  roots=[k for k,d in enumerate(indeg) if d==0]; seen=set(); chs=[]
  for r in sorted(roots,key=lambda k:nodes[k]['anchor']):
    ch=[];cur=r
    while cur not in seen:
      seen.add(cur);ch.append(cur)
      if cur not in succ:break
      cur=succ[cur]
    chs.append(ch)
  if len(nodes)<2 or len(seen)!=len(nodes):return None
  return bg,nodes,chs

def program(tail='delete'):
  def f(g):
    q=chains(g)
    if q is None:return None
    bg,nodes,chs=q;z=[list(r) for r in g]
    for ch in chs:
      k=0
      while k<len(ch):
        a=ch[k]
        if k+1<len(ch):
          b=ch[k+1];ci,cj=nodes[a]['center_pt'];z[ci][cj]=nodes[b]['center']
          for p,r in nodes[b]['pts']:z[p][r]=bg
          k+=2
        else:
          if tail=='delete':
            for p,r in nodes[a]['pts']:z[p][r]=bg
          k+=1
    return tuple(tuple(r) for r in z)
  return f

def main():
  if len(sys.argv)!=2:raise SystemExit('usage run_v20_supported_motifs.py EVAL_DIR')
  tasks=run_v2.v1.load_tasks(sys.argv[1]); V=[('supported-delete',program('delete')),('supported-keep',program('keep'))]
  fits=[];solves=[];rows=[]
  for tid,t in sorted(tasks.items()):
    fp=[];sp=[]
    for n,p in V:
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
  result={'schema':'verified-developmental-navigation.arc-agi2-supported-motifs.v20','evidence_label':'KNOWN_WORLD_RETROSPECTIVE_REPAIR',
   'change':'cross motifs are admitted only when supported by the symbolic key relation; exact V13 ring nodes remain primary',
   'demonstration_fit_count':len(fits),'heldout_solved_count':len(solves),'fit_ids':fits,'heldout_solved_ids':solves,
   'trigger_task_solved':'d35bdbdc' in solves,'source_distinct_solved_ids':[x for x in solves if x!='d35bdbdc'],'rows':rows,
   'claim_boundary':'Known-world diagnostic. A positive result must be transferred to a fresh protected split before recursive-capability claims.'}
  out=HERE/'results_v20_supported_motifs';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
  print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
if __name__=='__main__':main()
