#!/usr/bin/env python3
"""Fixture-native Crystal over realized EELS EIP-7928 BAL objects.

Evidence boundary:
- input is JSON produced by the pinned official EELS `fill` runner;
- feature grammar is frozen to projections of the serialized BAL schema;
- acquisition is exhaustive minimal-subset search;
- ablation and held-out family reuse are checked on realized fixtures.

This is empirical minimality on the generated fixture corpus, not universal
minimality of EIP-7928.
"""
from __future__ import annotations
import itertools, json, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ATOM_ORDER=("addresses","storage_reads","storage_change_slots",
            "storage_change_payloads","balance_changes","nonce_changes",
            "code_changes")

@dataclass(frozen=True)
class Record:
    family:str
    test_id:str
    bal:tuple

def freeze(x:Any)->Any:
    if isinstance(x,dict):
        return tuple((k,freeze(v)) for k,v in sorted(x.items()))
    if isinstance(x,list):
        return tuple(freeze(v) for v in x)
    return x

def load_records(root:Path)->list[Record]:
    out=[]
    # Use canonical blockchain fixtures only; engine fixtures duplicate the
    # same generated tests through another fixture format.
    base=root/"blockchain_tests"
    for f in sorted(base.rglob("*.json")):
        obj=json.loads(f.read_text())
        for test_id,fixture in obj.items():
            if not isinstance(fixture,dict):
                continue
            for block in fixture.get("blocks",[]):
                if isinstance(block,dict) and isinstance(block.get("blockAccessList"),list):
                    out.append(Record(f.stem,test_id,tuple(block["blockAccessList"])))
    if not out:
        raise SystemExit("NO_BLOCK_ACCESS_LIST_RECORDS")
    return out

def atom(record:Record,name:str)->Any:
    bal=record.bal
    if name=="addresses":
        return tuple(acc.get("address") for acc in bal)
    if name=="storage_reads":
        return tuple((i,tuple(acc.get("storageReads",[])))
                     for i,acc in enumerate(bal) if acc.get("storageReads"))
    if name=="storage_change_slots":
        return tuple((i,tuple(sc.get("slot") for sc in acc.get("storageChanges",[])))
                     for i,acc in enumerate(bal) if acc.get("storageChanges"))
    if name=="storage_change_payloads":
        # Deliberately exclude slot keys: those must be supplied by the
        # previously learned structural slot capability.
        return tuple((i,tuple(freeze(sc.get("slotChanges",[]))
                              for sc in acc.get("storageChanges",[])))
                     for i,acc in enumerate(bal) if acc.get("storageChanges"))
    if name=="balance_changes":
        return tuple((i,freeze(acc.get("balanceChanges",[])))
                     for i,acc in enumerate(bal) if acc.get("balanceChanges"))
    if name=="nonce_changes":
        return tuple((i,freeze(acc.get("nonceChanges",[])))
                     for i,acc in enumerate(bal) if acc.get("nonceChanges"))
    if name=="code_changes":
        return tuple((i,freeze(acc.get("codeChanges",[])))
                     for i,acc in enumerate(bal) if acc.get("codeChanges"))
    raise KeyError(name)

def target(record:Record,kind:str)->dict[str,Any]:
    if kind=="dependency":
        names=("addresses","storage_reads","storage_change_slots")
    elif kind=="reconstruction":
        names=("storage_change_slots","storage_change_payloads",
               "balance_changes","nonce_changes","code_changes")
    else:
        raise KeyError(kind)
    return {n:atom(record,n) for n in names}

def decode(record:Record,kind:str,selected:set[str])->dict[str,Any]:
    # Missing capabilities contribute the empty value of their target field.
    t=target(record,kind)
    return {n:(atom(record,n) if n in selected else ()) for n in t}

def closes(records:list[Record],kind:str,selected:set[str])->bool:
    return all(decode(r,kind,selected)==target(r,kind) for r in records)

def minimal_repairs(records:list[Record],kind:str,retained:set[str])->list[tuple[str,...]]:
    remaining=[n for n in ATOM_ORDER if n not in retained]
    if closes(records,kind,retained):
        return [()]
    for k in range(1,len(remaining)+1):
        good=[]
        for combo in itertools.combinations(remaining,k):
            if closes(records,kind,retained|set(combo)):
                good.append(combo)
        if good:
            return good
    return []

def family(records,names):
    wanted=set(names)
    xs=[r for r in records if r.family in wanted]
    if not xs:
        raise AssertionError(f"missing families: {sorted(wanted)}")
    return xs

def main():
    if len(sys.argv)<2:
        raise SystemExit("usage: fixture_crystal.py FIXTURE_DIR [CERT.json]")
    records=load_records(Path(sys.argv[1]))
    fams=sorted({r.family for r in records})

    # Generation 1: learn dependency interface from three storage families.
    g1_records=family(records,[
        "bal_noop_storage_write",
        "bal_delegated_storage_reads",
        "bal_delegated_storage_writes",
    ])
    retained:set[str]=set()
    g1=minimal_repairs(g1_records,"dependency",retained)
    assert g1, "dependency has no repair in frozen schema grammar"
    chosen1=g1[0]
    retained.update(chosen1)
    assert closes(g1_records,"dependency",retained)

    # Causal ablation: every atom in the chosen minimal repair is necessary
    # on the acquisition corpus.
    g1_ablations={}
    for n in chosen1:
        fails=not closes(g1_records,"dependency",retained-{n})
        g1_ablations[n]=fails
        assert fails,n

    # Held-out dependency family: no reacquisition allowed.
    dep_hold=family(records,["bal_account_access_target"])
    assert closes(dep_hold,"dependency",retained)
    dep_hold_repair=minimal_repairs(dep_hold,"dependency",retained)
    assert dep_hold_repair==[()]

    # Generation 2: switch consequence family. Cross-index withdrawal exposes
    # reconstruction residuals while reusing storage_change_slots from G1.
    cross_train=family(records,["bal_withdrawal_contract_cross_index"])
    assert "storage_change_slots" in retained
    before_g2=set(retained)
    g2=minimal_repairs(cross_train,"reconstruction",retained)
    assert g2
    chosen2=g2[0]
    retained.update(chosen2)
    assert closes(cross_train,"reconstruction",retained)
    assert "storage_change_slots" not in chosen2

    # Cross-index consolidation is source-distinct held-out transfer.
    cross_hold=family(records,["bal_consolidation_contract_cross_index"])
    assert closes(cross_hold,"reconstruction",retained)
    assert minimal_repairs(cross_hold,"reconstruction",retained)==[()]

    # Generation 3: code-changing fixtures may expose a genuinely new residual.
    code_recs=[r for r in records if r.family=="bal_code_changes"]
    g3=()
    if code_recs:
        repairs=minimal_repairs(code_recs,"reconstruction",retained)
        assert repairs
        g3=repairs[0]
        retained.update(g3)
        assert closes(code_recs,"reconstruction",retained)

    # Further source-distinct families must reuse the accumulated interface.
    transfer_families=["bal_zero_value_transfer","bal_net_zero_balance_transfer"]
    transfer_report={}
    for fn in transfer_families:
        rs=family(records,[fn])
        repairs=minimal_repairs(rs,"reconstruction",retained)
        transfer_report[fn]=repairs
        if repairs != [()]:
            # Crystal is allowed to acquire a genuinely new residual, then the
            # capability becomes retained for subsequent families.
            chosen=repairs[0]
            retained.update(chosen)
            assert closes(rs,"reconstruction",retained)

    # Final corpus qualification for both protected consequence families where
    # each is applicable.
    all_dep=[r for r in records if any((
        atom(r,"storage_reads"), atom(r,"storage_change_slots"), atom(r,"addresses")))]
    assert closes(all_dep,"dependency",retained)
    assert closes(records,"reconstruction",retained)

    cert={
      "protocol":"ETHEREUM_CRYSTAL_V7_FIXTURE_NATIVE",
      "fixture_records":len(records),
      "families":fams,
      "frozen_atoms":ATOM_ORDER,
      "g1_dependency_minimal_repairs":g1,
      "g1_chosen":chosen1,
      "g1_ablations":g1_ablations,
      "dependency_heldout_zero_reacquisition":True,
      "g2_retained_before":sorted(before_g2),
      "g2_reconstruction_minimal_repairs":g2,
      "g2_chosen":chosen2,
      "cross_index_consolidation_zero_reacquisition":True,
      "g3_code_chosen":g3,
      "later_transfer_repairs":transfer_report,
      "final_retained":sorted(retained),
      "verdict":"PASS_FIXTURE_NATIVE_CRYSTAL",
      "claim_boundary":"empirical minimality and compounding on pinned generated EELS fixtures"
    }
    if len(sys.argv)>2:
        Path(sys.argv[2]).write_text(json.dumps(cert,indent=2,sort_keys=True))
    print("ETHEREUM_CRYSTAL_V7=PASS")
    print(f"fixture_records={len(records)} families={len(fams)}")
    print("g1_dependency_promoted="+",".join(chosen1))
    print("g1_ablation_all_restore_failure=true")
    print("dependency_holdout_reacquisition=0")
    print("g2_reused=storage_change_slots")
    print("g2_new="+(",".join(chosen2) if chosen2 else "-"))
    print("cross_index_consolidation_reacquisition=0")
    print("g3_code_new="+(",".join(g3) if g3 else "-"))
    for fn,repairs in transfer_report.items():
        print(f"{fn}_minimal_additions="+repr(repairs))
    print("final_retained="+",".join(sorted(retained)))
    print("full_dependency_and_reconstruction_corpus_closed=true")

if __name__=="__main__":
    main()
