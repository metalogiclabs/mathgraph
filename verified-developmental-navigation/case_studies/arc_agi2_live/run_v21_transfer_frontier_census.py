import importlib.util
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v19=load('v19','run_v19_residual_history_policy.py')
v18=v19.v18
v17=v19.v17
v13=v19.v13

# Frozen before evaluation.  This run is a target-frontier census only: no
# cross-episode WARM policy is learned or evaluated here.
POOL_LIMIT=64
EXCLUDE=set(v13.TARGETS)
MAX_STATES=160


def audit_task(tid,task):
    states,keys=v17.states_for(task)
    if not states:return {'task':tid,'status':'NO_STATES'}
    if len(states)>MAX_STATES:return {'task':tid,'status':'STATE_CAP','states':len(states)}
    for s in states:
        df,hs,w,tr,trunc=v13.future_audit(task,s)
        s['demo']=bool(df);s['held']=bool(hs);s['truncated']=bool(trunc)
    demo=[s['demo'] for s in states];held=[s['held'] for s in states]
    full=v19.sufficient(states,keys,demo)
    if not full:
        return {'task':tid,'status':'FULL_LANGUAGE_COLLISION','states':len(states),'candidate_programs':len(keys),'any_truncation':any(s['truncated'] for s in states)}
    cold,ct=v19.run_history(states,keys,demo,False)
    oracle,ot=v18.run_oracle(states,keys,demo)
    cold_exact=v19.sufficient(states,cold,demo);oracle_exact=v19.sufficient(states,oracle,demo)
    cold_held=v19.sufficient(states,cold,held)
    oq=len(oracle);cq=len(cold)
    if oracle_exact:
        # A failed cold arm consumes the full 8-query budget without closing;
        # encode one step beyond the budget only for ranking headroom.
        effective_cold=cq if cold_exact else v19.MAX_QUERIES+1
        headroom=effective_cold-oq
    else:headroom=None
    return {'task':tid,'status':'AUDITED','states':len(states),'candidate_programs':len(keys),
      'future_positive':sum(demo),'full_language_exact':full,'any_truncation':any(s['truncated'] for s in states),
      'cold':{'exact':cold_exact,'heldout_exact':cold_held,'queries':cq,'unresolved':v19.unresolved(states,cold,demo)},
      'oracle':{'exact':oracle_exact,'queries':oq,'unresolved':v19.unresolved(states,oracle,demo)},
      'headroom_queries':headroom}


def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v21_transfer_frontier_census.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1])
    ids=[x for x in sorted(ev) if x not in EXCLUDE][:POOL_LIMIT]
    rows=[]
    for tid in ids:
        try:rows.append(audit_task(tid,ev[tid]))
        except Exception as e:rows.append({'task':tid,'status':'UNSUPPORTED','error':type(e).__name__+': '+str(e)[:240]})
    eligible=[r for r in rows if r.get('status')=='AUDITED' and r.get('oracle',{}).get('exact') and not r.get('any_truncation') and (r.get('headroom_queries') or 0)>0]
    eligible=sorted(eligible,key=lambda r:(-r['headroom_queries'],r['oracle']['queries'],r['task']))
    result={'schema':'verified-developmental-navigation.arc-transfer-frontier-census.v21',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{'pool':'first 64 lexicographic evaluation task IDs excluding V13-V20 four-task lineage','pool_limit':POOL_LIMIT,'max_states':MAX_STATES,'cold_policy':'V19 within-episode residual-history policy with no cross-episode retained state','oracle':'V18 full-label greedy ceiling','selection_rule':'oracle exact, no truncation, full V17 language sufficient, and cold query cost strictly above oracle or cold fails at budget 8','warm_policy_evaluated':False},
      'rows':rows,'eligible_frontier':[{'task':r['task'],'headroom_queries':r['headroom_queries'],'cold':r['cold'],'oracle':r['oracle'],'states':r['states'],'candidate_programs':r['candidate_programs']} for r in eligible],
      'summary':{'pool':len(ids),'audited':sum(r.get('status')=='AUDITED' for r in rows),'eligible_frontier':len(eligible),'unsupported':sum(r.get('status')=='UNSUPPORTED' for r in rows),'state_capped':sum(r.get('status')=='STATE_CAP' for r in rows),'full_language_collisions':sum(r.get('status')=='FULL_LANGUAGE_COLLISION' for r in rows)},
      'decision':'FRONTIER_FOUND' if eligible else 'NO_TRANSFER_HEADROOM_IN_FROZEN_POOL'}
    out=HERE/'results_v21_transfer_frontier_census';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
