#!/usr/bin/env python3
"""Crystal V9: consequence-specific BAL consumer compiler.

Input: canonical BAL objects from official generated EELS fixtures.
Frozen V8 capabilities are compiled into two consumer views:
  D: dependency scheduling = address + storage reads + changed storage slots
  R: state reconstruction = address + storage change payloads + balance/nonce/code

The parser operates directly on canonical BAL RLP and skips irrelevant fields
without materializing them. D + R must reassemble the exact original BAL bytes.

Performance claims are empirical on the declared pinned fixture corpus only.
"""
from __future__ import annotations
import gc, json, statistics, sys, time, tracemalloc
from pathlib import Path
from typing import Any, Callable
import ethereum_rlp as rlp
from execution_testing import BlockAccessList

SEEN={
 "bal_account_access_target","bal_code_changes",
 "bal_consolidation_contract_cross_index","bal_delegated_storage_reads",
 "bal_delegated_storage_writes","bal_net_zero_balance_transfer",
 "bal_noop_storage_write","bal_withdrawal_contract_cross_index",
 "bal_zero_value_transfer",
}

def hdr(b:bytes,p:int):
    x=b[p]
    if x<=0x7f: return ("s",p,p+1,p+1)
    if x<=0xb7:
        n=x-0x80; return ("s",p+1,p+1+n,p+1+n)
    if x<=0xbf:
        q=x-0xb7; n=int.from_bytes(b[p+1:p+1+q],"big")
        s=p+1+q; return ("s",s,s+n,s+n)
    if x<=0xf7:
        n=x-0xc0; return ("l",p+1,p+1+n,p+1+n)
    q=x-0xf7; n=int.from_bytes(b[p+1:p+1+q],"big")
    s=p+1+q; return ("l",s,s+n,s+n)

def children(b:bytes,start:int,end:int):
    p=start
    while p<end:
        k,s,e,n=hdr(b,p); yield (k,s,e,p,n); p=n
    assert p==end

def list_children(b:bytes,p:int):
    k,s,e,n=hdr(b,p); assert k=="l"; return list(children(b,s,e)),n

def payload(b:bytes,item):
    k,s,e,_,_=item; assert k=="s"; return b[s:e]

def dep_view(raw:bytes):
    k,s,e,n=hdr(raw,0); assert k=="l" and n==len(raw)
    out=[]
    for acct in children(raw,s,e):
        ak,as_,ae,ap,_=acct; assert ak=="l"
        fs=list(children(raw,as_,ae)); assert len(fs)==6
        addr=payload(raw,fs[0])
        # storage changes -> slots only
        sk,ss,se,_,_=fs[1]; assert sk=="l"
        slots=[]
        for slotent in children(raw,ss,se):
            ek,es,ee,_,_=slotent; assert ek=="l"
            parts=list(children(raw,es,ee)); assert len(parts)==2
            slots.append(payload(raw,parts[0]))
        # storage reads
        rk,rs,re,_,_=fs[2]; assert rk=="l"
        reads=[payload(raw,x) for x in children(raw,rs,re)]
        out.append((addr,tuple(reads),tuple(slots)))
    return tuple(out)

def recon_view(raw:bytes):
    k,s,e,n=hdr(raw,0); assert k=="l" and n==len(raw)
    out=[]
    for acct in children(raw,s,e):
        ak,as_,ae,_,_=acct; assert ak=="l"
        fs=list(children(raw,as_,ae)); assert len(fs)==6
        addr=payload(raw,fs[0])
        # storage changes: slot + indexed payload pairs
        sk,ss,se,_,_=fs[1]; assert sk=="l"
        sch=[]
        for slotent in children(raw,ss,se):
            ek,es,ee,_,_=slotent; assert ek=="l"
            parts=list(children(raw,es,ee)); assert len(parts)==2
            slot=payload(raw,parts[0])
            ck,cs,ce,_,_=parts[1]; assert ck=="l"
            changes=[]
            for ch in children(raw,cs,ce):
                qk,qs,qe,_,_=ch; assert qk=="l"
                pair=list(children(raw,qs,qe)); assert len(pair)==2
                changes.append((payload(raw,pair[0]),payload(raw,pair[1])))
            sch.append((slot,tuple(changes)))
        indexed=[]
        for fi in (3,4,5):
            lk,ls,le,_,_=fs[fi]; assert lk=="l"
            vals=[]
            for ch in children(raw,ls,le):
                qk,qs,qe,_,_=ch; assert qk=="l"
                pair=list(children(raw,qs,qe)); assert len(pair)==2
                vals.append((payload(raw,pair[0]),payload(raw,pair[1])))
            indexed.append(tuple(vals))
        out.append((addr,tuple(sch),indexed[0],indexed[1],indexed[2]))
    return tuple(out)

def reassemble(dep,recon):
    assert len(dep)==len(recon)
    accounts=[]
    for d,r in zip(dep,recon):
        da,reads,slots=d
        ra,sch,bals,nonces,codes=r
        assert da==ra
        assert tuple(x[0] for x in sch)==slots
        storage=[[slot,[[idx,val] for idx,val in changes]] for slot,changes in sch]
        accounts.append([da,storage,list(reads),
                         [[i,v] for i,v in bals],
                         [[i,v] for i,v in nonces],
                         [[i,v] for i,v in codes]])
    return rlp.encode(accounts)

def load_raw(root:Path):
    raws=[]
    meta=[]
    for path in sorted((root/"blockchain_tests").rglob("*.json")):
        obj=json.loads(path.read_text())
        for test_id,fixture in obj.items():
            if not isinstance(fixture,dict): continue
            for block in fixture.get("blocks",[]):
                bal=block.get("blockAccessList") if isinstance(block,dict) else None
                h=(block.get("blockHeader") or {}).get("blockAccessListHash") if isinstance(block,dict) else None
                if isinstance(bal,list) and isinstance(h,str):
                    raw=bytes(BlockAccessList(root=bal).rlp)
                    raws.append(raw); meta.append((path.stem,test_id,h))
    return raws,meta

def copied_bytes_dep(v):
    return sum(len(a)+sum(map(len,reads))+sum(map(len,slots))
               for a,reads,slots in v)
def copied_bytes_recon(v):
    n=0
    for a,sch,bals,nonces,codes in v:
        n+=len(a)
        for slot,changes in sch:
            n+=len(slot)+sum(len(i)+len(v) for i,v in changes)
        for seq in (bals,nonces,codes):
            n+=sum(len(i)+len(v) for i,v in seq)
    return n

def bench(fn:Callable[[bytes],Any],raws:list[bytes],rounds=7,repeats=20):
    times=[]; peaks=[]
    for _ in range(rounds):
        gc.collect(); tracemalloc.start(); t=time.perf_counter()
        for _j in range(repeats):
            for raw in raws: fn(raw)
        elapsed=time.perf_counter()-t
        _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
        times.append(elapsed); peaks.append(peak)
    return statistics.median(times),statistics.median(peaks)

def full_parse(raw):
    return BlockAccessList.from_rlp(raw)

def main():
    if len(sys.argv)<2: raise SystemExit("usage: consumer_views.py FIXTURES [CERT]")
    raws,meta=load_raw(Path(sys.argv[1])); assert raws
    held=[i for i,m in enumerate(meta) if m[0] not in SEEN]
    assert held, "no unseen fixture records"
    hraw=[raws[i] for i in held]; hmeta=[meta[i] for i in held]

    # Protected exactness on the unseen corpus.
    for raw,(fam,test_id,expected_hash) in zip(hraw,hmeta):
        d=dep_view(raw); r=recon_view(raw)
        rebuilt=reassemble(d,r)
        assert rebuilt==raw,(fam,test_id,"byte mismatch")
        calc="0x"+bytes(BlockAccessList.from_rlp(rebuilt).rlp_hash).hex()
        assert calc.lower()==expected_hash.lower(),(fam,test_id,calc,expected_hash)

    full_bytes=sum(map(len,hraw))
    dep_copied=sum(copied_bytes_dep(dep_view(x)) for x in hraw)
    rec_copied=sum(copied_bytes_recon(recon_view(x)) for x in hraw)

    ft,fm=bench(full_parse,hraw)
    dt,dm=bench(dep_view,hraw)
    rt,rm=bench(recon_view,hraw)

    cert={
      "protocol":"ETHEREUM_CRYSTAL_V9_CONSUMER_COMPILER",
      "total_records":len(raws),
      "heldout_records":len(hraw),
      "heldout_families":sorted({m[0] for m in hmeta}),
      "raw_bal_bytes":full_bytes,
      "dependency_materialized_payload_bytes":dep_copied,
      "reconstruction_materialized_payload_bytes":rec_copied,
      "dependency_payload_fraction":dep_copied/full_bytes,
      "reconstruction_payload_fraction":rec_copied/full_bytes,
      "benchmark_rounds":7,"benchmark_repeats":20,
      "full_parse_median_s":ft,"dependency_parse_median_s":dt,"reconstruction_parse_median_s":rt,
      "dependency_speedup_vs_full":ft/dt,
      "reconstruction_speedup_vs_full":ft/rt,
      "full_peak_bytes":fm,"dependency_peak_bytes":dm,"reconstruction_peak_bytes":rm,
      "dependency_peak_ratio":dm/fm if fm else None,
      "reconstruction_peak_ratio":rm/fm if fm else None,
      "exact_byte_reassembly_all_heldout":True,
      "exact_hash_match_all_heldout":True,
      "claim_boundary":"pinned generated held-out EELS EIP-7928 fixture corpus; Python microbenchmark"
    }
    if len(sys.argv)>2: Path(sys.argv[2]).write_text(json.dumps(cert,indent=2,sort_keys=True))
    print("ETHEREUM_CRYSTAL_V9=PASS")
    print(f"total_records={len(raws)} heldout_records={len(hraw)} heldout_families={len(set(m[0] for m in hmeta))}")
    print(f"raw_bal_bytes={full_bytes} dependency_payload_bytes={dep_copied} reconstruction_payload_bytes={rec_copied}")
    print(f"dependency_payload_fraction={dep_copied/full_bytes:.6f} reconstruction_payload_fraction={rec_copied/full_bytes:.6f}")
    print(f"full_parse_median_s={ft:.6f} dependency_parse_median_s={dt:.6f} reconstruction_parse_median_s={rt:.6f}")
    print(f"dependency_speedup_vs_full={ft/dt:.3f} reconstruction_speedup_vs_full={ft/rt:.3f}")
    print(f"full_peak_bytes={int(fm)} dependency_peak_bytes={int(dm)} reconstruction_peak_bytes={int(rm)}")
    print("heldout_exact_reassembly_and_hash=true")

if __name__=="__main__": main()
