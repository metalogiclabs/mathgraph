"""Finite Ethereum-style MSI experiment.

The model is intentionally tiny and exact. A state contains balances/nonces for A/B
plus two contract storage slots x/y and an unrelated slot z. Protected observations
are the success/failure and externally relevant post-state of continuations drawn
from a fixed transaction language. We synthesize the coarsest behavioural quotient
by equality of continuation signatures and test whether z is eliminated.

This is a bounded model result, not a claim about full Ethereum semantics.
"""
from dataclasses import dataclass
from itertools import product

@dataclass(frozen=True)
class S:
    a:int; b:int; na:int; nb:int; x:int; y:int; z:int

# Tiny Ethereum-like transaction language.
# transfer reads/writes sender/recipient balance and sender nonce.
# setx/sety read/write sender nonce and one storage slot.
TXS=("AtoB","BtoA","AsetX","BsetY")

def step(s,t):
    a,b,na,nb,x,y,z=s.a,s.b,s.na,s.nb,s.x,s.y,s.z
    if t=="AtoB":
        if a==0: return False,s
        return True,S(a-1,b+1,na+1,nb,x,y,z)
    if t=="BtoA":
        if b==0: return False,s
        return True,S(a+1,b-1,na,nb+1,x,y,z)
    if t=="AsetX": return True,S(a,b,na+1,nb,1-x,y,z)
    if t=="BsetY": return True,S(a,b,na,nb+1,x,1-y,z)
    raise ValueError(t)

def protected(s):
    # z is deliberately not a protected consequence: it is untouched by the
    # transaction family and cannot affect any continuation in this language.
    return (s.a,s.b,s.na,s.nb,s.x,s.y)

def sig(s, depth=2):
    out=[]
    for seq in product(TXS, repeat=depth):
        cur=s; trace=[]
        for t in seq:
            ok,cur=step(cur,t); trace.append(ok)
        out.append((seq,tuple(trace),protected(cur)))
    return tuple(out)

def states():
    # balances 0..2, nonces 0..1, storage bits; z has four noisy values.
    for a,b,na,nb,x,y,z in product(range(3),range(3),range(2),range(2),range(2),range(2),range(4)):
        yield S(a,b,na,nb,x,y,z)

def main():
    ss=list(states())
    groups={}
    for s in ss: groups.setdefault(sig(s),[]).append(s)
    # The synthesized quotient should equal protected projection exactly.
    by_p={}
    for s in ss: by_p.setdefault(protected(s),[]).append(s)
    assert {frozenset(v) for v in groups.values()} == {frozenset(v) for v in by_p.values()}
    assert all(len(v)==4 for v in groups.values()) # all four z values collapse

    # Exact continuation preservation within every quotient class.
    for g in groups.values():
        base=sig(g[0])
        assert all(sig(s)==base for s in g)

    # Causal deletion/ablation: each retained coordinate is necessary.
    # Removing any one protected coordinate must merge a pair with distinct signatures.
    names=("a","b","na","nb","x","y")
    witnesses={}
    for i,name in enumerate(names):
        seen={}
        for s in ss:
            p=list(protected(s)); p.pop(i); k=tuple(p)
            if k in seen and sig(seen[k]) != sig(s):
                witnesses[name]=(seen[k],s); break
            seen[k]=s
        assert name in witnesses, name

    # Parallelization claim: AsetX and BsetY commute on every state, while
    # opposite transfers have an explicit noncommuting witness.
    for s in ss:
        _,u=step(s,"AsetX"); _,uv=step(u,"BsetY")
        _,v=step(s,"BsetY"); _,vu=step(v,"AsetX")
        assert uv==vu
    noncomm=None
    for s in ss:
        _,u=step(s,"AtoB"); _,uv=step(u,"BtoA")
        _,v=step(s,"BtoA"); _,vu=step(v,"AtoB")
        if uv!=vu:
            noncomm=(s,uv,vu); break
    assert noncomm is not None

    print("ETHEREUM_MSI_V1=PASS")
    print(f"full_states={len(ss)} quotient_states={len(groups)} compression={len(ss)/len(groups):.1f}x")
    print("eliminated_coordinate=z")
    print("retained_minimal_coordinates="+",".join(names))
    print("parallel_pair=AsetX,BsetY universally_commutes=true")
    print("ordered_pair=AtoB,BtoA noncommuting_witness=true")
    print("ablation_witnesses="+",".join(sorted(witnesses)))

if __name__=="__main__": main()
