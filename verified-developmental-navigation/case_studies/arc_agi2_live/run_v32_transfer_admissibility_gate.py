import hashlib
import importlib.util
import json
import random
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

v31=load('v31','run_v31_blind_fresh_target_transfer.py')
v28,v27,v23,v19,v13=v31.v28,v31.v27,v31.v23,v31.v19,v31.v13
SOURCE=tuple(v28.SOURCE); MAXQ=v28.MAXQ; SHAM_SEED=v27.SHAM_SEED

# V32 tests the residual forced by V31: literal source memory can over-transfer.
# No new ARC semantics or task labels are introduced.  Each source-selected atom
# retains only an anonymous observable applicability profile: the balance fraction
# with which it split the CURRENT UNLABELLED quotient bucket at source use-time.
# On target, a retained atom may be reused only when its current bucket-balance
# fraction lies inside the convex hull [min,max] of its source-observed fractions.
# The gate never reads target future labels; labels are used only by the verifier
# to return the current collision and for post-hoc exactness auditing.

def current_bucket(states,chosen,current):
    a,_=current
    sig=tuple(bool(states[a]['obs'][q]) for q in chosen)
    return [i for i,s in enumerate(states) if tuple(bool(s['obs'][q]) for q in chosen)==sig]

def balance_fraction(states,chosen,current,atom):
    inds=current_bucket(states,chosen,current)
    n=len(inds)
    n1=sum(bool(states[i]['obs'][atom]) for i in inds); n0=n-n1
    return Fraction(min(n0,n1),n), (n0,n1,n)

def source_profiles(ev,sham=False):
    prof=defaultdict(list); rows=[]; truncated=False
    for tid in SOURCE:
        states,keys,demo,_=v23.prepare(ev[tid]); truncated|=any(s['truncated'] for s in states)
        chosen=[];history=[]
        rng=random.Random(SHAM_SEED+len(states)); perm=list(range(len(states)));rng.shuffle(perm)
        sham_labels=[False]*len(demo)
        for i,x in enumerate(demo): sham_labels[perm[i]]=bool(x)
        labels=sham_labels if sham else demo
        for qi in range(MAXQ):
            if v19.sufficient(states,chosen,labels): break
            cur=v19.collision(states,chosen,labels)
            if cur is None: break
            history.append(cur)
            sig,pref,meta=v27.best_source_profile(states,keys,chosen,cur,history,labels)
            if pref is None: break
            candidates=v27.admissible_profiles(states,keys,chosen,cur,history)
            matching=[x for x in candidates if x[1]==pref]
            matching.sort(key=lambda x:hashlib.sha256(x[0].encode()).hexdigest())
            atom=matching[0][0]
            frac,counts=balance_fraction(states,chosen,cur,atom)
            prof[atom].append(frac)
            rows.append({'task':tid,'query':qi+1,'atom':atom,'balance':[frac.numerator,frac.denominator],'bucket_counts':list(counts)})
            chosen.append(atom)
    bounds={a:(min(xs),max(xs)) for a,xs in prof.items()}
    return bounds,rows,truncated

def run_gated(states,keys,labels,bounds):
    chosen=[];history=[];trace=[];hits=0;rejected=0
    for qi in range(MAXQ):
        before=v19.unresolved(states,chosen,labels)
        if before==0: break
        cur=v19.collision(states,chosen,labels)
        if cur is None: break
        history.append(cur)
        raw=[]; admitted=[]
        for k in keys:
            if k in chosen or k not in bounds or not v19.separates(states,k,cur): continue
            frac,counts=balance_fraction(states,chosen,cur,k)
            lo,hi=bounds[k]
            row=(k,frac,counts,lo,hi)
            raw.append(row)
            if lo <= frac <= hi: admitted.append(row)
        if admitted:
            admitted.sort(key=lambda x:hashlib.sha256(x[0].encode()).hexdigest())
            k,frac,counts,lo,hi=admitted[0]; mode='GATED_SOURCE'; hits+=1
            meta={'balance':[frac.numerator,frac.denominator],'source_bounds':[[lo.numerator,lo.denominator],[hi.numerator,hi.denominator]],'raw_source_matches':len(raw),'admitted_source_matches':len(admitted)}
        else:
            rejected+=len(raw)
            k,f=v19.history_atom(states,keys,chosen,cur,history); mode='V19_FALLBACK'
            meta={'raw_source_matches':len(raw),'admitted_source_matches':0,'fallback_features':f}
        if k is None: break
        chosen.append(k)
        trace.append({'query':qi+1,'mode':mode,'atom':k,'unresolved_before':before,'unresolved_after':v19.unresolved(states,chosen,labels),**meta})
    return chosen,trace,hits,rejected

def arm(states,chosen,trace,hits,demo,held,rejected=0):
    return {'queries':len(chosen),'demo_exact':v19.sufficient(states,chosen,demo),'heldout_exact':v19.sufficient(states,chosen,held),'unresolved':v19.unresolved(states,chosen,demo),'transfer_hits':hits,'rejected_matches':rejected,'trace':trace}

def compact(a): return {k:a[k] for k in ('queries','demo_exact','heldout_exact','unresolved','transfer_hits','rejected_matches')}

def main():
    if len(sys.argv)!=3: raise SystemExit('usage: run_v32_transfer_admissibility_gate.py EVAL TRAIN')
    ev=v13.v2.v1.load_tasks(sys.argv[1]); tr=v13.v2.v1.load_tasks(sys.argv[2])
    chosen,_,eligible=v31.select_target(tr)
    if chosen is None: raise SystemExit('no V31 frontier')
    target=chosen['task']
    true_bounds,true_rows,ttr=source_profiles(ev,False); sham_bounds,sham_rows,strunc=source_profiles(ev,True)
    states,keys,demo,held=v23.prepare(tr[target])
    wc,wt,wh,wr=run_gated(states,keys,demo,true_bounds)
    sc,st,sh,sr=run_gated(states,keys,demo,sham_bounds)
    cc,ct=v19.run_history(states,keys,demo,False)
    warm=arm(states,wc,wt,wh,demo,held,wr); sham=arm(states,sc,st,sh,demo,held,sr); cold=arm(states,cc,ct,0,demo,held,0)
    strict=(warm['demo_exact'] and warm['heldout_exact'] and warm['transfer_hits']>0 and
            all((not x['demo_exact']) or warm['queries']<x['queries'] for x in (sham,cold)) and
            not ttr and not strunc and not any(s['truncated'] for s in states))
    result={'schema':'verified-developmental-navigation.arc-transfer-admissibility-gate.v32',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{'source_tasks':SOURCE,'target_task':target,'target_selection':'exact V31 blind frontier selector; target already exposed by V31 before V32 mechanism audit','candidate_language':'unchanged V17/V13','source_memory':'same V27 one-step verifier-optimal literal atoms plus only source-observed anonymous current-bucket balance fractions','admissibility':'retained atom reusable iff target current unlabelled quotient-bucket balance fraction lies within inclusive min/max source-observed range for that atom','target_labels_used_by_gate':False,'fallback':'frozen V19','max_queries':MAXQ,'sham':'identical gate learned from deterministic source-label permutation'},
      'source_profile_counts':{'true_atoms':len(true_bounds),'true_observations':len(true_rows),'sham_atoms':len(sham_bounds),'sham_observations':len(sham_rows)},
      'target':{'task':target,'states':len(states),'future_positive':sum(demo),'candidate_programs':len(keys),'arms':{'WARM_GATED':compact(warm),'SHAM_GATED':compact(sham),'COLD':compact(cold)},'warm_trace':wt,'sham_trace':st},
      'strict_gate':'PASS_TRANSFER_ADMISSIBILITY_GATE' if strict else 'FAIL_TRANSFER_ADMISSIBILITY_GATE',
      'claim_boundary':'Post-V31 mechanism audit on the V31-selected fresh target. Tests whether a source-only, label-free applicability gate prevents harmful literal over-transfer. It is not a new blind target replication.'}
    out=HERE/'results_v32_transfer_admissibility_gate';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__': main()
