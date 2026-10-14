"""V26: search for minimal verified-sufficient context inside V23 rules.

Start from each V23 strict patch matcher. Changed cells are always protected.
Unchanged contextual cells are candidate constraints. Greedily delete one
constraint at a time, retaining a deletion iff the *whole task program* still
reproduces every training pair exactly. Repeat to fixed point. The test output
is never consulted during selection.

This is a direct operational instance of the VDN quotient principle:
forget a distinction exactly when protected verified futures are unchanged.
Public ARC evaluation makes held-out reporting retrospective mechanism evidence.
"""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
import run_v2, run_v23_trace_induced_patch as v23

FIT_IDS={'332f06d7','36a08778','53fb4810','7b80bb43','88bcf3b4','b9e38dc0','d59b0160'}

def initial_keep(rule):
    return {(i,j) for i in range(rule['h']) for j in range(rule['w']) if not rule['mask'][i][j]}

def match(rule,g,a,b,keep):
    ph,pw=rule['h'],rule['w']; h,w=v23.shape(g)
    if a+ph>h or b+pw>w:return None
    p2g={0:0}; g2p={0:0}
    for i in range(ph):
      for j in range(pw):
        if not rule['mask'][i][j] and (i,j) not in keep: continue
        p=rule['in'][i][j]; x=g[a+i][b+j]
        if p in p2g and p2g[p]!=x:return None
        if x in g2p and g2p[x]!=p:return None
        p2g[p]=x; g2p[x]=p
    return p2g

def apply(z,r,keep):
    h,w=v23.shape(z); ph,pw=r['h'],r['w']; hs=[]
    for a in range(h-ph+1):
      for b in range(w-pw+1):
        m=match(r,z,a,b,keep)
        if m is not None: hs.append((a,b,m))
    if len(hs)!=1:return False
    a,b,m=hs[0]
    for i in range(ph):
      for j in range(pw):
        if r['mask'][i][j]:
          q=r['out'][i][j]; z[a+i][b+j]=0 if q==0 else m.get(q,z[a+i][b+j])
    return True

def prog(rs,keeps):
 def f(g):
  z=[list(r) for r in g]
  for _ in range(16):
   old=tuple(map(tuple,z))
   for r,k in zip(rs,keeps): apply(z,r,k)
   if tuple(map(tuple,z))==old:break
  return tuple(map(tuple,z))
 return f

def exact_train(t,rs,keeps):
    return run_v2.v1.exact_on_pairs(prog(rs,keeps),run_v2.v1.task_pairs(t))

def minimize(t,rs):
    keeps=[initial_keep(r) for r in rs]
    attempts=accepted=0; changed=True
    # deterministic deletion order; repeat because earlier failed removals can
    # become removable after other constraints disappear.
    while changed:
      changed=False
      for ri in range(len(rs)):
        for pos in sorted(list(keeps[ri])):
          attempts+=1
          trial=[set(k) for k in keeps]; trial[ri].remove(pos)
          if exact_train(t,rs,trial):
            keeps=trial; accepted+=1; changed=True
    return keeps,attempts,accepted

def hit_counts(g,rs,keeps):
    out=[]
    for r,k in zip(rs,keeps):
      h,w=v23.shape(g); n=0
      for a in range(h-r['h']+1):
       for b in range(w-r['w']+1):
        if match(r,g,a,b,k) is not None:n+=1
      out.append(n)
    return out

def main():
 if len(sys.argv)!=2:raise SystemExit('usage run_v26_minimal_sufficient_context.py EVAL_DIR')
 tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]
 for tid in sorted(FIT_IDS):
  t=tasks[tid]; rs,u=v23.learn_rules(t)
  strict=[initial_keep(r) for r in rs]
  assert u==len(t['train']) and exact_train(t,rs,strict)
  mins,attempts,accepted=minimize(t,rs)
  assert exact_train(t,rs,mins)
  total=sum(len(k) for k in strict); kept=sum(len(k) for k in mins)
  solved=False
  try:solved=run_v2.v1.task_solved(prog(rs,mins),t)
  except Exception:pass
  tests=[]
  for i,p in enumerate(t['test']):
    tests.append({'test_index':i,'strict_match_counts':hit_counts(p['input'],rs,strict),'minimal_match_counts':hit_counts(p['input'],rs,mins)})
  rows.append({'task':tid,'rule_count':len(rs),'context_total':total,'context_kept':kept,'context_removed':total-kept,
               'compression_ratio':(total/kept if kept else None),'deletion_attempts':attempts,'accepted_deletions':accepted,
               'heldout_solved':solved,'tests':tests})
 result={'schema':'verified-developmental-navigation.arc-agi2-minimal-sufficient-context.v26',
   'evidence_label':'KNOWN_WORLD_RETROSPECTIVE_REPAIR','selection_uses_test_outputs':False,
   'principle':'Delete contextual distinctions only when exact training behavior is invariant; iterate to a deletion-minimal fixed point.',
   'task_count':len(rows),'total_context':sum(r['context_total'] for r in rows),'total_kept':sum(r['context_kept'] for r in rows),
   'total_removed':sum(r['context_removed'] for r in rows),'tasks_with_any_forgetting':sum(r['context_removed']>0 for r in rows),
   'heldout_solved_ids':[r['task'] for r in rows if r['heldout_solved']], 'rows':rows}
 p=HERE/'results_v26_minimal_sufficient_context';p.mkdir(exist_ok=True);(p/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));
 print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
 for r in rows:print(r['task'],r['context_total'],r['context_kept'],r['context_removed'],r['heldout_solved'],r['tests'])
if __name__=='__main__':main()
