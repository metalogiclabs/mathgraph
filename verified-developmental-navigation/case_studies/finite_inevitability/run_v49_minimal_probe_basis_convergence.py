"""V49: test whether canonical convergence requires complete semantics or only a separating basis.

Same 3-state/3-action nonempty acceptable-set worlds as V48. For every subset P of action
membership probes, compute coarsest partitions satisfying existential block viability plus
agreement on P. Ask whether the resulting coarsest family is exactly the full option-profile
kernel. Find all inclusion-minimal / minimum-cardinality probe sets that achieve this.

This attacks the too-strong story 'convergence requires observing the full continuation
profile'. Hypothesis: full semantic completion is sufficient but not necessary; convergence
occurs as soon as the protected probe family is sufficient to pin the target interface.
"""
import itertools, json
from pathlib import Path

N=3; A=3
NONEMPTY=[frozenset(i for i in range(A) if mask&(1<<i)) for mask in range(1,1<<A)]
PROBESETS=[frozenset(i for i in range(A) if mask&(1<<i)) for mask in range(1<<A)]
OUT=Path(__file__).resolve().parent/'results_v49_minimal_probe_basis_convergence'

def canon(xs):
    m={}; out=[]
    for x in xs:
        if x not in m:m[x]=len(m)
        out.append(m[x])
    return tuple(out)

def parts(n):
    def rec(xs,m):
        if len(xs)==n: yield tuple(xs); return
        for v in range(m+2): yield from rec(xs+[v],max(m,v))
    yield from rec([0],0)
PARTS=list(parts(N))

def blocks(p): return [[i for i in range(N) if p[i]==b] for b in sorted(set(p))]
def refines(p,q): return all(not(p[i]==p[j]) or q[i]==q[j] for i in range(N) for j in range(N))
def sufficient(world,p,probes):
    for B in blocks(p):
        common=set(world[B[0]])
        for i in B[1:]: common &= set(world[i])
        if not common:return False
        for a in probes:
            if len({a in world[i] for i in B})>1:return False
    return True

def coarsest(suffs):
    return sorted(p for p in suffs if not any(q!=p and refines(p,q) for q in suffs))

def option_kernel(world): return canon(world)

def main():
    failures=[]; hist={}; all3_needed=0; strict_subset_enough=0; multi_min_basis=0; examples={}
    for world in itertools.product(NONEMPTY,repeat=N):
        q=option_kernel(world)
        good=[]
        for P in PROBESETS:
            suffs={p for p in PARTS if sufficient(world,p,P)}
            if coarsest(suffs)==[q]: good.append(P)
        if not good:
            failures.append(('no_basis',world,q));break
        k=min(map(len,good)); mins=[P for P in good if len(P)==k]
        hist[k]=hist.get(k,0)+1
        if k==A: all3_needed+=1
        else: strict_subset_enough+=1
        if len(mins)>1: multi_min_basis+=1
        # upward closure: once a probe set pins q, every superset must also pin q
        for P in good:
            for Q in PROBESETS:
                if P.issubset(Q) and Q not in good:
                    failures.append(('not_upward_closed',world,P,Q));break
            if failures:break
        if failures:break
        examples.setdefault(f'k{k}',{'world':[sorted(s) for s in world],'kernel':q,'minimum_bases':[sorted(P) for P in mins]})
    result={
      'schema':'verified-developmental-navigation.minimal-probe-basis-convergence.v49',
      'worlds_tested':343,'all_checks_pass':not failures,'failures':failures,
      'minimum_probe_basis_size_hist':hist,
      'worlds_where_full_3_probe_profile_is_necessary':all3_needed,
      'worlds_where_strict_subset_suffices':strict_subset_enough,
      'worlds_with_multiple_minimum_bases':multi_min_basis,
      'examples':examples,
      'mathematical_core':(
        'Full continuation semantics are sufficient but generally not necessary for canonical '
        'convergence. The endpoint is pinned as soon as the accumulated protected probes form a '
        'sufficient separator basis for the target interface. Supersets remain sufficient. Thus '
        'the inevitable object is not maximal knowledge of futures but a minimal protected basis '
        'whose induced constraints uniquely determine the required interface.'
      )
    }
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True));print(json.dumps(result,indent=2,sort_keys=True))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
