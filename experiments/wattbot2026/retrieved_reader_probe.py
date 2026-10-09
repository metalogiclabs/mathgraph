#!/usr/bin/env python3
"""WattBot source-chosen Flash-Lite QA with independent citation validation.

TRAIN-ONLY reused hash holdout. Source selection from DEV citations; answer
generation receives only question text and 24 pinned public PDFs. Gold holdout
rows enter only the immutable official Score.py AFTER predictions are made.
No test calls, no Kaggle submission. Provider responses are CANDIDATES.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.parse import urlparse
import zipfile

import pandas as pd
import requests

from free_reader_probe import (MODEL, ENDPOINT, SYSTEM_PROMPT, parse_answer,
                               verify_price_ceiling)
from holdout_probe import is_holdout, ARXIV_HOSTS
from numeric_answer_probe import build_candidate
from pdf_probe import download_one
from score_ablation import blank_submission, load_score
from train_probe import parse_refs
from wattbot import chunks_from_pages, ranked, norm, verify_candidate

MAX_BUDGET_USD = 0.12
MAX_REQUESTS = 63
SOURCE_BUDGET = 24
K = 6
MAX_EXCERPT = 1100
MAX_OUTPUT_TOKENS = 650
REQUEST_TIMEOUT_SECONDS = 75
REQUEST_PAUSE_SECONDS = 1.5

SYSTEM = (SYSTEM_PROMPT +
    " Answer from the question and evidence ONLY. If evidence does not support "
    "an answer return answer_value='is_blank'. Include source_index (zero-based "
    "from supplied evidence list) and supporting_quote (literal passage text). "
    "For multi-paper questions, use source_indices and supporting_quotes lists. "
    "Return answer_value as a STRING with exact number, words or Python-style "
    "string list; provide answer_unit or 'is_blank'. Avoid invented precision.")

def selected_sources(dev, docs):
    ref_counts = Counter(ref for raw in dev["ref_id"]
                         for ref in parse_refs(str(raw)))
    options = sorted(
        (ref for ref in ref_counts if ref in docs and
         (urlparse(str(docs[ref]["url"])).hostname or "").lower() in ARXIV_HOSTS),
        key=lambda ref:(-ref_counts[ref],ref))
    return options[:SOURCE_BUDGET]

def passages_for(question, all_chunks):
    # Lexical rank is frozen BEFORE any gold holdout comparison.
    candidates = ranked(question, all_chunks, min(100, len(all_chunks)))
    return [c for c in candidates if c["page"] > 0][:K], candidates

def conservative_charge(prompt: str, rate, output_tokens):
    # One token per UTF-8 byte is conservative for most tokenizers.
    return len(prompt.encode("utf-8")) * rate["prompt"] + output_tokens * rate["completion"]

def call_reader(key, question, passages, pricing):
    payload_passages = [
        {"source_index":i, "ref_id":item["ref_id"], "page":item["page"],
         "text":item["text"][:MAX_EXCERPT]}
        for i,item in enumerate(passages)
    ]
    prompt = json.dumps({"question":question,"passages":payload_passages},
                        ensure_ascii=False,separators=(",",":"))
    max_cost = conservative_charge(SYSTEM+prompt, pricing, MAX_OUTPUT_TOKENS)
    data = {
        "model":MODEL,"messages":[
            {"role":"system","content":SYSTEM},
            {"role":"user","content":prompt}],
        "response_format":{"type":"json_object"},
        "max_tokens":MAX_OUTPUT_TOKENS,
        "temperature":0.0,
        "stream":False,
    }
    try:
        response = requests.post(ENDPOINT, headers={
            "Authorization":"Bearer "+key,
            "Content-Type":"application/json",
            "HTTP-Referer":"https://metalogiclabs.xyz",
            "X-Title":"MathGraph WattBot score-bounded eval"},
            json=data, timeout=(10,REQUEST_TIMEOUT_SECONDS))
        if response.status_code!=200:
            return None, "HTTP_"+str(response.status_code), max_cost, 0.0
        body=response.json()
        if body.get("error"):
            return None, "PROVIDER_ERROR", max_cost, 0.0
        choice=(body.get("choices") or [{}])[0]
        content=(choice.get("message") or {}).get("content") or ""
        if isinstance(content,list):
            content="\n".join(p.get("text","") for p in content if isinstance(p,dict))
        result=parse_answer(content)
        if result is not None:
            result["source_index"] = None
            # Recover provenance fields from raw JSON object, if present.
            try:
                raw=json.loads(str(content).strip().strip("`"))
                if isinstance(raw,dict):
                    result["source_index"]=raw.get("source_index")
                    result["source_indices"]=raw.get("source_indices")
                    result["supporting_quotes"]=raw.get("supporting_quotes")
            except (ValueError,TypeError):
                pass
        usage=body.get("usage") or {}
        observed=usage.get("cost")
        observed=float(observed) if isinstance(observed,(float,int)) else 0.0
        if observed > max_cost+0.01:
            raise RuntimeError("Unexpected provider billing above pre-reserved ceiling")
        return result, ("OK" if result else "INVALID_JSON"), max_cost, observed
    except requests.RequestException as exc:
        return None, type(exc).__name__, max_cost, 0.0

def try_checked(generated, question, passages, docs):
    if not isinstance(generated, dict) or generated["answer_value"].lower() in (
        "is_blank","unknown","n/a","nan"):
        return None, "MODEL_ABSTAINED"
    picks=generated.get("source_indices")
    quotes=generated.get("supporting_quotes")
    if not isinstance(picks,list) or not isinstance(quotes,list):
        picks=[generated.get("source_index")]
        quotes=[generated.get("supporting_quote","")]
    if not picks or len(picks)!=len(quotes) or len(picks)>3:
        return None, "BAD_PROVENANCE_SHAPE"
    ev=[]
    refs=[]
    for idx, quote in zip(picks,quotes):
        if type(idx) is not int or not 0<=idx<len(passages):
            return None, "MISSING_SOURCE_INDEX"
        source=passages[idx]
        quote=str(quote or "").strip()
        if len(quote)<12 or norm(quote) not in norm(source["text"][:MAX_EXCERPT]):
            return None, "QUOTATION_NOT_ANCHORED"
        if source["ref_id"] not in refs:
            refs.append(source["ref_id"])
        ev.append({"ref_id":source["ref_id"],"page":source["page"],"quote":quote})
    candidate={
        "id":question["id"],"answer":generated["answer"],
        "answer_value":generated["answer_value"],"ref_ids":refs,
        "evidence":ev,
        "explanation":"Unverified semantic answer from LLM, with independently checked exact PDF page quotations"}
    try:
        result=verify_candidate(candidate,question,docs,passages)
        result["answer_unit"]=generated["answer_unit"] or "is_blank"
        return result,"PAGE_QUOTE_VERIFIED"
    except (ValueError,KeyError,TypeError,ZeroDivisionError):
        return None,"PAGE_CHECK_REJECTED"

def run(path):
    secret=os.environ.get("OPENROUTER_API_KEY","")
    if not secret:
        raise RuntimeError("Missing OpenRouter API key, refusing to call model")
    rate=verify_price_ceiling()
    with zipfile.ZipFile(path) as z:
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str})
        metadata=pd.read_csv(io.BytesIO(z.read("metadata.csv")),
                             keep_default_na=False,dtype={"id":str})
        docs={str(r["id"]):r for r in metadata.to_dict("records")}
        dev=train[~train["id"].map(is_holdout)].copy()
        hold=train[train["id"].map(is_holdout)].copy().reset_index(drop=True)
        sources=selected_sources(dev,docs)
        if len(sources)!=SOURCE_BUDGET:
            raise RuntimeError("Insufficient development-selected arXiv papers")
        if len(hold)>MAX_REQUESTS:
            raise ValueError("Holdout exceeds declared LLM request budget")
        with tempfile.TemporaryDirectory(prefix="wattbot_page_reader_") as td:
            folder=Path(td)
            pdf_chunks=[]
            hashes=[]
            for i,ref in enumerate(sources):
                if i:time.sleep(3.1)
                local=folder/(str(i)+".pdf")
                sha,_=download_one(str(docs[ref]["url"]),local)
                hits=chunks_from_pages(ref,str(docs[ref]["url"]),local)
                if not hits:
                    raise RuntimeError("Missing required PDF source text")
                pdf_chunks.extend(hits)
                hashes.append(sha)
            metadata_chunks=[{"ref_id":d["id"],"url":d["url"],"page":0,
                              "text":" ".join(str(d.get(k,"") or "")
                                    for k in ("title","citation","year","venue"))}
                             for d in docs.values()]
            all_chunks=metadata_chunks+pdf_chunks
            blank=blank_submission(hold).reset_index(drop=True)
            numeric=[]
            model=[]
            combined=[]
            outcomes=Counter()
            committed=0.
            observed=0.
            for i,item in blank.iterrows():
                question={"id":str(item["id"]),"question":str(item["question"])}
                passages,all_hits=passages_for(question["question"],all_chunks)
                numeric_row=build_candidate(question,all_hits,docs)
                numeric.append(numeric_row)
                selected=dict(item)
                if not passages:
                    outcomes["NO_PASSAGES"]+=1
                else:
                    # Explicit preflight worst-case charge budget.
                    prompt=json.dumps({"question":question["question"],
                        "passages":[{"source_index":j,"ref_id":x["ref_id"],"page":x["page"],
                                     "text":x["text"][:MAX_EXCERPT]}
                                    for j,x in enumerate(passages)]},
                        ensure_ascii=False,separators=(",",":"))
                    estimate=conservative_charge(SYSTEM+prompt,rate,MAX_OUTPUT_TOKENS)
                    if committed+estimate>MAX_BUDGET_USD:
                        outcomes["COST_CEILING"]+=1
                    else:
                        response,status,reserved,spent=call_reader(
                            secret,question["question"],passages,rate)
                        committed+=reserved
                        observed+=spent
                        if status.startswith("HTTP_429"):
                            outcomes["RATE_LIMIT_ABORT"]+=1
                            # Stop making calls, but still score completed partial experiment.
                            model.append(selected)
                            combined.append(numeric_row)
                            for j in range(i+1,len(blank)):
                                q={"id":str(blank.iloc[j]["id"]),
                                   "question":str(blank.iloc[j]["question"])}
                                _,future_hits=passages_for(q["question"],all_chunks)
                                num=build_candidate(q,future_hits,docs)
                                numeric.append(num)
                                model.append(dict(blank.iloc[j]))
                                combined.append(num)
                            break
                        if status!="OK":
                            outcomes[status]+=1
                        else:
                            checked,check=try_checked(response,question,passages,docs)
                            outcomes[check]+=1
                            if checked is not None:
                                selected=checked
                model.append(selected)
                combined.append(selected if selected["answer_value"]!="is_blank" else numeric_row)
                time.sleep(REQUEST_PAUSE_SECONDS)
            n=len(blank)
            if not all(len(x)==n for x in (model,numeric,combined)):
                raise RuntimeError("Candidate rows misaligned after budget/rate limit")
            def frame(rows):
                return pd.DataFrame(rows,columns=list(blank.columns))
            scoreboard=load_score(z,td)
            def official(dataframe):
                return round(float(scoreboard(hold.copy(deep=True),
                    dataframe.copy(deep=True),row_id_column_name="id",
                    verbose=False)),8)
            result={
                "train_dev_rows":len(dev),"holdout_rows":len(hold),
                "pdfs":len(sources),"pdf_chunks":len(pdf_chunks),
                "source_manifest_sha256":hashlib.sha256("\n".join(hashes).encode()).hexdigest(),
                "model":MODEL,"model_price":rate,
                "cost_ceiling_usd":MAX_BUDGET_USD,
                "max_reserved_usd":round(committed,7),
                "observed_api_usd":round(observed,7),
                "outcomes":dict(outcomes),
                "scores":{
                    "blank":official(blank),
                    "numeric24":official(frame(numeric)),
                    "reader_page_checked":official(frame(model)),
                    "reader_then_numeric_fallback":official(frame(combined)),
                },
                "scope":"Previously analyzed TRAIN-only holdout; no test labels or Kaggle submission. Page-verification is NOT entailment."
            }
            print("WATTBOT_RETRIEVED_FLASHLITE_HOLDOUT="+json.dumps(result,sort_keys=True),flush=True)

def self_test():
    sample=[{"ref_id":"p1","page":2,"url":"https://arxiv.org/abs/2401.00001",
             "text":"The paper used 1287 MWh in 2025."}]
    docs={"p1":{"url":sample[0]["url"]}}
    question={"id":"a","question":"What energy did the paper use?"}
    candidate,reason=try_checked({
        "answer":"1287 MWh","answer_value":"1287","answer_unit":"MWh",
        "source_index":0,"supporting_quote":"paper used 1287 MWh",
    },question,sample,docs)
    assert candidate is not None and reason=="PAGE_QUOTE_VERIFIED",reason
    assert candidate["answer_value"]=="1287"
    wrong,reason=try_checked({
        "answer":"999","answer_value":"999","answer_unit":"MWh",
        "source_index":0,"supporting_quote":"the authors proved nonexistent words",
    },question,sample,docs)
    assert wrong is None and reason=="QUOTATION_NOT_ANCHORED"
    print("RETRIEVED_READER_SELF_TEST=PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip")
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Provide --official-zip or --self-test")
