#!/usr/bin/env python3
"""Independent human-specified comparator; no normalizer or native imports.

Checks exact corpus and allowed results from original C contracts, including
quantified postconditions and distinguishing strict frame clauses.
"""
import hashlib,json,sys
from pathlib import Path
from itertools import product
PACKET_SHA="e70b963a6b84d06fcbe60bc95d5caa6e4d60389439d20c9d503ab18609fba01e"
REV="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
NAMES=["data/frama_c_problems/max.c","data/frama_c_problems/check_evens_in_array.c",
       "data/frama_c_problems/replace_evens.c","data/frama_c_problems/array_double.c",
       "data/frama_c_problems/reset_1st.c"]
FAMILIES=["MAX_OF_ARRAY","ALL_EVEN_01","ZERO_EVEN_POSITIONS","DOUBLE_INDEX_INITIALIZED"]
BLOBS=["c2f8aae98b7ad686eeb6d46c3f20af328477602a",
       "8fc9f1d3c6aab280c1cd4cf5819b4856c9ed4977",
       "5e782d34a1ee68cda1dc21e15777005a666c770c",
       "a559b35376d9828823714c19b02afb39a7e1b971",
       "70147e46d8d74e10bfe3fbb000d2498b77d9d52b"]
TARGETS=["302694fffbfb050ab5cab6adafd6624261264bf7",
         "5c2fd6e8a1b7bb1b9a21bc2e2121f53564e712e1",
         "433019c395bc42ca800c5320ac284f63d4a36d73",
         "2e5b9c8bab4bc60cdf4828353ea23b339dfd54f0",
         "b22649522e7f9ebac53a08f01ac2328ec9165ac9"]
def h(data):return hashlib.sha256(data).hexdigest()
def test_inputs(i):
    if i==3:
        for n in range(1,7):yield tuple(range(n))
        return
    for n in range(1,5):
        yield from product((-2,-1,0,1,2),repeat=n)
def extra(i):
    probes={
     0:[(-2,),(-2,2,1),(2,2,-1)],
     1:[(2,),(2,4,6),(2,3)],
     2:[(3,),(3,4,5),(-2,1,2,1)],
     3:[(0,),(0,1),(0,1,2,3)]}
    seen=set(test_inputs(i))
    return [x for x in probes[i] if x not in seen]
def allowed(i,row,post,value):
    if i==0:return post==row and value==max(row)
    if i==1:return post==row and value==(1 if all(x%2==0 for x in row) else 0)
    if i==2:return value is None and len(post)==len(row) and all(post[k]==0 for k in range(0,len(row),2))
    if i==3:return value is None and len(post)==len(row) and all(post[k]==2*k for k in range(len(row)))
    raise ValueError("UNSUPPORTED_CASE")
def check(evidence):
    evidence=Path(evidence)
    source_packet=(evidence/"SOURCE_ONLY_PACKET.json").read_bytes()
    if h(source_packet)!=PACKET_SHA:raise ValueError("SOURCE_ONLY_PACKET_CHANGED")
    packet=json.loads(source_packet)
    model=packet.get("cases")
    if len(model)!=5 or [x["source"] for x in model]!=NAMES or [x["c_blob"] for x in model]!=BLOBS:
        raise ValueError("SOURCE_COHORT_CHANGED")
    if ([x.get("family") for x in model[:4]]!=FAMILIES or
            model[4]["status"]!="UNKNOWN_UNSUPPORTED"):
        raise ValueError("NORMALIZATION_OUTCOME_CHANGED")
    report=json.loads((evidence/"NATIVE_REPORT.json").read_text())
    if report.get("status")!="COMPLETE_BOUNDED_NATIVE_REPLAY" or report.get("upstream")!=REV:
        raise ValueError("REPLAY_STATUS_INVALID")
    actual=[report["target_hashes"][row["target"]]["blob"] for row in model]
    if actual!=TARGETS:raise ValueError("TARGET_IDENTITY_CHANGED")
    raw=(evidence/"observations.jsonl").read_bytes()
    if h(raw)!=report["observations_sha256"]:raise ValueError("OBSERVATIONS_DIGEST_CHANGED")
    records=[json.loads(x) for x in raw.decode().splitlines()]
    expected=[]
    for i in range(4):
        expected.extend((i,row) for row in test_inputs(i))
        expected.extend((i,row) for row in extra(i))
    if len(expected)!=len(records):raise ValueError("INCOMPLETE_OBSERVATIONS")
    failed=[];diffs=0
    for index,((i,row),item) in enumerate(zip(expected,records)):
        if item["index"]!=index or item["case"]!=i or item["input"]!=list(row):
            raise ValueError("TEST_CENSUS_TAMPER:"+str(index))
        src=allowed(i,row,tuple(item["c_post"]),item["c_result"])
        dst=allowed(i,row,tuple(item["rust_post"]),item["rust_result"])
        if not src or not dst:failed.append(item)
        if item["c_post"]!=item["rust_post"] or item["c_result"]!=item["rust_result"]:diffs+=1
    status="BASELINE_TIE" if not failed else "BASELINE_CAUGHT_COUNTEREXAMPLE"
    verdict={"status":status,"executed":len(records),"recognized_contracts":4,
             "unsupported_not_authorized":1,"violations":len(failed),"differences":diffs,
             "first_counterexample":failed[:1],
             "baseline":"independently encoded complete four-rule finite source oracle",
             "cost_comparison":"NOT_MEASURED"}
    (evidence/"BASELINE_REPORT.json").write_text(json.dumps(verdict,sort_keys=True,indent=2)+"\n")
    print(json.dumps(verdict,sort_keys=True))
    return verdict
if __name__=="__main__":
    if check(sys.argv[1])["status"]!="BASELINE_TIE":raise SystemExit(1)
