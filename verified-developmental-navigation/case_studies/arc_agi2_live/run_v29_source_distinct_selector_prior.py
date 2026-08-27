"""V29: learn a selector prior from source-distinct ARC training tasks.

The seven evaluation targets are never used to score/select the prior. We scan a
bounded lexicographic prefix of ARC-AGI-2 training tasks, keep only tasks whose
V23 strict representation exactly fits demonstrations, compress them with V26,
and collect *ambiguous training episodes* where multiple matches exist but the
training output identifies at least one correct location. Each selector in the
fixed V28 family receives wins/trials on those episodes. The best empirical
selector is frozen, then used only as a fallback for ambiguous matches on the
seven known-world evaluation diagnostics.
"""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2, run_v23_trace_induced_patch as v23, run_v26_minimal_sufficient_context as v26, run_v28_learned_selector as v28

SOURCE_LIMIT=200
TARGET_IDS=sorted(v26.FIT_IDS)

def train_source_prior(tasks):
 stats={s:{'wins':0,'trials':0} for s in v28.SELECTORS if s!='unique'}
 scanned=fit_tasks=compressed=amb_eps=0
 for tid,t in sorted(tasks.items())[:SOURCE_LIMIT]:
  scanned+=1
  rs,u=v23.learn_rules(t)
  if u!=len(t['train']) or not rs:continue
  strict=[v26.initial_keep(r) for r in rs]
  if not v26.exact_train(t,rs,strict):continue
  fit_tasks+=1
  ks,_,_=v26.minimize(t,rs);compressed+=1
  for r,k in zip(rs,ks):
   for p in t['train']:
    cs=v28.candidates(p['input'],r,k)
    if len(cs)<=1:continue
    good={(a,b) for a,b,m in cs if v28.local_correct(p['input'],p['output'],r,(a,b,m))}
    if not good:continue
    amb_eps+=1
    for s in stats:
     c=v28.choose(cs,s,p['input']);stats[s]['trials']+=1
     if c is not None and (c[0],c[1]) in good:stats[s]['wins']+=1
 ranked=sorted(stats, key=lambda s:(-(stats[s]['wins']/stats[s]['trials'] if stats[s]['trials'] else -1),-stats[s]['trials'],s))
 best=ranked[0] if ranked and stats[ranked[0]]['trials'] else None
 return best,stats,{'scanned':scanned,'strict_fit_tasks':fit_tasks,'compressed_tasks':compressed,'ambiguous_episodes':amb_eps}

def prog_with_prior(rs,ks,prior):
 def f(g):
  z=[list(x) for x in g]
  for _ in range(16):
   before=tuple(map(tuple,z))
   for r,k in zip(rs,ks):
    cs=v28.candidates(z,r,k)
    c=cs[0] if len(cs)==1 else (v28.choose(cs,prior,z) if prior and len(cs)>1 else None)
    if c is None:continue
    a,b,m=c
    for i in range(r['h']):
     for j in range(r['w']):
      if r['mask'][i][j]:
       q=r['out'][i][j];z[a+i][b+j]=0 if q==0 else m.get(q,z[a+i][b+j])
   if tuple(map(tuple,z))==before:break
  return tuple(map(tuple,z))
 return f

def main():
 if len(sys.argv)!=3:raise SystemExit('usage ... TRAIN_DIR EVAL_DIR')
 train=run_v2.v1.load_tasks(sys.argv[1]);ev=run_v2.v1.load_tasks(sys.argv[2])
 prior,stats,source=train_source_prior(train);rows=[]
 for tid in TARGET_IDS:
  t=ev[tid];rs,u=v23.learn_rules(t);ks,_,_=v26.minimize(t,rs);p=prog_with_prior(rs,ks,prior)
  train_fit=run_v2.v1.exact_on_pairs(p,run_v2.v1.task_pairs(t))
  solved=False
  try:solved=bool(train_fit and run_v2.v1.task_solved(p,t))
  except Exception:pass
  rows.append({'task':tid,'train_fit':train_fit,'heldout_solved':solved})
 result={'schema':'verified-developmental-navigation.arc-agi2-source-distinct-selector-prior.v29',
  'evidence_label':'KNOWN_WORLD_RETROSPECTIVE_TRANSFER_TEST','selection_uses_evaluation_outputs':False,
  'source_limit':SOURCE_LIMIT,'source_summary':source,'selector_stats':stats,'frozen_prior':prior,
  'target_ids':TARGET_IDS,'target_train_fit_count':sum(r['train_fit'] for r in rows),
  'heldout_solved_ids':[r['task'] for r in rows if r['heldout_solved']],
  'principle':'When target history cannot separate selector hypotheses, use source-distinct verified history to rank separators; freeze before target outcomes.',
  'rows':rows}
 out=HERE/'results_v29_source_distinct_selector_prior';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True));print(rows)
if __name__=='__main__':main()
