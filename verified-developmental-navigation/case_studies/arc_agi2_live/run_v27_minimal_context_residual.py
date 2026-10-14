"""V27: classify what remains after V26's verified context compression.

Recompute the deletion-minimal training-sufficient contexts, then classify each
held-out rule as NO_MATCH / UNIQUE_MATCH / AMBIGUOUS_MATCH. This asks whether
compression repaired recognition and, if so, whether the residual moved from
observability to selectability. No test output is used to construct contexts.
"""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import run_v2,run_v23_trace_induced_patch as v23,run_v26_minimal_sufficient_context as v26
FIT_IDS=v26.FIT_IDS

def main():
 if len(sys.argv)!=2:raise SystemExit('usage run_v27_minimal_context_residual.py EVAL_DIR')
 tasks=run_v2.v1.load_tasks(sys.argv[1]); rows=[]; totals={'NO_MATCH':0,'UNIQUE_MATCH':0,'AMBIGUOUS_MATCH':0}
 for tid in sorted(FIT_IDS):
  t=tasks[tid];rs,u=v23.learn_rules(t);strict=[v26.initial_keep(r) for r in rs];mins,_,_=v26.minimize(t,rs)
  for ti,p in enumerate(t['test']):
   sc=v26.hit_counts(p['input'],rs,strict); mc=v26.hit_counts(p['input'],rs,mins)
   classes=[]
   for n in mc:
    c='NO_MATCH' if n==0 else ('UNIQUE_MATCH' if n==1 else 'AMBIGUOUS_MATCH');totals[c]+=1;classes.append(c)
   rows.append({'task':tid,'test_index':ti,'strict_counts':sc,'minimal_counts':mc,'classes':classes})
 result={'schema':'verified-developmental-navigation.arc-agi2-minimal-context-residual.v27',
  'evidence_label':'KNOWN_WORLD_RETROSPECTIVE_DIAGNOSTIC','selection_uses_test_outputs':False,
  'classification_totals':totals,'rows':rows,
  'interpretation':'If NO_MATCH falls but AMBIGUOUS_MATCH rises, verified forgetting repaired observability but exposed a selectability residual; the next justified move is to induce a selector from training traces, not add ontology.'}
 p=HERE/'results_v27_minimal_context_residual';p.mkdir(exist_ok=True);(p/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2,sort_keys=True));
 for r in rows:print(r)
if __name__=='__main__':main()
