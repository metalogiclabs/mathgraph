import hashlib
import importlib.util
import itertools
import json
import math
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

# Smallest extension beyond a single global method: one observable decision stump.
# State features are generic properties of the current quotient/residual candidate landscape.
STATE_FEATURES=(
    'history_size','bucket_size','separator_count','max_support','max_diversity',
    'support_argmax_count','diversity_argmax_count','argmax_overlap','support_diversity_disagree'
)

def candidate_rows(states,keys,chosen,current,history):
    rows=[]
    for k in keys:
        if k in chosen or not v19.separates(states,k,current):continue
        f=v23.feature_map(states,k,chosen,current,history)
        rows.append((k,f))
    return rows

def state_features(states,keys,chosen,current,history):
    rows=candidate_rows(states,keys,chosen,current,history)
    a,_=current
    cur_sig=tuple(bool(states[a]['obs'][q]) for q in chosen)
    bucket_size=sum(tuple(bool(s['obs'][q]) for q in chosen)==cur_sig for s in states)
    if not rows:
        return {x:0 for x in STATE_FEATURES}
    ms=max(f['history_support'] for _,f in rows)
    md=max(f['history_diversity'] for _,f in rows)
    sa={k for k,f in rows if f['history_support']==ms}
    da={k for k,f in rows if f['history_diversity']==md}
    return {
      'history_size':len(history),'bucket_size':bucket_size,'separator_count':len(rows),
      'max_support':ms,'max_diversity':md,'support_argmax_count':len(sa),
      'diversity_argmax_count':len(da),'argmax_overlap':len(sa & da),
      'support_diversity_disagree':int(sa!=da)
    }

def choose_with_method(states,keys,chosen,current,history,method):
    return v23.choose(states,keys,chosen,current,history,method)

def one_step_regret_for_method(states,keys,chosen,current,history,labels,method):
    k,_=choose_with_method(states,keys,chosen,current,history,method)
    before=v19.unresolved(states,chosen,labels)
    if k is None:return before,None
    best_after=v24.best_one_step_after(states,keys,chosen,current,labels)
    after=v19.unresolved(states,chosen+[k],labels)
    return after-best_after,k

def canonical_examples(ev,sham=False):
    # Fixed V19 trajectory generates decision states; target never enters learning.
    out=[];task_rows=[];trunc=False
    for tid in SOURCE:
        states,keys,labels,held=v23.prepare(ev[tid])
        chosen=[];history=[]
        rng=random.Random(SHAM_SEED+len(states));perm=list(range(len(states)));rng.shuffle(perm)
        local=[]
        for qi in range(MAXQ):
            if v19.unresolved(states,chosen,labels)==0:break
            cur=v19.collision(states,chosen,labels)
            if cur is None:break
            history.append(cur)
            score_hist=[(perm[a],perm[b]) for a,b in history] if sham else list(history)
            sf=state_features(states,keys,chosen,cur,score_hist)
            regrets=[]
            for m in METHODS:
                r,k=one_step_regret_for_method(states,keys,chosen,cur,score_hist,labels,m)
                regrets.append((r,m,k))
            best=min(r for r,_,_ in regrets)
            optimal=tuple(m for r,m,_ in regrets if r==best)
            out.append({'task':tid,'step':qi+1,'features':sf,'optimal_methods':optimal,'regrets':{m:r for r,m,_ in regrets}})
            # advance by frozen V19 COLD, independent of learned V25 policy
            k,_=v23.choose(states,keys,chosen,cur,score_hist,('history_support','history_diversity','bucket_balance','global_balance'))
            # To preserve exact V19 generation where possible, use native history chooser instead.
            cold_ch,_=v19.run_history(states,keys,labels,False)
            if qi < len(cold_ch): k=cold_ch[qi]
            if k is None or k in chosen:break
            chosen.append(k)
            local.append(k)
        task_rows.append({'task':tid,'examples':sum(e['task']==tid for e in out),'canonical_queries':len(chosen)})
        trunc|=any(s['truncated'] for s in states)
    return out,task_rows,trunc

def method_loss(examples,method):
    return sum(e['regrets'][method] for e in examples)

def best_method(examples):
    return min(METHODS,key=lambda m:(method_loss(examples,m),m)) if examples else METHODS[0]

def thresholds(examples,feature):
    vals=sorted(set(e['features'][feature] for e in examples))
    if len(vals)<2:return []
    return [(a+b)/2 for a,b in zip(vals,vals[1:])]

def train_stump(examples):
    # Include global method as a degenerate baseline; stumps must earn their extra condition.
    global_m=best_method(examples)
    best={'kind':'global','method':global_m,'loss':method_loss(examples,global_m),'complexity':0}
    for feat in STATE_FEATURES:
        for thr in thresholds(examples,feat):
            left=[e for e in examples if e['features'][feat] <= thr]
            right=[e for e in examples if e['features'][feat] > thr]
            if not left or not right:continue
            lm=best_method(left);rm=best_method(right)
            loss=method_loss(left,lm)+method_loss(right,rm)
            cand={'kind':'stump','feature':feat,'threshold':thr,'left_method':lm,'right_method':rm,'loss':loss,'complexity':1}
            key=(loss,1,feat,thr,lm,rm)
            bkey=(best['loss'],best['complexity'],best.get('feature',''),best.get('threshold',-1),best.get('left_method',best.get('method')),best.get('right_method',best.get('method')))
            if key<bkey:best=cand
    return best

def policy_method(policy,sf):
    if policy['kind']=='global':return tuple(policy['method'])
    return tuple(policy['left_method'] if sf[policy['feature']]<=policy['threshold'] else policy['right_method'])

def run_policy(states,keys,labels,policy,sham_runtime=False):
    chosen=[];history=[];trace=[]
    rng=random.Random(SHAM_SEED+len(states));perm=list(range(len(states)));rng.shuffle(perm)
    total_regret=0
    for qi in range(MAXQ):
        before=v19.unresolved(states,chosen,labels)
        if before==0:break
        cur=v19.collision(states,chosen,labels)
        if cur is None:break
        history.append(cur)
        score_hist=[(perm[a],perm[b]) for a,b in history] if sham_runtime else list(history)
        sf=state_features(states,keys,chosen,cur,score_hist)
        m=policy_method(policy,sf)
        k,f=choose_with_method(states,keys,chosen,cur,score_hist,m)
        if k is None:break
        best_after=v24.best_one_step_after(states,keys,chosen,cur,labels)
        chosen.append(k)
        after=v19.unresolved(states,chosen,labels)
        regret=after-best_after;total_regret+=regret
        trace.append({'q':qi+1,'state_features':sf,'selected_method':m,'atom':k,'unresolved_before':before,'unresolved_after':after,'one_step_regret':regret})
    return chosen,trace,total_regret

def arm(states,keys,demo,held,policy):
    ch,tr,reg=run_policy(states,keys,demo,policy,False)
    return {'queries':len(ch),'demo_exact':v19.sufficient(states,ch,demo),'heldout_exact':v19.sufficient(states,ch,held),'unresolved':v19.unresolved(states,ch,demo),'total_regret':reg,'trace':tr}

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v25_state_conditioned_method.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1])
    real_ex,real_rows,real_trunc=canonical_examples(ev,False)
    sham_ex,sham_rows,sham_trunc=canonical_examples(ev,True)
    warm_policy=train_stump(real_ex);sham_policy=train_stump(sham_ex)
    states,keys,demo,held=v23.prepare(ev[TARGET])
    arms={}
    arms['WARM']=arm(states,keys,demo,held,warm_policy)
    arms['SHAM_POLICY']=arm(states,keys,demo,held,sham_policy)
    cc,ct=v19.run_history(states,keys,demo,False)
    cold={'queries':len(cc),'demo_exact':v19.sufficient(states,cc,demo),'heldout_exact':v19.sufficient(states,cc,held),'unresolved':v19.unresolved(states,cc,demo),'trace':ct}
    arms['COLD']=cold;arms['ABLATION']=dict(cold)
    # RAW source atoms from canonical source trajectories only.
    source_atoms=[]
    for tid in SOURCE:
        st,ke,la,_=v23.prepare(ev[tid]);ch,_=v19.run_history(st,ke,la,False);source_atoms.extend(ch)
    rc,rt=v23.raw_replay(states,keys,demo,source_atoms)
    arms['RAW_HISTORY']={'queries':len(rc),'demo_exact':v19.sufficient(states,rc,demo),'heldout_exact':v19.sufficient(states,rc,held),'unresolved':v19.unresolved(states,rc,demo),'trace':rt}
    w=arms['WARM'];controls=[arms[x] for x in ('COLD','RAW_HISTORY','SHAM_POLICY','ABLATION')]
    policy_diff=warm_policy!=sham_policy
    strict=w['demo_exact'] and w['heldout_exact'] and all((not c['demo_exact']) or w['queries']<c['queries'] for c in controls) and policy_diff and not real_trunc and not any(s['truncated'] for s in states)
    result={'schema':'verified-developmental-navigation.arc-state-conditioned-method.v25',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{'source_tasks':SOURCE,'target_task':TARGET,'target_selection':'frozen blind V22 frontier; target excluded from learning','max_queries':MAXQ,
        'state_features':STATE_FEATURES,'policy_class':'global method or one depth-1 decision stump over observable residual-state geometry; leaf actions are unchanged V23 24-method language',
        'training_examples':'decision states from frozen V19 COLD source trajectories','training_loss':'sum of verified one-step regret of leaf method','sham':'same training procedure on deterministic index-permuted source residual histories',
        'arms':['WARM','COLD','RAW_HISTORY','SHAM_POLICY','ABLATION']},
      'warm_learning':{'policy':warm_policy,'examples':len(real_ex),'source_rows':real_rows,'truncated':real_trunc},
      'sham_learning':{'policy':sham_policy,'examples':len(sham_ex),'source_rows':sham_rows,'truncated':sham_trunc},
      'policy_differs_from_sham':policy_diff,
      'target':{'task':TARGET,'states':len(states),'future_positive':sum(demo),'candidate_programs':len(keys),'arms':arms,'any_truncation':any(s['truncated'] for s in states)},
      'strict_gate':'PASS_STATE_CONDITIONED_SOURCE_DISTINCT_COMPOUNDING' if strict else 'FAIL_STATE_CONDITIONED_SOURCE_DISTINCT_COMPOUNDING',
      'claim_boundary':'Tests whether verified source experience learns a minimal state-conditioned query-ranking method that improves an independently frozen ARC target beyond cold, raw-history, corrupted-history, and ablation controls. The observation/continuation languages remain frozen.'}
    out=HERE/'results_v25_state_conditioned_method';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
