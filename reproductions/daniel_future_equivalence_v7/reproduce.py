#!/usr/bin/env python3
"""V7 — resource-indexed developmental future equivalence."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
import json

Relation=frozenset[tuple[int,int]]

def universe(n): return frozenset((i,j) for i in range(n) for j in range(n))
def identity(n): return frozenset((i,i) for i in range(n))
def parent_equivalence(blocks):
    out=set(); s=0
    for z in blocks:
        b=range(s,s+z); s+=z
        out |= {(i,j) for i in b for j in b}
    return frozenset(out)
def obstruction(E,labels): return frozenset((i,j) for i,j in E if labels[i]!=labels[j])

@dataclass(frozen=True)
class Case:
    blocks:tuple[int,...]; y1:tuple[int,...]; y2:tuple[int,...]
    @property
    def n(self): return sum(self.blocks)
    @property
    def E(self): return parent_equivalence(self.blocks)
    @property
    def O1(self): return obstruction(self.E,self.y1)
    @property
    def E1(self): return self.E-self.O1
    @property
    def O2(self): return obstruction(self.E1,self.y2)
    @property
    def target(self): return self.E1-self.O2

CASES=tuple(Case((1,2,2),y1,y2) for y1 in product(range(2),repeat=5) for y2 in product(range(2),repeat=5))
assert len(CASES)==1024

@dataclass(frozen=True)
class Expr:
    op:str; a:"Expr|None"=None; b:"Expr|None"=None

def evaluate(e,c,warm):
    if e.op=="E": return c.E
    if e.op=="O1": return c.O1
    if e.op=="O2": return c.O2
    if e.op=="I": return identity(c.n)
    if e.op=="U": return universe(c.n)
    if e.op=="C": return universe(c.n)-evaluate(e.a,c,warm)
    if e.op=="T": return frozenset((j,i) for i,j in evaluate(e.a,c,warm))
    a,b=evaluate(e.a,c,warm),evaluate(e.b,c,warm)
    if e.op=="&": return a&b
    if e.op=="|": return a|b
    if e.op=="K":
        assert warm
        return a-b
    raise ValueError(e.op)

def semantic_closure(cases,warm,max_size):
    terms=[Expr(x) for x in ("E","O1","O2","I","U")]
    by={1:terms}; seen={}
    for e in terms: seen.setdefault(tuple(evaluate(e,c,warm) for c in cases),e)
    cumulative={1:len(seen)}
    snapshots={1:set(seen)}
    for size in range(2,max_size+1):
        cand=[]
        for x in by.get(size-1,[]): cand += [Expr("C",x),Expr("T",x)]
        for ls in range(1,size-1):
            rs=size-1-ls
            for l in by.get(ls,[]):
                for r in by.get(rs,[]):
                    for op in (["&","|","K"] if warm else ["&","|"]): cand.append(Expr(op,l,r))
        local={}
        for e in cand:
            sig=tuple(evaluate(e,c,warm) for c in cases)
            if sig not in seen and sig not in local: local[sig]=e
        by[size]=list(local.values()); seen.update(local)
        cumulative[size]=len(seen); snapshots[size]=set(seen)
    return seen,cumulative,snapshots

cold_all,cold_counts,cold_snap=semantic_closure(CASES,False,10)
warm_all,warm_counts,warm_snap=semantic_closure(CASES,True,10)

cold5=cold_snap[5]; warm5=warm_snap[5]
assert len(cold5)==23
assert len(warm5)==26
assert cold5 < warm5
assert len(warm5-cold5)==3
TARGET_SIG=tuple(c.target for c in CASES)
assert TARGET_SIG in warm5 and TARGET_SIG not in cold5

# Unbounded semantic equality follows structurally: cold is a sublanguage of warm,
# while every K(a,b) macro-expands to a & not(b) in the cold language.
# Finite enumeration provides a separate sanity check on this suite.
assert len(cold_all)==len(warm_all)==32
assert set(cold_all)==set(warm_all)
assert cold_counts[8]==cold_counts[9]==cold_counts[10]==32
assert warm_counts[8]==warm_counts[9]==warm_counts[10]==32

result={
 "protocol":"DANIEL_FUTURE_EQUIVALENCE_V7",
 "verdict":"PASS_RESOURCE_INDEXED_FUTURE_NONEQUIVALENCE",
 "precommit":"9a5c5cb44b1d42f5c8cab899d1f519e59e8ceb6d",
 "cases":1024,
 "H":5,
 "cold_future_H":len(cold5),
 "warm_future_H":len(warm5),
 "warm_only_future_behaviors":len(warm5-cold5),
 "v6_target_is_warm_only_at_H":True,
 "future_equivalent_at_H":False,
 "unbounded_semantic_closure_equal_by_macro_expansion":True,
 "finite_saturation_cold":cold_counts,
 "finite_saturation_warm":warm_counts,
 "finite_saturated_semantics":32,
 "claim":"On the complete frozen 1,024-case suite, installing the learned capability changes the extensional set of law behaviors reachable within H=5 from 23 to 26, while macro expansion proves unbounded semantic closure is unchanged.",
 "boundary":"This is a finite resource-indexed future-equivalence witness, not a universal definition of developmental state and not a transfer of the ETP theorem."
}
print(json.dumps(result,indent=2,sort_keys=True))
