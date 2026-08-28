import importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def load(name,file):
 s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
v20=load('v20','run_v20_cross_episode_policy_transfer.py')
v19=v20.v19
v13=v20.v13
SOURCE=set(v20.SOURCE_TASKS)

def main():
 if len(sys.argv)!=2:raise SystemExit('usage: ... EVAL')
 ev=v13.v2.v1.load_tasks(sys.argv[1]); rows=[]
 for tid in sorted(ev):
  if tid in SOURCE:continue
  states,keys,demo,held=v20.audit_task(ev[tid])
  trunc=any(s['truncated'] for s in states)
  nontrivial=bool(states) and 0<sum(demo)<len(states)
  demo_unres=v19.unresolved(states,keys,demo) if states else 0
  held_unres=v19.unresolved(states,keys,held) if states else 0
  rows.append({'task':tid,'states':len(states),'future_positive':sum(demo),'nontrivial':nontrivial,'truncated':trunc,'programs':len(keys),'full_demo_unresolved':demo_unres,'full_heldout_unresolved':held_unres,'full_demo_sufficient':nontrivial and demo_unres==0,'full_heldout_sufficient':nontrivial and held_unres==0})
 summary={
  'tasks':len(rows),
  'nontrivial':sum(r['nontrivial'] for r in rows),
  'no_truncation':sum(not r['truncated'] for r in rows),
  'nontrivial_no_truncation':sum(r['nontrivial'] and not r['truncated'] for r in rows),
  'full_demo_sufficient':sum(r['full_demo_sufficient'] and not r['truncated'] for r in rows),
  'full_demo_and_heldout_sufficient':sum(r['full_demo_sufficient'] and r['full_heldout_sufficient'] and not r['truncated'] for r in rows),
 }
 elig=[r['task'] for r in rows if r['nontrivial'] and not r['truncated'] and r['full_demo_sufficient'] and r['full_heldout_sufficient']]
 result={'schema':'verified-developmental-navigation.arc-v17-transfer-boundary.v20b','source':{'repository':'fchollet/ARC-AGI','commit':'399030444e0ab0cc8b4e199870fb20b863846f34'},'excluded_source_tasks':sorted(SOURCE),'summary':summary,'eligible_tasks':elig,'rows':rows,'decision':'V17_LANGUAGE_HAS_FRESH_TRANSFER_CARRIER' if elig else 'V17_LANGUAGE_SOURCE_BOUND','claim_boundary':'Full evaluation-set census of whether the frozen V17 cumulative observation language can represent the exact one-step future quotient on source-distinct ARC tasks. No policy comparison and no target selection tuning.'}
 out=HERE/'results_v20b_transfer_boundary_census';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
