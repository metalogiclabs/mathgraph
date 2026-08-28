import importlib.util
import itertools
import json
import random
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v24=load('v24','run_v24_trajectory_predictive_transfer.py')
v23=v24.v23
v19=v24.v19
v13=v24.v13
SOURCE=v24.SOURCE
TARGET=v24.TARGET
METHODS=v24.METHODS
MAXQ=v24.MAXQ
SHAM_SEED=v23.SHAM_SEED

# V25: source-only consequence quotient over decision states, represented by the
# smallest nontrivial state-conditioned policy class: one observable stump and
# one V23 ranking method per leaf. No target labels enter router selection.
DESCRIPTORS=('depth','bucket_size','separator_count')

def current_bucket_size(states,chosen,current):
    a,_=current
    sig=tuple(bool(states[a]['obs'][q]) for q in chosen)
    return sum(tuple(bool(s['obs'][q]) for q in chosen)==sig for s in states)

def separator_count(states,keys,chosen,current):
    return sum(k not in chosen and v19.separates(states,k,current) for k in keys)

def descriptor(states,keys,chosen,current,history):
    return {
      'depth':len(chosen),
      'bucket_size':current_bucket_size(states,chosen,current),
      'separator_count':separator_count(states,keys,chosen,current),
    }

def build_source_states(ev,sham=False):
    rows=[]
    for tid in SOURCE:
        states,keys,labels,_=v23.prepare(ev[tid])
        chosen=[];history=[]
        rng=random.Random(SHAM_SEED+len(states));perm=list(range(len(states)));rng.shuffle(perm)
        for qi in range(MAXQ):
            before=v19.unresolved(states,chosen,labels)
            if before==0:break
            cur=v19.collision(states,chosen,labels)
            if cur is None:break
            history.append(cur)
            score_hist=[(perm[a],perm[b]) for a,b in history] if sham else list(history)
            best_after=v24.best_one_step_after(states,keys,chosen,cur,labels)
            regrets={}
            choices={}
            for method in METHODS:
                k,_=v23.choose(states,keys,chosen,cur,score_hist,method)
                if k is None:
                    after=before
                else:
                    after=v19.unresolved(states,chosen+[k],labels)
                regrets[method]=after-best_after
                choices[method]=k
            d=descriptor(states,keys,chosen,cur,history)
            rows.append({'task':tid,'states':states,'keys':keys,'labels':labels,'chosen':tuple(chosen),
                         'history':tuple(history),'current':cur,'descriptor':d,'regrets':regrets,'choices':choices,
                         'best_after':best_after,'before':before})
            # Advance on frozen V19 COLD trajectory so training-state distribution
            # is independent of the V25 router being selected.
            k,_=v19.choose_history(states,keys,chosen,cur,history,False)
            if k is None:break
            chosen.append(k)
    return rows

def leaf_best(rows):
    best=None
    for m in METHODS:
        regret=sum(r['regrets'][m] for r in rows)
        cand=(-regret,m)
        if best is None or cand>best[0]:best=(cand,m,regret)
    return best[1],best[2]

def train_router(rows):
    base_m,base_regret=leaf_best(rows)
    best=None
    for field in DESCRIPTORS:
        vals=sorted(set(r['descriptor'][field] for r in rows))
        # thresholds are source-derived only; <= threshold goes left.
        for thr in vals[:-1]:
            left=[r for r in rows if r['descriptor'][field]<=thr]
            right=[r for r in rows if r['descriptor'][field]>thr]
            if not left or not right:continue
            lm,lr=leaf_best(left);rm,rr=leaf_best(right)
            total=lr+rr
            # prefer lower regret, then simpler balanced split, then deterministic tuple.
            balance=-abs(len(left)-len(right))
            cand=(-total,balance,field,-thr,lm,rm)
            if best is None or cand>best[0]:
                best=(cand,{'field':field,'threshold':thr,'left_method':lm,'right_method':rm,
                            'source_regret':total,'left_n':len(left),'right_n':len(right),
                            'global_method':base_m,'global_regret':base_regret})
    if best is None:
        return {'field':'depth','threshold':10**9,'left_method':base_m,'right_method':base_m,
                'source_regret':base_regret,'left_n':len(rows),'right_n':0,'global_method':base_m,'global_regret':base_regret}
    return best[1]

def method_for(router,d):
    return router['left_method'] if d[router['field']]<=router['threshold'] else router['right_method']

def run_router(states,keys,labels,router):
    chosen=[];history=[];trace=[]
    total_regret=0
    for qi in range(MAXQ):
        before=v19.unresolved(states,chosen,labels)
        if before==0:break
        cur=v19.collision(states,chosen,labels)
        if cur is None:break
        history.append(cur)
        d=descriptor(states,keys,chosen,cur,history)
        method=method_for(router,d)
        k,f=v23.choose(states,keys,chosen,cur,history,method)
        if k is None:break
        best_after=v24.best_one_step_after(states,keys,chosen,cur,labels)
        chosen.append(k)
        after=v19.unresolved(states,chosen,labels)
        regret=after-best_after;total_regret+=regret
        trace.append({'q':qi+1,'descriptor':d,'route':'left' if d[router['field']]<=router['threshold'] else 'right',
                      'method':method,'atom':k,'features':f,'unresolved_before':before,'unresolved_after':after,
                      'best_one_step_after':best_after,'one_step_regret':regret})
    return chosen,trace,total_regret

def router_public(r):
    return {k:(list(v) if isinstance(v,tuple) else v) for k,v in r.items()}

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v25_state_conditioned_method_transfer.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1])
    source_rows=build_source_states(ev,False)
    sham_rows=build_source_states(ev,True)
    warm_router=train_router(source_rows)
    sham_router=train_router(sham_rows)

    states,keys,demo,held=v23.prepare(ev[TARGET])
    wc,wt,wreg=run_router(states,keys,demo,warm_router)
    sc,st,sreg=run_router(states,keys,demo,sham_router)
    cc,ct=v19.run_history(states,keys,demo,False)

    # RAW control: literal source atoms from frozen source trajectories; then V23 fallback.
    source_atoms=[]
    for r in source_rows:
        k=v19.choose_history(r['states'],r['keys'],list(r['chosen']),r['current'],list(r['history']),False)[0]
        if k is not None:source_atoms.append(k)
    rc,rt=v23.raw_replay(states,keys,demo,source_atoms)

    def arm(ch,tr,reg=None):
        z={'queries':len(ch),'demo_exact':v19.sufficient(states,ch,demo),'heldout_exact':v19.sufficient(states,ch,held),
           'unresolved':v19.unresolved(states,ch,demo),'trace':tr}
        if reg is not None:z['total_regret']=reg
        return z
    arms={'WARM':arm(wc,wt,wreg),'SHAM_ROUTER':arm(sc,st,sreg),'COLD':arm(cc,ct),
          'ABLATION':arm(cc,ct),'RAW_HISTORY':arm(rc,rt)}
    w=arms['WARM'];controls=[arms[x] for x in ('COLD','RAW_HISTORY','SHAM_ROUTER','ABLATION')]
    routers_differ=(warm_router['field'],warm_router['threshold'],warm_router['left_method'],warm_router['right_method']) != \
                   (sham_router['field'],sham_router['threshold'],sham_router['left_method'],sham_router['right_method'])
    strict=w['demo_exact'] and w['heldout_exact'] and all((not c['demo_exact']) or w['queries']<c['queries'] for c in controls) \
           and routers_differ and not any(s['truncated'] for s in states)

    # Source consequence quotient summary: states equivalent when the set of minimum-regret
    # methods is identical. This records what verifier consequences actually forced.
    def quotient_summary(rows):
        classes={}
        for r in rows:
            mr=min(r['regrets'].values()); winners=tuple(m for m in METHODS if r['regrets'][m]==mr)
            key=tuple(winners)
            classes.setdefault(key,0);classes[key]+=1
        return {'decision_states':len(rows),'consequence_classes':len(classes),'class_sizes':sorted(classes.values(),reverse=True)}

    result={'schema':'verified-developmental-navigation.arc-state-conditioned-method-transfer.v25',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{'source_tasks':SOURCE,'target_task':TARGET,'target_used_for_router_selection':False,
        'target_selection':'frozen blind V22 frontier task; COLD 6 vs oracle 3',
        'training_states':'decision states along frozen V19 COLD source trajectories',
        'consequence_label':'per-state one-step verifier regret for each of the unchanged 24 V23 ranking methods',
        'router_language':'one source-derived threshold on depth, current quotient-bucket size, or available-separator count; one learned ranking method per leaf',
        'sham':'identical router learner using deterministic index-permuted source residual histories',
        'arms':['WARM','COLD','RAW_HISTORY','SHAM_ROUTER','ABLATION'],'max_queries':MAXQ},
      'source_consequence_quotient':quotient_summary(source_rows),
      'sham_consequence_quotient':quotient_summary(sham_rows),
      'warm_router':router_public(warm_router),'sham_router':router_public(sham_router),'routers_differ':routers_differ,
      'target':{'task':TARGET,'states':len(states),'future_positive':sum(demo),'candidate_programs':len(keys),
                'any_truncation':any(s['truncated'] for s in states),'arms':arms},
      'strict_gate':'PASS_STATE_CONDITIONED_SOURCE_DISTINCT_COMPOUNDING' if strict else 'FAIL_STATE_CONDITIONED_SOURCE_DISTINCT_COMPOUNDING',
      'claim_boundary':'Tests whether source verifier trajectories support a small state-conditioned transferable developmental method inside frozen V17 observation and V13 continuation languages. The router language is finite and supplied; its threshold and leaf methods are source-learned.'}
    out=HERE/'results_v25_state_conditioned_method_transfer';out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
