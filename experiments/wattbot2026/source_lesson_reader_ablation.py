#!/usr/bin/env python3
"""WattBot paired source-trained K6 reader with compiled developmental lessons.

Selection of source policy (two_medium) is frozen by prior dev-LOO citation
qualification run 37997556865, NEVER selected using target holdout labels.
Every question receives the original K6 pages and two authorized development
examples; only questions whose source selection changes receive a paired
second model call with SAME question, lesson and K6 budget but different real
pinned PDF pages. Independent quotation checker and candidate-value
provenance are evaluated after predictions freeze by official Score.py.

The evaluation reuses 63 previously inspected TRAIN questions; it is not a
Kaggle submission or scientific semantic entailment proof. Dev labeled
source IDs train retrieval; target holdout labels never enter inference.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import zipfile

import pandas as pd

import full_reader as base
from answer_value_residual_probe import raw_variant, usable
from citation_lesson_probe import SourceLessons,pick
from holdout_probe import is_holdout
from query_window import window_passages
from score_ablation import load_score
from source_refinement_probe import FrozenBM25
from verified_lesson import illustrate,self_test as lesson_test

POLICY="two_medium"
SOURCE_TRAIN_RUN=37997556865
SOURCE_DIGEST="4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
TRAIN_SHA="9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca"
SCORE_SHA="e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075"
BASE_READER_BLOB="4e1350ef72a44a333862dec23c737a2262ab99bc"
FIRST_CAP=.12
ALTERNATE_CAP=.12


def git_blob(path):
    raw=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()


def self_test():
    lesson_test()
    assert git_blob(base.__file__)==BASE_READER_BLOB
    assert base.K==6 and base.MAX_EXCERPT==1100
    assert base.MODEL=="google/gemini-2.5-flash-lite"
    assert POLICY=="two_medium"
    assert ALTERNATE_CAP<=base.MAX_BUDGET_USD
    assert FIRST_CAP==base.MAX_BUDGET_USD
    print("WATTBOT_SOURCE_LESSON_READER_SELF_TEST=PASS")


def run(archive):
    self_test()
    with zipfile.ZipFile(archive) as z:
        if hashlib.sha256(z.read("train_QA.csv")).hexdigest()!=TRAIN_SHA:
            raise RuntimeError("TRAIN source pin changed")
        if hashlib.sha256(z.read("Score.py")).hexdigest()!=SCORE_SHA:
            raise RuntimeError("Official Score.py pin changed")
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          dtype={"id":str},keep_default_na=False)
    rawdev=train[~train["id"].map(is_holdout)].to_dict("records")
    rawhold=train[train["id"].map(is_holdout)].to_dict("records")
    if len(rawdev)!=182 or len(rawhold)!=63:
        raise RuntimeError("Development/holdout split changed")
    learner=SourceLessons(rawdev)
    if len(learner.index)<150:
        raise RuntimeError("Insufficient qualified developmental source lessons")

    original_passages=base.passages_for
    original_model=base.call_reader
    original_numeric=base.build_candidate
    original_quote=base.try_checked
    all_index=[]
    page_map={}
    first={}
    second={}
    source_changed={}
    numeric={}
    checked={}
    docs_by_id={}
    spent=[0.,0.,0.,0.]
    counters=Counter()

    def frozen_pages(question,chunks):
        baseline,numeric_hits=original_passages(question,chunks)
        if not all_index:
            all_index.append(FrozenBM25(chunks))
        if all_index[0].n!=len(chunks):
            raise RuntimeError("Pinned corpus changed between questions")
        full_rank=all_index[0].ranked(question,all_index[0].n)
        rawpages=[p for p in full_rank if p["page"]>0][:base.K]
        if len(baseline)!=base.K or len(rawpages)!=base.K:
            raise RuntimeError("Frozen source evidence does not include K6")
        assert [(p["ref_id"],p["page"],p["score"]) for p in rawpages] == [
                (p["ref_id"],p["page"],p["score"]) for p in baseline]
        target,changed,confidence,neighbors=pick(
            question,full_rank,learner,POLICY)
        original_windows=window_passages(question,baseline,base.MAX_EXCERPT)
        learned_windows=window_passages(question,target,base.MAX_EXCERPT)
        for a,b in zip(baseline,original_windows):
            assert b["text"]==a["text"][b["excerpt_start"]:b["excerpt_end"]]
        for a,b in zip(target,learned_windows):
            assert b["text"]==a["text"][b["excerpt_start"]:b["excerpt_end"]]
        page_map[question]=(original_windows,learned_windows,changed)
        source_changed[question]=changed
        counters["questions"]+=1
        counters["source_changed"]+=int(changed)
        counters["original_evidence_pages"]+=len(original_windows)
        counters["alternative_evidence_pages"]+=len(learned_windows)
        return original_windows,numeric_hits

    def price_of(text,pages,price):
        wire=json.dumps({"question":text,
           "passages":[{"source_index":i,"ref_id":p["ref_id"],
             "page":p["page"],"text":p["text"][:base.MAX_EXCERPT]}
             for i,p in enumerate(pages)]},ensure_ascii=False,separators=(",",":"))
        return base.conservative_charge(base.SYSTEM+wire,price,base.MAX_OUTPUT_TOKENS)

    def model_pair(key,q,pages,rate):
        if q in first or q not in page_map:
            raise RuntimeError("Unknown or duplicate heldout question")
        original,alternative,changed=page_map[q]
        if [(x["ref_id"],x["page"],x["text"]) for x in pages]!=[
           (x["ref_id"],x["page"],x["text"]) for x in original]:
            raise RuntimeError("Reader first-page evidence altered")
        lesson=q+illustrate(q,rawdev)
        left=price_of(lesson,original,rate)
        if spent[0]+left>FIRST_CAP:
            raise RuntimeError("Original lesson reader reserved cost exceeded cap")
        right=price_of(lesson,alternative,rate) if changed else 0.
        if spent[2]+right>ALTERNATE_CAP:
            raise RuntimeError("Alternative source reader reserved cost exceeded cap")
        a,status1,bound1,cost1=original_model(key,lesson,original,rate)
        if abs(bound1-left)>1e-8:
            raise RuntimeError("First model price/usage disagrees")
        if status1 in ("HTTP_401","HTTP_403","HTTP_429","PROVIDER_ERROR"):
            raise RuntimeError("First model provider error")
        first[q]=(a,status1)
        spent[0]+=bound1
        spent[1]+=cost1
        counters["initial_"+status1]+=1
        if changed:
            b,status2,bound2,cost2=original_model(key,lesson,alternative,rate)
            if abs(bound2-right)>1e-8:
                raise RuntimeError("Alternate model price/usage disagrees")
            if status2 in ("HTTP_401","HTTP_403","HTTP_429","PROVIDER_ERROR"):
                raise RuntimeError("Alternative source reader provider error")
            second[q]=(b,status2)
            spent[2]+=bound2
            spent[3]+=cost2
            counters["alternate_"+status2]+=1
        return a,status1,bound1,cost1

    def save_numeric(q,hits,docs):
        docs_by_id[q["id"]]=docs
        item=original_numeric(q,hits,docs)
        if q["id"] not in numeric:numeric[q["id"]]=item
        return item

    def save_checked(raw,q,pages,docs):
        result,reason=original_quote(raw,q,pages,docs)
        checked[q["id"]]=(result,reason)
        counters["initial_"+reason]+=1
        return result,reason

    output=io.StringIO()
    try:
        base.passages_for=frozen_pages
        base.call_reader=model_pair
        base.build_candidate=save_numeric
        base.try_checked=save_checked
        with redirect_stdout(output):
            base.run(archive)
    finally:
        base.passages_for=original_passages
        base.call_reader=original_model
        base.build_candidate=original_numeric
        base.try_checked=original_quote

    marker="WATTBOT_FULL_READER_HOLDOUT="
    results=[json.loads(line[len(marker):]) for line in output.getvalue().splitlines()
             if line.startswith(marker)]
    if len(results)!=1 or results[0]["holdout_rows"]!=63:
        raise RuntimeError("Incomplete source reader scored cohort")
    prior=results[0]
    if prior["source_manifest_sha256"]!=SOURCE_DIGEST:
        raise RuntimeError("Pinned source sha256 changed")
    if (len(first)!=63 or len(numeric)!=63 or len(page_map)!=63 or
        counters["questions"]!=63 or
        counters["alternative_evidence_pages"]!=378):
        raise RuntimeError("Heldout question count or source page budget changed")
    if spent[0]>FIRST_CAP or spent[2]>ALTERNATE_CAP:
        raise RuntimeError("Reserved budget exceeded")

    hold=pd.DataFrame(rawhold).reset_index(drop=True)
    blank=base.blank_submission(hold).reset_index(drop=True)
    modes={k:[] for k in (
        "baseline_strict",
        "baseline_lesson_provisional",
        "source_trained_strict",
        "source_trained_provisional",
        "source_trained_preserve_baseline_quote",
    )}
    for _,row in blank.iterrows():
        id_=str(row["id"])
        q=str(row["question"])
        original_pages,alternate_pages,changed=page_map[q]
        original_raw,status=first[q]
        fallback=numeric[id_]
        verified,_=checked.get(id_,(None,"NOT_CHECKED"))
        first_candidate=(dict(verified) if verified is not None else
            raw_variant(row,original_raw,fallback,original_pages,"selected"))
        first_strict=(dict(verified) if verified is not None else dict(fallback))
        if changed:
            other,status2=second[q]
            alternative_checked,why=original_quote(
                other,{"id":id_,"question":q},
                alternate_pages,docs_by_id[id_])
            counters["alternative_"+why]+=1
            if (status2=="OK" and usable(other)):
                second_candidate=(dict(alternative_checked)
                    if alternative_checked is not None else
                    raw_variant(row,other,fallback,alternate_pages,"selected"))
            else:
                second_candidate=first_candidate
            second_strict=(dict(alternative_checked) if alternative_checked is not None
                           else first_strict)
        else:
            second_candidate=first_candidate
            second_strict=first_strict
        if second_candidate["answer_value"]!=first_candidate["answer_value"]:
            counters["answer_value_changed"]+=1
        modes["baseline_strict"].append(first_strict)
        modes["baseline_lesson_provisional"].append(first_candidate)
        modes["source_trained_strict"].append(second_strict)
        modes["source_trained_provisional"].append(second_candidate)
        modes["source_trained_preserve_baseline_quote"].append(
            dict(verified) if verified is not None else second_candidate)

    with zipfile.ZipFile(archive) as z:
        with tempfile.TemporaryDirectory(prefix="wattbot_source_reader_score_") as td:
            official=load_score(z,td)
            scores={}
            for name,rows in modes.items():
                df=pd.DataFrame(rows,columns=list(blank.columns))
                scores[name]=round(float(official(
                    hold.copy(deep=True),df,row_id_column_name="id",
                    verbose=False)),8)
    print("WATTBOT_SOURCE_LESSON_PAIRED_READER="+json.dumps({
        "status":"TRAIN_CANDIDATE_ONLY",
        "selected_source_policy":POLICY,
        "qualified_source_policy_run":SOURCE_TRAIN_RUN,
        "trained_dev_source_patterns":len(learner.index),
        "pinned_source_manifest":SOURCE_DIGEST,
        "score_arms_same_model_and_question_cohort":scores,
        "paired_source_policy_delta":round(scores["source_trained_provisional"]-
                                            scores["baseline_lesson_provisional"],8),
        "same_run_original_reader_score":prior["scores"],
        "source_pages_per_model_call":base.K,
        "contexts_and_model_outcomes":dict(counters),
        "first_reader_reserved_usd":round(spent[0],8),
        "first_reader_model_usd":round(spent[1],8),
        "extra_source_reader_reserved_usd":round(spent[2],8),
        "extra_source_reader_model_usd":round(spent[3],8),
        "boundary":"Question-to-source compiled on 182 development TRAIN "
          "labels, evaluated on 63 reused TRAIN holdout only. Model calls use "
          "identical question/lesson and exactly six pinned PDF excerpts, "
          "different source pages only for cases with a learned source proposal. "
          "Quote checking licenses PDF literal occurrence, never scientific "
          "entailment; all provisional model answer values remain CANDIDATE. "
          "No TEST answers/citations accessed and no Kaggle submission."
    },sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Provide --self-test or --official-zip")
