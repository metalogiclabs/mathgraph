"""V43: exact finite theorem census for the corrected 'minimal interface' story.

We stop talking specifically about ARC or utilities. Let X be a finite world-state set and
Gamma : X -> D be *the protected continuation requirement* (decision signature,
admissibility class, proof status, ranking class, etc.). An interface is a partition P of X.
P is Gamma-sufficient iff Gamma is constant on every block of P, i.e. Gamma factors through P.

Claims tested exhaustively for |X|=4 and every Gamma:X->{0,1,2}:
 T1 kernel(Gamma) is Gamma-sufficient.
 T2 every Gamma-sufficient interface refines kernel(Gamma): hence kernel(Gamma) is the
    unique coarsest sufficient interface.
 T3 every strictly coarser partition has a concrete counterexample pair x~P y with
    Gamma(x)!=Gamma(y).
 T4 starting from maximal forgetting and repeatedly splitting a bad block by Gamma value
    terminates exactly at kernel(Gamma), in at most |im Gamma|-1 split rounds.
 T5 if Gamma_old factors through Gamma_new (new requirement preserves all old distinctions),
    then kernel(Gamma_new) refines kernel(Gamma_old).
 T6 without that factorization premise, monotonic refinement is false in general; find an
    explicit counterexample among pairs of protected requirements.

These are finite exhaustive checks of elementary partition facts; the intended next step is
Lean proofs, not empirical extrapolation.
"""
import itertools,json
from pathlib import Path

N=4
OUT=Path(__file__).resolve().parent/'results_v43_protected_interface_theorems'

def canon(xs):
    m={};out=[]
    for x in xs:
        if x not in m:m[x]=len(m)
        out.append(m[x])
    return tuple(out)

def partitions(n):
    def rec(xs,m):
        if len(xs)==n:
            yield tuple(xs);return
        for v in range(m+2):
            yield from rec(xs+[v],max(m,v))
    yield from rec([0],0)

def refines(p,q):
    return all(p[i]!=p[j] or q[i]==q[j] for i in range(N) for j in range(N))

def sufficient(p,g):
    return all(p[i]!=p[j] or g[i]==g[j] for i in range(N) for j in range(N))

def factors(old,new):
    # old = h o new iff equal new-values always imply equal old-values.
    return all(new[i]!=new[j] or old[i]==old[j] for i in range(N) for j in range(N))

def split_to_kernel(g):
    # One round chooses one currently bad block and splits it by the actual protected value.
    p=(0,)*N; rounds=0
    while not sufficient(p,g):
        blocks={b:[i for i,x in enumerate(p) if x==b] for b in set(p)}
        bad=next(vs for vs in blocks.values() if len({g[i] for i in vs})>1)
        # preserve all other blocks; replace bad block by fibers of Gamma inside it
        labels=[]; key_to_lab={}; nextlab=0
        badset=set(bad)
        for i in range(N):
            key=('bad',g[i]) if i in badset else ('old',p[i])
            if key not in key_to_lab:key_to_lab[key]=nextlab;nextlab+=1
            labels.append(key_to_lab[key])
        p=canon(labels);rounds+=1
    return p,rounds

def main():
    ps=list(partitions(N)); gammas=list(itertools.product(range(3),repeat=N))
    fail=[]; strict_coarser_witnesses=0; max_rounds=0
    for g in gammas:
        k=canon(g)
        if not sufficient(k,g):fail.append(('T1',g,k));break
        for p in ps:
            if sufficient(p,g) and not refines(p,k):
                fail.append(('T2',g,p,k));break
            # P is strictly coarser than kernel when kernel refines P but P != kernel.
            if refines(k,p) and p!=k:
                wit=next(((i,j) for i in range(N) for j in range(i+1,N)
                          if p[i]==p[j] and g[i]!=g[j]),None)
                if wit is None:fail.append(('T3',g,p,k));break
                strict_coarser_witnesses+=1
        if fail:break
        got,r=split_to_kernel(g); max_rounds=max(max_rounds,r)
        if got!=k or r>max(0,len(set(g))-1):
            fail.append(('T4',g,got,k,r));break
    refinement_pairs=0; premise_pairs=0; no_premise_counterexample=None
    if not fail:
        for old in gammas:
            ko=canon(old)
            for new in gammas:
                kn=canon(new)
                if factors(old,new):
                    premise_pairs+=1
                    if not refines(kn,ko):
                        fail.append(('T5',old,new,ko,kn));break
                    refinement_pairs+=1
                elif no_premise_counterexample is None and not refines(kn,ko):
                    no_premise_counterexample={'old':old,'new':new,'kernel_old':ko,'kernel_new':kn}
            if fail:break
    if not fail and no_premise_counterexample is None:
        fail.append(('T6_no_counterexample_found',))
    result={
      'schema':'verified-developmental-navigation.protected-interface-theorems.v43',
      'state_count':N,'protected_maps':len(gammas),'partitions':len(ps),
      'all_checks_pass':not fail,'failures':fail,
      'strict_coarser_interfaces_with_witness':strict_coarser_witnesses,
      'max_counterexample_split_rounds':max_rounds,
      'factorization_premise_pairs':premise_pairs,
      'monotone_refinement_pairs_verified':refinement_pairs,
      'counterexample_to_unconditional_monotonicity':no_premise_counterexample,
      'mathematical_core':(
        'For a fixed protected requirement Gamma, the minimal sufficient interface is exactly '
        'the kernel equivalence of Gamma. Counterexamples are precisely witnesses that a proposed '
        'coarser quotient crosses Gamma-fibers. Requirement expansion refines the interface exactly '
        'when the old requirement factors through the new one; arbitrary requirement change need not.'
      )
    }
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
    if fail:raise SystemExit(1)
if __name__=='__main__':main()
