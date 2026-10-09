#!/usr/bin/env python3
"""Price-capped exact-model, page-grounded WattBot diagnostic. DEV questions ONLY.

Maximum 6 paid OpenRouter calls with a hard $0.01 budget, no test labels, no Kaggle submission.
Predictions are generated from question plus pinned retrieved paper excerpts;
gold labels are accessible only to official Score.py and development selection.
No raw question, model output, paper text or credential written to CI logs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import io
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlparse
import zipfile

import pandas as pd
import requests

from holdout_probe import is_holdout, ARXIV_HOSTS
from pdf_probe import download_one
from train_probe import load_csv, parse_refs
from score_ablation import load_score, blank_submission
from numeric_answer_probe import build_candidate
from wattbot import ranked, chunks_from_pages, verify_candidate, norm

MAX_REQUESTS = 6
MAX_EXPERIMENT_COST_USD = 0.01
MAX_PROMPT_TOKENS_CONSERVATIVE = 6000
spent_usd = 0.0
MAX_PDFS = 8
MODEL = "qwen/qwen3.5-flash"
MAX_MODEL_TOKENS = 1600
MAX_EXCERPT_CHARS = 1400
MAX_CONTEXTS = 4
API_URL = "https://openrouter.ai/api/v1/chat/completions"


def parse_json_response(text):
    t = str(text or "").strip()
    match = re.search(r"\{[\s\S]*\}",t)
    if not match:
        return None
    try:
        obj = json.loads(match.group())
    except (ValueError,TypeError):
        return None
    return obj if isinstance(obj,dict) else None


def numeric_value(v):
    if not isinstance(v,(int,float,str)) or isinstance(v,bool):
        return None
    raw=str(v).strip().replace(",","")
    if len(raw)>45 or not re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
        return None
    try:
        if not Decimal(raw).is_finite():
            return None
    except InvalidOperation:
        return None
    return raw


def generate(question, contexts, key):
    prompt = {
       "question":question,
       "evidence":[{"index":i,"ref_id":c["ref_id"],"page":c["page"],
                    "text":c["text"][:MAX_EXCERPT_CHARS]}
                   for i,c in enumerate(contexts)]
    }
    payload = {
      "model":MODEL,
      "messages":[
        {"role":"system","content":(
          "You answer research questions using ONLY provided source excerpts. "
          "Return a single JSON object with keys answer, answer_value, answer_unit, "
          "source_index. answer_value must be a numeric literal printed verbatim "
          "in one provided excerpt, or 'is_blank' when unavailable. "
          "source_index must be the integer index containing that number. "
          "No guesses, no lists, no equations, no extraneous text.")},
        {"role":"user","content":json.dumps(prompt,ensure_ascii=False)}
      ],
      "max_tokens":MAX_MODEL_TOKENS,
      "temperature":0,
    }
    try:
        r=requests.post(API_URL,
           headers={"Authorization":"Bearer "+key,
                    "Content-Type":"application/json",
                    "HTTP-Referer":"https://github.com/metalogiclabs/mathgraph",
                    "X-Title":"WattBot MathGraph capped noncommercial train probe"},
           json=payload,timeout=65)
        if r.status_code!=200:
            return None,{"http_status":r.status_code}
        obj=r.json()
        usage=obj.get("usage") or {}
        cost=usage.get("cost",0)
        reply=((obj.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        global spent_usd
        spent_usd += float(cost or 0)
        if spent_usd > MAX_EXPERIMENT_COST_USD:
            raise ValueError("Hard cost cap reached: stop further requests")
        return parse_json_response(reply),{"http_status":200,
            "reply_present":bool(reply),"cost":cost,
            "completion_tokens":usage.get("completion_tokens",0),
            "returned_model":obj.get("model","unknown")}
    except requests.RequestException as e:
        return None,{"request_exception":type(e).__name__}


def model_candidate(question, hits, docs, key):
    blank={"id":question["id"],"answer_value":"is_blank","ref_ids":[],
           "evidence":[],"explanation":"Free-LLM probe abstained; unverified source value."}
    if not hits:
        return verify_candidate(blank,question,docs,hits),{"reason":"no_context"}
    answer,stats=generate(question["question"],hits,key)
    if not isinstance(answer,dict):
        return verify_candidate(blank,question,docs,hits),stats
    value=numeric_value(answer.get("answer_value"))
    idx=answer.get("source_index")
    if value is None or type(idx) is not int or idx<0 or idx>=len(hits):
        return verify_candidate(blank,question,docs,hits),dict(stats,reason="bad_numeric_or_source_index")
    source=hits[idx]
    if source.get("page",0)<1:
        return verify_candidate(blank,question,docs,hits),dict(stats,reason="metadata_not_page")
    excerpt=source["text"][:MAX_EXCERPT_CHARS]
    # Literal grounding is independent of the LLM's assertion.
    observed={m.group().replace(",","") for m in re.finditer(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w.])",excerpt)}
    if value not in observed:
        return verify_candidate(blank,question,docs,hits),dict(stats,reason="number_not_in_quote")
    candidate={"id":question["id"],"answer":str(answer.get("answer") or value)[:150],
               "answer_value":value,
               "ref_ids":[source["ref_id"]],
               "evidence":[{"ref_id":source["ref_id"],"page":source["page"],
                            "quote":excerpt}],
               "derivation":{"expression":"v","inputs":{
                   "v":{"value":value,"evidence_index":0}}},
               "explanation":"MODEL CANDIDATE: quoted numeric literal, page anchored; entailment unknown."}
    try:
        checked=verify_candidate(candidate,question,docs,hits)
        checked["answer_unit"]=str(answer.get("answer_unit") or "is_blank")[:40]
        return checked,dict(stats,reason="checked_literal")
    except (ValueError,KeyError,TypeError,ZeroDivisionError):
        return verify_candidate(blank,question,docs,hits),dict(stats,reason="checker_rejected")


def run(official_zip):
    key=os.environ.get("OPENROUTER_API_KEY","")
    if not key:
        raise ValueError("Missing model credential")
    # Preflight the currently available exact model and refuse costly routes.
    catalog = requests.get("https://openrouter.ai/api/v1/models",
        headers={"Authorization":"Bearer "+key},timeout=25)
    catalog.raise_for_status()
    offered = [m for m in catalog.json().get("data",[]) if m.get("id")==MODEL]
    if len(offered)!=1:
        raise ValueError("Pinned low-cost model unavailable; no inference attempted")
    pricing=offered[0].get("pricing") or {}
    prompt_price=float(pricing["prompt"])
    completion_price=float(pricing["completion"])
    if prompt_price<0 or completion_price<0:
        raise ValueError("Unusable model pricing")
    maximum = MAX_REQUESTS*(MAX_PROMPT_TOKENS_CONSERVATIVE*prompt_price+
                           MAX_MODEL_TOKENS*completion_price)
    if maximum > MAX_EXPERIMENT_COST_USD:
        raise ValueError("Refuse inference: worst-case listed price exceeds $0.01")
    print("WATTBOT_PRICECAP_PREFLIGHT="+json.dumps({
       "model":MODEL,"listed_prompt_per_million_usd":round(prompt_price*1e6,5),
       "listed_completion_per_million_usd":round(completion_price*1e6,5),
       "conservative_max_usd":round(maximum,6),
       "hard_stop_usd":MAX_EXPERIMENT_COST_USD,
       "max_calls":MAX_REQUESTS,
       "note":"Single six-question DEVELOPMENT diagnostic, not production or recurring spend"
    },sort_keys=True),flush=True)
    with zipfile.ZipFile(official_zip) as z:
        metadata=load_csv(z,"metadata.csv")
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),keep_default_na=False,dtype={"id":str})
        docs={d["id"]:d for d in metadata}
        dev=train[~train["id"].map(is_holdout)].copy()
        refs=Counter(ref for _,r in dev.iterrows() for ref in parse_refs(str(r["ref_id"])))
        selected=sorted([ref for ref in refs if ref in docs and
               (urlparse(docs[ref]["url"]).hostname or "").lower() in ARXIV_HOSTS],
               key=lambda r:(-refs[r],r))[:MAX_PDFS]
        # Explicit train-development convenience sample: not an independent holdout.
        testable=dev[dev["ref_id"].map(
             lambda x: bool(parse_refs(x)) and set(parse_refs(x)) <= set(selected))]
        sample=testable.head(MAX_REQUESTS).copy().reset_index(drop=True)
        if len(sample)!=MAX_REQUESTS:
            raise ValueError("Insufficient cited development questions to fill tiny pilot")
        with tempfile.TemporaryDirectory(prefix="wattbot_free_train_llm_") as folder:
            chunks=[]
            for i,ref in enumerate(selected):
                if i:time.sleep(3.1)
                file=Path(folder)/f"{i}.pdf"
                download_one(docs[ref]["url"],file)
                chunks.extend(chunks_from_pages(ref,docs[ref]["url"],file))
            meta_chunks=[{"ref_id":d["id"],"url":d["url"],"page":0,
                          "text":" ".join(str(d.get(k,"") or "") for k in
                          ("title","citation","year","venue"))} for d in metadata]
            index=meta_chunks+chunks
            results=[]
            numeric_rows=[]
            outcomes=Counter()
            models=Counter()
            costs=[]
            for _,gold in sample.iterrows():
                question={"id":str(gold["id"]),"question":str(gold["question"])}
                hits=ranked(question["question"],index,min(len(index),100))
                full_pdfs=[h for h in hits if h.get("page",0)>0][:MAX_CONTEXTS]
                pred,diag=model_candidate(question,full_pdfs,docs,key)
                results.append(pred)
                numeric_rows.append(build_candidate(question,hits,docs))
                outcomes[diag.get("reason","no_json")]+=1
                if diag.get("returned_model"):models[diag["returned_model"]]+=1
                if diag.get("cost") is not None:costs.append(float(diag["cost"]))
                if diag.get("http_status") and diag["http_status"]!=200:
                    print("FREE_API_RESPONSE_CATEGORY="+str(diag["http_status"]),flush=True)
                time.sleep(1.5)
            baseline=blank_submission(sample).reset_index(drop=True)
            predictions=pd.DataFrame(results,columns=list(baseline.columns))
            numeric=pd.DataFrame(numeric_rows,columns=list(baseline.columns))
            scorer=load_score(z,folder)
            def score(df):
                return round(float(scorer(sample.copy(deep=True),df.copy(deep=True),
                         row_id_column_name="id",verbose=False)),8)
            print("WATTBOT_PRICECAPPED_LLM_TRAIN_PILOT="+json.dumps({
              "development_sample_rows":len(sample),
              "pdf_budget":MAX_PDFS,
              "model_requested":MODEL,
              "models_returned":dict(models),
              "number_of_api_requests":len(costs),
              "api_reported_cost_total":round(sum(costs),8),
              "hard_cost_cap_usd":MAX_EXPERIMENT_COST_USD,
              "admitted_nonblank_predictions":int((predictions["answer_value"]!="is_blank").sum()),
              "outcomes":dict(outcomes),
              "official_sample_blank":score(baseline),
              "official_sample_frozen_numeric":score(numeric),
              "official_sample_free_llm":score(predictions),
              "boundary":"Train-development selected small diagnostic ONLY. No heldout/test labels in LLM prompts, no leaderboard claim",
            },sort_keys=True),flush=True)


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip",required=True)
    run(p.parse_args().official_zip)
