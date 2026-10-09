#!/usr/bin/env python3
"""WattBot V2 protected-test candidate: quote-checked Flash-Lite with numeric fallback.

No test answer/label read. No model response or scientific source text appears
in logs. The exact classifier, retrieval, evidence verifier and fallback were
measured on labelled TRAIN holdout before this test submission.
"""
from __future__ import annotations

import argparse
from collections import Counter
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

from holdout_probe import is_holdout
from numeric_answer_probe import build_candidate
from pdf_probe import download_one
from retrieved_reader_probe import (
    SYSTEM, MODEL, MAX_EXCERPT, MAX_OUTPUT_TOKENS,
    selected_sources, passages_for, conservative_charge, call_reader,
    try_checked, MAX_BUDGET_USD
)
from free_reader_probe import verify_price_ceiling
from train_probe import load_csv
from wattbot import chunks_from_pages, COLUMNS

# Freeze the 2026 authority and scientific source family.
PINNED = {
    "Score.py":"e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
    "metadata.csv":"b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1",
    "train_QA.csv":"9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
    "test_Q.csv":"26038b21cb09588a39b0e95e5516e3827dadd499c85c3792d0ea46c10ae7066a",
}
PINNED_24_PDF_MANIFEST = "dd3eefee514b58ea807c6670241ad4bba9111058216f844d8996f20076568e23"
COST_CEILING_USD=0.45
MAX_UNSUCCESSFUL_MODEL_REQUESTS=35
MIN_GROUNDED_MODEL_PREDICTIONS=64
PAUSE_SECONDS=1.5

def create(official_zip:str, output_path:str):
    key=os.environ.get("OPENROUTER_API_KEY","")
    if not key:raise RuntimeError("No configured reader credential; no submission generated")
    pricing=verify_price_ceiling()
    with zipfile.ZipFile(official_zip) as z:
        for filename,digest in PINNED.items():
            actual=hashlib.sha256(z.read(filename)).hexdigest()
            if actual!=digest:
                raise RuntimeError("Pinned official file changed: "+filename+"; requalify")
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str})
        metadata=load_csv(z,"metadata.csv")
        test=[{"id":r["id"],"question":r["question"]} for r in load_csv(z,"test_Q.csv")]
    if len(test)!=317 or len(set(x["id"] for x in test))!=317:
        raise RuntimeError("Test question IDs changed; do not submit")
    dev=train[~train["id"].map(is_holdout)].copy()
    docs={d["id"]:d for d in metadata}
    selected=selected_sources(dev,docs)
    if len(selected)!=24:
        raise RuntimeError("Expected 24 pinned DEV-selected sources")
    with tempfile.TemporaryDirectory(prefix="wattbot_verified_v2_") as td:
        folder=Path(td)
        pdf_chunks=[]
        hashes=[]
        for i,doc_id in enumerate(selected):
            if i:time.sleep(3.1)
            file=folder/(str(i)+".pdf")
            sha,_=download_one(docs[doc_id]["url"],file)
            chunks=chunks_from_pages(doc_id,docs[doc_id]["url"],file)
            if not chunks:
                raise RuntimeError("Missing pinned PDF text; no partial corpus")
            hashes.append(sha)
            pdf_chunks.extend(chunks)
        source_digest=hashlib.sha256("\n".join(hashes).encode()).hexdigest()
        if source_digest!=PINNED_24_PDF_MANIFEST:
            raise RuntimeError("Scientific source PDF manifest changed; requalify")
        meta_chunks=[{"ref_id":d["id"],"url":d["url"],"page":0,
                      "text":" ".join(str(d.get(k,"") or "")
                              for k in ("title","citation","year","venue"))}
                     for d in metadata]
        corpus=meta_chunks+pdf_chunks
        accepted=0
        committed=0.0
        observed=0.0
        model_failures=0
        outcomes=Counter()
        rows=[]
        for ix,q in enumerate(test):
            passages,hits=passages_for(q["question"],corpus)
            fallback=build_candidate(q,hits,docs)
            chosen=fallback
            if not passages:
                outcomes["NO_PASSAGES"]+=1
            else:
                prompt=json.dumps({"question":q["question"],
                    "passages":[{"source_index":j,"ref_id":v["ref_id"],
                        "page":v["page"],"text":v["text"][:MAX_EXCERPT]}
                        for j,v in enumerate(passages)]},
                    ensure_ascii=False,separators=(",",":"))
                charge=conservative_charge(SYSTEM+prompt,pricing,MAX_OUTPUT_TOKENS)
                if committed+charge>COST_CEILING_USD:
                    raise RuntimeError("Pre-call model spend ceiling reached; no partial submission")
                generated,status,reserved,billed=call_reader(key,q["question"],passages,pricing)
                committed+=reserved
                observed+=billed
                if status!="OK":
                    model_failures+=1
                    outcomes[status]+=1
                    if status.startswith(("HTTP_429","HTTP_402","HTTP_401")):
                        raise RuntimeError("Model API credentials/rate unavailable; no partial submission")
                else:
                    proved,reason=try_checked(generated,q,passages,docs)
                    outcomes[reason]+=1
                    if proved is not None:
                        chosen=proved
                        accepted+=1
                if model_failures>MAX_UNSUCCESSFUL_MODEL_REQUESTS:
                    raise RuntimeError("Too many model failures, stop before Kaggle submission")
            if chosen["id"]!=q["id"]:
                raise RuntimeError("Submission row/provenance mismatch")
            rows.append(chosen)
            if ix<len(test)-1:time.sleep(PAUSE_SECONDS)
        if accepted<MIN_GROUNDED_MODEL_PREDICTIONS:
            raise RuntimeError("Insufficient evidence-checked responses; reject V2 before Kaggle submission")
        output=Path(output_path)
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open("w",encoding="utf-8",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(COLUMNS),extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
        with output.open(encoding="utf-8",newline="") as f:
            reader=csv.DictReader(f)
            back=list(reader)
            if reader.fieldnames!=list(COLUMNS) or len(back)!=317:
                raise RuntimeError("Wrong official submission shape")
            if any(not r["answer_value"] or not r["explanation"] for r in back):
                raise RuntimeError("Empty required answer or explanation")
        print("WATTBOT_VERIFIED_V2_READY="+json.dumps({
            "rows":len(rows),"candidate_source_pdfs":len(selected),
            "source_manifest_sha256":source_digest,
            "result_file_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
            "accepted_exact_quote_predictions":accepted,
            "fallback_numeric_or_abstained":len(rows)-accepted,
            "model_request_failures":model_failures,
            "model_qualification_states":dict(outcomes),
            "model":MODEL,"max_reserved_usd":round(committed,7),
            "reported_cost_usd":round(observed,7),
            "maximum_authorized_usd":COST_CEILING_USD,
            "boundary":"317 protected TEST questions only, no test labels, all science claims CANDIDATE until external Kaggle score.",
        },sort_keys=True),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    create(args.official_zip,args.out)
