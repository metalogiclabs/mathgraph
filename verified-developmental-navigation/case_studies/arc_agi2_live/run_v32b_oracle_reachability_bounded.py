"""V32b: bounded oracle reachability diagnostic.

V32 was infrastructure-cancelled after ~9m because BEAM=256, STEPS=24 made the
oracle search too large. That is not scientific evidence. V32b precommits a much
smaller carrier and explicit expansion cap, reports every test immediately, and
labels failures only as NO_TARGET_IN_BOUNDED_CARRIER rather than unrestricted
unreachability.
"""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2, run_v23_trace_induced_patch as v23, run_v26_minimal_sufficient_context as v26, run_v28_learned_selector as v28

TARGET_IDS=sorted(v26.FIT_IDS)
BEAM=48
STEPS=10
MAX_EXPANDED=50000

def tup(g): return tuple(tuple(r) for r in g)
def err(a,b):
    if v23.shape(a)!=v23.shape(b): return 10**9
    h,w=v23.shape(a);return sum(a[i][j]!=b[i][j] for i in range(h) for j in range(w))

def apply_choice(state,r,c):
    z=[list(x) for x in state];a,b,m=c
    for i in range(r['h']):
      for j in range(r['w']):
        if r['mask'][i][j]:
          q=r['out'][i][j];z[a+i][b+j]=0 if q==0 else m.get(q,z[a+i][b+j])
    return tup(z)

def successors(state,rs,ks):
    seen=set()
    for r,k in zip(rs,ks):
      for c in v28.candidates(state,r,k):
        z=apply_choice(state,r,c)
        if z!=state and z not in seen:seen.add(z);yield z

def search(x,y,rs,ks):
    start=tup(x);target=tup(y);start_e=err(start,target)
    if start==target:return {'status':'SOLVED','depth':0,'best_error':0,'start_error':0,'expanded':0}
    beam=[start];seen={start};expanded=0;best=start_e
    for depth in range(1,STEPS+1):
      cand=[]
      for s in beam:
        for z in successors(s,rs,ks):
          if z in seen:continue
          seen.add(z);expanded+=1;e=err(z,target);best=min(best,e)
          if e==0:return {'status':'SOLVED','depth':depth,'best_error':0,'start_error':start_e,'expanded':expanded}
          cand.append((e,z))
          if expanded>=MAX_EXPANDED:
            return {'status':'CAP_REACHED','depth':depth,'best_error':best,'start_error':start_e,'expanded':expanded}
      if not cand: return {'status':'CLOSURE_EXHAUSTED_WITHIN_DEPTH','depth':depth,'best_error':best,'start_error':start_e,'expanded':expanded}
      cand.sort(key=lambda q:q[0]);beam=[z for _,z in cand[:BEAM]]
    return {'status':'NO_TARGET_IN_BOUNDED_CARRIER','depth':STEPS,'best_error':best,'start_error':start_e,'expanded':expanded}

def main():
    if len(sys.argv)!=2:raise SystemExit('usage ... EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]);rows=[]
    for tid in TARGET_IDS:
      t=tasks[tid];rs,u=v23.learn_rules(t);ks,_,_=v26.minimize(t,rs);tests=[]
      for i,p in enumerate(t['test']):
        if 'output' not in p:continue
        q=search(p['input'],p['output'],rs,ks);q['test_index']=i;tests.append(q)
        print(json.dumps({'task':tid,**q}),flush=True)
      rows.append({'task':tid,'tests':tests,'all_tests_solved':bool(tests) and all(q['status']=='SOLVED' for q in tests)})
    statuses={}
    for r in rows:
      for q in r['tests']:statuses[q['status']]=statuses.get(q['status'],0)+1
    result={'schema':'verified-developmental-navigation.arc-agi2-oracle-reachability-bounded.v32b','evidence_label':'KNOWN_WORLD_BOUNDED_ORACLE_DIAGNOSTIC',
      'uses_heldout_outputs_for_search':True,'beam':BEAM,'steps':STEPS,'max_expanded_per_test':MAX_EXPANDED,
      'statuses':statuses,'fully_reachable_task_ids':[r['task'] for r in rows if r['all_tests_solved']],
      'principle':'Infrastructure cancellation is not evidence. This run answers only whether targets occur inside the explicitly bounded continuation carrier.',
      'rows':rows}
    out=HERE/'results_v32b_oracle_reachability_bounded';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True),flush=True)
if __name__=='__main__':main()
