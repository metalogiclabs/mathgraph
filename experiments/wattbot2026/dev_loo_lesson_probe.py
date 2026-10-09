#!/usr/bin/env python3
"""WattBot development leave-one-out lesson transfer, frozen full PDF corpus.

On all 182 *development* TRAIN rows, a target question's own official answer,
citations and other labeled fields are NEVER included in that question's
worked examples or model prompt. Both model responses see the SAME pinned six
PDF excerpts. Score after freezing responses with the official pinned
Score.py. Corpus membership includes all 114 officially enumerated arXiv
sources plus seven accessible reports, pinned to existing digest; reference
order is fixed by historical development ranking, so this is not a pristine
source-selection holdout. Dev labels are otherwise never prediction inputs.

This is a broader cross-validation check of lesson transfer, NOT Kaggle TEST.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path
import pandas as pd

import full_reader as base
from answer_value_residual_probe import raw_variant
from holdout_probe import is_holdout as original_split
from query_window import window_passages
from score_ablation import load_score
from verified_lesson import illustrate, self_test as lesson_self_test

BASE_BLOB="4e1350ef72a44a333862dec23c737a2262ab99bc"
SOURCE_DIGEST="4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
TRAIN_SHA="9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca"
SCORE_SHA="e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075"
EXPECTED_TARGETS=182
MAX_PRIMARY_RESERVED=.46
MAX_SECONDARY_RESERVED=.58
MAX_SECONDARY_QUESTIONS=182


def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()


def self_test():
    lesson_self_test()
    assert git_blob(Path(base.__file__).read_bytes())==BASE_BLOB
    assert base.MAX_REQUESTS==63 and base.SOURCE_BUDGET==114
    assert base.K==6 and base.MAX_EXCERPT==1100
    assert base.MODEL=="google/gemini-2.5-flash-lite"
    assert MAX_PRIMARY_RESERVED<.5 and MAX_SECONDARY_RESERVED<.6
    print("WATTBOT_DEV_LOO_LESSON_SELF_TEST=PASS")


def run(archive):
    self_test()
    with zipfile.ZipFile(archive) as z:
        if hashlib.sha256(z.read("train_QA.csv")).hexdigest()!=TRAIN_SHA:
            raise RuntimeError("Official TRAIN SHA changed")
        if hashlib.sha256(z.read("Score.py")).hexdigest()!=SCORE_SHA:
            raise RuntimeError("Official scorer SHA changed")
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str})
        metadata=pd.read_csv(io.BytesIO(z.read("metadata.csv")),
                             keep_default_na=False,dtype={"id":str})
    original_dev=train[~train["id"].map(original_split)].copy()
    original_hold=train[train["id"].map(original_split)].copy()
    if len(original_dev)!=182 or len(original_hold)!=63:
        raise RuntimeError("Official source/development split changed")
    bank=original_dev.to_dict("records")
    lookup={str(x["question"]):str(x["id"]) for x in bank}
    if len(lookup)!=EXPECTED_TARGETS:
        raise RuntimeError("Ambiguous dev question text; cannot preserve self-exclusion")
    # All 114 arXiv sources are included; preserve historical ordering so
    # the byte-level source digest matches existing production qualification.
    docs={str(row["id"]):row for row in metadata.to_dict("records")}
    original_source_order=base.selected_sources(original_dev,docs)
    if len(original_source_order)!=114:
        raise RuntimeError("Frozen enumerated source count changed")

    raw_model=base.call_reader
    original_passages=base.passages_for
    original_numeric=base.build_candidate
    original_checker=base.try_checked
    original_is_holdout=base.is_holdout
    original_selected=base.selected_sources
    before_request_cap=base.MAX_REQUESTS
    before_price_cap=base.MAX_BUDGET_USD
    status=Counter()
    first={}
    second={}
    six={}
    numeric={}
    checked={}
    docs_by_id={}
    extra=[0.,0.]

    def inverted_dev_split(ident):
        return not original_split(str(ident))

    def source_registry_only(dev,docs_runtime):
        ids=original_source_order
        if any(i not in docs_runtime for i in ids):
            raise RuntimeError("Pinned source ID absent")
        return ids

    def selected_passages(question,chunks):
        pages,hits=original_passages(question,chunks)
        shifted=window_passages(question,pages,base.MAX_EXCERPT)
        if len(shifted)!=base.K:
            raise RuntimeError("Not six grounded model contexts")
        for a,b in zip(pages,shifted):
            assert all(a[key]==b[key] for key in ("ref_id","url","page"))
            assert b["text"]==a["text"][b["excerpt_start"]:b["excerpt_end"]]
        status["questions"]+=1
        status["pages"]+=len(shifted)
        return shifted,hits

    def pair_model(key,question,passages,price):
        if question in first or question not in lookup:
            raise RuntimeError("Unknown or duplicate development question")
        ident=lookup[question]
        # This target's label row is excluded, even though another similar
        # source might remain in the 182-row development memory.
        others=[r for r in bank if str(r["id"])!=ident]
        if len(others)!=181:
            raise RuntimeError("Target development label entered exemplar bank")
        enrichment=illustrate(question,others)
        if "TRAIN DEVELOPMENT ONLY" not in enrichment:
            raise RuntimeError("Lesson provenance lost")
        prompt=json.dumps({
            "question":question+enrichment,
            "passages":[{"source_index":i,"ref_id":p["ref_id"],"page":p["page"],
                         "text":p["text"][:base.MAX_EXCERPT]}
                        for i,p in enumerate(passages)]
        },ensure_ascii=False,separators=(",",":"))
        reserved=base.conservative_charge(
            base.SYSTEM+prompt,price,base.MAX_OUTPUT_TOKENS)
        if extra[0]+reserved>MAX_SECONDARY_RESERVED:
            raise RuntimeError("Secondary developmental lesson budget exceeded")
        first_raw,first_status,first_charge,first_cost=raw_model(
            key,question,passages,price)
        if first_status in ("HTTP_401","HTTP_403","HTTP_429","PROVIDER_ERROR"):
            raise RuntimeError("Provider unavailable, no complete qualification")
        second_raw,second_status,second_charge,second_cost=raw_model(
            key,question+enrichment,passages,price)
        if second_status in ("HTTP_401","HTTP_403","HTTP_429","PROVIDER_ERROR"):
            raise RuntimeError("Lesson provider unavailable")
        if abs(second_charge-reserved)>1e-8:
            raise RuntimeError("Independent lesson reserve disagrees")
        first[question]=(first_raw,first_status)
        second[question]=(second_raw,second_status)
        six[question]=list(passages)
        extra[0]+=second_charge
        extra[1]+=second_cost
        status["first_"+first_status]+=1
        status["lesson_"+second_status]+=1
        status["paired"]+=1
        return first_raw,first_status,first_charge,first_cost

    def save_numeric(q,hits,docs):
        value=original_numeric(q,hits,docs)
        if q["id"] not in numeric:
            numeric[q["id"]]=value
        return value

    def save_checked(response,q,pages,docs):
        value,reason=original_checker(response,q,pages,docs)
        checked[q["id"]]=(value,reason)
        docs_by_id[q["id"]]=docs
        status["first_"+reason]+=1
        return value,reason

    captured=io.StringIO()
    try:
        base.call_reader=pair_model
        base.passages_for=selected_passages
        base.build_candidate=save_numeric
        base.try_checked=save_checked
        base.is_holdout=inverted_dev_split
        base.selected_sources=source_registry_only
        base.MAX_REQUESTS=EXPECTED_TARGETS
        base.MAX_BUDGET_USD=MAX_PRIMARY_RESERVED
        with redirect_stdout(captured):
            base.run(archive)
    finally:
        base.call_reader=raw_model
        base.passages_for=original_passages
        base.build_candidate=original_numeric
        base.try_checked=original_checker
        base.is_holdout=original_is_holdout
        base.selected_sources=original_selected
        base.MAX_REQUESTS=before_request_cap
        base.MAX_BUDGET_USD=before_price_cap

    marker="WATTBOT_FULL_READER_HOLDOUT="
    entries=[json.loads(line[len(marker):])
             for line in captured.getvalue().splitlines() if line.startswith(marker)]
    if len(entries)!=1:
        raise RuntimeError("Incomplete official scorer result")
    base_result=entries[0]
    if (base_result["source_manifest_sha256"]!=SOURCE_DIGEST or
        base_result["holdout_rows"]!=EXPECTED_TARGETS or
        status["paired"]!=EXPECTED_TARGETS or len(numeric)!=EXPECTED_TARGETS):
        raise RuntimeError("Source or question scope drift")
    if base_result["max_reserved_usd"]>MAX_PRIMARY_RESERVED or extra[0]>MAX_SECONDARY_RESERVED:
        raise RuntimeError("Verified model price exceeds boundary")

    original_dev=original_dev.reset_index(drop=True)
    blank=base.blank_submission(original_dev).reset_index(drop=True)
    rows={p:[] for p in (
        "first_provisional",
        "lesson_provisional",
        "lesson_when_first_invalid",
        "lesson_else_first_explicit_blank",
    )}
    for _,row in blank.iterrows():
        q=str(row["question"])
        ident=str(row["id"])
        a,astat=first[q]
        b,bstat=second[q]
        pages=six[q]
        numeric_value=numeric[ident]
        strict,_=checked.get(ident,(None,"MODEL_NOT_CHECKED"))
        a_value=(dict(strict) if strict is not None else
                 raw_variant(row,a,numeric_value,pages,"selected"))
        b_value=raw_variant(row,b,a_value,pages,"selected")
        rows["first_provisional"].append(a_value)
        rows["lesson_provisional"].append(
            b_value if bstat=="OK" and str(b.get("answer_value","")).strip().casefold()
                        not in ("","is_blank","na","n/a","unknown","none","nan","null")
            else a_value)
        rows["lesson_when_first_invalid"].append(
            a_value if strict is not None else b_value)
        rows["lesson_else_first_explicit_blank"].append(
            a_value if (isinstance(a,dict) and
                str(a.get("answer_value","")).strip().casefold() in
                ("","is_blank","na","n/a","unknown","none","nan","null")
                and (not isinstance(b,dict) or
                     str(b.get("answer_value","")).strip().casefold() in
                     ("","is_blank","na","n/a","unknown","none","nan","null")))
            else b_value if bstat=="OK" else a_value)

    with zipfile.ZipFile(archive) as z:
        with tempfile.TemporaryDirectory(prefix="wattbot_devloo_score_") as tmp:
            official=load_score(z,tmp)
            results={}
            for name,items in rows.items():
                df=pd.DataFrame(items,columns=list(blank.columns))
                results[name]=round(float(official(
                    original_dev.copy(deep=True),df,
                    row_id_column_name="id",verbose=False)),8)
    print("WATTBOT_DEV_LOO_LESSON="+json.dumps({
        "scope":"182 development TRAIN questions, each excluded from its own two-example bank",
        "source_digest":SOURCE_DIGEST,
        "development_rows":EXPECTED_TARGETS,
        "separate_63_train_holdout_excluded_from_scoring":True,
        "read_gold_during_question_inference":False,
        "frozen_corpus_source_registry_selected_using_original_development_labels":True,
        "scores":results,
        "paired_lesson_minus_first":round(
            results["lesson_provisional"]-results["first_provisional"],8),
        "first_model_usd":base_result["observed_api_usd"],
        "lesson_model_usd":round(extra[1],7),
        "first_conservative_reserved_usd":base_result["max_reserved_usd"],
        "lesson_conservative_reserved_usd":round(extra[0],7),
        "counters":dict(status),
        "boundary":"Only source-PDF quotation occurrence and official TRAIN scoring "
                   "are checked. The experiment cross-validates exemplar transfer "
                   "under prechosen source membership/order, NOT fully fresh source "
                   "discovery and NOT independent Kaggle TEST/leaderboard proof. "
                   "No protected TEST answers, citations or submissions."
    },sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Supply --self-test or --official-zip")
