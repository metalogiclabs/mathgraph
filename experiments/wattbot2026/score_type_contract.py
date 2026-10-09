#!/usr/bin/env python3
"""WattBot official answer-value TYPE contract; TRAIN metadata only.

Official source Score.py and CSVs are cryptographically pinned. This
diagnostic distinguishes exact-range tuple from derived tolerance-band list,
direct scalar, categorical value, and honest is_blank. Never inspect TEST
answer values/citations. All output is aggregate counts, no gold row text.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter,defaultdict
import hashlib
import io
import json
from decimal import Decimal, InvalidOperation
import zipfile

import pandas as pd

EXPECTED={
  "Score.py":"e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
  "train_QA.csv":"9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
  "test_Q.csv":"26038b21cb09588a39b0e95e5516e3827dadd499c85c3792d0ea46c10ae7066a",
}
FLAGS=("Quote","Table","Figure","Math","CrossPaper","Reconcile","is_NA")


def typ(value):
    text=str(value or "").strip()
    if text.casefold() in ("is_blank","na","n/a","nan","null","none",""):
        return "is_blank"
    try:
        numeric=Decimal(text.replace(",",""))
        if numeric.is_finite(): return "scalar"
    except InvalidOperation:
        pass
    try:
        parsed=ast.literal_eval(text)
    except (SyntaxError,ValueError,TypeError,MemoryError):
        parsed=None
    if isinstance(parsed,tuple):
        return ("explicit_range_tuple" if len(parsed)==2 else "tuple_other")
    if isinstance(parsed,list):
        return ("tolerance_band_or_list" if len(parsed)==2 else "list_other")
    if text.upper() in ("TRUE","FALSE","YES","NO"):
        return "boolean"
    return "term"


def group(rows):
    shape=Counter()
    flags=defaultdict(Counter)
    cohorts=defaultdict(Counter)
    for rec in rows:
        key=typ(rec["answer_value"])
        shape[key]+=1
        for flag in FLAGS:
            if str(rec.get(flag,"")).casefold().strip() in ("1","true","yes","x"):
                flags[flag][key]+=1
        cohorts[str(rec.get("Cohort","unknown"))[:80]][key]+=1
    return {
       "rows":len(rows),
       "answer_value_shapes":dict(shape),
       "evidence_flag_shapes":{f:dict(flags[f]) for f in FLAGS},
       "cohort_shapes":{k:dict(v) for k,v in sorted(cohorts.items())},
    }


def self_test():
    assert typ("119")=="scalar"
    assert typ("1,287")=="scalar"
    assert typ("[116,121]")=="tolerance_band_or_list"
    assert typ("(14,29)")=="explicit_range_tuple"
    assert typ("['A','B','C']")=="list_other"
    assert typ("FALSE")=="boolean"
    assert typ("is_blank")=="is_blank"
    assert typ("carbon intensity")=="term"
    print("WATTBOT_SCORE_TYPE_SELF_TEST=PASS")


def run(archive):
    self_test()
    with zipfile.ZipFile(archive) as z:
        for name,expected in EXPECTED.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=expected:
                raise RuntimeError("Official pinned data changed: "+name)
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str})
        test=pd.read_csv(io.BytesIO(z.read("test_Q.csv")),
                         keep_default_na=False,dtype={"id":str})
    from holdout_probe import is_holdout
    assert len(train)==245 and len(test)==317
    dev=train[~train["id"].map(is_holdout)]
    hold=train[train["id"].map(is_holdout)]
    if len(dev)!=182 or len(hold)!=63:raise RuntimeError("TRAIN split changed")
    # No access to hidden TEST answer values is needed; these are question
    # side metadata only. Never serialize individual test rows to CI logs.
    test_unit = int(sum(str(u).strip().casefold() not in (
        "is_blank","na","n/a","none","nan","null","")
                         for u in test["answer_unit"]))
    train_unit = int(sum(str(u).strip().casefold() not in (
        "is_blank","na","n/a","none","nan","null","")
                         for u in train["answer_unit"]))
    result={
       "dev":group(dev.to_dict("records")),
       "reused_holdout":group(hold.to_dict("records")),
       "all_train":group(train.to_dict("records")),
       "authorized_test_question_count":len(test),
       "authorized_test_unit_present":test_unit,
       "authorized_train_unit_present":train_unit,
       "scorer_sha256":EXPECTED["Score.py"],
       "boundary":"TRAIN gold values summarized by shape and evidence type "
                  "only, no individual labeled row; protected TEST answer and "
                  "citation labels not accessed. Tuple range, scalar result "
                  "within a training band, and categorical list are distinct "
                  "protected-future answer conventions.",
    }
    print("WATTBOT_SCORE_TYPE_CONTRACT="+json.dumps(result,sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Specify --self-test or --official-zip")
