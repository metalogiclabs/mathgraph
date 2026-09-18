"""V46: falsify uniqueness of the minimal interface for set-valued correct choice.

If a state merely requires choosing ANY action from a nonempty acceptable set A(x),
a representation block is sufficient when the acceptable sets of all states in that
block have nonempty intersection. Unlike a single-valued protected map Gamma, this
sufficiency predicate need not have a unique coarsest partition.

Exhaust all 3-state worlds with two actions and nonempty acceptable sets, enumerate
all partitions, and count worlds with multiple incomparable coarsest sufficient
interfaces. Also record the smallest counterexample.
"""
import itertools,json
from pathlib import Path
OUT=Path(__file__).resolve().parent/'results_v46_setvalued_choice_nonuniqueness'

def parts(n):
 out=[]
 def rec(a,m):
  if len(a)==n:out.append(tuple(a));return
  for v in range(m+2):rec(a+[v],max(m,v))
 rec([0],0);return out

def blocks(p):
 d={}
 for i,b in enumerate(p):d.setdefault(b,[]).append(i)
 return list(d.values())

def sufficient(p,A):
 for B in blocks(p):
  inter=set(A[B[0]])
  for i in B[1:]:inter &= set(A[i])
  if not inter:return False
 return True

def refines(p,q):
 return all(p[i]!=p[j] or q[i]==q[j] for i in range(len(p)) for j in range(len(p)))

def coarsest_members(suff):
 # maximal elements under coarsening: p is excluded if a distinct sufficient q is coarser
 return [p for p in suff if not any(q!=p and refines(p,q) for q in suff)]

def main():
 ps=parts(3); opts=[frozenset({0}),frozenset({1}),frozenset({0,1})]
 total=multi=unique=0; example=None
 for A in itertools.product(opts,repeat=3):
  total+=1;suff=[p for p in ps if sufficient(p,A)]; tops=coarsest_members(suff)
  if len(tops)==1:unique+=1
  else:
   multi+=1
   if example is None:example={'acceptable':[sorted(x) for x in A],'coarsest_interfaces':[list(p) for p in tops]}
 result={'schema':'verified-developmental-navigation.setvalued-choice-nonuniqueness.v46','worlds':total,'unique_coarsest_worlds':unique,'multiple_incomparable_coarsest_worlds':multi,'fraction_nonunique':multi/total,'example':example,
 'mathematical_core':'For existential correctness (choose any action acceptable in every state of a representation block), a unique coarsest sufficient interface need not exist. Kernel-quotient uniqueness requires a single-valued/extensional protected semantic map Gamma, or an explicit stronger semantics such as preserving the full acceptable-action set or a fixed policy selector.'}
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
 if multi==0:raise SystemExit('expected nonuniqueness not found')
if __name__=='__main__':main()
