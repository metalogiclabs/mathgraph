import importlib.util
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

v28=load('v28','run_v28_reusable_observation_transfer.py')
v27,v23,v19,v13=v28.v27,v28.v23,v28.v19,v28.v13
v21=load('v21','run_v21_transfer_frontier_census.py')
SOURCE=tuple(v28.SOURCE)
MAXQ=v28.MAXQ

# V31 selects a fresh ARC training target before either true or sham source memory
# is evaluated. Selection uses only the frozen pre-WARM frontier criterion from V22:
# positive protected future support, exact oracle, no truncation, and COLD>oracle.
# Among eligible tasks choose maximum headroom, then fewer oracle queries, then task id.

def select_target(pool):
    rows=[]
    excluded=set(SOURCE)|{v28.TARGET}
    for tid in sorted(pool):
        if tid in excluded: continue
        try: r=v21.audit_task(tid,pool[tid])
        except Exception as e:
            rows.append({'task':tid,'status':'UNSUPPORTED','error':type(e).__name__+': '+str(e)[:160]});continue
        rows.append(r)
    audited=[r for r in rows if r.get('status')=='AUDITED']
    eligible=[r for r in audited if r.get('future_positive',0)>0 and r.get('oracle',{}).get('exact') and not r.get('any_truncation') and (r.get('headroom_queries') or 0)>0]
    eligible=sorted(eligible,key=lambda r:(-r['headroom_queries'],r['oracle']['queries'],r['task']))
    return (eligible[0] if eligible else None), rows, eligible

def compact(a):
    return {k:a[k] for k in ('queries','demo_exact','heldout_exact','unresolved','transfer_hits')}

def main():
    if len(sys.argv)!=3: raise SystemExit('usage: run_v31_blind_fresh_target_transfer.py EVAL TRAIN')
    eval_tasks=v13.v2.v1.load_tasks(sys.argv[1])
    train_tasks=v13.v2.v1.load_tasks(sys.argv[2])

    chosen,census,eligible=select_target(train_tasks)
    if chosen is None:
        result={'schema':'verified-developmental-navigation.arc-blind-fresh-target-transfer.v31','strict_gate':'NO_FRESH_TRAIN_FRONTIER','summary':{'audited':sum(r.get('status')=='AUDITED' for r in census),'eligible':0}}
        out=HERE/'results_v31_blind_fresh_target_transfer';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True));return

    target=chosen['task']
    # Source learning remains exactly V27/V28 and uses only the original evaluation source tasks.
    true_model=v27.learn_quotient(eval_tasks,sham=False)
    sham_model=v27.learn_quotient(eval_tasks,sham=True)
    true_atoms=list(true_model['source_atoms']);sham_atoms=list(sham_model['source_atoms'])

    states,keys,demo,held=v23.prepare(train_tasks[target])
    warm=v28.make_arm(states,keys,demo,held,true_atoms)
    sham=v28.make_arm(states,keys,demo,held,sham_atoms)
    cc,ct=v19.run_history(states,keys,demo,False)
    cold=v27.arm(states,cc,ct,0,demo,held)
    arms={'WARM_TRUE_SOURCE_ATOMS':warm,'SHAM_SOURCE_ATOMS':sham,'COLD':cold,'ABLATION':dict(cold)}

    strict=(warm['transfer_hits']>0 and warm['demo_exact'] and warm['heldout_exact'] and
            all((not arms[x]['demo_exact']) or warm['queries']<arms[x]['queries'] for x in ('SHAM_SOURCE_ATOMS','COLD','ABLATION')) and
            not true_model['truncated'] and not sham_model['truncated'] and not any(s['truncated'] for s in states))
    if warm['transfer_hits']==0: decision='NO_TRUE_SOURCE_ATOM_SUPPORT_ON_FRESH_TARGET'
    elif strict: decision='PASS_BLIND_FRESH_TARGET_CAUSAL_TRANSFER'
    elif warm['queries']<cold['queries'] and warm['queries']==sham['queries']: decision='FRESH_TRANSFER_GAIN_NOT_SOURCE_CAUSAL'
    elif warm['queries']<cold['queries'] and warm['queries']>sham['queries']: decision='FRESH_SHAM_OUTPERFORMS_TRUE_SOURCE'
    else: decision='FAIL_BLIND_FRESH_TARGET_CAUSAL_TRANSFER'

    result={
      'schema':'verified-developmental-navigation.arc-blind-fresh-target-transfer.v31',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{
        'source_tasks':SOURCE,'source_split':'evaluation','target_split':'training','previous_target_excluded':v28.TARGET,
        'target_selection':'before WARM/SHAM evaluation: maximum frozen V22 COLD-minus-oracle headroom; tie fewer oracle queries then lexicographic task id',
        'eligibility':'AUDITED, future_positive>0, oracle exact, no truncation, COLD>oracle',
        'candidate_language':'unchanged V17 observation language and V13 continuation language',
        'source_learner':'exactly V27/V28','target_rule':'exactly V28 retained-literal-first then frozen V19 fallback','max_queries':MAXQ,
        'target_used_for_source_atom_selection':False,'warm_or_sham_used_for_target_selection':False,
      },
      'blind_census':{'pool':len(train_tasks),'audited':sum(r.get('status')=='AUDITED' for r in census),'eligible_count':len(eligible),'selected_frontier':{k:chosen.get(k) for k in ('task','states','future_positive','headroom_queries','cold','oracle')}},
      'target':{'task':target,'states':len(states),'future_positive':sum(demo),'candidate_programs':len(keys),'true_source_literal_support':len(set(true_atoms)&set(keys)),'sham_source_literal_support':len(set(sham_atoms)&set(keys)),'arms':{k:compact(v) for k,v in arms.items()}},
      'strict_gate':decision,
      'claim_boundary':'First target in this lineage selected from a fresh ARC split by a frozen pre-WARM headroom rule before true/sham memory evaluation. Tests source-distinct causal transfer of executable observations; it does not yet test broad multi-target generalization or blind target-relative V30 subset recompression.'
    }
    out=HERE/'results_v31_blind_fresh_target_transfer';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__': main()
