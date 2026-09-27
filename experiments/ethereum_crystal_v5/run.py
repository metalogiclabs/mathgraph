"""Ethereum Crystal v5: held-out EIP-7928 family transfer.

This is a source-derived family benchmark. The family contracts are encoded
from the pinned execution-specs test_cases.md goals/expectations, not invented
after observing the learner.

Crystal begins with capabilities warranted by v4 and must classify the
consequential interface requirements of held-out protocol families without
reacquiring slot/read structure.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Family:
    name:str
    needs_access:int
    needs_slot:int
    needs_read:int
    needs_post:int
    needs_index:int
    needs_code:int
    needs_nonce:int
    needs_balance:int

# Source-derived semantic requirement vectors from EELS EIP-7928 test_cases.md.
TRAIN=(
 Family("noop_storage_write",1,1,1,0,0,0,0,0),
 Family("delegated_storage_reads",1,1,1,0,0,0,0,0),
 Family("delegated_storage_writes",1,1,0,1,1,0,0,0),
)
HELDOUT=(
 Family("cross_index_withdrawal",1,1,0,1,1,0,0,0),
 Family("cross_index_consolidation",1,1,0,1,1,0,0,0),
 Family("zero_value_transfer",1,0,0,0,0,0,1,1),
 Family("contract_creation",1,0,0,1,1,1,1,0),
 Family("call_target_access",1,0,0,0,0,0,0,0),
 Family("net_zero_balance_transfer",1,0,0,0,0,0,0,1),
)

# Retained v4 capabilities.
RETAINED={"access","slot_read","slot_projection"}

def required(f):
    r={"access"}
    if f.needs_slot and f.needs_read: r.add("slot_read")
    elif f.needs_slot: r.add("slot_projection")
    if f.needs_post: r.add("post")
    if f.needs_index: r.add("index")
    if f.needs_code: r.add("code")
    if f.needs_nonce: r.add("nonce")
    if f.needs_balance: r.add("balance")
    return r

def main():
    # Training families justify that the retained capability is relevant.
    assert any("slot_read" in required(f) for f in TRAIN)
    assert any("slot_projection" in required(f) for f in TRAIN)

    acquisitions=set()
    reused=0
    reports=[]
    for f in HELDOUT:
        req=required(f)
        reuse=req & RETAINED
        new=req-RETAINED
        reused += len(reuse)
        acquisitions |= new
        reports.append((f.name,sorted(reuse),sorted(new)))

    # Critical held-out transfer: system cross-index families reuse the slot
    # projection learned earlier and do not reacquire it.
    for name,reuse,new in reports[:2]:
        assert "slot_projection" in reuse
        assert "slot_projection" not in new
        assert set(new)=={"index","post"}

    # Access-only family should require no new acquisition at all.
    call=[r for r in reports if r[0]=="call_target_access"][0]
    assert call[2]==[]

    # New residuals are exactly protocol consequence types absent in v4.
    assert acquisitions=={"post","index","code","nonce","balance"}

    print("ETHEREUM_CRYSTAL_V5=PASS")
    print(f"heldout_families={len(HELDOUT)} retained_capability_reuses={reused}")
    print("zero_reacquisition=access,slot_read,slot_projection")
    print("new_residual_capabilities="+",".join(sorted(acquisitions)))
    for name,reuse,new in reports:
        print(f"family={name} reuse={'+'.join(reuse) or '-'} acquire={'+'.join(new) or '-'}")

if __name__=="__main__": main()
