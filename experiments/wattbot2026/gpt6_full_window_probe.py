#!/usr/bin/env python3
"""Matched full-corpus GPT-6 Luna WattBot TRAIN-only model substitution.

Only the inference model/pricing changes relative to the frozen complete
question-window reader. The 114 arXiv + eight report source attempt, BM25
ranking, K=6, exact windows, quote verification and numeric fallback stay
unchanged. A model-id guard fails closed. Labels enter only the official scorer
after answers freeze. The reused 63-row TRAIN subset is NOT an independent
holdout or leaderboard result.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path

import requests

import full_reader as base
import full_window_probe as frozen
from query_window import window_passages

MODEL = "openai/gpt-6-luna"
MAX_PRICE_IN = 0.00000015
MAX_PRICE_OUT = 0.00000075
MAX_TOTAL_RESERVED_USD = 0.16
EXPECTED_GEMINI_SCORE = 0.49708995
EXPECTED_ARXIV_MANIFEST = "4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
EXPECTED_REPORT_MANIFEST = "a1720d14806ff219eaac8e0e8b8a5c8d6e87f596bba1a852505374ab4343b77d"
RESULT_PREFIX = "WATTBOT_FULL_READER_HOLDOUT="


def price_or_refuse():
    response=requests.get("https://openrouter.ai/api/v1/models",timeout=(8,25))
    response.raise_for_status()
    matches=[x for x in response.json().get("data",[]) if x.get("id")==MODEL]
    if len(matches)!=1:
        raise RuntimeError("Exact predeclared inference model is unavailable")
    pricing=matches[0].get("pricing") or {}
    try:
        prompt=float(pricing["prompt"])
        completion=float(pricing["completion"])
    except (KeyError,ValueError,TypeError) as exc:
        raise RuntimeError("Unknown exact model prices") from exc
    if not (0<=prompt<=MAX_PRICE_IN and 0<=completion<=MAX_PRICE_OUT):
        raise RuntimeError("Live inference prices exceed declared maximum")
    return {"prompt":prompt,"completion":completion}


def self_test():
    # Pin the original corpus reader, quote checker, window selector and budget.
    frozen.self_test()
    assert base.MODEL == "google/gemini-2.5-flash-lite"
    assert base.MAX_BUDGET_USD == 0.12
    assert base.K==6 and base.MAX_EXCERPT==1100 and base.MAX_REQUESTS==63
    assert base.SOURCE_BUDGET==114
    assert MODEL=="openai/gpt-6-luna"
    assert 0 < MAX_TOTAL_RESERVED_USD <= 0.16
    sample=[
        {"ref_id":"p","url":"https://arxiv.org/abs/1234","page":1,
         "text":"background "*300+"The electrical load was 72.5 MW."}
    ]
    chosen=window_passages("What was the electrical load in MW?",sample,1100)
    assert len(chosen)==1 and "72.5 MW" in chosen[0]["text"]
    assert chosen[0]["text"]==sample[0]["text"][
       chosen[0]["excerpt_start"]:chosen[0]["excerpt_end"]]
    print("WATTBOT_GPT6_FULL_WINDOW_SELF_TEST=PASS",flush=True)


def run(archive):
    self_test()
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("No approved model key, no calls may be made")
    old_model=base.MODEL
    old_price=base.verify_price_ceiling
    old_budget=base.MAX_BUDGET_USD
    old_passages=base.passages_for
    post=requests.post
    counters={"questions":0,"shifted_pages":0}

    def select_windows(question, index):
        raw, numeric_hits = old_passages(question,index)
        changed=window_passages(question,raw,base.MAX_EXCERPT)
        for before, after in zip(raw,changed):
            if (before["ref_id"],before["page"],before["url"]) != (
                    after["ref_id"],after["page"],after["url"]):
                raise AssertionError("Changed page identity or source order")
            if after["text"] != before["text"][
                    after["excerpt_start"]:after["excerpt_end"]]:
                raise AssertionError("Non-source passage text generated")
            counters["shifted_pages"] += after["excerpt_start"]!=0
        counters["questions"]+=1
        return changed,numeric_hits

    def require_model_reply(*args,**kwargs):
        response=post(*args,**kwargs)
        if response.status_code==200:
            data=response.json()
            if not isinstance(data,dict) or data.get("model")!=MODEL:
                raise RuntimeError("Provider changed the declared model identity")
        return response

    # Requests and SHA-verified source readers are preserved. Restore all
    # mutable module bindings even after failure or refusal.
    base.MODEL=MODEL
    base.verify_price_ceiling=price_or_refuse
    base.MAX_BUDGET_USD=MAX_TOTAL_RESERVED_USD
    base.passages_for=select_windows
    requests.post=require_model_reply
    out=io.StringIO()
    try:
        with redirect_stdout(out):
            base.run(archive)
    finally:
        requests.post=post
        base.MODEL=old_model
        base.verify_price_ceiling=old_price
        base.MAX_BUDGET_USD=old_budget
        base.passages_for=old_passages
    reports=[json.loads(s[len(RESULT_PREFIX):])
       for s in out.getvalue().splitlines() if s.startswith(RESULT_PREFIX)]
    if len(reports)!=1:
        raise RuntimeError("No single valid official-scored inference report")
    report=reports[0]
    if report["source_manifest_sha256"]!=EXPECTED_ARXIV_MANIFEST:
        raise RuntimeError("Scientific arXiv source manifest drift, reject score")
    if report["report_hash_manifest_sha256"]!=EXPECTED_REPORT_MANIFEST:
        raise RuntimeError("Scientific report source manifest drift, reject score")
    if report["model"]!=MODEL or report["holdout_rows"]!=63 or counters["questions"]!=63:
        raise RuntimeError("Unqualified inference model or holdout coverage")
    if report["max_reserved_usd"]>MAX_TOTAL_RESERVED_USD:
        raise RuntimeError("Worst-case reserved price outside model cap")
    observed=report["scores"]["reader_then_numeric_fallback"]
    print("WATTBOT_GPT6_FULL_WINDOW_COMPARISON="+json.dumps({
       "scope":"Reused 63-row TRAIN subset; official scorer; not Kaggle or independent holdout",
       "model":MODEL,
       "old_frozen_reader_git_blob":frozen.BASE_READER_BLOB,
       "old_exact_window_blob":"8b3e37e4e1b0ebd36bb157ec73f8d51354e5cdf7",
       "arxiv_manifest":EXPECTED_ARXIV_MANIFEST,
       "report_manifest":EXPECTED_REPORT_MANIFEST,
       "same_corpus_ranker_window_quote_gate_numeric_fallback":True,
       "full_paired_same_run_models":False,
       "historical_gemini_flash_lite_score":EXPECTED_GEMINI_SCORE,
       "gpt6_luna_official_train_score":observed,
       "delta_vs_historical":round(observed-EXPECTED_GEMINI_SCORE,8),
       "gpt6_luna_page_checked":report["scores"]["reader_page_checked"],
       "numeric_control":report["scores"]["numeric_all_pinned_accessible"],
       "outcomes":report["outcomes"],
       "model_price":report["model_price"],
       "maximum_reserved_usd":report["max_reserved_usd"],
       "observed_usd":report["observed_api_usd"],
       "questions":counters["questions"],
       "shifted_pages":counters["shifted_pages"],
       "promotion":"No promotion before causal controls and an independent official Kaggle score",
    },sort_keys=True),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--official-zip")
    args=parser.parse_args()
    if args.self_test:self_test()
    elif args.official_zip:run(args.official_zip)
    else:parser.error("Provide --self-test or --official-zip")
