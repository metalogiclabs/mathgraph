"""V45: exact conditions under which 'failure -> smallest distinction -> repaired interface' works.

A protected map Gamma:X->D defines the target quotient ker(Gamma). The learner does not get
to split by Gamma directly; it has a family of binary separator predicates q:X->{0,1}.
For a chosen family B, let Q_B identify states with the same vector of predicate answers.

Definitions:
  sound(B,Gamma): every q in B is constant inside each Gamma-fiber (never invents a
                  distinction irrelevant to the protected requirement).
  complete(B,Gamma): every pair with different Gamma values is separated by some q in B.

The theorem should be:
  Q_B = ker(Gamma)  iff  B is sound and complete.
If sound but incomplete, Q_B is too coarse (missed necessary distinctions).
If complete but unsound, Q_B is too fine (memorized unnecessary distinctions).

Exhaust every Gamma:X->{0,1,2} for |X|=4 and every subset of the 7 nontrivial binary
predicates modulo complement. This makes precise what the 'seek separator' step must assume.
"""
import itertools,json
from pathlib import Path
N=4
OUT=Path(__file__).resolve().parent/'results_v45_separator_basis_theorem'

def canon(xs):
 m={};o=[]
 for x in xs:
  if x not in m:m[x]=len(m)
  o.append(m[x])
 return tuple(o)

def refines(p,q):
 return all(p[i]!=p[j] or q[i]==q[j] for i in range(N) for j in range(N))

# predicates modulo complement: force q[0]=0; omit all-zero predicate
PREDS=[p for p in itertools.product((0,1),repeat=N) if p[0]==0 and any(p)]

def qbasis(fam):
 if not fam:return (0,)*N
 return canon(tuple(tuple(q[i] for q in fam) for i in range(N)))

def sound(fam,g):
 return all(all(g[i]!=g[j] or q[i]==q[j] for i in range(N) for j in range(N)) for q in fam)

def complete(fam,g):
 return all(g[i]==g[j] or any(q[i]!=q[j] for q in fam) for i in range(N) for j in range(N))

def main():
 gammas=list(itertools.product(range(3),repeat=N));fail=[]
 counts={'sound_complete':0,'sound_incomplete':0,'unsound_complete':0,'unsound_incomplete':0}
 min_basis_hist={}; examples={}
 for g in gammas:
  kg=canon(g); minsize=None
  for mask in range(1<<len(PREDS)):
   fam=[PREDS[k] for k in range(len(PREDS)) if mask>>k&1]
   s,c=sound(fam,g),complete(fam,g); qb=qbasis(fam)
   key=('sound_' if s else 'unsound_')+('complete' if c else 'incomplete')
   counts[key]+=1
   eq=(qb==kg)
   if eq!=(s and c):fail.append(('iff',g,mask,s,c,qb,kg));break
   if s and not c and not refines(kg,qb):fail.append(('sound_incomplete_not_coarse',g,mask,qb,kg));break
   if c and not s and not refines(qb,kg):fail.append(('complete_unsound_not_fine',g,mask,qb,kg));break
   if s and c:
    minsize=len(fam) if minsize is None else min(minsize,len(fam))
   examples.setdefault(key,{'gamma':g,'basis':fam,'Q_basis':qb,'Q_gamma':kg})
  if fail:break
  if minsize is not None:min_basis_hist[str(minsize)]=min_basis_hist.get(str(minsize),0)+1
 result={'schema':'verified-developmental-navigation.separator-basis-theorem.v45','state_count':N,
   'protected_maps':len(gammas),'binary_predicates_mod_complement':len(PREDS),
   'families_per_map':1<<len(PREDS),'all_checks_pass':not fail,'failures':fail,
   'counts':counts,'minimum_sound_complete_basis_size_hist':min_basis_hist,'examples':examples,
   'mathematical_core':(
    'A separator basis reconstructs the minimal protected interface exactly iff it is both '
    'sound (never splits protected-equivalent states) and complete (separates every protected-'
    'inequivalent pair). Sound-but-incomplete learning underfits the interface; complete-but-'
    'unsound learning overfits it. Counterexamples therefore do not justify arbitrary splitting: '
    'the induced distinction must itself be protected-relevant.'
   )}
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
 if fail:raise SystemExit(1)
if __name__=='__main__':main()
