"""V42: try to falsify the strongest formulation.

Claim under test: 'the minimal sufficient interface' is equivalence by all intervention
futures. Counter-hypothesis: for correct choice alone, preserving every future is too
strong; only distinctions that can change the optimal decision need survive.

Enumerate every 3-state, 2-action immediate decision world with strict utilities drawn
from {0,1,2}. Compare:
  Q_future   : states equal iff both action consequences are identical;
  Q_choice   : states equal iff the uniquely optimal action is identical.

Test that Q_choice is the unique coarsest partition sufficient for correct action, that
Q_future always refines it, and measure how often Q_future is strictly finer. A large
strict gap falsifies the literal identification of 'all-future equivalence' with the
minimal interface for choice, while preserving the deeper quotient principle.
"""
import itertools,json
from pathlib import Path

N=3
PAIRS=[p for p in itertools.product(range(3),repeat=2) if p[0]!=p[1]]
OUT=Path(__file__).resolve().parent/'results_v42_choice_vs_future_equivalence'

def canon(xs):
 m={};n=0;o=[]
 for x in xs:
  if x not in m:m[x]=n;n+=1
  o.append(m[x])
 return tuple(o)

def parts(n):
 def rec(xs,m):
  if len(xs)==n:yield tuple(xs);return
  for v in range(m+2):yield from rec(xs+[v],max(m,v))
 yield from rec([0],0)

def refines(p,q):
 return all(not(p[i]==p[j]) or q[i]==q[j] for i in range(N) for j in range(N))

def choice_sufficient(p,best):
 return all(not(p[i]==p[j]) or best[i]==best[j] for i in range(N) for j in range(N))

def main():
 ps=list(parts(N)); total=0;strict=0;fail=[]; savings=[]
 for world in itertools.product(PAIRS,repeat=N):
  total+=1
  best=tuple(0 if u[0]>u[1] else 1 for u in world)
  qf=canon(world); qc=canon(best)
  if not refines(qf,qc): fail.append(('future_not_refine_choice',world,qf,qc));break
  # unique coarsest choice-sufficient partition
  if not choice_sufficient(qc,best):fail.append(('qc_not_sufficient',world));break
  for p in ps:
   if choice_sufficient(p,best) and not refines(p,qc):
    fail.append(('qc_not_coarsest',world,p,qc));break
  if fail:break
  if qf!=qc:
   strict+=1;savings.append(len(set(qf))-len(set(qc)))
 result={
  'schema':'verified-developmental-navigation.choice-vs-future-equivalence.v42',
  'worlds':total,'failures':fail,'all_checks_pass':not fail,
  'future_strictly_finer_cases':strict,
  'future_strictly_finer_fraction':strict/total if total else None,
  'mean_extra_future_classes_when_strict':sum(savings)/len(savings) if savings else 0,
  'conclusion':(
   'For correct choice alone, all-future equivalence is generally stronger than necessary. '
   'The unique coarsest interface is decision/continuation-value equivalence: retain exactly '
   'distinctions that can change admissibility or ordering of relevant continuations. Future '
   'equivalence remains appropriate when the protected requirement is to preserve the full '
   'future semantics rather than only the current argmax.'
  )
 }
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
 if fail:raise SystemExit(1)
if __name__=='__main__':main()
