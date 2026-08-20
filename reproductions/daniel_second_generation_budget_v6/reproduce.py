#!/usr/bin/env python3
"""V6 — resource-indexed second-generation constructibility."""
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

def family(blocks,a1,a2):
    n=sum(blocks)
    return tuple(Case(blocks,y1,y2) for y1 in product(range(a1),repeat=n) for y2 in product(range(a2),repeat=n))

ACQUISITION=family((2,2),2,2)
HELDOUT=family((1,3),3,2)+family((2,3),2,3)
assert len(ACQUISITION)==256
assert len(HELDOUT)==9072

@dataclass(frozen=True)
class Expr:
    op:str; a:"Expr|None"=None; b:"Expr|None"=None
    def size(self):
        if self.op in {"E","O1","O2","I","U"}: return 1
        if self.op in {"C","T"}: return 1+self.a.size()
        return 1+self.a.size()+self.b.size()
    def pretty(self):
        if self.op in {"E","O1","O2","I","U"}: return self.op
        if self.op=="C": return f"not({self.a.pretty()})"
        if self.op=="T": return f"converse({self.a.pretty()})"
        return f"({self.a.pretty()} {self.op} {self.b.pretty()})"

def evaluate(e,c,mode="cold"):
    if e.op=="E": return c.E
    if e.op=="O1": return c.O1
    if e.op=="O2": return c.O2
    if e.op=="I": return identity(c.n)
    if e.op=="U": return universe(c.n)
    if e.op=="C": return universe(c.n)-evaluate(e.a,c,mode)
    if e.op=="T": return frozenset((j,i) for i,j in evaluate(e.a,c,mode))
    a,b=evaluate(e.a,c,mode),evaluate(e.b,c,mode)
    if e.op=="&": return a&b
    if e.op=="|": return a|b
    if e.op=="K":
        if mode=="warm": return a-b
        if mode=="sham_inter": return a&b
        if mode=="sham_union": return a|b
        raise ValueError("K absent")
    raise ValueError(e.op)

def search(cases,mode,max_size):
    target=tuple(c.target for c in cases)
    terms=[Expr(x) for x in ("E","O1","O2","I","U")]
    by={1:terms}; seen={}
    for e in terms: seen.setdefault(tuple(evaluate(e,c,mode) for c in cases),e)
    for size in range(1,max_size+1):
        if target in seen and seen[target].size()==size: return seen[target],size
        if size==max_size: break
        ns=size+1; cand=[]
        for x in by.get(ns-1,[]): cand += [Expr("C",x),Expr("T",x)]
        for ls in range(1,ns-1):
            rs=ns-1-ls
            for l in by.get(ls,[]):
                for r in by.get(rs,[]):
                    ops=["&","|"] + (["K"] if mode!="cold" else [])
                    for op in ops: cand.append(Expr(op,l,r))
        local={}
        for e in cand:
            sig=tuple(evaluate(e,c,mode) for c in cases)
            if sig not in seen and sig not in local: local[sig]=e
        by[ns]=list(local.values()); seen.update(local)
    return None

COLD=search(ACQUISITION,"cold",6)
WARM=search(ACQUISITION,"warm",5)
assert COLD is not None and COLD[1]==6
assert COLD[0].pretty()=="(E & not((O1 | O2)))"
assert search(ACQUISITION,"cold",5) is None
assert WARM is not None and WARM[1]==5
assert WARM[0].pretty()=="(E K (O1 | O2))"
assert search(ACQUISITION,"sham_inter",5) is None
assert search(ACQUISITION,"sham_union",5) is None

WARM_LAW=WARM[0]
heldout_warm=sum(evaluate(WARM_LAW,c,"warm")==c.target for c in HELDOUT)
assert heldout_warm==9072
assert search(HELDOUT,"cold",5) is None

def expand_k(e):
    if e.op in {"E","O1","O2","I","U"}: return e
    if e.op=="K": return Expr("&",expand_k(e.a),Expr("C",expand_k(e.b)))
    if e.op in {"C","T"}: return Expr(e.op,expand_k(e.a))
    return Expr(e.op,expand_k(e.a),expand_k(e.b))

EXPANDED=expand_k(WARM_LAW)
assert EXPANDED.size()==6
assert EXPANDED.pretty()==COLD[0].pretty()
assert all(evaluate(EXPANDED,c,"cold")==evaluate(WARM_LAW,c,"warm") for c in HELDOUT)

result={
 "protocol":"DANIEL_SECOND_GENERATION_BUDGET_V6",
 "verdict":"PASS_RESOURCE_INDEXED_SECOND_GENERATION_CONSTRUCTIBILITY",
 "precommit":"c916863cbeddfc65bcdad61530dcfd0b5db65e9b",
 "resource_budget_ast_nodes":5,
 "acquisition_cases":256,
 "heldout_cases":9072,
 "cold":{"shortest_size":COLD[1],"law":COLD[0].pretty(),"constructible_within_budget":False},
 "warm":{"shortest_size":WARM[1],"law":WARM_LAW.pretty(),"constructible_within_budget":True,"heldout_exact":heldout_warm},
 "shams":{"intersection_macro_within_budget":False,"union_macro_within_budget":False},
 "macro_expansion":{"expanded_law":EXPANDED.pretty(),"expanded_size":EXPANDED.size(),"unbounded_semantic_growth_claimed":False},
 "claim":"Retaining the learned repair capability changes the later law's constructibility under the frozen H=5 AST budget: cold minimum 6, warm minimum 5, with exact transfer to all 9,072 held-outs.",
 "boundary":"The warm law macro-expands exactly to the cold size-6 law. This is resource-indexed CapReach_H growth, not absolute semantic-language growth."
}
print(json.dumps(result,indent=2,sort_keys=True))
