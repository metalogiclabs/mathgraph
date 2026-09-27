#!/usr/bin/env python3
"""V8 exact reassembly and EIP-7928 hash qualification.

Consumes the realized EELS fixtures. Decomposes each BAL into the exact
capabilities promoted by fixture-native Crystal V7, reassembles the canonical
BAL object, and checks both structural equality and the block header BAL hash
using Ethereum's own BlockAccessList implementation.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from typing import Any
from execution_testing import BlockAccessList

CAPS=("addresses","storage_reads","storage_change_slots",
      "storage_change_payloads","balance_changes","nonce_changes","code_changes")

def freeze(x:Any)->Any:
    return json.loads(json.dumps(x))

def features(bal:list[dict])->dict[str,Any]:
    return {
      "addresses":[a.get("address") for a in bal],
      "storage_reads":{i:freeze(a.get("storageReads",[])) for i,a in enumerate(bal) if a.get("storageReads")},
      "storage_change_slots":{i:[s.get("slot") for s in a.get("storageChanges",[])] for i,a in enumerate(bal) if a.get("storageChanges")},
      "storage_change_payloads":{i:[freeze(s.get("slotChanges",[])) for s in a.get("storageChanges",[])] for i,a in enumerate(bal) if a.get("storageChanges")},
      "balance_changes":{i:freeze(a.get("balanceChanges",[])) for i,a in enumerate(bal) if a.get("balanceChanges")},
      "nonce_changes":{i:freeze(a.get("nonceChanges",[])) for i,a in enumerate(bal) if a.get("nonceChanges")},
      "code_changes":{i:freeze(a.get("codeChanges",[])) for i,a in enumerate(bal) if a.get("codeChanges")},
    }

def reassemble(f:dict[str,Any], selected:set[str])->list[dict]:
    addresses=f["addresses"] if "addresses" in selected else []
    out=[]
    for i,address in enumerate(addresses):
        slots=f["storage_change_slots"].get(i,[]) if "storage_change_slots" in selected else []
        payloads=f["storage_change_payloads"].get(i,[]) if "storage_change_payloads" in selected else []
        storage=[]
        if "storage_change_slots" in selected and "storage_change_payloads" in selected:
            assert len(slots)==len(payloads)
            storage=[{"slot":s,"slotChanges":p} for s,p in zip(slots,payloads)]
        out.append({
          "address":address,
          "storageChanges":storage,
          "storageReads":f["storage_reads"].get(i,[]) if "storage_reads" in selected else [],
          "balanceChanges":f["balance_changes"].get(i,[]) if "balance_changes" in selected else [],
          "nonceChanges":f["nonce_changes"].get(i,[]) if "nonce_changes" in selected else [],
          "codeChanges":f["code_changes"].get(i,[]) if "code_changes" in selected else [],
        })
    return out

def normhex(x)->str:
    return "0x"+bytes(x).hex()

def main():
    root=Path(sys.argv[1])
    records=[]
    for path in sorted((root/"blockchain_tests").rglob("*.json")):
        obj=json.loads(path.read_text())
        for test_id,fixture in obj.items():
            if not isinstance(fixture,dict): continue
            for block in fixture.get("blocks",[]):
                if not isinstance(block,dict): continue
                bal=block.get("blockAccessList")
                h=(block.get("blockHeader") or {}).get("blockAccessListHash")
                if isinstance(bal,list) and isinstance(h,str):
                    records.append((path.stem,test_id,bal,h))
    assert records, "no BAL/hash records"

    selected=set(CAPS)
    equality=0; hash_ok=0
    for family,test_id,bal,expected_hash in records:
        f=features(bal)
        rebuilt=reassemble(f,selected)
        assert rebuilt==bal, (family,test_id,"structural mismatch")
        equality+=1
        calc=normhex(BlockAccessList(root=rebuilt).rlp_hash)
        assert calc.lower()==expected_hash.lower(), (family,test_id,calc,expected_hash)
        hash_ok+=1

    # Causal ablation over the realized corpus: removing each promoted
    # capability must break exact reconstruction somewhere.
    ablation={}
    for cap in CAPS:
        bad=0
        for _,_,bal,_ in records:
            rebuilt=reassemble(features(bal),selected-{cap})
            if rebuilt!=bal:
                bad+=1
        ablation[cap]=bad
        assert bad>0, (cap,"no realized consequence")

    cert={
      "protocol":"ETHEREUM_CRYSTAL_V8_EXACT_BAL_REASSEMBLY",
      "records":len(records),
      "structural_equalities":equality,
      "eip7928_hash_matches":hash_ok,
      "capabilities":list(CAPS),
      "ablation_break_counts":ablation,
      "verdict":"PASS_EXACT_REASSEMBLY_AND_HASH",
      "claim_boundary":"pinned generated EELS blockchain fixtures in selected EIP-7928 families"
    }
    out=Path(sys.argv[2]) if len(sys.argv)>2 else None
    if out: out.write_text(json.dumps(cert,indent=2,sort_keys=True))
    print("ETHEREUM_CRYSTAL_V8=PASS")
    print(f"records={len(records)} exact_reassembly={equality} hash_matches={hash_ok}")
    print("ablation_break_counts="+",".join(f"{k}:{v}" for k,v in ablation.items()))
    print("exact_protocol_object_recovered_from_compounded_capabilities=true")

if __name__=="__main__": main()
