"""V41: exhaustive finite test of the 'minimal world-agency interface' claim.

Universe: every deterministic 3-state / 2-action world with a binary verifier-visible
observation on states. For a protected action alphabet A and horizon H, two states are
future-equivalent iff every action word of length <= H yields the same verifier trace.

We exhaustively test:
  T1 existence/uniqueness of the coarsest future-sufficient quotient;
  T2 every strictly coarser partition has a concrete separating continuation witness;
  T3 adding interventions can only refine (never coarsen) the quotient;
  T4 removing interventions can only coarsen (never refine) the quotient;
  T5 counterexample-guided splitting from the indiscrete partition converges exactly
     to the future quotient;
  T6 full-state identity is often unnecessary (strict compression occurs).

This does not prove a theorem about intelligence in general. It tests whether the core
claims are mathematical consequences in the complete bounded class, not artifacts of
one hand-designed example.
"""
from __future__ import annotations
import itertools, json
from pathlib import Path
from collections import Counter

N=3
ACTIONS=(0,1)
MAX_H=3
OUT=Path(__file__).resolve().parent/'results_v41_finite_interface_inevitability'

def words(actions,h):
    out=[()]
    for k in range(1,h+1): out.extend(itertools.product(actions, repeat=k))
    return out

def run_word(trans,s,w):
    for a in w: s=trans[s][a]
    return s

def signature(trans,obs,s,actions,h):
    # verifier-visible terminal consequence for every available continuation
    return tuple(obs[run_word(trans,s,w)] for w in words(actions,h))

def quotient(trans,obs,actions,h):
    sig=[signature(trans,obs,s,actions,h) for s in range(N)]
    cls={}; nxt=0; q=[]
    for x in sig:
        if x not in cls: cls[x]=nxt; nxt+=1
        q.append(cls[x])
    return tuple(q),sig

def canon_partition(labels):
    mp={}; nxt=0; out=[]
    for x in labels:
        if x not in mp: mp[x]=nxt; nxt+=1
        out.append(mp[x])
    return tuple(out)

def partitions(n):
    # all set partitions in restricted-growth-string form
    def rec(xs,maxv):
        if len(xs)==n:
            yield tuple(xs); return
        for v in range(maxv+2):
            yield from rec(xs+[v],max(maxv,v))
    yield from rec([0],0)

def refines(p,q):
    # p refines q: same p-class => same q-class
    for i in range(N):
      for j in range(N):
        if p[i]==p[j] and q[i]!=q[j]: return False
    return True

def future_sufficient(p,sigs):
    for i in range(N):
      for j in range(N):
        if p[i]==p[j] and sigs[i]!=sigs[j]: return False
    return True

def separating_word(trans,obs,i,j,actions,h):
    for w in words(actions,h):
        if obs[run_word(trans,i,w)] != obs[run_word(trans,j,w)]: return w
    return None

def split_loop(trans,obs,actions,h):
    p=(0,)*N; steps=0
    while True:
        found=None
        for i in range(N):
          for j in range(i+1,N):
            if p[i]==p[j]:
                w=separating_word(trans,obs,i,j,actions,h)
                if w is not None: found=(i,j,w); break
          if found: break
        if not found:return canon_partition(p),steps
        # split every current class by consequence under this witness
        _,_,w=found
        labels=[(p[s],obs[run_word(trans,s,w)]) for s in range(N)]
        p=canon_partition(labels);steps+=1
        if steps>10: raise RuntimeError('nonconvergent split loop')

def main():
    parts=list(partitions(N)); counts=Counter(); failures=[]; worlds=0
    compression_hist=Counter(); split_hist=Counter()
    for flat in itertools.product(range(N), repeat=N*len(ACTIONS)):
        trans=tuple(tuple(flat[s*2:(s+1)*2]) for s in range(N))
        for obs in itertools.product((0,1), repeat=N):
            worlds+=1
            for h in range(MAX_H+1):
                q,sigs=quotient(trans,obs,ACTIONS,h)
                # T1: q sufficient and every sufficient partition refines q.
                if not future_sufficient(q,sigs): failures.append(('T1a',trans,obs,h,q));break
                for p in parts:
                    if future_sufficient(p,sigs) and not refines(p,q):
                        failures.append(('T1b',trans,obs,h,p,q));break
                if failures:break
                counts['T1_cases']+=1

                # T2: any strictly coarser-than-q partition merges a separated pair.
                for p in parts:
                    if refines(q,p) and p!=q:
                        witness=False
                        for i in range(N):
                          for j in range(i+1,N):
                            if p[i]==p[j] and q[i]!=q[j] and separating_word(trans,obs,i,j,ACTIONS,h) is not None:
                                witness=True;break
                          if witness:break
                        if not witness: failures.append(('T2',trans,obs,h,p,q));break
                if failures:break
                counts['T2_cases']+=1

                # T3/T4 compare {0} to {0,1} at same horizon.
                q0,_=quotient(trans,obs,(0,),h)
                if not refines(q,q0): failures.append(('T3',trans,obs,h,q0,q));break
                if not refines(q,q0): failures.append(('T4',trans,obs,h,q0,q));break
                counts['T3T4_cases']+=1

                # T5 residual-driven splitting converges exactly.
                qs,steps=split_loop(trans,obs,ACTIONS,h)
                if qs!=q: failures.append(('T5',trans,obs,h,qs,q));break
                split_hist[steps]+=1; counts['T5_cases']+=1

                k=len(set(q)); compression_hist[k]+=1
                if k<N: counts['strict_compression_cases']+=1
            if failures:break
        if failures:break

    total=counts['T1_cases']
    result={
      'schema':'verified-developmental-navigation.finite-interface-inevitability.v41',
      'worlds':worlds,'horizons_per_world':MAX_H+1,'cases':total,
      'failures':failures[:3],
      'all_checks_pass':not failures,
      'counts':dict(counts),
      'compression_class_count_hist':{str(k):v for k,v in sorted(compression_hist.items())},
      'split_steps_hist':{str(k):v for k,v in sorted(split_hist.items())},
      'strict_compression_fraction':counts['strict_compression_cases']/total if total else None,
      'interpretation':(
        'Within the complete finite class, future-equivalence is the unique coarsest safe interface; '
        'every extra merge has an intervention witness; intervention-set expansion monotonically '
        'refines the interface; and counterexample-guided splitting reconstructs it from maximal forgetting.'
      )
    }
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))
    if failures: raise SystemExit(1)
if __name__=='__main__': main()
