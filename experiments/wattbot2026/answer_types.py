#!/usr/bin/env python3
"""Official TRAIN answer-value type inventory. Aggregates only, no row leaks."""
import ast
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
import csv
import io
import json
import re
import zipfile
import argparse


def kind(value):
    s = str(value or "").strip()
    if s.casefold() in {"", "nan", "is_blank", "n/a", "none", "null", "[]"}:
        return "blank"
    v = s.replace(",", "").replace("−","-")
    try:
        d = Decimal(v.rstrip("%"))
        if d.is_finite():
            return "percentage" if v.endswith("%") else "number"
    except InvalidOperation:
        pass
    try:
        obj = ast.literal_eval(s)
        if isinstance(obj,(list,tuple,set,dict)):
            return "structured_list"
    except (ValueError,SyntaxError,TypeError,MemoryError):
        pass
    if s.casefold() in {"true","false","yes","no"}:
        return "boolean"
    return "short_text" if len(s.split()) <= 6 else "long_text"


def run(path):
    with zipfile.ZipFile(path) as z:
        rows = list(csv.DictReader(io.StringIO(z.read("train_QA.csv").decode("utf-8-sig"))))
    global_counts=Counter()
    bucket_counts=defaultdict(Counter)
    flags = ["Quote","Table","Figure","Math","CrossPaper","Reconcile","is_NA"]
    for r in rows:
        k=kind(r.get("answer_value",""))
        global_counts[k]+=1
        for flag in flags:
            if str(r.get(flag,"")).strip()=="1":
                bucket_counts[flag][k]+=1
    print("WATTBOT_ANSWER_TYPES="+json.dumps({
        "n_training_rows":len(rows),
        "answer_value_types":dict(global_counts),
        "stratified_types":{k:dict(v) for k,v in bucket_counts.items()},
        "note":"TRAIN answer labels read only for aggregate type profiling, never used as test predictions",
    },sort_keys=True))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip",required=True)
    run(p.parse_args().official_zip)
