"""V32: oracle future-consistency upper bound on the seven known evaluation diagnostics.

V31 showed that, on source training episodes, future consequence is a highly
accurate separator of ambiguous local actions. The key unresolved question is
whether the current V23+V26 representation/action closure already CONTAINS the
held-out answer and selection is the bottleneck, or whether the answer is not
reachable at all.

This run is deliberately KNOWN-WORLD / ORACLE DIAGNOSTIC: held-out outputs are
used only to rank/search continuations. Therefore any solve is an upper bound on
reachable capability, not an ARC generalization claim.
"""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2, run_v23_trace_induced_patch as v23, run_v26_minimal_sufficient_context as v26, run_v28_learned_selector as v28

TARGET_IDS=sorted(v26.FIT_IDS)
BEAM=256
STEPS=24

def tup(g): return tuple(tuple(r) for r in g)
def err(a,b):
    if v23.shape(a)!=v23.shape(b): return 10**9
    h,w=v23.shape(a)
    return sum(a[i][j]!=b[i][j] for i in range(h) for j in range(w))

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
        if z!=state and z not in seen:
          seen.add(z);yield z

def oracle_search(x,y,rs,ks):
    start=tup(x); target=tup(y)
    if start==target:return {'solved':True,'depth':0,'best_error':0,'expanded':0}
    beam=[start]; seen={start}; expanded=0; best=err(start,target)
    for depth in range(1,STEPS+1):
      cand=[]
      for s in beam:
        for z in successors(s,rs,ks):
          if z in seen:continue
          seen.add(z);expanded+=1
          e=err(z,target);best=min(best,e)
          if e==0:return {'solved':True,'depth':depth,'best_error':0,'expanded':expanded}
          cand.append((e,z))
      if not cand:break
      cand.sort(key=lambda q:q[0]);beam=[z for _,z in cand[:BEAM]]
    return {'solved':False,'depth':None,'best_error':best,'expanded':expanded}

def main():
    if len(sys.argv)!=2:raise SystemExit('usage ... EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]);rows=[]
    for tid in TARGET_IDS:
      t=tasks[tid];rs,u=v23.learn_rules(t);ks,_,_=v26.minimize(t,rs)
      tests=[]
      for i,p in enumerate(t['test']):
        if 'output' not in p: continue
        q=oracle_search(p['input'],p['output'],rs,ks);q['test_index']=i;tests.append(q)
      rows.append({'task':tid,'tests':tests,'all_tests_solved':bool(tests) and all(q['solved'] for q in tests)})
    result={'schema':'verified-developmental-navigation.arc-agi2-oracle-future-upper-bound.v32',
      'evidence_label':'KNOWN_WORLD_ORACLE_REACHABILITY_DIAGNOSTIC','uses_heldout_outputs_for_search':True,
      'beam':BEAM,'steps':STEPS,'task_count':len(rows),
      'fully_reachable_task_ids':[r['task'] for r in rows if r['all_tests_solved']],
      'solved_test_examples':sum(q['solved'] for r in rows for q in r['tests']),
      'total_test_examples':sum(len(r['tests']) for r in rows),
      'principle':'Use the verifier as an oracle only to decide whether the current continuation closure contains the target. If even oracle-guided search fails, selection is not the primary bottleneck.',
      'rows':rows}
    out=HERE/'results_v32_oracle_future_upper_bound';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True))
    for r in rows:print(r)
if __name__=='__main__':main()
