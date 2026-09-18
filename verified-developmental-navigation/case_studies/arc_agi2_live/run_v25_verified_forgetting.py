"""V25: quotient V23 representations by forgetting unchanged context.
Choose the coarsest matcher that still exactly reproduces every training pair,
then freeze it on held-out examples. Public evaluation => retrospective only.
"""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
import run_v2, run_v23_trace_induced_patch as v23
MODES=('changed_only','strict') # coarsest first

def match(rule,g,a,b,mode):
    ph,pw=rule['h'],rule['w']; h,w=v23.shape(g)
    if a+ph>h or b+pw>w:return None
    p2g={0:0}; g2p={0:0}
    for i in range(ph):
      for j in range(pw):
        if mode=='changed_only' and not rule['mask'][i][j]: continue
        p=rule['in'][i][j]; x=g[a+i][b+j]
        if p in p2g and p2g[p]!=x:return None
        if x in g2p and g2p[x]!=p:return None
        p2g[p]=x; g2p[x]=p
    return p2g

def apply(z,r,mode):
    h,w=v23.shape(z); ph,pw=r['h'],r['w']; hs=[]
    for a in range(h-ph+1):
      for b in range(w-pw+1):
        m=match(r,z,a,b,mode)
        if m is not None:hs.append((a,b,m))
    if len(hs)!=1:return False
    a,b,m=hs[0]
    for i in range(ph):
      for j in range(pw):
        if r['mask'][i][j]:
          q=r['out'][i][j]; z[a+i][b+j]=0 if q==0 else m.get(q,z[a+i][b+j])
    return True

def prog(rs,mode):
 def f(g):
  z=[list(r) for r in g]
  for _ in range(16):
   old=tuple(map(tuple,z))
   for r in rs:apply(z,r,mode)
   if tuple(map(tuple,z))==old:break
  return tuple(map(tuple,z))
 return f

def main():
 if len(sys.argv)!=2:raise SystemExit('usage ... EVAL_DIR')
 tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]
 for tid,t in sorted(tasks.items()):
  rs,u=v23.learn_rules(t); chosen=None
  if u==len(t['train']) and rs:
   for mode in MODES:
    if run_v2.v1.exact_on_pairs(prog(rs,mode),run_v2.v1.task_pairs(t)):
     chosen=mode;break
  solved=bool(chosen and run_v2.v1.task_solved(prog(rs,chosen),t))
  rows.append({'task':tid,'mode':chosen,'heldout_solved':solved})
 result={'schema':'verified-developmental-navigation.arc-agi2-verified-forgetting.v25','evidence_label':'KNOWN_WORLD_RETROSPECTIVE_REPAIR','forgetting_order':list(MODES),'selection_rule':'coarsest representation preserving exact demonstration behavior','mode_counts':{m:sum(r['mode']==m for r in rows) for m in MODES},'heldout_solved_ids':[r['task'] for r in rows if r['heldout_solved']],'rows':rows}
 p=HERE/'results_v25_verified_forgetting';p.mkdir(exist_ok=True);(p/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
if __name__=='__main__':main()
