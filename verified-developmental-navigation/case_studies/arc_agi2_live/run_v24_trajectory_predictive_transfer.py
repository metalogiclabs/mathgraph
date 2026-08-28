import importlib.util
import itertools
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v23=load('v23','run_v23_source_trained_method_transfer.py')
v19=v23.v19
v13=v23.v13
SOURCE=v23.SOURCE
TARGET=v23.TARGET
METHODS=v23.METHODS
MAXQ=v23.MAXQ

# V24 changes only how the retained method is learned from source experience.
# Target query ranking remains the same frozen V23 method language.

def best_one_step_after(states,keys,chosen,current,labels):
    vals=[]
    for k in keys:
        if k in chosen or not v19.separates(states,k,current):continue
        vals.append(v19.unresolved(states,chosen+[k],labels))
    return min(vals) if vals else v19.unresolved(states,chosen,labels)

def run_predictive(states,keys,labels,method,sham=False):
    chosen=[];hist=[];trace=[]
    import random
    rng=random.Random(v23.SHAM_SEED+len(states));perm=list(range(len(states)));rng.shuffle(perm)
    total_regret=0;total_contraction=0;oracle_contraction=0
    for qi in range(MAXQ):
        before=v19.unresolved(states,chosen,labels)
        if before==0:break
        cur=v19.collision(states,chosen,labels)
        if cur is None:break
        hist.append(cur)
        score_hist=[(perm[a],perm[b]) for a,b in hist] if sham else list(hist)
        k,f=v23.choose(states,keys,chosen,cur,score_hist,method)
        if k is None:break
        best_after=best_one_step_after(states,keys,chosen,cur,labels)
        chosen.append(k)
        after=v19.unresolved(states,chosen,labels)
        regret=after-best_after
        contraction=before-after
        best_contraction=before-best_after
        total_regret+=regret;total_contraction+=contraction;oracle_contraction+=best_contraction
        trace.append({'q':qi+1,'atom':k,'features':f,'unresolved_before':before,'unresolved_after':after,
                      'best_one_step_after':best_after,'one_step_regret':regret,
                      'realized_contraction':contraction,'best_available_contraction':best_contraction})
    return chosen,trace,{'total_regret':total_regret,'realized_contraction':total_contraction,'oracle_available_contraction':oracle_contraction}

def source_predictive_score(ev,method,sham=False):
    rows=[];exact=held=0;cost=regret=0;realized=oracle=0;trunc=False
    for tid in SOURCE:
        states,keys,demo,heldlabels=v23.prepare(ev[tid])
        ch,tr,metrics=run_predictive(states,keys,demo,method,sham)
        ex=v19.sufficient(states,ch,demo);hx=v19.sufficient(states,ch,heldlabels)
        exact+=int(ex);held+=int(hx);cost+=len(ch) if ex else MAXQ+1
        regret+=metrics['total_regret'];realized+=metrics['realized_contraction'];oracle+=metrics['oracle_available_contraction']
        trunc|=any(s['truncated'] for s in states)
        rows.append({'task':tid,'queries':len(ch),'exact':ex,'heldout_exact':hx,**metrics})
    # Primary: fit source futures; then minimize one-step predictive regret; then held-out
    # and total query cost. Target is never consulted.
    score=(exact,-regret,held,-cost,realized)
    return score,rows,trunc,{'exact':exact,'heldout_exact':held,'total_regret':regret,'total_cost':cost,
                             'realized_contraction':realized,'oracle_available_contraction':oracle}

def select_method(ev,sham=False):
    best=None
    for m in METHODS:
        score,rows,trunc,agg=source_predictive_score(ev,m,sham)
        cand=(score,m)
        if best is None or cand>best[0]:best=(cand,m,score,rows,trunc,agg)
    return {'method':best[1],'score':best[2],'rows':best[3],'truncated':best[4],'aggregate':best[5]}

def target_arm(states,keys,demo,held,method):
    ch,tr,metrics=run_predictive(states,keys,demo,method,False)
    return {'queries':len(ch),'demo_exact':v19.sufficient(states,ch,demo),'heldout_exact':v19.sufficient(states,ch,held),
            'unresolved':v19.unresolved(states,ch,demo),'predictive_metrics':metrics,'trace':tr}

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v24_trajectory_predictive_transfer.py EVAL')
    ev=v13.v2.v1.load_tasks(sys.argv[1])
    warm=select_method(ev,False);sham=select_method(ev,True)
    states,keys,demo,held=v23.prepare(ev[TARGET])
    arms={}
    arms['WARM']=target_arm(states,keys,demo,held,warm['method'])
    arms['SHAM_METHOD']=target_arm(states,keys,demo,held,sham['method'])
    cc,ct=v19.run_history(states,keys,demo,False)
    cold={'queries':len(cc),'demo_exact':v19.sufficient(states,cc,demo),'heldout_exact':v19.sufficient(states,cc,held),
          'unresolved':v19.unresolved(states,cc,demo),'trace':ct}
    arms['COLD']=cold
    arms['ABLATION']=dict(cold)
    # Literal source atoms control, using only the WARM source trajectories.
    source_atoms=[]
    for tid in SOURCE:
        st,ke,la,_=v23.prepare(ev[tid]);ch,_,_=run_predictive(st,ke,la,warm['method'],False);source_atoms.extend(ch)
    rc,rt=v23.raw_replay(states,keys,demo,source_atoms)
    arms['RAW_HISTORY']={'queries':len(rc),'demo_exact':v19.sufficient(states,rc,demo),'heldout_exact':v19.sufficient(states,rc,held),
                         'unresolved':v19.unresolved(states,rc,demo),'trace':rt}
    w=arms['WARM'];controls=[arms[x] for x in ('COLD','RAW_HISTORY','SHAM_METHOD','ABLATION')]
    strict=w['demo_exact'] and w['heldout_exact'] and all((not c['demo_exact']) or w['queries']<c['queries'] for c in controls) \
           and not any(s['truncated'] for s in states) and not warm['truncated'] and warm['method']!=sham['method']
    result={'schema':'verified-developmental-navigation.arc-trajectory-predictive-transfer.v24',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{'source_tasks':SOURCE,'target_task':TARGET,'target_selection':'frozen blind V22 frontier task; COLD 6 vs oracle 3',
        'target_used_for_method_selection':False,'method_language':'unchanged V23: 24 lexicographic permutations of four generic residual-geometry features',
        'learning_signal':'source-only accumulated one-step predictive regret against best available separator for each verifier-returned residual',
        'selection_order':['source exact tasks','minimum total one-step regret','source heldout exact tasks','minimum total query cost','realized contraction'],
        'sham':'identical learner and predictive-regret scoring with deterministic index-permuted source residual histories',
        'arms':['WARM','COLD','RAW_HISTORY','SHAM_METHOD','ABLATION'],'max_queries':MAXQ},
      'warm_source_selection':warm,'sham_source_selection':sham,
      'target':{'task':TARGET,'states':len(states),'future_positive':sum(demo),'candidate_programs':len(keys),'any_truncation':any(s['truncated'] for s in states),'arms':arms},
      'strict_gate':'PASS_TRAJECTORY_PREDICTIVE_SOURCE_DISTINCT_COMPOUNDING' if strict else 'FAIL_TRAJECTORY_PREDICTIVE_SOURCE_DISTINCT_COMPOUNDING',
      'claim_boundary':'Tests whether verified source residual trajectories identify a transferable query-ranking method beyond a corrupted-history control, inside frozen V17 observation and V13 continuation languages. No target labels enter source method selection.'}
    out=HERE/'results_v24_trajectory_predictive_transfer';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
