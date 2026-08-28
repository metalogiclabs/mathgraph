import importlib.util
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v25=load('v25','run_v25_state_conditioned_method.py')
v24=v25.v24
v23=v25.v23
v21=load('v21','run_v21_transfer_frontier_census.py')
v19=v25.v19
v13=v25.v13
SOURCE=set(v25.SOURCE)
MAX_STATES=160

# V26 does not change the learner. It freezes the V25 policies from the four
# source tasks, then selects a target panel independently using only the
# pre-existing COLD-vs-oracle frontier criterion.

def prepare_task(task):
    states,keys=v21.v17.states_for(task)
    if not states:return None,None,None,None,'NO_STATES'
    if len(states)>MAX_STATES:return None,None,None,None,'STATE_CAP'
    for s in states:
        df,hs,w,tr,trunc=v13.future_audit(task,s)
        s['demo']=bool(df);s['held']=bool(hs);s['truncated']=bool(trunc)
    demo=[s['demo'] for s in states];held=[s['held'] for s in states]
    if not v19.sufficient(states,keys,demo):return states,keys,demo,held,'FULL_LANGUAGE_COLLISION'
    return states,keys,demo,held,'AUDITED'

def frontier_row(split,tid,task):
    try:
        states,keys,demo,held,status=prepare_task(task)
        if status!='AUDITED':
            return {'split':split,'task':tid,'status':status,'states':len(states) if states else 0}
        cold,_=v19.run_history(states,keys,demo,False)
        oracle,_=v21.v18.run_oracle(states,keys,demo)
        ce=v19.sufficient(states,cold,demo);oe=v19.sufficient(states,oracle,demo)
        effective=len(cold) if ce else v19.MAX_QUERIES+1
        headroom=effective-len(oracle) if oe else None
        return {'split':split,'task':tid,'status':'AUDITED','states':len(states),'candidate_programs':len(keys),
          'future_positive':sum(demo),'any_truncation':any(s['truncated'] for s in states),
          'cold_exact':ce,'cold_queries':len(cold),'cold_heldout_exact':v19.sufficient(states,cold,held),
          'oracle_exact':oe,'oracle_queries':len(oracle),'headroom_queries':headroom}
    except Exception as e:
        return {'split':split,'task':tid,'status':'UNSUPPORTED','error':type(e).__name__+': '+str(e)[:240]}

def raw_source_atoms(eval_tasks,warm_policy):
    atoms=[]
    for tid in sorted(SOURCE):
        st,ke,la,_=v23.prepare(eval_tasks[tid])
        ch,_,_=v25.run_policy(st,ke,la,warm_policy,False)
        atoms.extend(ch)
    return atoms

def eval_panel_task(task,warm_policy,sham_policy,source_atoms):
    states,keys,demo,held,status=prepare_task(task)
    assert status=='AUDITED'
    warm=v25.arm(states,keys,demo,held,warm_policy)
    sham=v25.arm(states,keys,demo,held,sham_policy)
    cc,ct=v19.run_history(states,keys,demo,False)
    cold={'queries':len(cc),'demo_exact':v19.sufficient(states,cc,demo),'heldout_exact':v19.sufficient(states,cc,held),'unresolved':v19.unresolved(states,cc,demo)}
    rc,rt=v23.raw_replay(states,keys,demo,source_atoms)
    raw={'queries':len(rc),'demo_exact':v19.sufficient(states,rc,demo),'heldout_exact':v19.sufficient(states,rc,held),'unresolved':v19.unresolved(states,rc,demo)}
    return {'WARM':warm,'SHAM_POLICY':sham,'COLD':cold,'RAW_HISTORY':raw,'ABLATION':dict(cold)}

def eff(a):
    return a['queries'] if a['demo_exact'] else v19.MAX_QUERIES+1

def main():
    if len(sys.argv)!=2:raise SystemExit('usage run_v26_frozen_policy_target_panel.py ARC_DATA_ROOT')
    root=Path(sys.argv[1])
    train=v13.v2.v1.load_tasks(root/'training')
    ev=v13.v2.v1.load_tasks(root/'evaluation')

    # Freeze the two V25 learned policies before any target-panel selection.
    real_ex,_,real_trunc=v25.canonical_examples(ev,False)
    sham_ex,_,sham_trunc=v25.canonical_examples(ev,True)
    warm_policy=v25.train_stump(real_ex)
    sham_policy=v25.train_stump(sham_ex)
    source_atoms=raw_source_atoms(ev,warm_policy)

    rows=[]
    for split,tasks in [('training',train),('evaluation',ev)]:
        for tid in sorted(tasks):
            if tid in SOURCE:continue
            rows.append(frontier_row(split,tid,tasks[tid]))

    eligible=[r for r in rows if r.get('status')=='AUDITED' and r.get('future_positive',0)>0 and r.get('oracle_exact') and not r.get('any_truncation') and (r.get('headroom_queries') or 0)>0]
    eligible=sorted(eligible,key=lambda r:(r['split'],r['task']))

    panel=[]
    for r in eligible:
        task=(train if r['split']=='training' else ev)[r['task']]
        arms=eval_panel_task(task,warm_policy,sham_policy,source_atoms)
        panel.append({**r,'arms':arms})

    names=['WARM','SHAM_POLICY','COLD','RAW_HISTORY','ABLATION']
    totals={n:sum(eff(p['arms'][n]) for p in panel) for n in names}
    exact={n:sum(int(p['arms'][n]['demo_exact'] and p['arms'][n]['heldout_exact']) for p in panel) for n in names}
    pairwise={'warm_better_sham':sum(eff(p['arms']['WARM'])<eff(p['arms']['SHAM_POLICY']) for p in panel),
              'warm_equal_sham':sum(eff(p['arms']['WARM'])==eff(p['arms']['SHAM_POLICY']) for p in panel),
              'warm_worse_sham':sum(eff(p['arms']['WARM'])>eff(p['arms']['SHAM_POLICY']) for p in panel)}

    strict=bool(panel) and not real_trunc and not sham_trunc and warm_policy!=sham_policy \
      and exact['WARM']==len(panel) \
      and totals['WARM']<totals['SHAM_POLICY'] \
      and totals['WARM']<totals['COLD'] \
      and totals['WARM']<totals['RAW_HISTORY'] \
      and totals['WARM']<totals['ABLATION']

    result={'schema':'verified-developmental-navigation.arc-frozen-policy-target-panel.v26',
      'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
      'precommit':{'source_tasks':sorted(SOURCE),'policy_source':'V25 learner unchanged; WARM and SHAM policies frozen before panel census',
        'candidate_pool':'all ARC training + evaluation tasks excluding four V25 source task IDs',
        'panel_selection':'positive future support, full frozen V17 observation language sufficient, exact V18 oracle, no truncation, strict V19 COLD > oracle query headroom',
        'warm_or_sham_used_for_panel_selection':False,'max_states':MAX_STATES,'max_queries':v19.MAX_QUERIES,
        'strict_gate':'WARM exact on every panel task and aggregate effective query cost strictly below SHAM, COLD, RAW_HISTORY, and ABLATION'},
      'frozen_policies':{'WARM':warm_policy,'SHAM_POLICY':sham_policy,'different':warm_policy!=sham_policy},
      'census_summary':{'pool':len(rows),'audited':sum(r.get('status')=='AUDITED' for r in rows),'positive_support':sum(r.get('status')=='AUDITED' and r.get('future_positive',0)>0 for r in rows),'eligible_panel':len(eligible),'unsupported':sum(r.get('status')=='UNSUPPORTED' for r in rows),'state_capped':sum(r.get('status')=='STATE_CAP' for r in rows),'full_language_collisions':sum(r.get('status')=='FULL_LANGUAGE_COLLISION' for r in rows)},
      'eligible_targets':[{'split':r['split'],'task':r['task'],'states':r['states'],'future_positive':r['future_positive'],'cold_queries':r['cold_queries'],'oracle_queries':r['oracle_queries'],'headroom_queries':r['headroom_queries']} for r in eligible],
      'panel':panel,'aggregate':{'effective_query_cost':totals,'exact_demo_and_heldout':exact,**pairwise},
      'strict_gate':'PASS_FROZEN_POLICY_SOURCE_DISTINCT_PANEL_COMPOUNDING' if strict else 'FAIL_FROZEN_POLICY_SOURCE_DISTINCT_PANEL_COMPOUNDING',
      'claim_boundary':'Tests systematic source-distinct transfer of the already-frozen V25 state-conditioned policy over an independently selected ARC target panel. Panel membership is determined without WARM or SHAM performance.'}
    out=HERE/'results_v26_frozen_policy_target_panel';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
