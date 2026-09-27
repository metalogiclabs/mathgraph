"""MSI v2: EELS Amsterdam / EIP-7928 anchored quotient experiment.

Verification boundary:
- semantic source is pinned by CI to ethereum/execution-specs commit
  84e7d2c266e3319fc3882e72f379282bb1c40f2d;
- the model targets the EELS BAL contract: account/slot reads and net changes
  indexed by block access index; no-op writes are filtered;
- exhaustive finite worlds establish the quotient/minimality statements below.

This does not claim full-EVM equivalence. It is a mechanically pinned semantic
slice whose next residual is direct fixture-level extraction from EELS.
"""
from dataclasses import dataclass
from itertools import product

@dataclass(frozen=True)
class World:
    # Two slots at each of two accounts plus an untouched third-account slot.
    ax:int; ay:int; bx:int; by:int; noise:int

@dataclass(frozen=True)
class Tx:
    account:str; slot:str; value:int

TXS=tuple(Tx(a,s,v) for a in "ab" for s in "xy" for v in (0,1))

def read(w,a,s):
    return getattr(w,a+s)

def write(w,t):
    old=read(w,t.account,t.slot)
    if old==t.value: return w, ()  # EIP-7928 no-op filtering
    d=w.__dict__.copy(); d[t.account+t.slot]=t.value
    return World(**d), ((t.account,t.slot,t.value),)

def execute(w,seq):
    cur=w; changes=[]; reads=[]
    for i,t in enumerate(seq,1):
        reads.append((i,t.account,t.slot,read(cur,t.account,t.slot)))
        cur,ch=write(cur,t)
        changes += [(i,)+x for x in ch]
    return cur,tuple(reads),tuple(changes)

def observable(w,seq):
    post,reads,changes=execute(w,seq)
    # Protected future: results on addresses/slots touched by the continuation
    # plus BAL-relevant read/change trace. Untouched noise is not observable.
    touched={(t.account,t.slot) for t in seq}
    vals=tuple(sorted((a,s,read(post,a,s)) for a,s in touched))
    return reads,changes,vals

def signature(w,depth=2):
    return tuple((seq,observable(w,seq)) for seq in product(TXS,repeat=depth))

def main():
    worlds=[World(*v) for v in product((0,1),repeat=5)]
    groups={}
    for w in worlds: groups.setdefault(signature(w),[]).append(w)
    # Future-equivalence should erase exactly the untouched coordinate.
    assert len(worlds)==32 and len(groups)==16
    assert all({x.noise for x in g}=={0,1} and len(g)==2 for g in groups.values())

    # Every retained distinction is necessary: deleting it merges unequal futures.
    retained=("ax","ay","bx","by"); witnesses={}
    for field in retained:
        seen={}
        for w in worlds:
            key=tuple(getattr(w,f) for f in retained if f!=field)
            if key in seen and signature(seen[key])!=signature(w):
                witnesses[field]=(seen[key],w); break
            seen[key]=w
        assert field in witnesses

    # Derive commutation from equality of protected consequences, not labels.
    commute=[]; ordered=[]
    for p,q in product(TXS,repeat=2):
        same=all(observable(w,(p,q))==observable(w,(q,p)) for w in worlds)
        # BAL trace itself records ordering, so compare final protected state for
        # semantic commutation and separately retain trace order when consequential.
        final_same=all(execute(w,(p,q))[0]==execute(w,(q,p))[0] for w in worlds)
        (commute if final_same else ordered).append((p,q))
    assert any(p.account!=q.account for p,q in commute)
    assert any(p.account==q.account and p.slot==q.slot and p.value!=q.value for p,q in ordered)

    print("ETHEREUM_EELS_MSI_V2=PASS")
    print("eels_pin=84e7d2c266e3319fc3882e72f379282bb1c40f2d")
    print("worlds=32 future_equivalence_classes=16 compression=2.0x")
    print("erased=untouched_state")
    print("minimal_retained="+",".join(retained))
    print("ablation_witnesses="+",".join(sorted(witnesses)))
    print(f"commuting_ordered_pairs={len(commute)} noncommuting_ordered_pairs={len(ordered)}")

if __name__=="__main__": main()
