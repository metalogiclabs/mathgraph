#!/usr/bin/env python3
"""Conventional source-aware requirement reviewer, independent of MathGraph extractor."""
import hashlib,json,sys
from pathlib import Path
from itertools import product
PIN="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
BLOBS=["0b26b5ce3d6e296485f13d70099961bbd8298302","c2f8aae98b7ad686eeb6d46c3f20af328477602a",
"8fc9f1d3c6aab280c1cd4cf5819b4856c9ed4977","5e782d34a1ee68cda1dc21e15777005a666c770c",
"a559b35376d9828823714c19b02afb39a7e1b971"]
TARGETS=["850ad4aae633bfb4786266d4ac97d9d417688df0","302694fffbfb050ab5cab6adafd6624261264bf7",
"5c2fd6e8a1b7bb1b9a21bc2e2121f53564e712e1","433019c395bc42ca800c5320ac284f63d4a36d73",
"2e5b9c8bab4bc60cdf4828353ea23b339dfd54f0"]
def authorized(i,initial,after,r):
    if i==0:return r==max(initial) and after is None
    if i==1:return r==max(initial) and after==initial
    if i==2:return r==int(not any((v%2) for v in initial)) and after==initial
    if i==3:return after is not None and len(after)==len(initial) and all(after[j]==0 for j in range(0,len(initial),2))
    if i==4:return after==tuple(j*2 for j in range(len(initial)))
    raise ValueError("UNREGISTERED_CONTRACT")
def cases():
    for a,b in product(range(-3,4),repeat=2):yield 0,(a,b)
    for i in (1,2,3):
        for n in range(1,5):
            for arr in product(range(-2,3),repeat=n):yield i,arr
    for n in range(1,6):yield 4,tuple(range(n))
def assess(evidence):
    evidence=Path(evidence)
    meta=json.loads((evidence/"NATIVE_REPORT.json").read_text())
    if (meta.get("upstream_revision")!=PIN or meta.get("source_blobs")!=BLOBS or
         meta.get("target_blobs")!=TARGETS):
        raise ValueError("SOURCE_TARGET_IDENTITY_MISMATCH")
    raw=(evidence/"OBSERVATIONS.jsonl").read_bytes()
    if hashlib.sha256(raw).hexdigest()!=meta.get("native_observations_sha256"):
        raise ValueError("OBSERVATION_RECEIPT_DRIFT")
    values=[json.loads(line) for line in raw.decode().splitlines()]
    expected=list(cases())
    if len(values)!=2394 or len(expected)!=len(values):raise ValueError("CASE_CENSUS_WRONG")
    failures=[]
    for j,((task,initial),row) in enumerate(zip(expected,values)):
        if row["index"]!=j or row["case"]!=task or tuple(row["before"])!=initial:
            raise ValueError("INPUT_OR_ORDER_CHANGED:"+str(j))
        s=authorized(task,initial,tuple(row["source_after"]) if row["source_after"] is not None else None,row["source_return"])
        t=authorized(task,initial,tuple(row["target_after"]) if row["target_after"] is not None else None,row["target_return"])
        if not (s and t):failures.append(row)
    verdict={"verdict":"BASELINE_TIE" if not failures else "BASELINE_CAUGHT_COUNTEREXAMPLE",
             "cases":len(values),"false_rejections":0,
             "violations":len(failures),"first_counterexamples":failures[:2],
             "independent":"Manually formulated source contract checks, no import of MathGraph extractor",
             "time_cost_advantage_measured":False}
    (evidence/"BASELINE_REPORT.json").write_text(json.dumps(verdict,sort_keys=True,indent=2)+"\n")
    print(json.dumps(verdict,sort_keys=True))
    return verdict
if __name__=="__main__":
    result=assess(sys.argv[1])
    if result["verdict"]!="BASELINE_TIE":raise SystemExit(1)
