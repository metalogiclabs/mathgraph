import hashlib
import importlib.util
import itertools
import json
import random
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v19=load('v19','run_v19_residual_history_policy.py')
v18=v19.v18
v17=v19.v17
v13=v19.v13
MAXQ=v19.MAX_QUERIES
SOURCE=tuple(v13.TARGETS)
TARGET='60c09cac'  # frozen by blind V22 census before WARM method evaluation
SHAM_SEED=20260828

FEATURES=('history_support','history_diversity','bucket_balance','global_balance')
# Fixed, small method language: lexicographic orderings of generic verifier-local geometry.
METHODS=tuple(itertools.permutations(FEATURES))

def prepare(task):
    states,keys=v17.states_for(task)
    for s in states:
        df,hs,w,tr,trunc=v13.future_audit(task,s)
        s['demo']=bool(df);s['held']=bool(hs);s['truncated']=bool(trunc)
    return states,keys,[s['demo'] for s in states],[s['held'] for s in states]

def feature_map(states,k,chosen,current,history):
    hs=sum(v19.separates(states,k,p) for p in history)
    sig=tuple((bool(states[a]['obs'][k]),bool(states[b]['obs'][k])) for a,b in history)
    hd=len(set(sig))
    # Current quotient bucket is observable from already chosen questions; labels are not used.
    a,_=current
    cur_sig=tuple(bool(states[a]['obs'][q]) for q in chosen)
    inds=[i for i,s in enumerate(states) if tuple(bool(s['obs'][q]) for q in chosen)==cur_sig]
    b1=sum(bool(states[i]['obs'][k]) for i in inds);b0=len(inds)-b1
    gb1=sum(bool(s['obs'][k]) for s in states);gb0=len(states)-gb1
    return {'history_support':hs,'history_diversity':hd,'bucket_balance':b0*b1,'global_balance':gb0*gb1}

def choose(states,keys,chosen,current,history,method):
    best=None
    for k in keys:
        if k in chosen or not v19.separates(states,k,current):continue
        f=feature_map(states,k,chosen,current,history)
        score=tuple(f[x] for x in method)+(hashlib.sha256(k.encode()).hexdigest(),)
        if best is None or score>best[0]:best=(score,k,f)
    return (best[1],best[2]) if best else (None,None)

def run(states,keys,labels,method,sham=False):
    chosen=[];hist=[];trace=[]
    rng=random.Random(SHAM_SEED+len(states));perm=list(range(len(states)));rng.shuffle(perm)
    for qi in range(MAXQ):
        before=v19.unresolved(states,chosen,labels)
        if before==0:break
        cur=v19.collision(states,chosen,labels)
        if cur is None:break
        hist.append(cur)
        score_hist=[(perm[a],perm[b]) for a,b in hist] if sham else list(hist)
        k,f=choose(states,keys,chosen,cur,score_hist,method)
        if k is None:break
        chosen.append(k)
        trace.append({'q':qi+1,'atom':k,'features':f,'unresolved_before':before,'unresolved_after':v19.unresolved(states,chosen,labels)})
    return chosen,trace

def source_score(ev,method,sham=False):
    rows=[];exact=0;cost=0;held=0;trunc=False
    for tid in SOURCE:
        states,keys,demo,heldlabels=prepare(ev[tid]);ch,tr=run(states,keys,demo,method,sham)
        ex=v19.sufficient(states,ch,demo);hx=v19.sufficient(states,ch,heldlabels)
        exact+=int(ex);held+=int(hx);cost+=len(ch) if ex else MAXQ+1;trunc|=any(s['truncated'] for s in states)
        rows.append({'task':tid,'queries':len(ch),'exact':ex,'heldout_exact':hx})
    return (exact,held,-cost),rows,trunc

def select_method(ev,sham=False):
    best=None
    for m in METHODS:
        score,rows,trunc=source_score(ev,m,sham)
        # deterministic source-only selection; method tuple breaks exact ties.
        cand=(score,m)
        if best is None or cand>best[0]:best=(cand,m,score,rows,trunc)
    return {'method':best[1],'score':best[2],'rows':best[3],'truncated':best[4]}

def raw_replay(states,keys,labels,source_atoms):
    # Literal source atoms are intentionally useless if names do not exist on target;
    # after attempted replay, fall back to V19 COLD. This tests structure vs memorized IDs.
    chosen=[k for k in source_atoms if k in keys]
    if v19.sufficient(states,chosen,labels):return chosen,[]
    cold,tr=v19.run_history(states,keys,labels,False)
    return cold,[{'raw_matches':len(chosen),'fallback':'V19_COLD'}]+tr

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v23_source_trained_method_transfer.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1])
    warm=select_method(ev,False);sham=select_method(ev,True)
    # source literal atoms from the winning warm method, retained only for RAW control
    source_atoms=[]
    for tid in SOURCE:
        st,ke,la,_=prepare(ev[tid]);ch,_=run(st,ke,la,warm['method'],False);source_atoms.extend(ch)
    states,keys,demo,held=prepare(ev[TARGET])
    arms={}
    wc,wt=run(states,keys,demo,warm['method'],False)
    sc,st=run(states,keys,demo,sham['method'],False)
    cc,ct=v19.run_history(states,keys,demo,False)
    rc,rt=raw_replay(states,keys,demo,source_atoms)
    ac,at=v19.run_history(states,keys,demo,False)
    for name,ch,tr in [('WARM',wc,wt),('COLD',cc,ct),('RAW_HISTORY',rc,rt),('SHAM_METHOD',sc,st),('ABLATION',ac,at)]:
        arms[name]={'queries':len(ch),'demo_exact':v19.sufficient(states,ch,demo),'heldout_exact':v19.sufficient(states,ch,held),'unresolved':v19.unresolved(states,ch,demo),'trace':tr}
    w=arms['WARM'];controls=[arms[x] for x in ('COLD','RAW_HISTORY','SHAM_METHOD','ABLATION')]
    strict=w['demo_exact'] and w['heldout_exact'] and all((not c['demo_exact']) or w['queries']<c['queries'] for c in controls) and not any(s['truncated'] for s in states) and not warm['truncated']
    result={'schema':'verified-developmental-navigation.arc-source-trained-method-transfer.v23',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{'source_tasks':SOURCE,'target_task':TARGET,'target_selection':'blind V22 full-evaluation census: unique positive-support task with COLD 6 vs oracle 3','target_used_for_method_selection':False,'method_language':'24 lexicographic permutations of four generic residual-geometry features','features':FEATURES,'max_queries':MAXQ,'arms':['WARM','COLD','RAW_HISTORY','SHAM_METHOD','ABLATION']},
      'warm_source_selection':warm,'sham_source_selection':sham,'target':{'task':TARGET,'states':len(states),'future_positive':sum(demo),'candidate_programs':len(keys),'any_truncation':any(s['truncated'] for s in states),'arms':arms},
      'strict_gate':'PASS_SOURCE_DISTINCT_METHOD_COMPOUNDING' if strict else 'FAIL_SOURCE_DISTINCT_METHOD_COMPOUNDING',
      'claim_boundary':'Tests transfer of a source-trained query-ranking method to one independently selected ARC evaluation task inside the frozen V17 observation and V13 continuation languages. It does not establish unrestricted feature invention or broad ARC generalization.'}
    out=HERE/'results_v23_source_trained_method_transfer';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
