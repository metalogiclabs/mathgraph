#!/usr/bin/env python3
"""Audit only missing-value counts in a user-owned failed WattBot submission.

Never print source question text, test answers, candidate values, or rows.
Treat competition's strict CSV parsing as final authority for field presence.
"""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path

COLUMNS=("id","question","answer","answer_value","answer_unit",
         "ref_id","ref_url","supporting_materials","explanation")

def run(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f)
        fields=r.fieldnames
        if fields!=list(COLUMNS):
            raise RuntimeError("Wrong column headers or unexpected order")
        missing=Counter()
        null_tokens=Counter()
        count=0
        literal_nulls={"","nan","none","null","na","n/a","nat","<na>"}
        for row in r:
            count+=1
            for name in COLUMNS:
                raw=row.get(name)
                if raw is None or not raw.strip():
                    missing[name]+=1
                elif raw.strip().casefold() in literal_nulls:
                    null_tokens[name]+=1
        print("WATTBOT_FAILED_SUBMISSION_NULL_COUNTS="+json.dumps({
            "row_count":count,
            "blank_or_missing_per_column":dict(missing),
            "potential_auto_na_literal_per_column":dict(null_tokens),
            "boundary":"No question, source or prediction content disclosed; no resubmission performed"
        },sort_keys=True),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--submission",required=True)
    run(p.parse_args().submission)
