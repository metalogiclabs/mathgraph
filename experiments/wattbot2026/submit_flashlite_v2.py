#!/usr/bin/env python3
"""MathGraph WattBot V2: frozen 24-PDF Flash-Lite RAG on TEST questions ONLY.

The qualified training comparison is CI #37892176890, scorer 0.2952381
vs numeric 0.20925926 on the previously inspected 63-row train holdout.

This executable deliberately has NO test-gold reader. Its only label access is
the 182 DEV citation IDs used for frozen source selection. It never uses
question-specific gold answers, a 2025 dataset, or manual test overrides.
The output is merely a scientific QA candidate, NOT a verified proof.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
import zipfile

import pandas as pd
import requests

from flashlite_rag_probe import (
    SOURCE_BUDGET, MODEL, SYSTEM_PROMPT, MAX_OUTPUT_TOKENS,
    source_list, passages_for_question, select_anchored_page,
    with_model_answer,
)
from free_reader_probe import request_free_reader, verify_price_ceiling
from holdout_probe import is_holdout
from numeric_answer_probe import build_candidate
from pdf_probe import download_one
from wattbot import chunks_from_pages, ranked, COLUMNS

# Immutable Kaggle 2026 authority from verified schema run #37888722521.
OFFICIAL_SHA256 = {
    "Score.py":"e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
    "metadata.csv":"b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1",
    "train_QA.csv":"9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
    "test_Q.csv":"26038b21cb09588a39b0e95e5516e3827dadd499c85c3792d0ea46c10ae7066a",
}
SOURCE_MANIFEST_SHA256 = "dd3eefee514b58ea807c6670241ad4bba9111058216f844d8996f20076568e23"
MAX_ESTIMATED_USD = 0.40
MIN_SUCCESSFUL_API_FRACTION = 0.70
REQUEST_PAUSE_SECONDS = 0.65


def checked_test_questions(z:zipfile.ZipFile) -> list[dict[str,str]]:
    for name,expected in OFFICIAL_SHA256.items():
        actual=hashlib.sha256(z.read(name)).hexdigest()
        if actual!=expected:
            raise ValueError("Official file changed; stop and requalify "+name)
    with io.TextIOWrapper(z.open("test_Q.csv"),encoding="utf-8-sig",newline="") as stream:
        reader=csv.DictReader(stream)
        rows=[{"id":str(row["id"]), "question":str(row["question"])} for row in reader]
    if len(rows)!=317 or len(set(q["id"] for q in rows))!=317:
        raise ValueError("Unexpected official TEST IDs or row count")
    if any(not q["id"] or not q["question"] for q in rows):
        raise ValueError("Blank test ID or question")
    return rows


def run(archive_path:str,output_path:str):
    key=os.environ.get("OPENROUTER_API_KEY","")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not configured")
    price=verify_price_ceiling()
    if SOURCE_BUDGET!=24 or MODEL!="google/gemini-2.5-flash-lite":
        raise RuntimeError("Model or 24-source authority changed")
    with zipfile.ZipFile(archive_path) as z:
        tests=checked_test_questions(z)
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),keep_default_na=False,dtype={"id":str})
        meta=pd.read_csv(io.BytesIO(z.read("metadata.csv")),keep_default_na=False,dtype={"id":str})
    dev=train[~train["id"].map(is_holdout)].copy()
    if len(dev)!=182:
        raise ValueError("Development split changed; stop")
    docs={str(r["id"]):r for r in meta.to_dict("records")}
    selected=source_list(dev,docs)
    if len(selected)!=SOURCE_BUDGET:raise ValueError("Expected 24 frozen sources")
    cost_reserved=0.
    reported_costs=[]
    success=0
    nonblank=0
    anchored=0
    responses={}
    rows=[]
    with tempfile.TemporaryDirectory(prefix="mathgraph_wattbot_v2_") as folder:
        root=Path(folder)
        chunks=[]
        hashes=[]
        for i,ref in enumerate(selected):
            if i:time.sleep(3.1)
            path=root/f"source_{i}.pdf"
            sha,_=download_one(str(docs[ref]["url"]),path)
            pieces=chunks_from_pages(ref,str(docs[ref]["url"]),path)
            if not pieces:raise ValueError("Pinned public PDF missing text")
            chunks.extend(pieces)
            hashes.append(sha)
        manifest=hashlib.sha256("\n".join(hashes).encode()).hexdigest()
        if manifest!=SOURCE_MANIFEST_SHA256:
            raise ValueError("Source PDF checksum manifest changed: requalify")
        meta_chunks=[{"ref_id":m["id"],"url":m["url"],"page":0,
                      "text":" ".join(str(m.get(k,"") or "") for k in
                                       ("title","citation","year","venue"))}
                     for m in meta.to_dict("records")]
        numeric_index=meta_chunks+chunks
        for i,test in enumerate(tests):
            question=test["question"]
            rank=ranked(question,numeric_index,min(100,len(numeric_index)))
            fallback=build_candidate(test,rank,docs)
            pages,prompt=passages_for_question(question,chunks)
            candidate=fallback
            if prompt:
                estimate=(len(prompt)+len(question)+len(SYSTEM_PROMPT)+1000)*price["prompt"]+MAX_OUTPUT_TOKENS*price["completion"]
                if cost_reserved+estimate<=MAX_ESTIMATED_USD:
                    cost_reserved+=estimate
                    try:
                        response,status,usage=request_free_reader(key,question,prompt)
                    except requests.RequestException as exc:
                        response,status,usage=None,type(exc).__name__,None
                    responses[status]=responses.get(status,0)+1
                    if usage and isinstance(usage.get("cost_observed"),(int,float)):
                        reported_costs.append(float(usage["cost_observed"]))
                    if status=="OK":
                        success+=1
                        if response:
                            model_candidate=with_model_answer(
                                {"id":test["id"],"question":question,
                                 "answer":"Unable to answer from available source text.",
                                 "answer_value":"is_blank",
                                 "answer_unit":"is_blank",
                                 "ref_id":"is_blank","ref_url":"is_blank",
                                 "supporting_materials":"is_blank",
                                 "explanation":"No independently anchored model answer."},response)
                            if model_candidate["answer_value"]!="is_blank":
                                source=select_anchored_page(response["supporting_quote"],pages)
                                if source:
                                    anchored+=1
                                    model_candidate=with_model_answer(model_candidate,response,source)
                                candidate=model_candidate
                else:
                    responses["PRECALL_BUDGET_ABORT"]=responses.get("PRECALL_BUDGET_ABORT",0)+1
            # Discard any unrelated/extra host-response fields.
            if str(candidate["id"]) != test["id"]:
                raise ValueError("Prediction ID mismatch")
            result={col: str(candidate.get(col,"is_blank")) for col in COLUMNS}
            result["id"]=test["id"]
            result["question"]=question
            if not result["answer_value"] or not result["explanation"]:
                raise ValueError("Invalid prediction missing required fields")
            nonblank+=result["answer_value"]!="is_blank"
            rows.append(result)
            if i+1<len(tests):time.sleep(REQUEST_PAUSE_SECONDS)
    # Fail closed; never waste a Kaggle submission on wholesale API failures.
    if success < int(len(tests)*MIN_SUCCESSFUL_API_FRACTION):
        raise RuntimeError("Provider response success insufficient for V2 admission: "+
                           str(success)+" of "+str(len(tests)))
    if sum(reported_costs)>MAX_ESTIMATED_USD:
        raise RuntimeError("API reported charge exceeds declared V2 cap")
    output=Path(output_path)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(COLUMNS),extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    with output.open("r",encoding="utf-8",newline="") as f:
        reader=csv.DictReader(f)
        check=list(reader)
        assert reader.fieldnames==list(COLUMNS) and len(check)==317
        assert [r["id"] for r in check]==[t["id"] for t in tests]
    print("WATTBOT_V2_CANDIDATE_PREPARED="+json.dumps({
        "test_rows":len(tests),
        "nonblank":nonblank,
        "page_anchored_model_outputs":anchored,
        "successful_model_api_responses":success,
        "api_status_summary":responses,
        "pinned_pdfs":len(selected),
        "pinned_pdf_chunks":len(chunks),
        "source_manifest_sha256":manifest,
        "model_id":MODEL,
        "budget_cap_usd":MAX_ESTIMATED_USD,
        "precommitted_estimated_usd":round(cost_reserved,8),
        "reported_cost_usd":round(sum(reported_costs),8),
        "submission_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
        "boundary":"TEST questions only, source identity DEV-only. Answer correctness decided by Kaggle; not a verified proof",
    },sort_keys=True),flush=True)


def self_test():
    assert list(COLUMNS)==["id","question","answer","answer_value","answer_unit",
                            "ref_id","ref_url","supporting_materials","explanation"]
    assert len(OFFICIAL_SHA256)==4
    assert SOURCE_BUDGET==24 and MAX_ESTIMATED_USD<1
    assert MIN_SUCCESSFUL_API_FRACTION==.70
    print("WATTBOT_V2_SELF_TEST=PASS")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip")
    p.add_argument("--out")
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test:self_test()
    elif args.official_zip and args.out:run(args.official_zip,args.out)
    else:p.error("--official-zip and --out, or --self-test required")
