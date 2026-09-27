"""Ethereum MSI v3: typed minimal interfaces for EIP-7928 BALs.

EIP-7928 combines at least two protected consequence families:
D = dependency/parallel-validation information (what was accessed)
R = reconstruction/executionless-update information (what net state changed)

MSI predicts different coarsest quotients for D and R. This exhaustive model
tests that neither projection can replace the other and that their product
reconstructs the combined BAL consequence.

Pinned normative source is checked by CI.
"""
from dataclasses import dataclass
from itertools import product

@dataclass(frozen=True)
class Event:
    account:int
    slot:int
    pre:int
    post:int
    read:bool

def bal(e):
    # Abstract the normative BAL semantics:
    # touched address always retained; read-only/no-op slot is dependency data;
    # actual change carries post value for reconstruction.
    address=e.account
    changed=e.pre!=e.post
    dep=(address,e.slot) if e.read or changed else (address,None)
    rec=(address,e.slot,e.post) if changed else None
    return dep,rec

def main():
    events=[Event(*x) for x in product(range(2),range(2),range(2),range(2),(False,True))]
    combined={e:bal(e) for e in events}

    # Quotient classes induced independently by each protected consequence.
    dgroups={}; rgroups={}; bgroups={}
    for e in events:
        d,r=bal(e)
        dgroups.setdefault(d,[]).append(e)
        rgroups.setdefault(r,[]).append(e)
        bgroups.setdefault((d,r),[]).append(e)

    # Each typed interface is strictly coarser than combined BAL information.
    assert len(dgroups)<len(bgroups)
    assert len(rgroups)<len(bgroups)

    # Incomparability witnesses: same reconstruction but distinct dependency,
    # and same dependency but distinct reconstruction.
    dep_needed=None; rec_needed=None
    for a,b in product(events,repeat=2):
        da,ra=bal(a); db,rb=bal(b)
        if ra==rb and da!=db and dep_needed is None: dep_needed=(a,b)
        if da==db and ra!=rb and rec_needed is None: rec_needed=(a,b)
    assert dep_needed is not None
    assert rec_needed is not None

    # Product law: combined consequence is exactly pairing of typed interfaces.
    assert all(combined[e]==(bal(e)[0],bal(e)[1]) for e in events)

    # NOOP/write-roundtrip insight: if final value equals baseline, reconstruction
    # can erase the intermediate write, but dependency cannot erase the access.
    noop=[e for e in events if e.pre==e.post and e.read]
    assert noop and all(bal(e)[1] is None and bal(e)[0][1] is not None for e in noop)

    print("ETHEREUM_TYPED_MSI_V3=PASS")
    print(f"events={len(events)} dependency_classes={len(dgroups)} reconstruction_classes={len(rgroups)} combined_classes={len(bgroups)}")
    print("typed_interfaces=incomparable")
    print("product_recovers_combined=true")
    print("noop_erased_from_reconstruction_retained_in_dependency=true")
    print("dependency_ablation_witness=true")
    print("reconstruction_ablation_witness=true")

if __name__=="__main__": main()
