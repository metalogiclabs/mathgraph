import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v13=load('v13','run_v13_groundup_future_quotient.py')
v14=load('v14','run_v14_demo_indexed_future_quotient.py')
v15=load('v15','run_v15_context_generated_future_quotient.py')
v16=load('v16','run_v16_embedding_context_future_quotient.py')

# V17 fixes a developmental-protocol error: V14/V15/V16 tested replacement
# vocabularies. Development should retain lawful earlier observations and add the
# smallest licensed extension. No new observation type is introduced here.

def states_for(task):
    pairs=v13.v2.v1.task_pairs(task);states=v13.first_stage_states(task)
    for s in states:
        obs={}
        for k,v in v14.demo_indexed_obs(s['tp']).items():obs['scalar:'+k]=v
        for k,v in v15.context_obs(s['tp']).items():obs['geom:'+k]=v
        for di,((orig,target),(mid,_)) in enumerate(zip(pairs,s['tp'])):
            hm,wm=v13.shape(mid)
            for gi,(gname,gfn) in enumerate(v16.GEOMS):
                q=v16.safe(gfn,orig)
                if q is None:continue
                hq,wq=v13.shape(q)
                for r in range(max(0,hm-hq+1)):
                    for c in range(max(0,wm-wq+1)):
                        obs[f'emb:d{di}:g{gi}:r{r}:c{c}']=v16.subgrid_eq(mid,q,r,c)
                occ=v16.occurrence_signature(mid,q)
                for n in range(0,5):obs[f'emb:d{di}:g{gi}:count_eq_{n}']=(len(occ)==n)
        s['obs']=obs
    keys=sorted(set().union(*(s['obs'].keys() for s in states))) if states else []
    for s in states:
        for k in keys:s['obs'].setdefault(k,False)
    return states,keys

def buckets(states,label,sub):
    b=defaultdict(list)
    for i,s in enumerate(states):b[tuple(s['obs'][k] for k in sub)].append(i)
    return b

def unresolved_pairs(states,label,sub):
    n=0
    for inds in buckets(states,label,sub).values():
        p=sum(bool(states[i][label]) for i in inds);z=len(inds)-p;n+=p*z
    return n

def sufficient(states,label,sub):return unresolved_pairs(states,label,sub)==0

def collision(states,label,keys):
    for inds in buckets(states,label,keys).values():
        labs={bool(states[i][label]) for i in inds}
        if len(labs)>1:
            p=next(states[i] for i in inds if states[i][label]);n=next(states[i] for i in inds if not states[i][label])
            return {'positive_audit':p['program_audit'],'negative_audit':n['program_audit']}
    return None

def irreducible_basis(states,keys,label):
    if not sufficient(states,label,keys):return None,'FULL_CUMULATIVE_COLLISION',collision(states,label,keys),None
    if sufficient(states,label,()):return [],'EMPTY_SUFFICIENT',None,[]
    # Deduplicate identical observational columns.
    uniq=[];seen=set()
    for k in keys:
        col=tuple(s['obs'][k] for s in states)
        if col not in seen:seen.add(col);uniq.append(k)
    chosen=[];remaining=list(uniq);trace=[];cur=unresolved_pairs(states,label,chosen)
    while cur>0:
        best=None
        for k in remaining:
            nxt=unresolved_pairs(states,label,chosen+[k]);gain=cur-nxt
            cand=(gain,-nxt,k)
            if best is None or cand>best[0]:best=(cand,k,nxt)
        if best is None or best[0][0]<=0:return None,'GREEDY_STALLED_DESPITE_FULL_SUFFICIENCY',None,trace
        _,k,nxt=best;chosen.append(k);remaining.remove(k);trace.append({'add':k,'unresolved_before':cur,'unresolved_after':nxt});cur=nxt
    # Backward ablation: remove every redundant chosen bit until inclusion-minimal.
    changed=True
    while changed:
        changed=False
        for k in list(chosen):
            trial=[x for x in chosen if x!=k]
            if sufficient(states,label,trial):chosen=trial;trace.append({'ablate_redundant':k});changed=True;break
    necessary={k:not sufficient(states,label,[x for x in chosen if x!=k]) for k in chosen}
    assert all(necessary.values())
    return chosen,'IRREDUCIBLE_FOUND',None,trace

def kind(k):return k.split(':',1)[0]

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v17_cumulative_future_quotient.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1]);rows=[]
    for tid in v13.TARGETS:
        t=ev[tid];st,keys=states_for(t)
        for s in st:
            df,hs,w,tr,trunc=v13.future_audit(t,s);s['demo_future_success']=df;s['heldout_success']=hs;s['truncated']=trunc
        bd,sd,cd,td=irreducible_basis(st,keys,'demo_future_success')
        bh,sh,ch,th=irreducible_basis(st,keys,'heldout_success')
        rows.append({'task':tid,'states':len(st),'cumulative_bits':len(keys),
          'demo_future_positive':sum(s['demo_future_success'] for s in st),'heldout_future_positive':sum(s['heldout_success'] for s in st),
          'demo_status':sd,'demo_basis':bd,'demo_basis_size':None if bd is None else len(bd),'demo_basis_kinds':None if bd is None else [kind(k) for k in bd],'demo_collision':cd,'demo_trace':td,
          'heldout_status':sh,'heldout_basis':bh,'heldout_basis_size':None if bh is None else len(bh),'heldout_basis_kinds':None if bh is None else [kind(k) for k in bh],'heldout_collision':ch,'heldout_trace':th,
          'any_truncation':any(s['truncated'] for s in st)})
    result={'schema':'verified-developmental-navigation.arc-cumulative-future-quotient.v17b',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'frozen_targets':v13.TARGETS,
      'correction':'V14-V16 replacement vocabularies were diagnostic probes. V17 restores developmental persistence: each lawful prior observation language is retained and later languages are additive.',
      'basis_guarantee':'Each reported basis is sufficient and inclusion-minimal by exhaustive single-feature ablation; global cardinality minimality is not claimed.',
      'new_concepts_added':False,
      'cumulative_languages':['demo-indexed scalar relations','primitive geometric equality contexts','raw transformed-input embedding offsets/counts'],
      'tasks':rows,
      'decision':'CUMULATIVE_IRREDUCIBLE_BASIS_ALL_TASKS' if all(r['demo_basis'] is not None for r in rows) else 'CUMULATIVE_LANGUAGE_EXHAUSTED_ON_AT_LEAST_ONE_TASK'}
    out=HERE/'results_v17_cumulative_future_quotient';out.mkdir(exist_ok=True)
    (out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
