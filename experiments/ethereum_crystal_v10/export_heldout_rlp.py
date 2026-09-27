#!/usr/bin/env python3
"""Export V9 held-out canonical BAL RLP records for native benchmarks."""
import json, struct, sys
from pathlib import Path
from execution_testing import BlockAccessList

SEEN={
 "bal_account_access_target","bal_code_changes",
 "bal_consolidation_contract_cross_index","bal_delegated_storage_reads",
 "bal_delegated_storage_writes","bal_net_zero_balance_transfer",
 "bal_noop_storage_write","bal_withdrawal_contract_cross_index",
 "bal_zero_value_transfer",
}

def main():
    root=Path(sys.argv[1]); out=Path(sys.argv[2]); raws=[]
    for path in sorted((root/"blockchain_tests").rglob("*.json")):
        if path.stem in SEEN: continue
        obj=json.loads(path.read_text())
        for fixture in obj.values():
            if not isinstance(fixture,dict): continue
            for block in fixture.get("blocks",[]):
                bal=block.get("blockAccessList") if isinstance(block,dict) else None
                if isinstance(bal,list):
                    raws.append(bytes(BlockAccessList(root=bal).rlp))
    assert raws
    with out.open("wb") as f:
        f.write(b"CV10")
        f.write(struct.pack("<I",len(raws)))
        for raw in raws:
            f.write(struct.pack("<I",len(raw))); f.write(raw)
    print(f"V10_RLP_EXPORT records={len(raws)} bytes={sum(map(len,raws))} file={out}")

if __name__=="__main__": main()
