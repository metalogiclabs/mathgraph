#!/usr/bin/env python3
import json,re,statistics,sys
text=open(sys.argv[1]).read()
pat=re.compile(r'^(BenchmarkCrystalApply(?:FullGeth|View)-\d+)\s+\d+\s+([0-9.]+) ns/op\s+([0-9.]+) B/op\s+([0-9]+) allocs/op',re.M)
d={}
for name,ns,b,a in pat.findall(text):
 key="full" if "FullGeth" in name else "view"; d.setdefault(key,[]).append((float(ns),float(b),float(a)))
assert len(d.get("full",[]))>=3 and len(d.get("view",[]))>=3,d
med=lambda k,i:statistics.median(x[i] for x in d[k])
out={
 "protocol":"ETHEREUM_CRYSTAL_V12_GETH_SNAP_APPLY_VIEW",
 "geth_commit":"920c07774c65ebb3023536f85df642c44478b540",
 "full_ns_op":med("full",0),"apply_view_ns_op":med("view",0),"speedup":med("full",0)/med("view",0),
 "full_B_op":med("full",1),"apply_view_B_op":med("view",1),"allocation_byte_ratio":med("view",1)/med("full",1),
 "full_allocs_op":med("full",2),"apply_view_allocs_op":med("view",2),"allocation_call_ratio":med("view",2)/med("full",2),
 "performance_positive":med("view",0)<med("full",0) and med("view",1)<med("full",1),
 "protected_consumer":"eth/protocols/snap applyAccessList final-state consequences",
 "claim_boundary":"benchmark-only compact apply view checked against production geth BAL objects on pinned held-out EELS corpus"
}
open(sys.argv[2],"w").write(json.dumps(out,indent=2,sort_keys=True)); print(json.dumps(out,indent=2,sort_keys=True))
