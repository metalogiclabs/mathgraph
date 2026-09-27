#!/usr/bin/env python3
import json,re,statistics,sys
s=open(sys.argv[1]).read()
pat=re.compile(r'^BenchmarkCrystalCatchup(Full|Compact)-\d+\s+\d+\s+([0-9.]+) ns/op\s+([0-9.]+) B/op\s+([0-9]+) allocs/op',re.M)
d={}
for kind,ns,b,a in pat.findall(s):
    d.setdefault(kind.lower(),[]).append((float(ns),float(b),float(a)))
assert len(d.get("full",[]))>=3 and len(d.get("compact",[]))>=3,d
med=lambda k,i:statistics.median(x[i] for x in d[k])
out={
 "protocol":"ETHEREUM_CRYSTAL_V16_GETH_CATCHUP_END_TO_END",
 "records":1112,
 "full_ns_op":med("full",0),
 "compact_ns_op":med("compact",0),
 "speedup":med("full",0)/med("compact",0),
 "full_B_op":med("full",1),
 "compact_B_op":med("compact",1),
 "allocation_byte_ratio":med("compact",1)/med("full",1),
 "full_allocs_op":med("full",2),
 "compact_allocs_op":med("compact",2),
 "allocation_call_ratio":med("compact",2)/med("full",2),
 "claim_boundary":"pinned geth in-memory snap applyAccessList + batch-write corpus pass; final DB digest parity separately checked"
}
open(sys.argv[2],"w").write(json.dumps(out,indent=2,sort_keys=True))
print(json.dumps(out,indent=2,sort_keys=True))
