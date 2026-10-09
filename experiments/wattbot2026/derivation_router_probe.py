#!/usr/bin/env python3
"""WattBot: derivation-first second reader only when QUESTION asks a calculation.

Same Flash-Lite six-excerpt first response is frozen for every 63-row TRAIN
question. Question-only grammar then triggers an independently bounded
ten-passage second read that requests source operands, calculations and exact
quotes. The unchanged official scorer compares all routes using the same
first and second responses. No TRAIN label influences routing or prompts.

The second reader is a claim generator, never a scientific proof authority.
Independent source quotation checks protect provenance; semantic relevance
of premises remains UNKNOWN. No Kaggle protected TEST, submit or publication.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import zipfile

import pandas as pd
import requests

import full_reader as base
from answer_value_residual_probe import raw_variant, usable
from verified_lesson import (illustrate, task_type, self_test as lessons_self_test)
from holdout_probe import is_holdout
from query_window import window_passages
from score_ablation import load_score

BASE_BLOB = "4e1350ef72a44a333862dec23c737a2262ab99bc"
PIN = {
  "Score.py":"e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
  "train_QA.csv":"9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
}
SOURCE_PIN="4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
SECONDARY_RESERVE_USD=.85
SECONDARY_TOP_K=10
SOL_MODEL="openai/gpt-6-sol"
SOL_TYPES=frozenset(("Math","CrossPaper"))
SOL_PROMPT_RATE_CEILING=.000002
SOL_COMPLETION_RATE_CEILING=.00001

INTENT_RE = re.compile(
    r"\b(?:calculate|compute|derive|estimate\s+the\s+(?:difference|ratio)|"
    r"percentage|percent|ratio|fraction|relative|average|mean|"
    r"sum|total\s+of|combined|difference|increase|decrease|"
    r"reduction|savings|equivalent|equivalence|"
    r"compared\s+(?:with|to)|comparison|reconcile|reconciliation|"
    r"versus|vs\.?|both\s+(?:papers|studies|reports)|"
    r"across\s+(?:the\s+)?(?:two|both|multiple)\s+"
    r"(?:papers|studies|reports)|"
    r"(?:upper|lower)\s+bound|range\s+(?:between|of))\b",
    re.I,
)
SECOND_INSTRUCTION=(
    "IMPORTANT: This is a quantitative/cross-document question. Do not "
    "copy a nearby number unless it actually answers the question. "
    "First identify the scientific quantities that are relevant and their "
    "source context. If the requested result must be calculated rather "
    "than copied, carry out the arithmetic carefully using the source "
    "numbers and compatible units. For cross-document comparison, identify "
    "each source separately, preserve both as source_indices where needed. "
    "For a range, return the endpoints in a Python-style string list if "
    "asked; for an exact number return only the number in answer_value. "
    "Cite literal supporting_quotes that actually occur in the supplied "
    "source passages. If the required inputs are absent, answer is_blank. "
    "Do not claim a computation or a citation you cannot support."
)


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest()


def derivation_question(question):
    return bool(INTENT_RE.search(str(question or "")))


def get_sol_pricing():
    response=requests.get("https://openrouter.ai/api/v1/models",timeout=(8,30))
    response.raise_for_status()
    matches=[model for model in response.json().get("data",[])
             if model.get("id")==SOL_MODEL]
    if len(matches)!=1:
        raise RuntimeError("GPT-6 Sol unavailable or ambiguous")
    pricing=matches[0].get("pricing") or {}
    p=float(pricing.get("prompt","nan"))
    c=float(pricing.get("completion","nan"))
    if not (0<=p<=SOL_PROMPT_RATE_CEILING
            and 0<=c<=SOL_COMPLETION_RATE_CEILING):
        raise RuntimeError("GPT-6 Sol live pricing exceeds frozen scope")
    return {"prompt":p,"completion":c}


def self_test():
    lessons_self_test()
    assert git_blob(Path(base.__file__).read_bytes())==BASE_BLOB
    assert base.K==6 and base.MAX_EXCERPT==1100 and base.MAX_REQUESTS==63
    assert base.MODEL=="google/gemini-2.5-flash-lite"
    assert derivation_question("What was the percentage change from 2020 to 2023?")
    assert derivation_question("Compare results across two studies.")
    assert derivation_question("What is the arithmetic mean energy usage?")
    assert not derivation_question("What was the reported electricity consumption?")
    assert not derivation_question("What was the publication year?")
    assert SECONDARY_RESERVE_USD>base.MAX_BUDGET_USD
    assert task_type("What percent increase was observed?")=="Math"
    assert task_type("Compare both studies' energy.")=="CrossPaper"
    assert task_type("What was the reported value?") not in SOL_TYPES
    print("WATTBOT_TYPED_SOL_LESSON_SELF_TEST=PASS")


def run(archive):
    self_test()
    with zipfile.ZipFile(archive) as z:
        for name,hash_value in PIN.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=hash_value:
                raise RuntimeError("Official TRAIN or scorer SHA moved: "+name)
        dev_train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
            keep_default_na=False,dtype={"id":str})
        worked=[item for item in dev_train.to_dict("records")
                if not is_holdout(str(item["id"]))]
        if len(worked)!=182:
            raise RuntimeError("Development example universe changed")
    sol_rate=get_sol_pricing()
    original_passages=base.passages_for
    original_model=base.call_reader
    original_numeric=base.build_candidate
    original_checker=base.try_checked
    pages_by_question={}
    ranked_by_question={}
    first_raw={}
    first_pages={}
    second_raw={}
    first_checked={}
    numeric={}
    docs_by_id={}
    stats=Counter()
    extra=[0.0,0.0]

    def windowed(question, chunks):
        passages,hits=original_passages(question,chunks)
        shifted=window_passages(question,passages,base.MAX_EXCERPT)
        pages_by_question[question]=shifted
        ranked_by_question[question]=hits
        stats["first_questions"]+=1
        stats["first_pages"]+=len(shifted)
        for parent,child in zip(passages,shifted):
            for key in ("ref_id","page","url"):
                assert parent[key]==child[key]
            assert child["text"]==parent["text"][
                child["excerpt_start"]:child["excerpt_end"]]
        return shifted,hits

    def call_model(key,question,passages,price):
        response,status,bound,actual=original_model(key,question,passages,price)
        if question in first_raw:
            raise RuntimeError("First response duplicated")
        first_raw[question]=(response,status)
        first_pages[question]=list(passages)
        stats["worked_example_question"]+=1
        # The exact same six PDF excerpts are supplied to both model calls:
        # the ONLY change is two development-only worked examples appended
        # to the instruction, never a target holdout label or source.
        expanded=list(passages)
        if len(expanded)!=base.K:
            raise RuntimeError("Lesson policy changed source depth")
        enriched=question+illustrate(question,worked)
        wire=json.dumps({"question":enriched,
                         "passages":[{"source_index":i,"ref_id":p["ref_id"],
                             "page":p["page"],"text":p["text"][:base.MAX_EXCERPT]}
                             for i,p in enumerate(expanded)]},
                        ensure_ascii=False,separators=(",",":"))
        question_type=task_type(question)
        use_sol=question_type in SOL_TYPES
        rate=sol_rate if use_sol else price
        charge=base.conservative_charge(
            base.SYSTEM+wire,rate,base.MAX_OUTPUT_TOKENS)
        if extra[0]+charge>SECONDARY_RESERVE_USD:
            stats["extra_cost_guard"]+=1
            return response,status,bound,actual
        prior_model=base.MODEL
        try:
            base.MODEL=SOL_MODEL if use_sol else prior_model
            later,reason,reserve,reported=original_model(
                key,enriched,expanded,rate)
        finally:
            base.MODEL=prior_model
        extra[0]+=reserve
        extra[1]+=reported
        stats["sol_tasks" if use_sol else "flashlite_tasks"]+=1
        if abs(charge-reserve) > 0.00000001:
            raise RuntimeError("Second-pass cost calculation diverges")
        second_raw[question]=(later,reason,expanded)
        stats["second_"+reason]+=1
        return response,status,bound,actual

    def save_numeric(question,hits,docs):
        item=original_numeric(question,hits,docs)
        if question["id"] not in numeric:
            numeric[question["id"]]=item
        return item

    def save_checked(raw,question,passages,docs):
        candidate,reason=original_checker(raw,question,passages,docs)
        first_checked[question["id"]]=(candidate,reason)
        docs_by_id[question["id"]]=docs
        stats["first_"+reason]+=1
        return candidate,reason

    buf=io.StringIO()
    try:
        base.passages_for=windowed
        base.call_reader=call_model
        base.build_candidate=save_numeric
        base.try_checked=save_checked
        with redirect_stdout(buf):
            base.run(archive)
    finally:
        base.passages_for=original_passages
        base.call_reader=original_model
        base.build_candidate=original_numeric
        base.try_checked=original_checker

    prefix="WATTBOT_FULL_READER_HOLDOUT="
    scores=[json.loads(x[len(prefix):]) for x in buf.getvalue().splitlines()
            if x.startswith(prefix)]
    if len(scores)!=1 or scores[0]["holdout_rows"]!=63:
        raise RuntimeError("Incomplete official holdout evaluation")
    baseline=scores[0]
    if baseline["source_manifest_sha256"]!=SOURCE_PIN:
        raise RuntimeError("PDF manifest changed")
    if len(first_raw)!=63 or len(first_checked)>63 or len(numeric)!=63:
        raise RuntimeError("Partial question cohort")
    if stats["first_pages"]!=378 or stats["first_questions"]!=63:
        raise RuntimeError("Changed six-source reader cohort")
    if extra[0]>SECONDARY_RESERVE_USD:
        raise RuntimeError("Additional spend exceeded reserved cap")

    with zipfile.ZipFile(archive) as z:
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
               keep_default_na=False,dtype={"id":str})
        hold=train[train["id"].map(is_holdout)].reset_index(drop=True)
        blank=base.blank_submission(hold).reset_index(drop=True)
        cols=list(blank.columns)
        arms={name:[] for name in (
          "first_strict",
          "first_provisional",
          "second_verified_when_first_unverified",
          "second_provisional_when_first_unverified",
          "second_verified_prefer_on_intent",
          "second_provisional_prefer_on_intent",
          "second_agreement_only",
        )}
        for _,row in blank.iterrows():
            ident=str(row["id"])
            q=str(row["question"])
            original,status=first_raw[q]
            prior_checked,_=first_checked.get(ident,(None,"FIRST_NOT_CHECKED"))
            default=numeric[ident]
            prior=raw_variant(row,original,default,first_pages[q],"selected")
            second,second_status,more=second_raw.get(q,(None,"NOT_TRIGGERED",[]))
            second_provisional=raw_variant(row,second,prior,more,"selected")
            later_checked,reason=original_checker(
                second,{"id":ident,"question":q},more,docs_by_id[ident])
            if second is not None:
                stats["second_check_"+reason]+=1
            first_strict=(dict(prior_checked) if prior_checked is not None
                          else dict(default))
            first_provisional=(dict(prior_checked) if prior_checked is not None
                               else prior)
            if later_checked is not None:
                stats["second_anchored"]+=1
            arms["first_strict"].append(first_strict)
            arms["first_provisional"].append(first_provisional)
            arms["second_verified_when_first_unverified"].append(
                dict(prior_checked) if prior_checked is not None else
                dict(later_checked) if later_checked is not None else dict(default))
            arms["second_provisional_when_first_unverified"].append(
                dict(prior_checked) if prior_checked is not None else
                dict(later_checked) if later_checked is not None else
                second_provisional)
            arms["second_verified_prefer_on_intent"].append(
                dict(later_checked) if later_checked is not None else first_strict)
            arms["second_provisional_prefer_on_intent"].append(
                second_provisional if usable(second) else first_provisional)
            # An agreement between independent reads is evidence of model
            # consistency, NOT a proof the answer is correct.
            same_value=(usable(original) and usable(second) and
                        str(original.get("answer_value","")).strip()
                        ==str(second.get("answer_value","")).strip())
            if same_value:stats["answer_value_agreement"]+=1
            arms["second_agreement_only"].append(
                second_provisional if same_value else first_provisional)

        with tempfile.TemporaryDirectory(prefix="wattbot_derivation_route_") as tmp:
            scorer=load_score(z,tmp)
            official={}
            for name,rows in arms.items():
                f=pd.DataFrame(rows,columns=cols)
                official[name]=round(float(scorer(hold.copy(deep=True),
                    f,row_id_column_name="id",verbose=False)),8)
    if abs(official["first_strict"]-
           baseline["scores"]["reader_then_numeric_fallback"])>0.00000002:
        raise RuntimeError("First-pass official scoring mismatch")
    print("WATTBOT_TYPED_SOL_LESSON_HOLDOUT="+json.dumps({
       "status":"CANDIDATE_TRAIN_ONLY",
       "scope":"Frozen 63 previously inspected TRAIN rows; same primary model outputs",
       "model":base.MODEL,"source_sha256":SOURCE_PIN,
       "model_call_routing":"Question-only task_type selects GPT-6 Sol for "
         "Math or CrossPaper; same Flash-Lite model elsewhere. Two worked "
         "examples from 182 development TRAIN, no target holdout label.",
       "only_router":"Question-only typed model specialization (Math/CrossPaper "
         "versus Quote/Table/Figure) with identical six pinned PDF excerpts "
         "and two development-only lesson exemplars",
       "score_arms":official,
       "strict_baseline":official["first_strict"],
       "provisional_baseline":official["first_provisional"],
       "deltas_vs_first_provisional":{
           k:round(v-official["first_provisional"],8)
           for k,v in official.items()},
       "counters":dict(stats),
       "first_api_reported_usd":baseline["observed_api_usd"],
       "secondary_reserved_usd":round(extra[0],7),
       "secondary_reported_usd":round(extra[1],7),
       "boundary":"One baseline Flash-Lite model response per question, "
         "same six pinned PDF snippets for every second model. Type classifier "
         "uses question wording and 182 development labels only, never target "
         "holdout answer/reference. Independent exact-page source check "
         "certifies literal provenance, NOT scientific semantic entailment. "
         "Only reused 63 TRAIN questions scored after output freeze; "
         "no protected TEST inference or Kaggle submission."
    },sort_keys=True),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--official-zip")
    args=parser.parse_args()
    if args.self_test:self_test()
    elif args.official_zip:run(args.official_zip)
    else:parser.error("Use --self-test or --official-zip")
