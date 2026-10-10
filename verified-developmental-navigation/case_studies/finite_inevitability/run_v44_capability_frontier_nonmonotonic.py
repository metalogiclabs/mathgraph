"""V44: falsify/repair the claim that 'new powers create new perceptual obligations'.

Let each state have strict utilities for three actions. Compare the decision-sufficient
quotient for action frontier A_old={0,1} with A_new={0,1,2}. If the protected requirement
at each time is *only the currently optimal action*, adding capability need not monotonically
refine perception: a new action can make previously important old distinctions irrelevant,
or create new distinctions, or do both.

Enumerate all 3-state worlds whose per-state utilities are permutations of (0,1,2).
Classify Q_new relative to Q_old as equal / strictly finer / strictly coarser / incomparable.
Also verify that if the protected requirement is cumulative Gamma_cum=(best_old,best_new),
its kernel always refines Q_old and Q_new.
"""
import itertools,json
from pathlib import Path

N=3
PROFILES=list(itertools.permutations((0,1,2)))
OUT=Path(__file__).resolve().parent/'results_v44_capability_frontier_nonmonotonic'

def canon(xs):
 m={};o=[]
 for x in xs:
  if x not in m:m[x]=len(m)
  o.append(m[x])
 return tuple(o)

def refines(p,q):
 return all(p[i]!=p[j] or q[i]==q[j] for i in range(N) for j in range(N))

def best(profile,actions):
 return max(actions,key=lambda a:profile[a])

def main():
 counts={'equal':0,'new_strictly_finer':0,'new_strictly_coarser':0,'incomparable':0}
 examples={};fail=[];total=0
 for world in itertools.product(PROFILES,repeat=N):
  total+=1
  bo=tuple(best(u,(0,1)) for u in world); bn=tuple(best(u,(0,1,2)) for u in world)
  qo,qn=canon(bo),canon(bn)
  nr=refines(qn,qo); orr=refines(qo,qn)
  if nr and orr:k='equal'
  elif nr:k='new_strictly_finer'
  elif orr:k='new_strictly_coarser'
  else:k='incomparable'
  counts[k]+=1
  examples.setdefault(k,{'world':world,'best_old':bo,'best_new':bn,'Q_old':qo,'Q_new':qn})
  qcum=canon(tuple(zip(bo,bn)))
  if not refines(qcum,qo) or not refines(qcum,qn):
   fail.append(('cumulative_not_refine',world,qo,qn,qcum));break
 result={
  'schema':'verified-developmental-navigation.capability-frontier-nonmonotonic.v44',
  'worlds':total,'all_checks_pass':not fail,'failures':fail,'counts':counts,
  'fractions':{k:v/total for k,v in counts.items()},'examples':examples,
  'conclusion':(
   'Capability expansion alone does not imply monotone perceptual refinement when the protected '
   'requirement is only current optimal choice. New actions can refine, coarsen, or reorganize the '
   'minimal decision interface. Monotone refinement is recovered when the protected requirement is '
   'cumulative (or more generally when the old requirement factors through the new protected map).'
  )
 }
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
 if fail:raise SystemExit(1)
if __name__=='__main__':main()
