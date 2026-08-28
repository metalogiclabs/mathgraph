import hashlib, importlib.util, itertools, json, sys
from fractions import Fraction
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v31=load('v31','run_v31_blind_fresh_target_transfer.py')
v32=load('v32','run_v32_transfer_admissibility_gate.py')
v28,v27,v23,v19,v13=v31.v28,v31.v27,v31.v23,v31.v19,v31.v13
MAXQ=v28.MAXQ

# This is a measurement experiment, not a new transfer policy.
# We ask whether the exact V32 reuse state is future-sufficient.  At every reachable
# WARM_GATED decision state on all frozen V31-eligible targets, every available TRUE
# source atom is counterfactually forced once and compared with the frozen V19 fallback.
# The verifier supplies labels only to score those counterfactual futures post hoc.
# No ARC semantics, task IDs, or target-derived rule enters the state representation.

FEATURES=('balance_fraction','bucket_n','split_min','split_max','unresolved_before','history_size','history_support','history_diversity','raw_source_matches','admitted_source_matches')

def finish_v19(states,keys,labels,chosen,history,budget):
    chosen=list(chosen); history=list(history); used=0
    while used < budget:
        before=v19.unresolved(states,chosen,labels)
        if before==0: break
        cur=v19.collision(states,chosen,labels)
        if cur is None: break
        history.append(cur)
        k,_=v19.history_atom(states,keys,chosen,cur,history)
        if k is None: break
        chosen.append(k); used+=1
    return {'exact':v19.sufficient(states,chosen,labels),'queries':len(chosen),'unresolved':v19.unresolved(states,chosen,labels)}

def future_rank(x):
    # exact first; then fewer total queries; then smaller surviving verifier residual.
    return (1 if x['exact'] else 0, -x['queries'], -x['unresolved'])

def profile_features(states,chosen,cur,history,k,raw_n,adm_n):
    frac,counts=v32.balance_fraction(states,chosen,cur,k); n0,n1,n=counts
    support=sum(v19.separates(states,k,p) for p in history)
    sig=tuple((bool(states[a]['obs'][k]),bool(states[b]['obs'][k])) for a,b in history)
    return {
      'balance_fraction':(frac.numerator,frac.denominator),
      'bucket_n':n,'split_min':min(n0,n1),'split_max':max(n0,n1),
      'unresolved_before':v19.unresolved(states,chosen,[s['_label'] for s in states]),
      'history_size':len(history),'history_support':support,'history_diversity':len(set(sig)),
      'raw_source_matches':raw_n,'admitted_source_matches':adm_n}

def is_pure(rows,extra):
    seen={}
    collisions=[]
    for r in rows:
        key=(r['atom'],r['v32_admitted'])+tuple(tuple(r['features'][f]) if isinstance(r['features'][f],list) else r['features'][f] for f in extra)
        y=r['prefer_source']
        if key in seen and seen[key]!=y: collisions.append(key)
        else: seen[key]=y
    return len(collisions)==0,collisions

def main():
    if len(sys.argv)!=3: raise SystemExit('usage: run_v34_consequence_state_census.py EVAL TRAIN')
    ev=v13.v2.v1.load_tasks(sys.argv[1]); tr=v13.v2.v1.load_tasks(sys.argv[2])
    _,_,eligible=v31.select_target(tr)
    bounds,source_rows,trunc=v32.source_profiles(ev,False)
    atoms=set(bounds)
    rows=[]
    for er in eligible:
        tid=er['task']; states,keys,demo,held=v23.prepare(tr[tid])
        for i,s in enumerate(states): s['_label']=bool(demo[i])
        chosen=[];history=[]
        for qi in range(MAXQ):
            if v19.unresolved(states,chosen,demo)==0: break
            cur=v19.collision(states,chosen,demo)
            if cur is None: break
            history.append(cur)
            available=[]; admitted=[]
            for k in keys:
                if k in chosen or k not in atoms or not v19.separates(states,k,cur): continue
                frac,_=v32.balance_fraction(states,chosen,cur,k); lo,hi=bounds[k]
                available.append((k,frac,lo,hi))
                if lo<=frac<=hi: admitted.append((k,frac,lo,hi))
            fallback,_=v19.history_atom(states,keys,chosen,cur,history)
            # Counterfactual audit each remembered move against taking frozen fallback now.
            for k,frac,lo,hi in available:
                forced=finish_v19(states,keys,demo,chosen+[k],history,MAXQ-(qi+1))
                if fallback is None:
                    fb={'exact':False,'queries':len(chosen),'unresolved':v19.unresolved(states,chosen,demo)}
                else:
                    fb=finish_v19(states,keys,demo,chosen+[fallback],history,MAXQ-(qi+1))
                feats=profile_features(states,chosen,cur,history,k,len(available),len(admitted))
                # JSON-normalize tuple feature.
                feats['balance_fraction']=list(feats['balance_fraction'])
                rows.append({'task':tid,'step':qi+1,'atom':k,'v32_admitted':bool(lo<=frac<=hi),
                  'source_bounds':[[lo.numerator,lo.denominator],[hi.numerator,hi.denominator]],
                  'features':feats,'forced_source_future':forced,'fallback_future':fb,
                  'prefer_source':future_rank(forced)>future_rank(fb),'tie':future_rank(forced)==future_rank(fb)})
            # Advance exact frozen V32 WARM_GATED policy, to define reachable states only.
            if admitted:
                admitted.sort(key=lambda x:hashlib.sha256(x[0].encode()).hexdigest()); nxt=admitted[0][0]
            else: nxt=fallback
            if nxt is None: break
            chosen.append(nxt)
    # Is V32's binary state (atom identity + admitted/rejected) future-sufficient?
    base_pure,base_collisions=is_pure(rows,())
    mixed=[]
    groups={}
    for r in rows:
        key=(r['atom'],r['v32_admitted']); groups.setdefault(key,set()).add(r['prefer_source'])
    mixed=[{'atom':k[0],'v32_admitted':k[1]} for k,ys in groups.items() if len(ys)>1]
    minima=[]
    if not base_pure:
        for n in range(1,len(FEATURES)+1):
            for sub in itertools.combinations(FEATURES,n):
                ok,_=is_pure(rows,sub)
                if ok: minima.append(list(sub))
            if minima: break
    decision='V32_STATE_FUTURE_SUFFICIENT' if base_pure else ('FORCED_REFINEMENT_FOUND' if minima else 'FROZEN_FEATURES_INSUFFICIENT')
    result={'schema':'verified-developmental-navigation.arc-consequence-state-census.v34',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{'panel':'all frozen V31-eligible training targets','reachable_states':'exact frozen V32 WARM_GATED trajectory only','memory':'TRUE V32 source profiles','comparison':'force each available retained source atom once vs frozen V19 fallback once, then complete remaining budget with frozen V19','future_order':'exactness, then fewer total queries, then smaller unresolved residual','base_state':'literal atom identity + V32 admitted/rejected bit','candidate_refinements':FEATURES,'search':'exhaustive smallest feature subset yielding label-pure future preference classes','target_labels_used_for_state':False,'target_labels_used_for_audit':True,'max_queries':MAXQ},
      'measurements':{'eligible_targets':len(eligible),'decision_rows':len(rows),'mixed_base_classes':len(mixed),'mixed_classes':mixed,'base_state_future_sufficient':base_pure,'minimum_refinement_cardinality':len(minima[0]) if minima else 0,'minimum_refinements':minima},
      'strict_gate':decision,
      'rows':rows,
      'claim_boundary':'Mechanism census only. Any discovered refinement is post-hoc evidence that the V32 state representation is insufficient; it is not yet a deployed or blind transfer rule.'}
    out=HERE/'results_v34_consequence_state_census';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__': main()
