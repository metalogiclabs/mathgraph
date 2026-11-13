"""V28: induce selectors only after V26 verified compression exposes ambiguity.

No held-out output participates in selection. For each V23 rule we first obtain
its V26 deletion-minimal context. On training inputs, enumerate all matches and
identify which candidate locations produce locally correct edits. Search a tiny
predeclared selector family over candidate geometry and retain the first selector
that chooses a correct candidate on every training occurrence where the rule is
applicable. Freeze selector + representation and evaluate test inputs.

This tests the V27 residual directly: observability improved, so can training
history induce selectability without adding a new object ontology?
"""
import json,sys,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2, run_v23_trace_induced_patch as v23, run_v26_minimal_sufficient_context as v26
FIT_IDS=sorted(v26.FIT_IDS)

SELECTORS=('unique','top','bottom','left','right','center_near','center_far','topleft','bottomright')

def candidates(g,r,k):
 h,w=v23.shape(g); out=[]
 for a in range(h-r['h']+1):
  for b in range(w-r['w']+1):
   m=v26.match(r,g,a,b,k)
   if m is not None:out.append((a,b,m))
 return out

def choose(cs,sel,g):
 if not cs:return None
 if sel=='unique': return cs[0] if len(cs)==1 else None
 h,w=v23.shape(g)
 if sel=='top': key=lambda x:(x[0],x[1])
 elif sel=='bottom': key=lambda x:(-x[0],x[1])
 elif sel=='left': key=lambda x:(x[1],x[0])
 elif sel=='right': key=lambda x:(-x[1],x[0])
 elif sel=='topleft': key=lambda x:(x[0]+x[1],x[0],x[1])
 elif sel=='bottomright': key=lambda x:(-(x[0]+x[1]),-x[0],-x[1])
 elif sel=='center_near': key=lambda x:((x[0]-(h-1)/2)**2+(x[1]-(w-1)/2)**2,x[0],x[1])
 elif sel=='center_far': key=lambda x:(-((x[0]-(h-1)/2)**2+(x[1]-(w-1)/2)**2),x[0],x[1])
 return min(cs,key=key)

def local_correct(inp,out,r,cand):
 a,b,m=cand
 for i in range(r['h']):
  for j in range(r['w']):
   if not r['mask'][i][j]:continue
   q=r['out'][i][j]; want=0 if q==0 else m.get(q,inp[a+i][b+j])
   if out[a+i][b+j]!=want:return False
 return True

def learn_selector(t,r,k):
 episodes=[]
 for p in t['train']:
  cs=candidates(p['input'],r,k)
  good={(a,b) for a,b,m in cs if local_correct(p['input'],p['output'],r,(a,b,m))}
  if cs and good:episodes.append((p['input'],cs,good))
 if not episodes:return None,0
 for s in SELECTORS:
  ok=True
  for g,cs,good in episodes:
   c=choose(cs,s,g)
   if c is None or (c[0],c[1]) not in good:ok=False;break
  if ok:return s,len(episodes)
 return None,len(episodes)

def apply_selected(z,r,k,sel):
 cs=candidates(z,r,k); c=choose(cs,sel,z) if sel else None
 if c is None:return False
 a,b,m=c
 for i in range(r['h']):
  for j in range(r['w']):
   if r['mask'][i][j]:
    q=r['out'][i][j];z[a+i][b+j]=0 if q==0 else m.get(q,z[a+i][b+j])
 return True

def prog(rs,ks,sels):
 def f(g):
  z=[list(x) for x in g]
  for _ in range(16):
   before=tuple(map(tuple,z))
   for r,k,s in zip(rs,ks,sels):apply_selected(z,r,k,s)
   if tuple(map(tuple,z))==before:break
  return tuple(map(tuple,z))
 return f

def main():
 if len(sys.argv)!=2:raise SystemExit('usage ... EVAL_DIR')
 tasks=run_v2.v1.load_tasks(sys.argv[1]);rows=[]
 for tid in FIT_IDS:
  t=tasks[tid];rs,u=v23.learn_rules(t);ks,_,_=v26.minimize(t,rs)
  sels=[];supports=[]
  for r,k in zip(rs,ks):
   s,n=learn_selector(t,r,k);sels.append(s);supports.append(n)
  p=prog(rs,ks,sels)
  train_fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t)) if all(s is not None for s in sels) else False
  solved=False
  try:solved=bool(train_fit and run_v2.v1.task_solved(p,t))
  except Exception:pass
  test_counts=[]
  for q in t['test']:
   test_counts.append([len(candidates(q['input'],r,k)) for r,k in zip(rs,ks)])
  rows.append({'task':tid,'selectors':sels,'selector_supports':supports,'all_selectors_learned':all(s is not None for s in sels),
    'train_fit_after_selector':train_fit,'heldout_solved':solved,'test_match_counts':test_counts})
 result={'schema':'verified-developmental-navigation.arc-agi2-learned-selector.v28','evidence_label':'KNOWN_WORLD_RETROSPECTIVE_REPAIR',
  'selection_uses_test_outputs':False,'selector_family':list(SELECTORS),'task_count':len(rows),
  'tasks_all_selectors_learned':sum(r['all_selectors_learned'] for r in rows),
  'tasks_train_fit_after_selector':sum(r['train_fit_after_selector'] for r in rows),
  'heldout_solved_ids':[r['task'] for r in rows if r['heldout_solved']],
  'principle':'After verified quotienting exposes ambiguous continuations, induce the smallest separator from training continuation history before changing ontology.',
  'rows':rows}
 out=HERE/'results_v28_learned_selector';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
 print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
 for r in rows:print(r)
if __name__=='__main__':main()
