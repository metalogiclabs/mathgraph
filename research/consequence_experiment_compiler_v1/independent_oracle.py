#!/usr/bin/env python3
"""Independently implemented finite reference semantics and exhaustive comparator.

Does not import the candidate compiler. Uses separate fixed-point transition
enumeration, Bellman-Ford-style path relaxation and full subset enumeration.
A completed closure is checked against every admitted transition.
"""
from __future__ import annotations
from itertools import combinations, product
import time
from typing import Any


def pairs(labels):
    return {(i,j) for i in range(len(labels)) for j in range(i+1,len(labels)) if labels[i] == labels[j]}


def all_partitions(n):
    def recur(path):
        if len(path) == n:
            yield tuple(path)
            return
        for z in range(max(path)+2):
            yield from recur(path + [z])
    yield from recur([0])


def oracle(src: dict[str, Any]) -> dict[str, Any]:
    n=len(src['protected'])
    protected=src['protected']
    actions={a['name']:a for a in src['operations']}
    observations={o['name']:o for o in src['readouts']}
    granted=set(src['grants'])
    ops=[a for a in actions.values() if a['name'] in granted
         and all(protected[i] == protected[a['image'][i]] for i in range(n))]
    ops.sort(key=lambda a:a['name'])
    # Enumerate the entire finite semigroup by explicit round-based expansion.
    identity=tuple(range(n))
    states={identity}
    while True:
        nxt=set(states)
        for f in states:
            for op in ops:
                nxt.add(tuple(op['image'][k] for k in f))
        if len(nxt)==len(states): break
        if len(nxt)>65536:raise OverflowError('incomplete semantic model; no oracle')
        states=nxt
    for f in states:
        for op in ops:
            assert tuple(op['image'][i] for i in f) in states
    # Distinct shortest-path procedure: global relaxation over the CLOSED graph.
    best={identity:(0,0,())}
    edges=[(f,tuple(op['image'][k] for k in f),op['cost'],op['name'])
           for f in sorted(states) for op in ops]
    for it in range(len(states)):
        changed=False
        for u,v,c,name in edges:
            if u not in best:continue
            old=best[u]
            val=(old[0]+c,old[1]+1,old[2]+(name,))
            if v not in best or val < best[v]:
                best[v]=val;changed=True
        if not changed:break
    else:
        raise AssertionError('Shortest path did not stabilize within finite graph bound')
    assert set(best)==states
    names=src['base_readouts']
    old={ (i,j) for i in range(n) for j in range(i+1,n)
           if all(observations[name]['values'][i]==observations[name]['values'][j] for name in names) }
    labels=tuple(tuple(observations[name]['values'][i] for name in names)+(src['desired_labels'][i],)
                 for i in range(n))
    target=pairs(labels)
    require=tuple(sorted(old-target))
    choices={}
    for f, (cost, length, word) in best.items():
        for observation in observations.values():
            if observation['name'] not in granted: continue
            prof=tuple(observation['values'][f[i]] for i in range(n))
            if not target <= pairs(prof):continue
            mask=sum(1<<i for i,(a,b) in enumerate(require) if prof[a]!=prof[b])
            if not mask:continue
            score=(cost+observation['cost'],length+1,word+(observation['name'],))
            if (prof not in choices or score<choices[prof][0]):
                choices[prof]=(score,mask)
    allmask=(1<<len(require))-1
    covered=0
    for _,mask in choices.values(): covered|=mask
    if covered!=allmask:
        return {'status':'UNREALIZABLE_IN_COMPLETE_DECLARED_FINITE_GRAMMAR',
                'basis_cost':None,'unresolved_pairs':[list(require[i]) for i in range(len(require)) if not covered&(1<<i)],
                'transformation_count':len(states),'profile_count':len(choices)}
    # Exhaustively enumerate every subset of distinct source-allowable observation profiles.
    experiments=list(choices.values())
    winner=None
    # Tiny four-state models typically expose <=8 distinct informative profiles.
    assert len(experiments)<=18, 'Oracle budget exceeded: not an impossibility result'
    for bits in range(1<<len(experiments)):
        joint=0;total=0;number=0
        for i,(key,mask) in enumerate(experiments):
            if bits>>i&1:
                joint |= mask;total+=key[0];number+=1
        if joint == allmask:
            rank=(total,number)
            if winner is None or rank<winner:winner=rank
    assert winner is not None
    return {'status':'EXACT_BASIS_CONSTRUCTED','basis_cost':winner[0],
            'basis_size':winner[1],'unresolved_pairs':[],
            'transformation_count':len(states),'profile_count':len(choices)}


def verify_constructed_witness(src, answer):
    protected=src['protected'];n=len(protected)
    source_views={r['name']:r['values'] for r in src['readouts']}
    target=pairs([tuple(source_views[name][i] for name in src['base_readouts'])+(src['desired_labels'][i],) for i in range(n)])
    for obj in answer.get('basis') or []:
        assert obj['program'][-1] in src['base_readouts'] or obj['program'][-1] in [r['name'] for r in src['readouts']]
        value=list(range(n))
        for name in obj['program'][:-1]:
            action=next(o for o in src['operations'] if o['name']==name)
            assert name in src['grants'] and all(protected[i]==protected[action['image'][i]] for i in range(n))
            value=[action['image'][i] for i in value]
        obs=next(o for o in src['readouts'] if o['name']==obj['program'][-1]);assert obs['name'] in src['grants']
        readout=[obs['values'][v] for v in value]
        assert readout==obj['values']
        assert obj['cost']==sum(next(o['cost'] for o in src['operations'] if o['name']==name) for name in obj['program'][:-1])+obs['cost']
        assert target <= pairs(readout)
    base_names=src['base_readouts']; base=[]
    for i in range(n):
        base.append(tuple(next(o for o in src['readouts'] if o['name']==name)['values'][i] for name in base_names))
    full=pairs(base)
    for o in answer.get('basis') or []:full &= pairs(o['values'])
    if answer['status']=='EXACT_BASIS_CONSTRUCTED': assert full==target
    else:assert answer['basis'] is None
    return True


def check_galois():
    """Reimplement 4-state classical adjunction census independently of candidate."""
    pairindex=list(combinations(range(4),2))
    formula=[]
    for function in product((0,1),repeat=4):
        relation=sum(1<<i for i,(a,b) in enumerate(pairindex) if function[a]==function[b])
        formula.append(relation)
    assert len(formula)==16
    partitions=list(all_partitions(4))
    assert len(partitions)==15
    eqs=[sum(1<<i for i,(a,b) in enumerate(pairindex) if p[a]==p[b]) for p in partitions]
    # Small dynamic cache of intersections of the chosen source kernels.
    meets=[63]*65536
    for s in range(1,65536):
        lsb=s&-s
        meets[s]=meets[s^lsb] & formula[lsb.bit_length()-1]
    checked=0
    for r in eqs:
        admissible=sum(1<<j for j,relation in enumerate(formula) if relation & r == r)
        for subset,meet in enumerate(meets):
            lhs=(subset & ~admissible)==0
            rhs=(r & ~meet)==0
            assert lhs==rhs
            checked+=1
    assert checked==983040
    return checked