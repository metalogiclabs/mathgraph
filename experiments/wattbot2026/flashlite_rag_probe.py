#!/usr/bin/env python3
"""Source-verified Flash-Lite RAG experiment on WattBot's fixed TRAIN holdout.

No gold holdout answers/references are given to the model or used to select its
contexts. PDF selection uses only 182 development questions' citation labels,
as in previously qualified 24-paper numeric baseline. This previously inspected
63-row holdout is diagnostic, not a pristine independent competition test.

Eight-question source-oracle DEV reader used the SAME model, system prompt,
temperature and max output tokens. This experiment removes the source oracle.
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

from free_reader_probe import (
    MODEL, SYSTEM_PROMPT, request_free_reader, verify_price_ceiling,
    MAX_CHARS_PER_CHUNK,
)
from holdout_probe import is_holdout, ARXIV_HOSTS
from pdf_probe import download_one
from report_loader import download_report
from numeric_answer_probe import build_candidate
from score_ablation import load_score, blank_submission
from train_probe import parse_refs
from wattbot import chunks_from_pages, ranked, norm

SOURCE_BUDGET = 114
CONTEXT_CHUNKS = 6
MAX_CALLS = 63
MAX_ESTIMATED_USD = 0.08
MAX_OUTPUT_TOKENS = 450


def source_list(dev: pd.DataFrame, docs: dict[str,dict]) -> list[str]:
    counts=Counter(r for refs in dev["ref_id"].map(parse_refs) for r in refs)
    selected=[
        ref for ref in counts
        if ref in docs and
        (urlparse(str(docs[ref]["url"])).hostname or "").lower() in ARXIV_HOSTS
    ]
    selected.sort(key=lambda d:(-counts[d],d))
    return selected[:SOURCE_BUDGET]


def passages_for_question(q: str, pdf_chunks: list[dict]):
    # Same lexical scorer as V1, with explicit source-diversity cap 2 pages.
    ranked_pages=ranked(q,pdf_chunks,min(200,len(pdf_chunks)))
    selected=[]
    counts=Counter()
    for page in ranked_pages:
        if counts[page["ref_id"]]>=2:
            continue
        selected.append(page)
        counts[page["ref_id"]]+=1
        if len(selected)>=CONTEXT_CHUNKS:
            break
    prompt="\n\n".join(
        f"[SOURCE:{p['ref_id']} PAGE:{p['page']}] "+p["text"][:MAX_CHARS_PER_CHUNK]
        for p in selected
    )
    return selected,prompt


def select_anchored_page(quote: str, pages: list[dict]):
    if not quote:
        return None
    match=norm(quote)
    for page in pages:
        if match in norm(page["text"]):
            return page
    return None


def with_model_answer(original:dict, response:dict, page=None):
    result=dict(original)
    value=str(response["answer_value"]).strip()
    if not value or value.lower() in ("is_blank","na","unknown","none"):
        return result
    result["answer"]=response["answer"]
    result["answer_value"]=value
    result["answer_unit"]=response["answer_unit"] or "is_blank"
    result["explanation"]="CANDIDATE: pinned source-retrieved model answer; scientific entailment unverified"
    if page is not None:
        result["ref_id"]=repr([page["ref_id"]])
        result["ref_url"]=repr([page["url"]])
        result["supporting_materials"]=repr([response["supporting_quote"]])
    return result


def run(official_zip:str):
    key=os.environ.get("OPENROUTER_API_KEY","")
    if not key:
        raise RuntimeError("No configured OpenRouter key; no model requests made")
    price=verify_price_ceiling()
    with zipfile.ZipFile(official_zip) as z:
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str})
        meta=pd.read_csv(io.BytesIO(z.read("metadata.csv")),
                         keep_default_na=False,dtype={"id":str})
        dev=train[~train["id"].map(is_holdout)].copy()
        hold=train[train["id"].map(is_holdout)].copy().reset_index(drop=True)
        if len(hold)!=63:
            raise ValueError("Frozen split shifted; stop before model calls")
        docs={str(d["id"]):d for d in meta.to_dict("records")}
        selected=source_list(dev,docs)
        if len(selected)!=SOURCE_BUDGET:
            raise ValueError("Official corpus did not expose exactly 114 pinned arXiv sources")
        hashes=[]
        pdf_chunks=[]
        prefix_24_chunks=[]
        with tempfile.TemporaryDirectory(prefix="wattbot_lite_rag_") as td:
            folder=Path(td)
            for i,ref in enumerate(selected):
                if i:time.sleep(3.1)
                path=folder/f"ref_{i}.pdf"
                sha,_=download_one(str(docs[ref]["url"]),path)
                rows=chunks_from_pages(ref,str(docs[ref]["url"]),path)
                if not rows:
                    raise ValueError("No text in pinned public paper")
                pdf_chunks.extend(rows)
                if i<24:
                    prefix_24_chunks.extend(rows)
                hashes.append(sha)
            # Archive the arXiv-only control before adding the separate
            # officially pinned report sources; this prevents retrospective
            # substitution of source evidence for any control arm.
            arxiv_chunks=list(prefix_24_chunks)
            report_rows=[d for d in meta.to_dict("records")
                         if str(d.get("type","")).strip().lower()=="report"]
            if len(report_rows)!=8:
                raise ValueError("Pinned report authority changed; requalify source registry")
            report_types=Counter()
            report_errors=Counter()
            report_hashes=[]
            for i,d in enumerate(report_rows):
                if i:time.sleep(2)
                try:
                    report=download_report(str(d["id"]),str(d["url"]))
                    pdf_chunks.extend(report["chunks"])
                    report_types[report["kind"]]+=1
                    report_hashes.append(report["sha256"])
                except (requests.RequestException,ValueError,RuntimeError) as err:
                    report_errors[type(err).__name__]+=1
                    report_hashes.append("UNKNOWN")
            meta_chunks=[{"ref_id":d["id"],"url":d["url"],"page":0,
                          "text":" ".join(str(d.get(k,"") or "") for k in
                                         ("title","citation","year","venue"))}
                         for d in meta.to_dict("records")]
            numeric_index=meta_chunks+pdf_chunks
            arxiv_index=meta_chunks+arxiv_chunks
            initial=blank_submission(hold).reset_index(drop=True)
            model_values=[]
            model_anchored=[]
            model_strict=[]
            model_fallback=[]
            numeric_rows=[]
            numeric_24_control=[]
            status_counts=Counter()
            anchored=0
            model_answers=0
            budget_committed=0.
            observed_costs=[]
            candidate_pages=0
            for i,item in initial.iterrows():
                original=dict(item)
                q=str(item["question"])
                corpus_hits=ranked(q,numeric_index,min(100,len(numeric_index)))
                numeric=build_candidate(
                    {"id":str(item["id"]),"question":q},corpus_hits,docs)
                numeric_rows.append(numeric)
                old_hits=ranked(q,arxiv_index,min(100,len(arxiv_index)))
                numeric_24_control.append(build_candidate(
                    {"id":str(item["id"]),"question":q},old_hits,docs))
                pages,prompt=passages_for_question(q,pdf_chunks)
                candidate_pages+=len(pages)
                answer_value=dict(original)
                cited=dict(original)
                strict=dict(original)
                if prompt and i<MAX_CALLS:
                    max_estimate=(
                        len(prompt)+len(q)+len(SYSTEM_PROMPT)+1000
                    )*price["prompt"] + MAX_OUTPUT_TOKENS*price["completion"]
                    if budget_committed+max_estimate <= MAX_ESTIMATED_USD:
                        budget_committed+=max_estimate
                        try:
                            response,status,usage=request_free_reader(key,q,prompt)
                        except requests.RequestException as exc:
                            response,status,usage=None,type(exc).__name__,None
                        status_counts[status]+=1
                        if usage and isinstance(usage.get("cost_observed"),(int,float)):
                            observed_costs.append(usage["cost_observed"])
                        if response and status=="OK":
                            answer_value=with_model_answer(original,response)
                            if answer_value["answer_value"]!="is_blank":
                                model_answers+=1
                                matching=select_anchored_page(response["supporting_quote"],pages)
                                if matching:
                                    anchored+=1
                                    cited=with_model_answer(original,response,matching)
                                    strict=dict(cited)
                                else:
                                    cited=with_model_answer(original,response)
                    else:
                        status_counts["BUDGET_ABORT"]+=1
                model_values.append(answer_value)
                model_anchored.append(cited)
                model_strict.append(strict)
                # Baseline numeric fallback only on abstention or missing
                # answer; this is a predeclared policy, not gold-conditioned.
                if answer_value["answer_value"]=="is_blank":
                    model_fallback.append(numeric)
                else:
                    model_fallback.append(cited)
            scorer=load_score(z,str(folder))
            def dataframe(rows):
                return pd.DataFrame(rows,columns=list(initial.columns))
            def official(rows):
                frame=rows if isinstance(rows,pd.DataFrame) else dataframe(rows)
                return round(float(scorer(
                    hold.copy(deep=True),frame.copy(deep=True),
                    row_id_column_name="id",verbose=False)),8)
            result={
                "scores":{
                    "all_abstain":official(initial),
                    "numeric_24_arxiv_control":official(numeric_24_control),
                    "numeric_plus_reports":official(numeric_rows),
                    "llm_answer_only":official(model_values),
                    "llm_page_anchored_refs":official(model_anchored),
                    "llm_strict_abstain_without_anchor":official(model_strict),
                    "llm_numeric_fallback":official(model_fallback),
                },
                "dev_rows":len(dev),"holdout_rows":len(hold),
                "pinned_source_pdfs":len(selected),"pdf_chunks":len(pdf_chunks),
                "arxiv_prefix_control_pdfs":24,
                "report_source_types":dict(report_types),
                "report_failures":dict(report_errors),
                "report_digest_manifest_sha256":hashlib.sha256(
                    "\\n".join(report_hashes).encode()).hexdigest(),
                "pages_in_prompts":candidate_pages,
                "source_manifest_sha256":hashlib.sha256(
                    "\n".join(hashes).encode()).hexdigest(),
                "model":MODEL,"model_nonblank":model_answers,
                "model_quote_anchored":anchored,
                "model_status":dict(status_counts),
                "spend":{
                    "maximum_estimated_usd":MAX_ESTIMATED_USD,
                    "conservative_precommitted_usd":round(budget_committed,6),
                    "reported_api_cost_sum_usd":round(sum(observed_costs),6),
                },
                "boundary":"All 114 pinned arXiv papers + accessible report documents; reused TRAIN holdout, not leaderboard, model text is candidate only.",
            }
            print("WATTBOT_FLASHLITE_RAG_HOLDOUT="+json.dumps(result,sort_keys=True),flush=True)


def self_test():
    assert SOURCE_BUDGET==114
    assert CONTEXT_CHUNKS==6
    assert MAX_ESTIMATED_USD==0.08
    chunk={"ref_id":"doc","page":2,"url":"https://arxiv.org/pdf/2601.12345",
           "text":"Total training energy measured 1,287 MWh."}
    assert select_anchored_page("1,287 MWh",[chunk])==chunk
    assert select_anchored_page("10,000 MWh",[chunk]) is None
    original={"answer_value":"is_blank","ref_id":"is_blank"}
    answer={"answer":"1,287 MWh","answer_value":"1287",
            "answer_unit":"MWh","supporting_quote":"1,287 MWh"}
    out=with_model_answer(original,answer,chunk)
    assert out["answer_value"]=="1287" and out["ref_id"]=="['doc']"
    assert original["answer_value"]=="is_blank"
    print("FLASHLITE_RAG_SELF_TEST=PASS")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--official-zip")
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:self_test()
    elif args.official_zip:run(args.official_zip)
    else:parser.error("--self-test or --official-zip required")
