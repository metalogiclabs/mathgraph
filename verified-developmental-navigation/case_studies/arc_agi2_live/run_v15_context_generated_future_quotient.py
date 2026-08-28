import importlib.util
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v13',HERE/'run_v13_groundup_future_quotient.py')
v13=importlib.util.module_from_spec(spec);spec.loader.exec_module(v13)

# V15 is licensed by V14's exact full-vocabulary collision. We add no semantic
# feature names. Observation contexts are generated from the already-admitted
# primitive geometric action carrier. Each context emits only verifier-neutral
# equality bits over raw grids.
GEOMS=list(v13.v2.v1.GEOMS)

def safe(fn,g):
    try:return fn(g)
    except Exception:return None

def context_obs(tp):
    out={}
    for di,(x,y) in enumerate(tp):
        for gi,(gname,gfn) in enumerate(GEOMS):
            gx=safe(gfn,x)
            # Two generic context responses: fixed point and target equality.
            # gname is audit-only; learning receives indexed bits.
            out[f'd{di}:g{gi}:self']=(gx==x)
            out[f'd{di}:g{gi}:target']=(gx==y)
    return out

def states_for(task):
    st=v13.first_stage_states(task)
    for s in st:s['obs']=context_obs(s['tp'])
    return st

def sufficient(states,label,sub):
    b=defaultdict(set)
    for s in states:b[tuple(s['obs'][k] for k in sub)].add(bool(s[label]))
    return all(len(v)==1 for v in b.values())

def collision(states,label,keys):
    b=defaultdict(list)
    for s in states:b[tuple(s['obs'][k] for k in keys)].append(s)
    for sig,arr in b.items():
        labs={bool(s[label]) for s in arr}
        if len(labs)>1:
            p=next(s for s in arr if s[label]);n=next(s for s in arr if not s[label])
            return {'positive_audit':p['program_audit'],'negative_audit':n['program_audit'],'signature':list(sig)}
    return None

def minimal_basis(states,label,max_k=6):
    keys=sorted(states[0]['obs']) if states else []
    if not sufficient(states,label,keys):
        return None,'FULL_CONTEXT_VOCABULARY_COLLISION',collision(states,label,keys)
    if sufficient(states,label,()):return [],'EMPTY_SUFFICIENT',None
    # quotient observationally duplicate columns before subset search
    uniq=[];seen=set()
    for k in keys:
        col=tuple(s['obs'][k] for s in states)
        if col not in seen:seen.add(col);uniq.append(k)
    for k in range(1,min(max_k,len(uniq))+1):
        for sub in itertools.combinations(uniq,k):
            if sufficient(states,label,sub):return list(sub),'MINIMAL_FOUND',None
    return None,f'FULL_SUFFICIENT_NO_BASIS_LE_{max_k}',None

def decode_basis(basis):
    if basis is None:return None
    out=[]
    for k in basis:
        # d#:g#:kind -> audit transform name only after discovery
        a,b,kind=k.split(':');gi=int(b[1:])
        out.append({'raw_key':k,'demo':int(a[1:]),'context_index':gi,'context_audit_name':GEOMS[gi][0],'response':kind})
    return out

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v15_context_generated_future_quotient.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1]);rows=[]
    for tid in v13.TARGETS:
        t=ev[tid];st=states_for(t)
        for s in st:
            df,hs,w,tr,trunc=v13.future_audit(t,s)
            s['demo_future_success']=df;s['heldout_success']=hs;s['truncated']=trunc
        bd,sd,cd=minimal_basis(st,'demo_future_success')
        bh,sh,ch=minimal_basis(st,'heldout_success')
        rows.append({
          'task':tid,'states':len(st),'demo_future_positive':sum(s['demo_future_success'] for s in st),
          'heldout_future_positive':sum(s['heldout_success'] for s in st),'any_truncation':any(s['truncated'] for s in st),
          'demo_status':sd,'demo_minimal_basis_raw':bd,'demo_minimal_basis_audit':decode_basis(bd),'demo_collision':cd,
          'heldout_status':sh,'heldout_minimal_basis_raw':bh,'heldout_minimal_basis_audit':decode_basis(bh),'heldout_collision':ch,
        })
    result={
      'schema':'verified-developmental-navigation.arc-context-generated-future-quotient.v15',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'frozen_targets':v13.TARGETS,
      'licensed_by':'V14 exact full-vocabulary collisions: all demo-indexed scalar shape/color predicates were identical across states with different verified second-step futures.',
      'observation_generation':'Apply each already-admitted primitive geometric action as a raw-grid context; retain only equality-to-self and equality-to-target bits.',
      'contexts_audit':[n for n,_ in GEOMS],
      'tasks':rows,
      'decision':'CONTEXT_BASIS_FORCED_ALL_TASKS' if all(r['demo_minimal_basis_raw'] is not None for r in rows) else 'CONTEXT_LANGUAGE_EXHAUSTED_ON_AT_LEAST_ONE_TASK'
    }
    out=HERE/'results_v15_context_generated_future_quotient';out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
