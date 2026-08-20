#!/usr/bin/env python3
"""V5 — closure-relative law identity across two relational DSL presentations."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from collections import defaultdict
import json

Relation = frozenset[tuple[int,int]]

def universe(n): return frozenset((i,j) for i in range(n) for j in range(n))
def identity(n): return frozenset((i,i) for i in range(n))
def converse(r): return frozenset((j,i) for i,j in r)
def parent_equivalence(blocks):
    out=set(); start=0
    for size in blocks:
        block=range(start,start+size); start += size
        out |= {(i,j) for i in block for j in block}
    return frozenset(out)

def obstruction(E,labels): return frozenset((i,j) for i,j in E if labels[i] != labels[j])
def target_kernel(E,labels): return frozenset((i,j) for i,j in E if labels[i] == labels[j])

@dataclass(frozen=True)
class Case:
    blocks: tuple[int,...]
    arity: int
    labels: tuple[int,...]
    @property
    def n(self): return sum(self.blocks)
    @property
    def E(self): return parent_equivalence(self.blocks)
    @property
    def O(self): return obstruction(self.E,self.labels)
    @property
    def target(self): return target_kernel(self.E,self.labels)

def family(blocks,arity):
    return tuple(Case(blocks,arity,l) for l in product(range(arity),repeat=sum(blocks)))

ACQUISITION = family((2,3),2) + family((1,2,2),3)
HELDOUT = family((2,2,2),4) + family((1,3,3),2)
assert len(ACQUISITION) == 275
assert len(HELDOUT) == 4224

@dataclass(frozen=True)
class AExpr:
    op:str; a:"AExpr|None"=None; b:"AExpr|None"=None
    def size(self): return 1 if self.op in {"E","O","I","U"} else (1+self.a.size() if self.op=="T" else 1+self.a.size()+self.b.size())
    def pretty(self):
        if self.op in {"E","O","I","U"}: return self.op
        if self.op=="T": return f"converse({self.a.pretty()})"
        return f"({self.a.pretty()} {self.op} {self.b.pretty()})"

def eval_a(e,c,override_O=None):
    if e.op=="E": return c.E
    if e.op=="O": return c.O if override_O is None else override_O
    if e.op=="I": return identity(c.n)
    if e.op=="U": return universe(c.n)
    if e.op=="T": return converse(eval_a(e.a,c,override_O))
    a,b=eval_a(e.a,c,override_O),eval_a(e.b,c,override_O)
    return {"&":a&b,"|":a|b,"\\":a-b}[e.op]

@dataclass(frozen=True)
class BExpr:
    op:str; a:"BExpr|None"=None; b:"BExpr|None"=None
    def size(self): return 1 if self.op in {"E","O","I","U"} else (1+self.a.size() if self.op in {"T","C"} else 1+self.a.size()+self.b.size())
    def pretty(self):
        if self.op in {"E","O","I","U"}: return self.op
        if self.op=="T": return f"converse({self.a.pretty()})"
        if self.op=="C": return f"not({self.a.pretty()})"
        return f"({self.a.pretty()} {self.op} {self.b.pretty()})"

def eval_b(e,c,override_O=None):
    if e.op=="E": return c.E
    if e.op=="O": return c.O if override_O is None else override_O
    if e.op=="I": return identity(c.n)
    if e.op=="U": return universe(c.n)
    if e.op=="T": return converse(eval_b(e.a,c,override_O))
    if e.op=="C": return universe(c.n)-eval_b(e.a,c,override_O)
    a,b=eval_b(e.a,c,override_O),eval_b(e.b,c,override_O)
    return {"&":a&b,"|":a|b}[e.op]

def search_a(cases,max_size=5):
    target=tuple(c.target for c in cases); by={1:[AExpr(x) for x in ("E","O","I","U")]}; seen={}
    for e in by[1]: seen.setdefault(tuple(eval_a(e,c) for c in cases),e)
    for size in range(1,max_size+1):
        if size>1:
            cand=[]
            for x in by.get(size-1,[]): cand.append(AExpr("T",x))
            for ls in range(1,size-1):
                rs=size-1-ls
                for l in by.get(ls,[]):
                    for r in by.get(rs,[]):
                        for op in ("&","|","\\"): cand.append(AExpr(op,l,r))
            local={}
            for e in cand:
                sig=tuple(eval_a(e,c) for c in cases)
                if sig not in seen and sig not in local: local[sig]=e
            by[size]=list(local.values()); seen.update(local)
        if target in seen and seen[target].size()==size: return seen[target],size
    raise AssertionError("DSL A found no law")

def search_b(cases,max_size=6):
    target=tuple(c.target for c in cases); by={1:[BExpr(x) for x in ("E","O","I","U")]}; seen={}
    for e in by[1]: seen.setdefault(tuple(eval_b(e,c) for c in cases),e)
    for size in range(1,max_size+1):
        if size>1:
            cand=[]
            for x in by.get(size-1,[]): cand += [BExpr("T",x),BExpr("C",x)]
            for ls in range(1,size-1):
                rs=size-1-ls
                for l in by.get(ls,[]):
                    for r in by.get(rs,[]):
                        for op in ("&","|"): cand.append(BExpr(op,l,r))
            local={}
            for e in cand:
                sig=tuple(eval_b(e,c) for c in cases)
                if sig not in seen and sig not in local: local[sig]=e
            by[size]=list(local.values()); seen.update(local)
        if target in seen and seen[target].size()==size: return seen[target],size
    raise AssertionError("DSL B found no law")

LAW_A,SIZE_A=search_a(ACQUISITION)
LAW_B,SIZE_B=search_b(ACQUISITION)
assert LAW_A.pretty()=="(E \\ O)" and SIZE_A==3
assert LAW_B.pretty()=="(E & not(O))" and SIZE_B==4
assert LAW_A.pretty()!=LAW_B.pretty()

exact_a=exact_b=same=0
for c in HELDOUT:
    a,b=eval_a(LAW_A,c),eval_b(LAW_B,c)
    exact_a += a==c.target
    exact_b += b==c.target
    same += a==b
assert exact_a==exact_b==same==4224

strict=[c for c in HELDOUT if c.target!=c.E]
empty=frozenset()
no_o_a=sum(eval_a(LAW_A,c,empty)!=c.target for c in strict)
no_o_b=sum(eval_b(LAW_B,c,empty)!=c.target for c in strict)
assert len(strict)==no_o_a==no_o_b==4152

result={
  "protocol":"DANIEL_LAW_IDENTITY_V5",
  "verdict":"PASS_CROSS_DSL_BEHAVIORAL_LAW_IDENTITY",
  "precommit":"9b43530fe9d204f60d5f614a6fd1377b774eb43b",
  "acquisition_cases":len(ACQUISITION),
  "heldout_cases":len(HELDOUT),
  "dsl_a":{"difference_present":True,"law":LAW_A.pretty(),"size":SIZE_A},
  "dsl_b":{"difference_present":False,"complement_present":True,"law":LAW_B.pretty(),"size":SIZE_B},
  "literal_programs_different":True,
  "heldout_exact_a":exact_a,
  "heldout_exact_b":exact_b,
  "heldout_extensional_agreement":same,
  "strict_heldout_cases":len(strict),
  "no_obstruction_failures_a":no_o_a,
  "no_obstruction_failures_b":no_o_b,
  "claim":"Two supplied generic relational DSLs independently synthesize different shortest programs with identical verified repair behavior on all 4,224 held-out cases.",
  "boundary":"Behavioral identity is established only relative to these DSLs and verifier semantics; this is not a universal theory of capability identity."
}
print(json.dumps(result,indent=2,sort_keys=True))
