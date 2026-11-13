"""V47: test whether noncanonical existential interfaces converge under cumulative verified probes.

Worlds: 3 states, 3 actions. Each state has a nonempty acceptable-action set.
A partition/interface is sufficient at probe set P iff every block:
  (1) admits at least one common acceptable action (existential correctness), and
  (2) agrees on membership of every probed action (cumulative protected evidence).

For each of all 7^3 worlds and all 3! probe orders, recompute the coarsest sufficient
interfaces after each cumulative probe. Test:
  T1 sufficient-family monotonicity: adding probes never adds sufficient partitions;
  T2 final uniqueness: after all action-membership probes, there is exactly one coarsest
     sufficient interface;
  T3 final identity: that unique interface is equality of full acceptable-action sets;
  T4 path independence: every probe order reaches the same final interface.

This tests the precise convergence claim suggested by V46: existential correctness can
admit incomparable maximal compressions, but cumulative observation of the complete
protected continuation profile canonically resolves the ambiguity.
"""
import itertools, json
from pathlib import Path

N=3
A=3
NONEMPTY=[frozenset(i for i in range(A) if mask&(1<<i)) for mask in range(1,1<<A)]
OUT=Path(__file__).resolve().parent/'results_v47_probe_completion_convergence'

def canon(labels):
    m={}; out=[]; nxt=0
    for x in labels:
        if x not in m:
            m[x]=nxt; nxt+=1
        out.append(m[x])
    return tuple(out)

def parts(n):
    def rec(xs,m):
        if len(xs)==n:
            yield tuple(xs); return
        for v in range(m+2):
            yield from rec(xs+[v],max(m,v))
    yield from rec([0],0)

PARTS=list(parts(N))

def blocks(p):
    return [[i for i in range(N) if p[i]==b] for b in sorted(set(p))]

def refines(p,q):
    # p finer than q
    return all(not (p[i]==p[j]) or q[i]==q[j] for i in range(N) for j in range(N))

def sufficient(world,p,probes):
    for B in blocks(p):
        common=set(world[B[0]])
        for i in B[1:]: common &= set(world[i])
        if not common: return False
        for a in probes:
            vals={a in world[i] for i in B}
            if len(vals)>1: return False
    return True

def coarsest(suffs):
    # maximal under coarsening = no strictly coarser sufficient q
    out=[]
    for p in suffs:
        if not any(q!=p and refines(p,q) for q in suffs):
            out.append(p)
    return sorted(out)

def option_kernel(world):
    return canon(world)

def main():
    failures=[]; worlds=0; paths=0
    nonunique_hist={0:0,1:0,2:0,3:0}
    path_nonunique_hist={0:0,1:0,2:0,3:0}
    examples={}
    for world in itertools.product(NONEMPTY, repeat=N):
        worlds+=1
        final_expected=option_kernel(world)
        world_stage_seen={k:set() for k in range(A+1)}
        for order in itertools.permutations(range(A)):
            paths+=1
            prev_suffs=None
            for k in range(A+1):
                probes=frozenset(order[:k])
                suffs={p for p in PARTS if sufficient(world,p,probes)}
                cs=tuple(coarsest(suffs))
                world_stage_seen[k].add(cs)
                if len(cs)>1:
                    path_nonunique_hist[k]+=1
                    examples.setdefault(f'nonunique_k{k}', {'world':[sorted(x) for x in world],'order':order,'coarsest':cs})
                if prev_suffs is not None and not suffs.issubset(prev_suffs):
                    failures.append(('family_not_monotone',world,order,k)); break
                prev_suffs=suffs
            if failures: break
            final_cs=coarsest(prev_suffs)
            if len(final_cs)!=1:
                failures.append(('final_not_unique',world,order,final_cs)); break
            if final_cs[0]!=final_expected:
                failures.append(('final_not_option_kernel',world,order,final_cs[0],final_expected)); break
        if failures: break
        # count a world as stage-nonunique if any order at that stage is nonunique
        for k in range(A+1):
            if any(len(cs)>1 for cs in world_stage_seen[k]): nonunique_hist[k]+=1
        # path independence is already implied by final==expected for every order; assert explicit
        finals={cs for cs in world_stage_seen[A]}
        if len(finals)!=1:
            failures.append(('path_dependent_final',world,finals)); break
    result={
      'schema':'verified-developmental-navigation.probe-completion-convergence.v47',
      'worlds':worlds,'probe_orders_per_world':6,'paths':paths,
      'all_checks_pass':not failures,'failures':failures,
      'worlds_with_nonunique_coarsest_by_probe_count':nonunique_hist,
      'path_stages_with_nonunique_coarsest':path_nonunique_hist,
      'examples':examples,
      'mathematical_core':(
        'Existential action-compatibility can admit multiple incomparable coarsest interfaces. '
        'When protected evidence is accumulated as sound continuation-membership probes, the '
        'family of sufficient interfaces shrinks monotonically. Once the probe family is complete '
        'for the protected continuation profile, every probe order converges to the same unique '
        'interface: equality of full continuation profiles. Canonical convergence therefore requires '
        'completion of the protected semantics, not merely repeated compression.'
      )
    }
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True,default=list))
    print(json.dumps(result,indent=2,sort_keys=True,default=list))
    if failures: raise SystemExit(1)
if __name__=='__main__': main()
