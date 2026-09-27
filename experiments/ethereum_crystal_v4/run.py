"""Ethereum Crystal v4: failure-generated interface capability compounding.

Uses the same epistemic shape as DEVELOPMENTAL_CAPABILITY_GROWTH_V1:
old closure failure -> obstruction witness -> frozen candidate refinement ->
verified repair -> ablation -> source-distinct held-out reuse at zero acquisition.

Domain: typed EIP-7928 consequence interfaces.
"""
from dataclasses import dataclass
from itertools import product

@dataclass(frozen=True)
class E:
    account:int; slot:int; pre:int; post:int; read:int

WORLD=tuple(E(*x) for x in product((0,1),repeat=5))

def changed(e): return int(e.pre!=e.post)
def touched(e): return int(bool(e.read) or bool(changed(e)))
def dep(e): return (e.account,e.slot) if touched(e) else (e.account,None)
def rec(e): return (e.account,e.slot,e.post) if changed(e) else None

# Initial interface intentionally confounds read-only access with no access and
# confounds post-value distinctions. This models an underpowered state-diff lens.
def f_account(e): return e.account
def f_changed(e): return changed(e)
def f_slot(e): return e.slot
def f_read(e): return e.read
def f_post(e): return e.post
def f_pre(e): return e.pre
CANDIDATES=(("slot",f_slot),("read",f_read),("post",f_post),("pre",f_pre))

def key(e,features): return tuple(f(e) for _,f in features)
def conflicts(features,target):
    cells={}
    for e in WORLD: cells.setdefault(key(e,features),[]).append(e)
    out=[]
    for k,xs in cells.items():
        vals={target(x) for x in xs}
        if len(vals)>1: out.append((k,xs,vals))
    return out
def closes(features,target): return not conflicts(features,target)

def acquire(features,target,available):
    """Cheapest decisive one-feature repair from a frozen family."""
    good=[]
    for n,f in available:
        ext=features+((n,f),)
        if closes(ext,target): good.append((n,f))
    return good

def main():
    base=(("account",f_account),("changed",f_changed))

    # Generation 1: dependency target. One-step repair is impossible: this is a
    # real residual requiring recursive acquisition.
    assert not closes(base,dep)
    g1=acquire(base,dep,CANDIDATES)
    assert g1==[], g1

    # Crystal residual recursion: score candidates by strict conflict reduction,
    # promote the unique best separator, then retry closure.
    before=len(conflicts(base,dep))
    scored=[]
    for n,f in CANDIDATES:
        ext=base+((n,f),); scored.append((len(conflicts(ext,dep)),n,f))
    scored.sort(key=lambda z:(z[0],z[1]))
    best_count,best_name,best_fn=scored[0]
    assert best_count<before
    # In this domain slot is the first structural separator.
    assert best_name=="slot", scored
    cap1=base+((best_name,best_fn),)

    g2=acquire(cap1,dep,tuple(x for x in CANDIDATES if x[0]!=best_name))
    assert [n for n,_ in g2]==["read"], [n for n,_ in g2]
    cap2=cap1+(g2[0],)
    assert closes(cap2,dep)

    # Causal ablation restores failure.
    assert not closes(tuple(x for x in cap2 if x[0]!="slot"),dep)
    assert not closes(tuple(x for x in cap2 if x[0]!="read"),dep)

    # Source-distinct held-out task: reconstruction. Existing slot capability
    # transfers for free; only post is newly required. Compare acquisition from
    # scratch vs from retained capability.
    assert not closes(base,rec)
    scratch1=acquire(base,rec,CANDIDATES)
    # Again no one-step closure from scratch.
    assert scratch1==[]

    retained=cap1 # reuse structural slot capability learned from dependency
    transfer=acquire(retained,rec,tuple(x for x in CANDIDATES if x[0]!="slot"))
    assert [n for n,_ in transfer]==["post"], [n for n,_ in transfer]
    cap3=retained+(transfer[0],)
    assert closes(cap3,rec)

    # Zero-rediscovery: slot was not reacquired on held-out reconstruction.
    heldout_acquisitions=[transfer[0][0]]
    assert "slot" not in heldout_acquisitions

    # Compound combined interface from retained verified capabilities.
    combined_names={n for n,_ in cap2}|{n for n,_ in cap3}
    combined=tuple((n,dict(base+CANDIDATES)[n]) for n in ("account","changed","slot","read","post") if n in combined_names)
    assert closes(combined,dep) and closes(combined,rec)

    print("ETHEREUM_CRYSTAL_V4=PASS")
    print(f"dependency_conflicts_initial={before} after_first_separator={best_count}")
    print("generation1_promoted=slot")
    print("generation2_promoted=read dependency_closed=true")
    print("heldout_target=reconstruction")
    print("heldout_reused=slot acquisition_cost=0")
    print("heldout_new_acquisition=post")
    print("ablation_slot=FAIL_RESTORED ablation_read=FAIL_RESTORED")
    print("combined_interface_closes_dependency_and_reconstruction=true")

if __name__=="__main__": main()
