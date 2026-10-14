"""V33: localize why V32b targets are unreachable in the current action closure.

Known-world diagnostic only. For each held-out test, compare the target edit set to
all one-step actions available under frozen V23+V26. This separates:
  EFFECT_SUPPORT_MISSING  target cells no available action can touch correctly;
  VALUE_MISSING           target cells are touchable but no available action writes target value;
  COMPOSITION_OR_SELECTION support/value exist locally, so failure is downstream;
  NO_ACTIONS              continuation carrier is empty at the test state.
"""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2, run_v23_trace_induced_patch as v23, run_v26_minimal_sufficient_context as v26, run_v28_learned_selector as v28
TARGET_IDS=sorted(v26.FIT_IDS)

def tup(g): return tuple(tuple(r) for r in g)
def apply_choice(state,r,c):
    z=[list(x) for x in state];a,b,m=c
    for i in range(r['h']):
      for j in range(r['w']):
        if r['mask'][i][j]:
          q=r['out'][i][j];z[a+i][b+j]=0 if q==0 else m.get(q,z[a+i][b+j])
    return tup(z)

def diff_cells(a,b):
    if v23.shape(a)!=v23.shape(b): return None
    h,w=v23.shape(a)
    return {(i,j) for i in range(h) for j in range(w) if a[i][j]!=b[i][j]}

def diagnose(x,y,rs,ks):
    if v23.shape(x)!=v23.shape(y): return {'class':'SHAPE_CHANGE_MISSING'}
    target=diff_cells(x,y); actions=[]
    for ri,(r,k) in enumerate(zip(rs,ks)):
      for c in v28.candidates(x,r,k):
        z=apply_choice(x,r,c)
        if z==tup(x): continue
        changed=diff_cells(x,z)
        correct={(i,j) for (i,j) in changed if z[i][j]==y[i][j] and x[i][j]!=y[i][j]}
        actions.append({'rule':ri,'pos':[c[0],c[1]],'changed':changed,'correct':correct,'state':z})
    if not actions:
      return {'class':'NO_ACTIONS','target_changed_cells':len(target)}
    touched=set().union(*(a['changed'] for a in actions))
    correctly_writable=set().union(*(a['correct'] for a in actions))
    missing_support=target-touched
    missing_values=target-correctly_writable
    best=max((len(a['correct']) for a in actions),default=0)
    if missing_support:
      cls='EFFECT_SUPPORT_MISSING'
    elif missing_values:
      cls='VALUE_MISSING'
    else:
      cls='COMPOSITION_OR_SELECTION'
    return {'class':cls,'target_changed_cells':len(target),'available_actions':len(actions),
      'touchable_target_cells':len(target & touched),'correctly_writable_target_cells':len(target & correctly_writable),
      'missing_support_cells':len(missing_support),'missing_value_cells':len(missing_values),'best_one_step_correct_cells':best}

def main():
    if len(sys.argv)!=2: raise SystemExit('usage ... EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]; totals={}
    for tid in TARGET_IDS:
      t=tasks[tid]; rs,u=v23.learn_rules(t); ks,_,_=v26.minimize(t,rs)
      for i,p in enumerate(t['test']):
        if 'output' not in p: continue
        d=diagnose(p['input'],p['output'],rs,ks); d.update(task=tid,test_index=i); rows.append(d); totals[d['class']]=totals.get(d['class'],0)+1
        print(json.dumps(d,sort_keys=True),flush=True)
    result={'schema':'verified-developmental-navigation.arc-agi2-missing-continuation-census.v33',
      'evidence_label':'KNOWN_WORLD_LOCAL_CAPABILITY_DIAGNOSTIC','totals':totals,'rows':rows,
      'routing':'If support/value is missing, expand the action/representation language. If locally complete, keep continuation reasoning and test composition/order.'}
    out=HERE/'results_v33_missing_continuation_census';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps({'totals':totals,'n':len(rows)},indent=2,sort_keys=True))
if __name__=='__main__': main()
