import hashlib
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent

def load(name, file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v18=load('v18','run_v18_residual_induced_query_synthesis.py')
v17=v18.v17
v13=v18.v13
MAX_QUERIES=v18.MAX_QUERIES


def bucket_indices(states, chosen):
    b=defaultdict(list)
    for i,s in enumerate(states): b[tuple(bool(s['obs'][k]) for k in chosen)].append(i)
    return b

def unresolved(states, chosen, labels):
    n=0
    for inds in bucket_indices(states,chosen).values():
        p=sum(bool(labels[i]) for i in inds); n+=p*(len(inds)-p)
    return n

def sufficient(states, chosen, labels): return unresolved(states,chosen,labels)==0

def collision_with_bucket(states, chosen, labels):
    for inds in bucket_indices(states,chosen).values():
        pos=next((i for i in inds if labels[i]),None); neg=next((i for i in inds if not labels[i]),None)
        if pos is not None and neg is not None: return (pos,neg),inds
    return None,None

def active_atom(states, keys, chosen, pair, bucket):
    if pair is None:return None,None
    a,b=pair; best=None
    for k in keys:
        if k in chosen: continue
        va=bool(states[a]['obs'][k]); vb=bool(states[b]['obs'][k])
        if va==vb: continue
        n1=sum(bool(states[i]['obs'][k]) for i in bucket); n0=len(bucket)-n1
        # No labels beyond the returned pair: maximize raw ambiguity reduction in
        # the currently unresolved observational bucket. Hash is fixed tie-break.
        split=n0*n1
        bal=min(n0,n1)
        tie=hashlib.sha256(k.encode()).hexdigest()
        cand=(split,bal,tie)
        if best is None or cand>best[0]: best=(cand,k,{'n0':n0,'n1':n1,'split_score':split})
    return (best[1],best[2]) if best else (None,None)

def run_active(states,keys,labels):
    chosen=[];trace=[]
    for q in range(MAX_QUERIES):
        before=unresolved(states,chosen,labels)
        if before==0:break
        pair,bucket=collision_with_bucket(states,chosen,labels)
        k,meta=active_atom(states,keys,chosen,pair,bucket)
        if k is None:
            trace.append({'query':q+1,'status':'NO_SEPARATOR','pair':pair});break
        chosen.append(k);after=unresolved(states,chosen,labels)
        trace.append({'query':q+1,'pair':pair,'bucket_size':len(bucket),'atom':k,
                      **meta,'true_unresolved_before':before,'true_unresolved_after':after})
    return chosen,trace

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v18b_active_separator_query_synthesis.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1]);rows=[]
    for tid in v13.TARGETS:
        task=ev[tid];states,keys=v17.states_for(task)
        for s in states:
            df,hs,w,tr,trunc=v13.future_audit(task,s);s['demo']=bool(df);s['held']=bool(hs);s['truncated']=bool(trunc)
        demo=[s['demo'] for s in states];held=[s['held'] for s in states]
        active,trace=run_active(states,keys,demo)
        first,first_trace=v18.run_real_residual(states,keys,demo)
        rows.append({'task':tid,'states':len(states),'future_positive':sum(demo),'candidate_programs':len(keys),
          'active':{'queries_used':len(active),'demo_exact':sufficient(states,active,demo),'heldout_exact':sufficient(states,active,held),'unresolved':unresolved(states,active,demo),'atoms':active,'trace':trace},
          'v18_first_separator':{'queries_used':len(first),'demo_exact':sufficient(states,first,demo),'heldout_exact':sufficient(states,first,held),'unresolved':unresolved(states,first,demo)},
          'oracle':{'queries_used':len(v18.run_oracle(states,keys,demo)[0]),'demo_exact':sufficient(states,v18.run_oracle(states,keys,demo)[0],demo)},
          'any_truncation':any(s['truncated'] for s in states)})
    active_exact=sum(r['active']['demo_exact'] for r in rows);held_exact=sum(r['active']['heldout_exact'] for r in rows);first_exact=sum(r['v18_first_separator']['demo_exact'] for r in rows)
    strict=active_exact==4 and held_exact==4 and active_exact>first_exact and not any(r['any_truncation'] for r in rows)
    result={'schema':'verified-developmental-navigation.arc-active-separator-query-synthesis.v18b',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'frozen_targets':v13.TARGETS,
      'precommit':{'max_queries_per_task':MAX_QUERIES,'candidate_language':'identical to V18','feedback':'one true unresolved positive/negative future collision','selection':'among atoms separating only that pair, maximize unlabeled n0*n1 split of the current observational bucket; SHA256 tie-break'},
      'claim_boundary':'No extra future labels are exposed beyond the one verifier-returned collision pair. The selection score uses only candidate observation values on the current ambiguous bucket.',
      'tasks':rows,
      'summary':{'active_exact_tasks':active_exact,'active_heldout_exact_tasks':held_exact,'v18_first_separator_exact_tasks':first_exact},
      'strict_gate':'PASS_ACTIVE_RESIDUAL_SEPARATOR_ALL_TASKS' if strict else 'FAIL_ACTIVE_RESIDUAL_SEPARATOR_ALL_TASKS'}
    out=HERE/'results_v18b_active_separator_query_synthesis';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
