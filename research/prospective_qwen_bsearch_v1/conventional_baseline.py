#!/usr/bin/env python3
"""Equally informed direct conventional contract check, independently coded."""
import hashlib
import json
from pathlib import Path
import sys

C_BLOB="c31d685b159f072d75212aa48ba98e1e19a0f207"
R_BLOB="2286ec1d646fd1c5ae90a5aafe95ff48d2420188"
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def independent_oracle(array,key,value):
    indices=[i for i,x in enumerate(array) if x==key]
    return (value in indices) if indices else (value==len(array))
def assess(evidence):
    evidence=Path(evidence)
    native=json.loads((evidence/"native_report.json").read_text())
    if native.get("source_blob_sha")!=C_BLOB or native.get("target_blob_sha")!=R_BLOB:
        raise ValueError("SOURCE_PROVENANCE_MISMATCH")
    records=[json.loads(line) for line in (evidence/"observations.jsonl").read_text().splitlines()]
    if len(records)!=1764:
        raise ValueError("INCOMPLETE_CASE_CENSUS")
    bad=[]
    for r in records:
        arr,key=r["array"],r["key"]
        c_ok=independent_oracle(arr,key,r["c"]) and r["c_unchanged"]
        t_ok=independent_oracle(arr,key,r["rust"]) and r["rust_unchanged"]
        if not c_ok or not t_ok:bad.append(r)
    result={"cases":len(records),"failures":len(bad),"first_counterexample":bad[:1],
            "verdict":"BASELINE_TIE" if len(bad)==0 else "BASELINE_CAUGHT_COUNTEREXAMPLE",
            "comparator":"source-aware fully informed contract evaluator; no MathGraph oracle import",
            "economic_advantage_measured":False}
    (evidence/"baseline_report.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
    return result
if __name__=="__main__":
    report=assess(sys.argv[1])
    if report["verdict"]!="BASELINE_TIE":raise SystemExit(1)
