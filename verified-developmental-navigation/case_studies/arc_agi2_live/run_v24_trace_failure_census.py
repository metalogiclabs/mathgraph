"""V24: diagnose V23's generalization residual before changing ontology.

For each V23 demonstration-fit task, freeze its induced rules and inspect the
held-out input. Classify each rule by match multiplicity and compare the frozen
program output to the known-world held-out output. This is retrospective only.
"""
import json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import run_v2, run_v23_trace_induced_patch as v23

FIT_IDS={'332f06d7','36a08778','53fb4810','7b80bb43','88bcf3b4','b9e38dc0','d59b0160'}

def hits(grid, rule):
    h,w=v23.shape(grid); ph,pw=rule['h'],rule['w']; out=[]
    for a in range(h-ph+1):
      for b in range(w-pw+1):
        m=v23.match_color_equivariant(rule['in'],grid,a,b)
        if m is not None: out.append((a,b,m))
    return out

def diff(a,b):
    if v23.shape(a)!=v23.shape(b): return {'shape_mismatch':True}
    h,w=v23.shape(a); pts=[(i,j) for i in range(h) for j in range(w) if a[i][j]!=b[i][j]]
    return {'shape_mismatch':False,'wrong_cells':len(pts)}

def classify(t):
    rules,_=v23.learn_rules(t); rows=[]
    for ti,pair in enumerate(t['test']):
      x=pair['input']; y=pair.get('output'); counts=[len(hits(x,r)) for r in rules]
      pred=v23.program(rules)(x)
      d=diff(pred,y) if y is not None else None
      if all(c==0 for c in counts): cls='NO_MATCH'
      elif any(c>1 for c in counts) and not any(c==1 for c in counts): cls='MULTIPLE_MATCHES'
      elif d and not d.get('shape_mismatch') and d.get('wrong_cells')==0: cls='SOLVED'
      else: cls='RIGHT_OR_PARTIAL_MATCH_WRONG_ACTION_OR_COMPOSITION'
      rows.append({'test_index':ti,'rule_match_counts':counts,'classification':cls,'diff':d})
    return rows

def main():
    if len(sys.argv)!=2: raise SystemExit('usage: run_v24_trace_failure_census.py EVAL_DIR')
    tasks=run_v2.v1.load_tasks(sys.argv[1]); outrows={}; totals={}
    for tid in sorted(FIT_IDS):
      rr=classify(tasks[tid]); outrows[tid]=rr
      for r in rr: totals[r['classification']]=totals.get(r['classification'],0)+1
    result={'schema':'verified-developmental-navigation.arc-agi2-v23-failure-census.v24',
      'evidence_label':'KNOWN_WORLD_RETROSPECTIVE_DIAGNOSTIC','fit_tasks':sorted(FIT_IDS),
      'classification_totals':totals,'tasks':outrows,
      'routing':'Repair the dominant diagnosed failure coordinate before adding any new object ontology.'}
    p=HERE/'results_v24_trace_failure_census'; p.mkdir(exist_ok=True)
    (p/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)); print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__': main()
