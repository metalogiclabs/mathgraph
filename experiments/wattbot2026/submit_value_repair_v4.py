#!/usr/bin/env python3
"""WattBot V4: safely compose independently TRAIN-qualified source-value repair.

Exactly frozen official competition inputs, corpus digests, PDF windows, model,
budget and full 317-row CSV gate are inherited unchanged from V3. The only
intervention is a source-unique literal-value repair for rejected model quotes.
The independent versioned Kaggle server alone determines the external score.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import full_reader as reader
import submit_full_reader as v3
from value_anchor import repaired_by_value, self_test as value_self_test

BASELINE_READER_BLOB="4e1350ef72a44a333862dec23c737a2262ab99bc"
EXCERPT_BLOB="8b3e37e4e1b0ebd36bb157ec73f8d51354e5cdf7"
EVIDENCE_RUN=37971044770

def git_blob(path):
    body=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(body)).encode()+b"\0"+body).hexdigest()

def self_test():
    v3.self_test()
    value_self_test()
    assert git_blob(reader.__file__)==BASELINE_READER_BLOB
    assert git_blob(Path(__file__).with_name("query_window.py"))==EXCERPT_BLOB
    assert reader.MODEL=="google/gemini-2.5-flash-lite"
    assert reader.MAX_EXCERPT==1100 and reader.K==6
    assert v3.MAX_API_COST_USD==0.65
    assert v3.EXPECTED_TEST_ROWS==317
    print("WATTBOT_VALUE_REPAIRED_V4_SELF_TEST=PASS",flush=True)

def run(archive,out):
    self_test()
    baseline_checker=reader.try_checked
    counts=Counter()
    def checked_with_unique_literal_repair(generated,question,passages,docs):
        checked,reason=baseline_checker(generated,question,passages,docs)
        if checked is not None:
            counts["original_"+reason]+=1
            return checked,reason
        repaired,repair_reason=repaired_by_value(
            generated,question,passages,docs,reason)
        counts["original_rejection_"+reason]+=1
        counts["repair_"+repair_reason]+=1
        if repaired is not None:
            counts["admitted_new"]+=1
            return repaired,"VALUE_LITERAL_PAGE_ANCHORED"
        return checked,reason
    reader.try_checked=checked_with_unique_literal_repair
    try:
        v3.run(archive,out,policy="window")
    finally:
        reader.try_checked=baseline_checker
    # V3 already validated exact 317 rows plus every CSV field.
    print("WATTBOT_V4_REPAIR_ADMISSION="+json.dumps({
        "source":"Exact copied source-value repair, green paired TRAIN run",
        "train_qualification_run":EVIDENCE_RUN,
        "kaggle_score":"UNKNOWN until independently COMPLETE",
        "no_labels_used_for_prediction":True,
        "unchanged_corpus_reader_model_window_budget_transport":True,
        "repair_policy_counts":dict(counts),
        "science_boundary":"Value literally on one authorized page, NOT semantic entailment",
    },sort_keys=True),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    p.add_argument("--out")
    a=p.parse_args()
    if a.self_test:
        self_test()
    elif a.official_zip and a.out:
        run(a.official_zip,a.out)
    else:
        p.error("Provide --self-test or --official-zip and --out")
