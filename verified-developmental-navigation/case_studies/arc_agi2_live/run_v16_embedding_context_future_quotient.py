import importlib.util
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v13',HERE/'run_v13_groundup_future_quotient.py')
v13=importlib.util.module_from_spec(spec);spec.loader.exec_module(v13)
GEOMS=list(v13.v2.v1.GEOMS)

def safe(fn,g):
    try:return fn(g)
    except Exception:return None

def subgrid_eq(big,small,r,c):
    hb,wb=v13.shape(big);hs,ws=v13.shape(small)
    if r<0 or c<0 or r+hs>hb or c+ws>wb:return False
    return all(big[r+i][c+j]==small[i][j] for i in range(hs) for j in range(ws))

def occurrence_signature(big,small):
    hb,wb=v13.shape(big);hs,ws=v13.shape(small)
    if hs>hb or ws>wb:return ()
    return tuple((r,c) for r in range(hb-hs+1) for c in range(wb-ws+1) if subgrid_eq(big,small,r,c))

def states_for(task):
    # Need original input alongside transformed demo intermediate.
    pairs=v13.v2.v1.task_pairs(task)
    states=v13.first_stage_states(task)
    for s in states:
        obs={}
        for di,((orig,target),(mid,_)) in enumerate(zip(pairs,s['tp'])):
            hm,wm=v13.shape(mid)
            for gi,(gname,gfn) in enumerate(GEOMS):
                q=safe(gfn,orig)
                if q is None:continue
                hq,wq=v13.shape(q)
                # Generic finite placement carrier. Positions are raw integer indices,
                # not semantic left/right/top/bottom labels.
                for r in range(max(0,hm-hq+1)):
                    for c in range(max(0,wm-wq+1)):
                        obs[f'd{di}:g{gi}:r{r}:c{c}']=subgrid_eq(mid,q,r,c)
                # Also retain occurrence count only as a generated numeric equality bank.
                occ=occurrence_signature(mid,q)
                for n in range(0,5):obs[f'd{di}:g{gi}:count_eq_{n}']=(len(occ)==n)
        s['obs']=obs
    # Normalize keys: absent placement in a state's smaller grid means False.
    keys=sorted(set().union(*(s['obs'].keys() for s in states))) if states else []
    for s in states:
        for k in keys:s['obs'].setdefault(k,False)
    return states,keys

def sufficient(states,label,sub):
    b=defaultdict(set)
    for s in states:b[tuple(s['obs'][k] for k in sub)].add(bool(s[label]))
    return all(len(v)==1 for v in b.values())

def collision(states,label,keys):
    b=defaultdict(list)
    for s in states:b[tuple(s['obs'][k] for k in keys)].append(s)
    for sig,arr in b.items():
        if len({bool(s[label]) for s in arr})>1:
            p=next(s for s in arr if s[label]);n=next(s for s in arr if not s[label])
            return {'positive_audit':p['program_audit'],'negative_audit':n['program_audit']}
    return None

def minimal_basis(states,keys,label,max_k=5):
    if not sufficient(states,label,keys):return None,'FULL_EMBEDDING_VOCABULARY_COLLISION',collision(states,label,keys)
    if sufficient(states,label,()):return [],'EMPTY_SUFFICIENT',None
    # Dedup columns; then exact minimal cardinality search up to max_k.
    uniq=[];seen=set()
    for k in keys:
        col=tuple(s['obs'][k] for s in states)
        if col not in seen:seen.add(col);uniq.append(k)
    for n in range(1,min(max_k,len(uniq))+1):
        for sub in itertools.combinations(uniq,n):
            if sufficient(states,label,sub):return list(sub),'MINIMAL_FOUND',None
    return None,f'FULL_SUFFICIENT_NO_BASIS_LE_{max_k}',None

def decode(keys):
    if keys is None:return None
    out=[]
    for k in keys:
        parts=k.split(':');gi=int(parts[1][1:])
        out.append({'raw_key':k,'context_audit_name':GEOMS[gi][0]})
    return out

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v16_embedding_context_future_quotient.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1]);rows=[]
    for tid in v13.TARGETS:
        t=ev[tid];st,keys=states_for(t)
        for s in st:
            df,hs,w,tr,trunc=v13.future_audit(t,s)
            s['demo_future_success']=df;s['heldout_success']=hs;s['truncated']=trunc
        bd,sd,cd=minimal_basis(st,keys,'demo_future_success')
        bh,sh,ch=minimal_basis(st,keys,'heldout_success')
        rows.append({'task':tid,'states':len(st),'generated_embedding_bits':len(keys),
          'demo_future_positive':sum(s['demo_future_success'] for s in st),'heldout_future_positive':sum(s['heldout_success'] for s in st),
          'demo_status':sd,'demo_basis_raw':bd,'demo_basis_audit':decode(bd),'demo_collision':cd,
          'heldout_status':sh,'heldout_basis_raw':bh,'heldout_basis_audit':decode(bh),'heldout_collision':ch,
          'any_truncation':any(s['truncated'] for s in st)})
    result={'schema':'verified-developmental-navigation.arc-embedding-context-future-quotient.v16',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'frozen_targets':v13.TARGETS,
      'licensed_by':'V15 exact collisions after all primitive geometric fixed-point/target-equality contexts.',
      'observation_generation':'For every primitive geometric image of each original demo input, enumerate every raw subgrid offset in each first-stage intermediate and emit exact-match bits; no semantic placement labels.',
      'tasks':rows,
      'decision':'EMBEDDING_BASIS_FORCED_ALL_TASKS' if all(r['demo_basis_raw'] is not None for r in rows) else 'EMBEDDING_LANGUAGE_EXHAUSTED_ON_AT_LEAST_ONE_TASK'}
    out=HERE/'results_v16_embedding_context_future_quotient';out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
