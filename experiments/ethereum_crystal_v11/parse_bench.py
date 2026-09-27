#!/usr/bin/env python3
import json,re,statistics,sys
text=open(sys.argv[1]).read()
pat=re.compile(r'^(BenchmarkCrystal(?:FullGeth|DependencyView)-\d+)\s+\d+\s+([0-9.]+) ns/op\s+([0-9.]+) B/op\s+([0-9]+) allocs/op',re.M)
d={}
for name,ns,b,alloc in pat.findall(text):
    key="full" if "FullGeth" in name else "dependency"
    d.setdefault(key,[]).append((float(ns),float(b),float(alloc)))
assert len(d.get("full",[]))>=3 and len(d.get("dependency",[]))>=3,d
m=lambda key,i: statistics.median(x[i] for x in d[key])
out={
 "protocol":"ETHEREUM_CRYSTAL_V11_GETH_PACKAGE",
 "geth_commit":"920c07774c65ebb3023536f85df642c44478b540",
 "full_ns_op":m("full",0),"dependency_ns_op":m("dependency",0),
 "speedup":m("full",0)/m("dependency",0),
 "full_B_op":m("full",1),"dependency_B_op":m("dependency",1),
 "allocation_byte_ratio":m("dependency",1)/m("full",1),
 "full_allocs_op":m("full",2),"dependency_allocs_op":m("dependency",2),
 "allocation_call_ratio":m("dependency",2)/m("full",2),
 "performance_positive":m("dependency",0)<m("full",0) and m("dependency",1)<m("full",1),
 "claim_boundary":"go-ethereum BAL package benchmark on pinned V9 held-out EELS RLP corpus"
}
open(sys.argv[2],"w").write(json.dumps(out,indent=2,sort_keys=True))
print(json.dumps(out,indent=2,sort_keys=True))
