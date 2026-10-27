#!/usr/bin/env python3
"""Source-aware, independent conventional comparator; no MathGraph import."""
from itertools import combinations_with_replacement,product
import hashlib,json,sys
from pathlib import Path

def sha(data):return hashlib.sha256(data).hexdigest()
def expected():
    for length in range(6):
        for row in combinations_with_replacement((-2,-1,0,1,2),length):
            for key in (-3,-2,-1,0,1,2,3):yield "sorted_minus_one",row,key
    for length in range(5):
        for row in product((-2,-1,0,1,2),repeat=length):
            for key in (-3,-2,-1,0,1,2,3):yield "unsorted_uintmax",row,key
def allowed(kind,row,key,r):
    found=[i for i,x in enumerate(row) if x==key]
    return r in found if found else r==(-1 if kind=="sorted_minus_one" else 4294967295)
def run(directory):
    directory=Path(directory)
    report=json.loads((directory/"native_report.json").read_text())
    raw=(directory/"observations.jsonl").read_bytes()
    if sha(raw)!=report.get("observations_sha256"):raise ValueError("OBSERVATION_EVIDENCE_CHANGED")
    records=[json.loads(x) for x in raw.decode().splitlines()]
    listed=list(expected())
    if len(records)!=len(listed) or len(records)!=7231:
        raise ValueError("INCOMPLETE_CORPUS")
    missed=[]
    for i,((kind,row,key),record) in enumerate(zip(listed,records)):
        if (record["kind"]!=kind or tuple(record["row"])!=row or
                record["key"]!=key or record["index"]!=i):
            raise ValueError("INPUT_CENSUS_INCONSISTENT")
        if (not allowed(kind,row,key,record["c"]) or
            not allowed(kind,row,key,record["rust"]) or
            not record["c_unchanged"] or not record["rust_unchanged"]):
            missed.append(record)
    result={"case_count":len(listed),"failure_count":len(missed),
            "first_counterexample":missed[:1],
            "verdict":"BASELINE_TIE" if not missed else "BASELINE_CAUGHT_COUNTEREXAMPLE",
            "assurance_scope":"Independent source-aware direct result comparison",
            "relative_detection_advantage":"NONE_DEMONSTRATED",
            "relative_cost_advantage":"NOT_MEASURED"}
    (directory/"baseline_report.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    return result
if __name__=="__main__":
    result=run(sys.argv[1])
    if result["verdict"]!="BASELINE_TIE":raise SystemExit(1)
