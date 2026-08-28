import hashlib
import importlib.util
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

v20=load('v20','run_v20_cross_episode_policy_transfer.py')
v19=v20.v19
v17=v20.v17
v13=v20.v13
SOURCE_TASKS=tuple(v20.SOURCE_TASKS)
TARGET_EPISODES=6
MAX_QUERIES=v20.MAX_QUERIES
SHAM_SEED=20260828


def fp(k):
    parts=k.split(':');out=[]
    for p in parts:
        if re.fullmatch(r'd\d+',p):out.append('d*')
        elif re.fullmatch(r'r\d+',p):out.append('r*')
        elif re.fullmatch(r'c\d+',p):out.append('c*')
        else:out.append(p)
    return ':'.join(out)


def audit_task(task):
    return v20.audit_task(task)


def compile_source_policy(source_ev,sham=False):
    totals=defaultdict(float);counts=defaultdict(int);literal=defaultdict(float);literal_counts=defaultdict(int);rows=[]
    for ti,tid in enumerate(SOURCE_TASKS):
        states,keys,demo,held=audit_task(source_ev[tid]);chosen=[];history=[]
        rng=random.Random(SHAM_SEED+ti+len(states));perm=list(range(len(states)));rng.shuffle(perm)
        for _ in range(MAX_QUERIES):
            if v19.unresolved(states,chosen,demo)==0:break
            cur=v19.collision(states,chosen,demo)
            if cur is None:break
            history.append(cur)
            k,_=v19.history_atom(states,keys,chosen,cur,list(history))
            if k is None:break
            chosen.append(k)
        scored=[(perm[a],perm[b]) for a,b in history] if sham else history
        for k in keys:
            cov=sum(v19.separates(states,k,p) for p in scored if max(p)<len(states));f=fp(k)
            totals[f]+=cov;counts[f]+=1;literal[k]+=cov;literal_counts[k]+=1
        rows.append({'task':tid,'residuals':len(history),'exact':v19.sufficient(states,chosen,demo),'truncated':any(s['truncated'] for s in states)})
    return ({f:totals[f]/counts[f] for f in totals},{k:literal[k]/literal_counts[k] for k in literal},rows)


def run_arm(states,keys,labels,source_policy=None,literal_policy=None):
    chosen=[];history=[];trace=[];index={k:i for i,k in enumerate(keys)}
    for step in range(MAX_QUERIES):
        before=v19.unresolved(states,chosen,labels)
        if before==0:break
        cur=v19.collision(states,chosen,labels)
        if cur is None:break
        history.append(cur)
        cand=[k for k in keys if k not in chosen and v19.separates(states,k,cur)]
        if not cand:break
        def score(k):
            prior=0 if source_policy is None else source_policy.get(fp(k),0.0)
            lit=0 if literal_policy is None else literal_policy.get(k,0.0)
            support=sum(v19.separates(states,k,p) for p in history)
            diversity=len(set((bool(states[a]['obs'][k]),bool(states[b]['obs'][k])) for a,b in history))
            return (prior,lit,support,diversity,hashlib.sha256(k.encode()).hexdigest())
        k=max(cand,key=score);chosen.append(k)
        trace.append({'query':step+1,'pair':cur,'atom':k,'fingerprint':fp(k),'before':before,'after':v19.unresolved(states,chosen,labels)})
    return chosen,trace


def legal(states,keys,demo,held):
    return bool(states) and not any(s['truncated'] for s in states) and 0<sum(demo)<len(states) and v19.unresolved(states,keys,demo)==0 and v19.unresolved(states,keys,held)==0


def main():
    if len(sys.argv)!=3:raise SystemExit('usage: run_v20c_cross_split_policy_transfer.py SOURCE_EVAL TARGET_TRAIN')
    source=v13.v2.v1.load_tasks(sys.argv[1]);target=v13.v2.v1.load_tasks(sys.argv[2])
    warm,raw,source_rows=compile_source_policy(source,False);sham,_,sham_rows=compile_source_policy(source,True)
    targets=[];scanned=0
    for tid in sorted(target):
        scanned+=1;states,keys,demo,held=audit_task(target[tid])
        if legal(states,keys,demo,held):targets.append((tid,states,keys,demo,held))
        if len(targets)>=TARGET_EPISODES:break
    rows=[]
    for tid,states,keys,demo,held in targets:
        specs={'WARM':(warm,None),'COLD':(None,None),'RAW_HISTORY':(None,raw),'SHAM':(sham,None),'ANCESTOR_ABLATION':(None,None)};arms={}
        for n,(p,l) in specs.items():
            chosen,trace=run_arm(states,keys,demo,p,l);arms[n]={'queries_used':len(chosen),'demo_exact':v19.sufficient(states,chosen,demo),'heldout_exact':v19.sufficient(states,chosen,held),'unresolved':v19.unresolved(states,chosen,demo),'atoms':chosen,'trace':trace}
        rows.append({'task':tid,'states':len(states),'future_positive':sum(demo),'candidate_programs':len(keys),'arms':arms})
    names=['WARM','COLD','RAW_HISTORY','SHAM','ANCESTOR_ABLATION']
    exact={n:sum(r['arms'][n]['demo_exact'] and r['arms'][n]['heldout_exact'] for r in rows) for n in names}
    unresolved={n:sum(r['arms'][n]['unresolved'] for r in rows) for n in names}
    warm_only=[r['task'] for r in rows if r['arms']['WARM']['demo_exact'] and r['arms']['WARM']['heldout_exact'] and not any(r['arms'][n]['demo_exact'] and r['arms'][n]['heldout_exact'] for n in names[1:])]
    strict=len(rows)>0 and bool(warm_only) and exact['WARM']>max(exact[n] for n in names[1:]) and unresolved['WARM']<min(unresolved[n] for n in names[1:]) and not any(r['truncated'] for r in source_rows)
    result={'schema':'verified-developmental-navigation.arc-cross-split-policy-transfer.v20c','source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34','split':'evaluation','tasks':SOURCE_TASKS},'target':{'split':'training','selection':'lexicographic first six legal carriers; no task IDs inspected before run','scanned':scanned,'eligible':[x[0] for x in targets]},'precommit':{'max_queries':MAX_QUERIES,'transfer_object':'residual-induced mean score over anonymized executable observation-program fingerprints','arms':names,'strict_gate':'>=1 WARM-only exact; WARM exact > every control; WARM unresolved total < every control; no source truncation'},'source_rows':source_rows,'sham_source_rows':sham_rows,'tasks':rows,'summary':{'exact_tasks':exact,'unresolved_totals':unresolved,'warm_only_exact_targets':warm_only},'strict_gate':'PASS_CROSS_SPLIT_DEVELOPMENTAL_COMPOUNDING' if strict else 'FAIL_CROSS_SPLIT_DEVELOPMENTAL_COMPOUNDING','claim_boundary':'Prospective evaluation-to-training ARC transfer under frozen V17 low-level observation language and 8-query budget; policy/discovery only, not new formability.'}
    out=HERE/'results_v20c_cross_split_policy_transfer';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
