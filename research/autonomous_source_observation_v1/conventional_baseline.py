"""Independent conventional source-aware reviewer, not importing MathGraph code.

Expert-decoded C contract families are sealed explicitly here; this comparator
has the SAME original C and native observations. It can handle implication-only
array_find contracts that the conservative MathGraph parser abstains on.
"""
import hashlib,json,sys
from itertools import combinations_with_replacement,product
from pathlib import Path

REVISION="6c8b35b5dd8e94473b713b7edcf4bf4142f214e3"
CASE_NAMES=[
 "data/frama_c_problems/array_find.c",
 "data/frama_c_problems/search.c",
 "data/frama_c_problems/search_2.c",
 "data/frama_c_problems/binary_search.c",
 "data/tutorial_wp/ex-3-binary-search-u-answer.c"
]
SOURCE_BLOBS=[
 "f58f554e4658e54ff40eb36d4b1ef86514d6a32c",
 "5b3c3811c4471f444ecbeae23c04a9b00c3eac7c",
 "e5935f3f2563e5cdb7dd241804e398b45533fee4",
 "1157b9f889bf2bd5b0200fbf166d0881668052da",
 "b39c798dcecc4938de0e6bff983bef0c611abb53"
]
EXPECTED_RULES=["NEGATIVE_ONE","PRESENCE_01","PRESENCE_01","NEGATIVE_ONE","LENGTH"]
VALUES=(-2,-1,0,1,2)
KEYS=(-3,-2,-1,0,1,2,3)
def sha(b):return hashlib.sha256(b).hexdigest()
def expected_rows(i):
    sorted_input=i in (3,4)
    low=1 if i in (1,2) else 0
    high=5 if sorted_input else 4
    for n in range(low,high+1):
        arr=(combinations_with_replacement(VALUES,n) if sorted_input else product(VALUES,repeat=n))
        for row in arr:
            for key in KEYS:yield row,key
def source_authorizes(i,row,key,ret):
    positions={k for k,x in enumerate(row) if x==key}
    mode=EXPECTED_RULES[i]
    if mode=="PRESENCE_01":return ret==(1 if positions else 0)
    if positions:return ret in positions
    if mode=="NEGATIVE_ONE":return ret==-1
    if mode=="LENGTH":return ret==len(row)
    return False
def compare(evidence):
    evidence=Path(evidence)
    report=json.loads((evidence/"NATIVE_REPORT.json").read_text())
    if report.get("upstream_revision")!=REVISION:raise ValueError("UPSTREAM_REVISION_UNTRUSTED")
    metadata=report.get("source_and_target",[])
    if len(metadata)!=5 or [x["source"] for x in metadata]!=CASE_NAMES or [x["source_blob"] for x in metadata]!=SOURCE_BLOBS:
        raise ValueError("SOURCE_PROVENANCE_UNTRUSTED")
    data=(evidence/"observations.jsonl").read_bytes()
    if sha(data)!=report.get("observations_sha256"):raise ValueError("OBSERVATIONS_DIGEST_DRIFT")
    rows=[json.loads(x) for x in data.decode().splitlines()]
    index=0;bad=[];confirmed=0
    for i in range(5):
        for row,key in expected_rows(i):
            if index>=len(rows):raise ValueError("MISSING_CASE")
            item=rows[index]
            if (item["case"]!=i or tuple(item["row"])!=row or item["key"]!=key):
                raise ValueError("FROZEN_CORPUS_OR_ORDER_CHANGED:"+str(index))
            c_good=source_authorizes(i,row,key,item["source"]) and item["source_unchanged"]
            r_good=source_authorizes(i,row,key,item["target"]) and item["target_unchanged"]
            if not c_good or not r_good:bad.append(item)
            confirmed+=1;index+=1
    if index!=len(rows):raise ValueError("EXTRA_OBSERVATIONS")
    output={"verdict":"BASELINE_TIE" if not bad else "BASELINE_CAUGHT_REAL_COUNTEREXAMPLE",
            "total":confirmed,"source_cases_evaluated":5,"source_requirements_manually_interpreted":True,
            "MathGraph_syntactic_extractor_coverage":4,
            "first_failed_cases":bad[:3],"failed_count":len(bad),
            "comparison":"Strong source-aware, manually authored independent rule comparator; equal information, not equal engineering labor",
            "relative_cost":"UNKNOWN_UNMEASURED"}
    (evidence/"BASELINE_REPORT.json").write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    print(json.dumps(output,sort_keys=True))
    return output
if __name__=="__main__":
    verdict=compare(sys.argv[1])
    if verdict["verdict"]!="BASELINE_TIE":raise SystemExit(1)
