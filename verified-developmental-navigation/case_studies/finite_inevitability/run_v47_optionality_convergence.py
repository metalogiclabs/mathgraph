"""V47: when current existential correctness admits several incomparable compressed
interfaces, test whether accumulating sound continuation semantics canonically resolves the
ambiguity.

Worlds: 3 states, 2 actions. Each state has a nonempty acceptable-action set.
A partition is CURRENT-VIABLE iff every block has at least one action acceptable in every
state in that block. This is the set-valued/existential regime from V46.

We then protect cumulative semantic probes p_a(x) := [a is acceptable at x]. A partition is
probe-compatible iff each block is constant on all protected probes. For k=0,1,2 probes,
compute the coarsest partitions satisfying both current viability and probe compatibility.
With both action-membership probes protected, the probe signature is exactly the full
acceptable-action set A(x), so the predicted endpoint is the canonical kernel quotient of A.

The test also checks whether merely adding one sound probe always makes the family of
coarsest interfaces smaller. It need not: cumulative semantic information shrinks the
feasible set, but the number of incomparable maximally compressed solutions can increase.
"""
import itertools, json
from pathlib import Path

N=3
ACTIONS=(0,1)
NONEMPTY=(frozenset([0]), frozenset([1]), frozenset([0,1]))
OUT=Path(__file__).resolve().parent/'results_v47_optionality_convergence'

def canon(xs):
    m={}; out=[]
    for x in xs:
        if x not in m:m[x]=len(m)
        out.append(m[x])
    return tuple(out)

def parts(n):
    def rec(xs,m):
        if len(xs)==n:
            yield tuple(xs); return
        for v in range(m+2):
            yield from rec(xs+[v], max(m,v))
    yield from rec([0],0)

def blocks(p):
    return [[i for i in range(N) if p[i]==b] for b in sorted(set(p))]

def viable(p,world):
    return all(set.intersection(*(set(world[i]) for i in B)) for B in blocks(p))

def probe_ok(p,world,protected_actions):
    for B in blocks(p):
        for a in protected_actions:
            vals={a in world[i] for i in B}
            if len(vals)>1:return False
    return True

def coarsest(feasible):
    if not feasible:return []
    k=min(len(set(p)) for p in feasible)
    return sorted([p for p in feasible if len(set(p))==k])

def set_kernel(world):
    return canon(tuple(tuple(sorted(s)) for s in world))

def main():
    ps=list(parts(N)); total=0; end_fail=[]; family_growth=0; family_shrink=0; family_equal=0
    nonunique0=0; resolved_by_one=0; resolved_only_by_full=0; examples={}
    size_paths={}
    for world in itertools.product(NONEMPTY, repeat=N):
        total+=1
        fam=[]
        for protected in [(),(0,),(0,1)]:
            feasible=[p for p in ps if viable(p,world) and probe_ok(p,world,protected)]
            fam.append(coarsest(feasible))
        path=tuple(len(f) for f in fam); size_paths[str(path)]=size_paths.get(str(path),0)+1
        if len(fam[0])>1:
            nonunique0+=1
            if len(fam[1])==1: resolved_by_one+=1
            if len(fam[1])>1 and len(fam[2])==1: resolved_only_by_full+=1
        if len(fam[1])>len(fam[0]):
            family_growth+=1; examples.setdefault('family_growth',{'world':[sorted(s) for s in world],'families':fam})
        elif len(fam[1])<len(fam[0]): family_shrink+=1
        else: family_equal+=1
        qA=set_kernel(world)
        if fam[2] != [qA]:
            end_fail.append({'world':[sorted(s) for s in world],'full_family':fam[2],'qA':qA}); break
    result={
      'schema':'verified-developmental-navigation.optionality-convergence.v47',
      'worlds':total,'all_checks_pass':not end_fail,'failures':end_fail,
      'current_nonunique_worlds':nonunique0,
      'nonunique_resolved_by_first_probe':resolved_by_one,
      'nonunique_resolved_only_by_full_signature':resolved_only_by_full,
      'first_probe_family_change':{'grow':family_growth,'shrink':family_shrink,'equal':family_equal},
      'coarsest_family_size_paths':size_paths,
      'examples':examples,
      'mathematical_core':(
        'Existential current correctness can admit multiple incomparable coarsest interfaces. '
        'Accumulating sound continuation coordinates does not by itself guarantee monotone '
        'shrinkage of the set of maximally compressed interfaces. But once the protected '
        'signature is extensionally complete for the continuation semantics A(x), the '
        'ambiguity collapses to the unique kernel quotient of A. Thus optionality resolves '
        'nonuniqueness canonically only relative to a specified complete protected semantics.'
      )
    }
    OUT.mkdir(parents=True,exist_ok=True); (OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)); print(json.dumps(result,indent=2,sort_keys=True))
    if end_fail: raise SystemExit(1)
if __name__=='__main__':main()
