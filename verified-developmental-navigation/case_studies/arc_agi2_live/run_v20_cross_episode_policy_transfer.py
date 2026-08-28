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

v19=load('v19','run_v19_residual_history_policy.py')
v18=v19.v18
v17=v19.v17
v13=v19.v13
SOURCE_TASKS=tuple(v13.TARGETS)
TARGET_EPISODES=6
MAX_SCAN=80
MAX_QUERIES=v18.MAX_QUERIES
SHAM_SEED=20260828


def fp(k):
    """Mechanical source-independent observation-program fingerprint.

    Preserve executable opcode/relation structure but erase demo, row and column
    identities. No target labels or task IDs enter the fingerprint.
    """
    parts=k.split(':')
    out=[]
    for p in parts:
        if re.fullmatch(r'd\d+',p): out.append('d*')
        elif re.fullmatch(r'r\d+',p): out.append('r*')
        elif re.fullmatch(r'c\d+',p): out.append('c*')
        else: out.append(p)
    return ':'.join(out)


def audit_task(task):
    states,keys=v17.states_for(task)
    for s in states:
        df,hs,w,tr,trunc=v13.future_audit(task,s)
        s['demo']=bool(df);s['held']=bool(hs);s['truncated']=bool(trunc)
    demo=[s['demo'] for s in states];held=[s['held'] for s in states]
    return states,keys,demo,held


def compile_source_policy(ev, sham=False):
    totals=defaultdict(float);counts=defaultdict(int)
    literal=defaultdict(float);literal_counts=defaultdict(int)
    source_rows=[]
    for ti,tid in enumerate(SOURCE_TASKS):
        task=ev[tid];states,keys,demo,held=audit_task(task)
        chosen=[];history=[]
        rng=random.Random(SHAM_SEED+ti+len(states))
        perm=list(range(len(states)));rng.shuffle(perm)
        # Reproduce the verifier-driven source episode; only returned residuals are retained.
        for _ in range(MAX_QUERIES):
            if v19.unresolved(states,chosen,demo)==0:break
            cur=v19.collision(states,chosen,demo)
            if cur is None:break
            history.append(cur)
            k,_=v19.history_atom(states,keys,chosen,cur,list(history))
            if k is None:break
            chosen.append(k)
        scored_hist=[(perm[a],perm[b]) for a,b in history] if sham else list(history)
        for k in keys:
            coverage=sum(v19.separates(states,k,p) for p in scored_hist if max(p)<len(states))
            f=fp(k);totals[f]+=coverage;counts[f]+=1
            literal[k]+=coverage;literal_counts[k]+=1
        source_rows.append({'task':tid,'states':len(states),'residuals':len(history),'source_exact':v19.sufficient(states,chosen,demo),'any_truncation':any(s['truncated'] for s in states)})
    policy={f:totals[f]/counts[f] for f in totals}
    literal_policy={k:literal[k]/literal_counts[k] for k in literal}
    return policy,literal_policy,source_rows


def run_arm(states,keys,labels,source_policy=None,literal_policy=None):
    chosen=[];history=[];trace=[]
    index={k:i for i,k in enumerate(keys)}
    for q in range(MAX_QUERIES):
        before=v19.unresolved(states,chosen,labels)
        if before==0:break
        cur=v19.collision(states,chosen,labels)
        if cur is None:break
        history.append(cur)
        candidates=[k for k in keys if k not in chosen and v19.separates(states,k,cur)]
        if not candidates:break
        def score(k):
            hist_support=sum(v19.separates(states,k,p) for p in history)
            diversity=len(set((bool(states[a]['obs'][k]),bool(states[b]['obs'][k])) for a,b in history))
            prior=0.0 if source_policy is None else source_policy.get(fp(k),0.0)
            lit=0.0 if literal_policy is None else literal_policy.get(k,0.0)
            tie=hashlib.sha256(k.encode()).hexdigest()
            return (prior,lit,hist_support,diversity,tie)
        k=max(candidates,key=score)
        chosen.append(k)
        trace.append({'query':q+1,'pair':cur,'atom':k,'fingerprint':fp(k),'score':score(k),'before':before,'after':v19.unresolved(states,chosen,labels)})
    return chosen,trace


def eligible(states,keys,demo,held):
    if not states or any(s['truncated'] for s in states):return False
    p=sum(demo)
    if p==0 or p==len(states):return False
    if v19.unresolved(states,keys,demo)!=0:return False
    if v19.unresolved(states,keys,held)!=0:return False
    return True


def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v20_cross_episode_policy_transfer.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1])
    warm_policy,raw_policy,source_rows=compile_source_policy(ev,False)
    sham_policy,_,sham_source_rows=compile_source_policy(ev,True)

    targets=[];scanned=0
    for tid in sorted(ev):
        if tid in SOURCE_TASKS:continue
        if scanned>=MAX_SCAN or len(targets)>=TARGET_EPISODES:break
        scanned+=1
        task=ev[tid]
        states,keys,demo,held=audit_task(task)
        if eligible(states,keys,demo,held):targets.append((tid,states,keys,demo,held))

    rows=[]
    for tid,states,keys,demo,held in targets:
        arms={
          'WARM':run_arm(states,keys,demo,source_policy=warm_policy),
          'COLD':run_arm(states,keys,demo),
          'RAW_HISTORY':run_arm(states,keys,demo,literal_policy=raw_policy),
          'SHAM':run_arm(states,keys,demo,source_policy=sham_policy),
          'ANCESTOR_ABLATION':run_arm(states,keys,demo),
        }
        out={}
        for name,(chosen,trace) in arms.items():
            out[name]={'queries_used':len(chosen),'demo_exact':v19.sufficient(states,chosen,demo),'heldout_exact':v19.sufficient(states,chosen,held),'unresolved':v19.unresolved(states,chosen,demo),'atoms':chosen,'trace':trace}
        rows.append({'task':tid,'states':len(states),'future_positive':sum(demo),'candidate_programs':len(keys),'arms':out})

    def exact(name):return sum(r['arms'][name]['demo_exact'] and r['arms'][name]['heldout_exact'] for r in rows)
    def unresolved_total(name):return sum(r['arms'][name]['unresolved'] for r in rows)
    exacts={n:exact(n) for n in ['WARM','COLD','RAW_HISTORY','SHAM','ANCESTOR_ABLATION']}
    unresolved_totals={n:unresolved_total(n) for n in exacts}
    warm_only=[r['task'] for r in rows if r['arms']['WARM']['demo_exact'] and r['arms']['WARM']['heldout_exact'] and not any(r['arms'][n]['demo_exact'] and r['arms'][n]['heldout_exact'] for n in ['COLD','RAW_HISTORY','SHAM','ANCESTOR_ABLATION'])]
    strict=(len(rows)>0 and bool(warm_only) and exacts['WARM']>max(exacts[n] for n in exacts if n!='WARM') and unresolved_totals['WARM']<min(unresolved_totals[n] for n in unresolved_totals if n!='WARM') and not any(r['any_truncation'] for r in source_rows))
    result={'schema':'verified-developmental-navigation.arc-cross-episode-policy-transfer.v20',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{'source_tasks':SOURCE_TASKS,'target_selection':'lexicographic evaluation IDs excluding source; first six among first 80 scanned with nontrivial verifier future split, full V17 cumulative-language sufficiency on demo+heldout, and no continuation truncation','target_episodes':TARGET_EPISODES,'max_scan':MAX_SCAN,'max_queries':MAX_QUERIES,'transfer_object':'mean certified residual-separation score by mechanically anonymized executable observation-program fingerprint','fingerprint':'erase demo/row/column indices only; preserve executable opcode/relation structure','arms':['WARM','COLD','RAW_HISTORY','SHAM','ANCESTOR_ABLATION'],'strict_gate':'at least one WARM-only exact target; WARM exact count exceeds every control; WARM total unresolved pairs below every control; no source truncation'},
      'source_rows':source_rows,'sham_source_rows':sham_source_rows,'scanned':scanned,'eligible_targets':[x[0] for x in targets],'tasks':rows,
      'summary':{'exact_tasks':exacts,'unresolved_totals':unresolved_totals,'warm_only_exact_targets':warm_only},
      'strict_gate':'PASS_CROSS_EPISODE_DEVELOPMENTAL_COMPOUNDING' if strict else 'FAIL_CROSS_EPISODE_DEVELOPMENTAL_COMPOUNDING',
      'claim_boundary':'Prospective source-distinct ARC policy transfer under a frozen low-level observation language and query budget. It is a policy/discovery claim, not constructor-language invention.'}
    out=HERE/'results_v20_cross_episode_policy_transfer';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
