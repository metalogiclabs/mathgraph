import hashlib, importlib.util, itertools, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v34=load('v34','run_v34_consequence_state_census.py')
v32,v31,v28,v23,v19,v13=v34.v32,v34.v31,v34.v28,v34.v23,v34.v19,v34.v13
MAXQ=v28.MAXQ

# V35 converts the V34 mechanism census into an out-of-target predictive test.
# The four minimum V34 refinements are frozen before evaluation.  For each held-out
# target, a conservative exact lookup is learned only from the other 28 targets'
# counterfactual verifier outcomes.  The held-out target's counterfactual labels are
# never used to choose source-vs-fallback.  Unseen or impure classes fall back to V19.
REFINEMENTS=(
    ('balance_fraction','unresolved_before'),
    ('bucket_n','unresolved_before'),
    ('split_min','unresolved_before'),
    ('unresolved_before','history_size'),
)

def norm(x):
    if isinstance(x,list): return tuple(x)
    if isinstance(x,tuple): return tuple(x)
    return x

def class_key(atom,admitted,features,refinement):
    return (atom,bool(admitted))+tuple(norm(features[f]) for f in refinement)

def collect_rows(ev,tr,eligible,bounds):
    atoms=set(bounds); rows=[]
    for er in eligible:
        tid=er['task']; states,keys,demo,held=v23.prepare(tr[tid])
        for i,s in enumerate(states): s['_label']=bool(demo[i])
        chosen=[]; history=[]
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
            for k,frac,lo,hi in available:
                forced=v34.finish_v19(states,keys,demo,chosen+[k],history,MAXQ-(qi+1))
                if fallback is None:
                    fb={'exact':False,'queries':len(chosen),'unresolved':v19.unresolved(states,chosen,demo)}
                else:
                    fb=v34.finish_v19(states,keys,demo,chosen+[fallback],history,MAXQ-(qi+1))
                feats=v34.profile_features(states,chosen,cur,history,k,len(available),len(admitted))
                feats['balance_fraction']=list(feats['balance_fraction'])
                rows.append({'task':tid,'atom':k,'v32_admitted':bool(lo<=frac<=hi),'features':feats,
                             'prefer_source':v34.future_rank(forced)>v34.future_rank(fb),
                             'tie':v34.future_rank(forced)==v34.future_rank(fb)})
            if admitted:
                admitted.sort(key=lambda x:hashlib.sha256(x[0].encode()).hexdigest()); nxt=admitted[0][0]
            else: nxt=fallback
            if nxt is None: break
            chosen.append(nxt)
    return rows

def learn_lookup(rows,heldout,refinement):
    ys={}
    for r in rows:
        if r['task']==heldout: continue
        k=class_key(r['atom'],r['v32_admitted'],r['features'],refinement)
        ys.setdefault(k,set()).add(bool(r['prefer_source']))
    # Conservative: act only when every observed training future for an exact class says force source.
    return {k:next(iter(v)) for k,v in ys.items() if len(v)==1}, {k for k,v in ys.items() if len(v)>1}

def online_features(states,chosen,cur,history,k,raw_n,adm_n,labels):
    frac,counts=v32.balance_fraction(states,chosen,cur,k); n0,n1,n=counts
    support=sum(v19.separates(states,k,p) for p in history)
    sig=tuple((bool(states[a]['obs'][k]),bool(states[b]['obs'][k])) for a,b in history)
    return {'balance_fraction':(frac.numerator,frac.denominator),'bucket_n':n,
            'split_min':min(n0,n1),'split_max':max(n0,n1),
            'unresolved_before':v19.unresolved(states,chosen,labels),
            'history_size':len(history),'history_support':support,
            'history_diversity':len(set(sig)),'raw_source_matches':raw_n,
            'admitted_source_matches':adm_n}

def run_policy(states,keys,labels,bounds,lookup,refinement):
    chosen=[]; history=[]; trace=[]; hits=0; lookup_hits=0; unseen=0; predicted_fallback=0
    atoms=set(bounds)
    for qi in range(MAXQ):
        before=v19.unresolved(states,chosen,labels)
        if before==0: break
        cur=v19.collision(states,chosen,labels)
        if cur is None: break
        history.append(cur)
        available=[]; v32_admitted=[]
        for k in keys:
            if k in chosen or k not in atoms or not v19.separates(states,k,cur): continue
            frac,_=v32.balance_fraction(states,chosen,cur,k); lo,hi=bounds[k]
            available.append((k,lo<=frac<=hi))
            if lo<=frac<=hi: v32_admitted.append(k)
        candidates=[]
        for k,adm in available:
            f=online_features(states,chosen,cur,history,k,len(available),len(v32_admitted),labels)
            ck=class_key(k,adm,f,refinement)
            pred=lookup.get(ck,None)
            if pred is True: candidates.append((k,ck))
            elif pred is False: predicted_fallback+=1
            else: unseen+=1
        if candidates:
            candidates.sort(key=lambda x:hashlib.sha256(x[0].encode()).hexdigest())
            nxt,ck=candidates[0]; mode='LOO_SOURCE'; hits+=1; lookup_hits+=1
        else:
            nxt,_=v19.history_atom(states,keys,chosen,cur,history); mode='V19_FALLBACK'
        if nxt is None: break
        chosen.append(nxt)
        trace.append({'query':qi+1,'mode':mode,'atom':nxt,'unresolved_before':before,
                      'unresolved_after':v19.unresolved(states,chosen,labels),
                      'available_source_matches':len(available),'v32_admitted_matches':len(v32_admitted)})
    return {'queries':len(chosen),'demo_exact':v19.sufficient(states,chosen,labels),
            'unresolved':v19.unresolved(states,chosen,labels),'transfer_hits':hits,
            'lookup_hits':lookup_hits,'unseen_class_checks':unseen,
            'predicted_fallback_checks':predicted_fallback,'chosen':chosen,'trace':trace}

def run_v32(states,keys,labels,bounds):
    c,t,h,r=v32.run_gated(states,keys,labels,bounds)
    return {'queries':len(c),'demo_exact':v19.sufficient(states,c,labels),'unresolved':v19.unresolved(states,c,labels),
            'transfer_hits':h,'chosen':c,'trace':t}

def run_cold(states,keys,labels):
    c,t=v19.run_history(states,keys,labels,False)
    return {'queries':len(c),'demo_exact':v19.sufficient(states,c,labels),'unresolved':v19.unresolved(states,c,labels),
            'transfer_hits':0,'chosen':c,'trace':t}

def add_heldout(states,a,held):
    a=dict(a); a['heldout_exact']=v19.sufficient(states,a['chosen'],held); a.pop('chosen',None); return a

def score(per):
    solved=sum(x['demo_exact'] and x['heldout_exact'] for x in per.values())
    demo=sum(x['demo_exact'] for x in per.values())
    total_q=sum(x['queries'] for x in per.values())
    residual=sum(x['unresolved'] for x in per.values())
    return {'solved_both':solved,'demo_exact':demo,'total_queries':total_q,'total_unresolved':residual}

def better(a,b):
    return (a['solved_both'],a['demo_exact'],-a['total_queries'],-a['total_unresolved']) > (b['solved_both'],b['demo_exact'],-b['total_queries'],-b['total_unresolved'])

def main():
    if len(sys.argv)!=3: raise SystemExit('usage: run_v35_leave_one_target_out_residual_gate.py EVAL TRAIN')
    ev=v13.v2.v1.load_tasks(sys.argv[1]); tr=v13.v2.v1.load_tasks(sys.argv[2])
    _,_,eligible=v31.select_target(tr)
    bounds,source_rows,trunc=v32.source_profiles(ev,False)
    rows=collect_rows(ev,tr,eligible,bounds)
    tids=[x['task'] for x in eligible]
    baselines={'V32_GATED':{},'COLD':{}}
    policies={'+'.join(r):{} for r in REFINEMENTS}
    lookup_stats={'+'.join(r):{} for r in REFINEMENTS}
    target_trunc=False
    for tid in tids:
        states,keys,demo,held=v23.prepare(tr[tid]); target_trunc|=any(s['truncated'] for s in states)
        baselines['V32_GATED'][tid]=add_heldout(states,run_v32(states,keys,demo,bounds),held)
        baselines['COLD'][tid]=add_heldout(states,run_cold(states,keys,demo),held)
        for ref in REFINEMENTS:
            name='+'.join(ref); lookup,mixed=learn_lookup(rows,tid,ref)
            p=run_policy(states,keys,demo,bounds,lookup,ref)
            policies[name][tid]=add_heldout(states,p,held)
            lookup_stats[name][tid]={'pure_training_classes':len(lookup),'mixed_training_classes':len(mixed)}
    scores={k:score(v) for k,v in baselines.items()}
    policy_scores={k:score(v) for k,v in policies.items()}
    winners=[k for k,s in policy_scores.items() if better(s,scores['V32_GATED']) and better(s,scores['COLD'])]
    strict=bool(winners) and not trunc and not target_trunc
    result={'schema':'verified-developmental-navigation.arc-loo-residual-relative-gate.v35',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{'panel':'same 29 frozen V31-eligible training targets','refinements':['+'.join(x) for x in REFINEMENTS],
        'training':'for each held-out target, exact class lookup learned from counterfactual rows of other targets only',
        'prediction':'force retained source atom only if exact class is observed outside held-out target and all training labels strictly prefer source; otherwise frozen V19 fallback',
        'heldout_counterfactual_labels_used_for_policy':False,'source_memory':'TRUE V32 source profiles','max_queries':MAXQ,
        'comparison':'LOO residual-relative policies vs frozen V32 gate and COLD','trajectory':'policy is deployed online; unseen states conservatively fall back'},
      'measurements':{'eligible_targets':len(tids),'counterfactual_training_rows':len(rows),'baseline_scores':scores,'policy_scores':policy_scores,'strict_winners':winners},
      'lookup_stats':lookup_stats,'baselines':baselines,'policies':policies,
      'strict_gate':'PASS_LOO_RESIDUAL_RELATIVE_TRANSFER' if strict else 'FAIL_LOO_RESIDUAL_RELATIVE_TRANSFER',
      'claim_boundary':'Cross-target leave-one-out deployment on the already-audited V34 panel. Held-out target counterfactual futures are excluded from its policy learner, but the panel and four candidate refinements were selected after V34. This is stronger than a mechanism census, weaker than a fresh prospective blind replication.'}
    out=HERE/'results_v35_leave_one_target_out_residual_gate';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__': main()
