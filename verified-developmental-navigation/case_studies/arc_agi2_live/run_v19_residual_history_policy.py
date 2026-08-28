import hashlib
import importlib.util
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v18=load('v18','run_v18_residual_induced_query_synthesis.py')
v17=v18.v17
v13=v18.v13
MAX_QUERIES=v18.MAX_QUERIES
SHUFFLE_SEED=20260828


def buckets(states, chosen):
    b=defaultdict(list)
    for i,s in enumerate(states):b[tuple(bool(s['obs'][k]) for k in chosen)].append(i)
    return b

def unresolved(states, chosen, labels):
    n=0
    for inds in buckets(states,chosen).values():
        p=sum(bool(labels[i]) for i in inds);n+=p*(len(inds)-p)
    return n

def sufficient(states,chosen,labels):return unresolved(states,chosen,labels)==0

def collision(states,chosen,labels):
    for inds in buckets(states,chosen).values():
        pos=next((i for i in inds if labels[i]),None);neg=next((i for i in inds if not labels[i]),None)
        if pos is not None and neg is not None:return (pos,neg)
    return None

def separates(states,k,pair):
    a,b=pair
    return bool(states[a]['obs'][k]) != bool(states[b]['obs'][k])

def history_atom(states,keys,chosen,current,history):
    if current is None:return None,None
    best=None
    for k in keys:
        if k in chosen or not separates(states,k,current):continue
        # Learned state is only the verifier-returned collision history.
        # Every admissible candidate separates current; rank by how often the same
        # executable predicate would also have separated prior observed residuals.
        support=sum(separates(states,k,p) for p in history)
        # Prefer predicates with distinct response signatures over the observed
        # residual history; this is still computed only from returned pairs.
        sig=tuple((bool(states[a]['obs'][k]),bool(states[b]['obs'][k])) for a,b in history)
        diversity=len(set(sig))
        tie=hashlib.sha256(k.encode()).hexdigest()
        cand=(support,diversity,tie)
        if best is None or cand>best[0]:best=(cand,k,{'history_support':support,'history_diversity':diversity})
    return (best[1],best[2]) if best else (None,None)

def run_history(states,keys,labels,sham=False):
    chosen=[];history=[];trace=[]
    # Sham mapping is frozen independently of query choices and preserves pair count.
    rng=random.Random(SHUFFLE_SEED+len(states))
    perm=list(range(len(states)));rng.shuffle(perm)
    for q in range(MAX_QUERIES):
        before=unresolved(states,chosen,labels)
        if before==0:break
        cur=collision(states,chosen,labels)
        if cur is None:break
        history.append(cur)
        hist_for_score=[(perm[a],perm[b]) for a,b in history] if sham else list(history)
        k,meta=history_atom(states,keys,chosen,cur,hist_for_score)
        if k is None:
            trace.append({'query':q+1,'status':'NO_SEPARATOR','current_pair':cur});break
        chosen.append(k);after=unresolved(states,chosen,labels)
        trace.append({'query':q+1,'current_pair':cur,'atom':k,**meta,
          'history_size':len(history),'true_unresolved_before':before,'true_unresolved_after':after})
    return chosen,trace

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v19_residual_history_policy.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1]);rows=[]
    for tid in v13.TARGETS:
        task=ev[tid];states,keys=v17.states_for(task)
        for s in states:
            df,hs,w,tr,trunc=v13.future_audit(task,s);s['demo']=bool(df);s['held']=bool(hs);s['truncated']=bool(trunc)
        demo=[s['demo'] for s in states];held=[s['held'] for s in states]
        learned,lt=run_history(states,keys,demo,False)
        sham,st=run_history(states,keys,demo,True)
        base,bt=v18.run_real_residual(states,keys,demo)
        oracle,_=v18.run_oracle(states,keys,demo)
        rows.append({'task':tid,'states':len(states),'future_positive':sum(demo),'candidate_programs':len(keys),
          'learned_history':{'queries_used':len(learned),'demo_exact':sufficient(states,learned,demo),'heldout_exact':sufficient(states,learned,held),'unresolved':unresolved(states,learned,demo),'atoms':learned,'trace':lt},
          'sham_history':{'queries_used':len(sham),'demo_exact':sufficient(states,sham,demo),'heldout_exact':sufficient(states,sham,held),'unresolved':unresolved(states,sham,demo),'atoms':sham,'trace':st},
          'v18_first_separator':{'queries_used':len(base),'demo_exact':sufficient(states,base,demo),'heldout_exact':sufficient(states,base,held),'unresolved':unresolved(states,base,demo)},
          'oracle':{'queries_used':len(oracle),'demo_exact':sufficient(states,oracle,demo),'unresolved':unresolved(states,oracle,demo)},
          'any_truncation':any(s['truncated'] for s in states)})
    L=sum(r['learned_history']['demo_exact'] for r in rows);LH=sum(r['learned_history']['heldout_exact'] for r in rows);S=sum(r['sham_history']['demo_exact'] for r in rows);B=sum(r['v18_first_separator']['demo_exact'] for r in rows)
    strict=L==4 and LH==4 and L>B and L>S and not any(r['any_truncation'] for r in rows)
    result={'schema':'verified-developmental-navigation.arc-residual-history-policy.v19',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'frozen_targets':v13.TARGETS,
      'precommit':{'max_queries_per_task':MAX_QUERIES,'candidate_language':'identical to V18/V18b','feedback':'one true unresolved positive/negative future collision per step','learned_state':'ordered history of verifier-returned collision pairs only','selection':'candidate must separate current residual; maximize number of retained prior residual pairs also separated, then residual-signature diversity, SHA256 tie-break','sham':'same algorithm with deterministic index-permuted residual history','shuffle_seed':SHUFFLE_SEED},
      'claim_boundary':'No global future labels enter query ranking. Labels are used only by the verifier to return the next unresolved collision and for post-hoc auditing.',
      'tasks':rows,'summary':{'learned_exact_tasks':L,'learned_heldout_exact_tasks':LH,'sham_exact_tasks':S,'v18_exact_tasks':B},
      'strict_gate':'PASS_RESIDUAL_HISTORY_INDUCES_QUERY_POLICY' if strict else 'FAIL_RESIDUAL_HISTORY_INDUCES_QUERY_POLICY'}
    out=HERE/'results_v19_residual_history_policy';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
