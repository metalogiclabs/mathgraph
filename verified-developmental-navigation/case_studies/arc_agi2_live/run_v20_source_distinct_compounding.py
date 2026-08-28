import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v19=load('v19','run_v19_residual_history_policy.py')
v18=v19.v18
v17=v19.v17
v13=v19.v13
MAX_QUERIES=8

# Frozen before target evaluation. Learn and transfer task IDs are disjoint.
LEARN_TARGETS=('0c786b71','59341089')
TRANSFER_TARGETS=('833dafe3','be03b35f')

# The retained object is induced only from source episodes.  It does not retain
# literal atom IDs.  Each query is represented by a source-independent response
# fingerprint over verifier-returned residual pairs: support count and ordered
# response-pair pattern.  The policy is a frequency table over such fingerprints.
def fp(states,k,history):
    sig=tuple((int(bool(states[a]['obs'][k])),int(bool(states[b]['obs'][k]))) for a,b in history)
    support=sum(x!=y for x,y in sig)
    return (support,sig)

def learn_policy(ev):
    counts=Counter();episodes=[]
    for tid in LEARN_TARGETS:
        task=ev[tid];states,keys=v17.states_for(task)
        for s in states:
            df,hs,w,tr,trunc=v13.future_audit(task,s);s['demo']=bool(df);s['truncated']=bool(trunc)
        labels=[s['demo'] for s in states];chosen=[];history=[];trace=[]
        for q in range(MAX_QUERIES):
            if v19.unresolved(states,chosen,labels)==0:break
            cur=v19.collision(states,chosen,labels)
            if cur is None:break
            history.append(cur)
            k,meta=v19.history_atom(states,keys,chosen,cur,history)
            if k is None:break
            f=fp(states,k,history);counts[f]+=1;chosen.append(k)
            trace.append({'q':q+1,'fingerprint':repr(f),'history_support':meta['history_support'],'history_diversity':meta['history_diversity']})
        episodes.append({'task':tid,'exact':v19.sufficient(states,chosen,labels),'trace':trace,'truncated':any(s['truncated'] for s in states)})
    return counts,episodes

def choose(states,keys,chosen,current,history,policy=None,ablate=False,sham=False):
    candidates=[]
    for k in keys:
        if k in chosen or not v19.separates(states,k,current):continue
        f=fp(states,k,history)
        prior=0 if policy is None or ablate else policy.get(f,0)
        if sham: prior=-prior
        support=f[0];diversity=len(set(f[1]));tie=hashlib.sha256(k.encode()).hexdigest()
        candidates.append(((prior,support,diversity,tie),k,repr(f)))
    if not candidates:return None,None
    candidates.sort(reverse=True)
    return candidates[0][1],{'prior':candidates[0][0][0],'fingerprint':candidates[0][2]}

def run_arm(states,keys,labels,policy,arm):
    chosen=[];history=[];trace=[]
    for q in range(MAX_QUERIES):
        before=v19.unresolved(states,chosen,labels)
        if before==0:break
        cur=v19.collision(states,chosen,labels)
        if cur is None:break
        history.append(cur)
        k,meta=choose(states,keys,chosen,cur,history,policy,
                      ablate=(arm in ('COLD','ABLATION')),
                      sham=(arm=='SHAM_POLICY'))
        if k is None:break
        chosen.append(k);after=v19.unresolved(states,chosen,labels)
        trace.append({'q':q+1,'atom':k,'unresolved_before':before,'unresolved_after':after,**meta})
    return chosen,trace

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v20_source_distinct_compounding.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1]);policy,learn=learn_policy(ev);rows=[]
    for tid in TRANSFER_TARGETS:
        task=ev[tid];states,keys=v17.states_for(task)
        for s in states:
            df,hs,w,tr,trunc=v13.future_audit(task,s);s['demo']=bool(df);s['held']=bool(hs);s['truncated']=bool(trunc)
        demo=[s['demo'] for s in states];held=[s['held'] for s in states]
        arms={}
        for arm in ('WARM','COLD','SHAM_POLICY','ABLATION'):
            chosen,tr=run_arm(states,keys,demo,policy,arm)
            arms[arm]={'queries_used':len(chosen),'demo_exact':v19.sufficient(states,chosen,demo),'heldout_exact':v19.sufficient(states,chosen,held),'unresolved':v19.unresolved(states,chosen,demo),'trace':tr}
        rows.append({'task':tid,'states':len(states),'candidate_programs':len(keys),'arms':arms,'any_truncation':any(s['truncated'] for s in states)})
    warm=sum(r['arms']['WARM']['demo_exact'] for r in rows);cold=sum(r['arms']['COLD']['demo_exact'] for r in rows);sham=sum(r['arms']['SHAM_POLICY']['demo_exact'] for r in rows);abl=sum(r['arms']['ABLATION']['demo_exact'] for r in rows);held=sum(r['arms']['WARM']['heldout_exact'] for r in rows)
    strict=warm>cold and warm>sham and warm>abl and held==warm and not any(r['any_truncation'] for r in rows) and not any(e['truncated'] for e in learn)
    result={'schema':'verified-developmental-navigation.arc-source-distinct-compounding.v20',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{'learn_targets':LEARN_TARGETS,'transfer_targets':TRANSFER_TARGETS,'disjoint_tasks':True,'max_queries_per_task':MAX_QUERIES,'candidate_language':'unchanged V17-V19 cumulative executable observations','retained_object':'frequency table over source-independent residual-response fingerprints; no literal atom IDs','arms':['WARM','COLD','SHAM_POLICY','ABLATION']},
      'learn_episodes':learn,'retained_policy_size':len(policy),'transfer':rows,
      'summary':{'warm_exact':warm,'warm_heldout_exact':held,'cold_exact':cold,'sham_exact':sham,'ablation_exact':abl},
      'strict_gate':'PASS_SOURCE_DISTINCT_RECURSIVE_COMPOUNDING' if strict else 'FAIL_SOURCE_DISTINCT_RECURSIVE_COMPOUNDING',
      'claim_boundary':'Tests source-distinct transfer of a verifier-induced query-policy object inside the frozen ARC carrier and observation language. It does not establish unrestricted feature invention or open-ended self-development.'}
    out=HERE/'results_v20_source_distinct_compounding';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
