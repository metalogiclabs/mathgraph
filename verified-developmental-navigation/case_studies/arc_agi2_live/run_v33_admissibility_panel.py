import importlib.util, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def load(name,file):
    sp=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
v31=load('v31','run_v31_blind_fresh_target_transfer.py')
v32=load('v32','run_v32_transfer_admissibility_gate.py')
v28=v31.v28; v27=v31.v27; v23=v31.v23; v19=v31.v19; v13=v31.v13
MAXQ=v28.MAXQ

def compact(a):
    return {k:a[k] for k in ('queries','demo_exact','heldout_exact','unresolved','transfer_hits') if k in a}

def main():
    if len(sys.argv)!=3: raise SystemExit('usage: run_v33_admissibility_panel.py EVAL TRAIN')
    eval_tasks=v13.v2.v1.load_tasks(sys.argv[1]); train_tasks=v13.v2.v1.load_tasks(sys.argv[2])
    chosen,census,eligible=v31.select_target(train_tasks)
    # Freeze source memories/gates once, before panel evaluation.
    true_model=v27.learn_quotient(eval_tasks,sham=False)
    sham_model=v27.learn_quotient(eval_tasks,sham=True)
    true_atoms=list(true_model['source_atoms']); sham_atoms=list(sham_model['source_atoms'])
    true_profiles=v32.learn_source_profiles(eval_tasks, sham=False)
    sham_profiles=v32.learn_source_profiles(eval_tasks, sham=True)

    rows=[]
    for r in eligible:
        tid=r['task']
        states,keys,demo,held=v23.prepare(train_tasks[tid])
        wc,wt,wh,wr=v32.run_gated(states,keys,demo,true_atoms,true_profiles)
        warm_g=v32.arm(states,wc,wt,wh,wr,demo,held)
        sc,st,sh,sr=v32.run_gated(states,keys,demo,sham_atoms,sham_profiles)
        sham_g=v32.arm(states,sc,st,sh,sr,demo,held)
        warm_u=v28.make_arm(states,keys,demo,held,true_atoms)
        cc,ct=v19.run_history(states,keys,demo,False)
        cold=v27.arm(states,cc,ct,0,demo,held)
        rows.append({'task':tid,'frontier_headroom':r['headroom_queries'],'oracle_queries':r['oracle']['queries'],
                     'WARM_GATED':compact(warm_g),'WARM_UNGATED':compact(warm_u),'SHAM_GATED':compact(sham_g),'COLD':compact(cold)})

    def summary(name):
        xs=[x[name] for x in rows]
        return {'exact':sum(bool(a['demo_exact'] and a['heldout_exact']) for a in xs),
                'mean_queries':sum(a['queries'] for a in xs)/len(xs) if xs else None,
                'total_unresolved':sum(a['unresolved'] for a in xs),
                'total_transfer_hits':sum(a.get('transfer_hits',0) for a in xs)}
    sums={k:summary(k) for k in ('WARM_GATED','WARM_UNGATED','SHAM_GATED','COLD')}
    improved_vs_ungated=sum((x['WARM_GATED']['demo_exact'] and x['WARM_GATED']['heldout_exact']) and not (x['WARM_UNGATED']['demo_exact'] and x['WARM_UNGATED']['heldout_exact']) for x in rows)
    harmed_vs_ungated=sum((x['WARM_UNGATED']['demo_exact'] and x['WARM_UNGATED']['heldout_exact']) and not (x['WARM_GATED']['demo_exact'] and x['WARM_GATED']['heldout_exact']) for x in rows)
    strict=(sums['WARM_GATED']['exact']>sums['WARM_UNGATED']['exact'] and sums['WARM_GATED']['exact']>sums['SHAM_GATED']['exact'] and sums['WARM_GATED']['exact']>sums['COLD']['exact'] and harmed_vs_ungated==0)
    decision='PASS_PANEL_TRANSFER_ADMISSIBILITY' if strict else 'FAIL_PANEL_TRANSFER_ADMISSIBILITY'
    result={'schema':'verified-developmental-navigation.arc-transfer-admissibility-panel.v33',
            'source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},
            'precommit':{'panel':'all V31-eligible training targets under exact frozen V31 eligibility','eligible_count':len(eligible),'max_queries':MAXQ,'source_memory':'exact V27/V28 true and sham atoms','gate':'exact V32 source-only balance-fraction admissibility','ungated':'exact V28 literal-first reuse','cold':'frozen V19','target_labels_used_by_gate':False},
            'summary':sums,'improved_vs_ungated_exact':improved_vs_ungated,'harmed_vs_ungated_exact':harmed_vs_ungated,'strict_gate':decision,'rows':rows,
            'claim_boundary':'Panel replication across all targets that satisfy the frozen V31 frontier eligibility rule. This is not a hidden benchmark; targets are known after V31 census, but V32 gate and source memory are frozen before panel evaluation.'}
    out=HERE/'results_v33_admissibility_panel';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__': main()
