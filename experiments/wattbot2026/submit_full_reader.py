#!/usr/bin/env python3
"""Frozen WattBot 2026 full-corpus reader candidate generator.

No protected test labels. Download only 114 official version-pinned arXiv
sources and 8 official report URLs, with bounded retries and source hashes.
Use the already-qualified full_reader semantic policies, exact-page quotation
checker and numeric fallback. Source excerpt policy (prefix/window) is an
explicit input, fixed before any Kaggle submission. Hard spending boundary
and all-column CSV transport gate fail closed.
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
import requests

import full_reader as base
from query_window import window_passages
from submission_gate import validate_submission
from wattbot import chunks_from_pages, ranked
from holdout_probe import is_holdout
from numeric_answer_probe import build_candidate
from cached_pdf import cached_download
from report_loader import download_report
from train_probe import parse_refs

EXPECTED = {
    "Score.py":"e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
    "metadata.csv":"b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1",
    "train_QA.csv":"9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
    "test_Q.csv":"26038b21cb09588a39b0e95e5516e3827dadd499c85c3792d0ea46c10ae7066a",
}
ARXIV_MANIFEST="4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
REPORT_MANIFEST="a1720d14806ff219eaac8e0e8b8a5c8d6e87f596bba1a852505374ab4343b77d"
MAX_API_COST_USD=0.65
EXPECTED_TEST_ROWS=317


def make_question(item):
    return {"id":str(item["id"]),"question":str(item["question"])}


def normalize_unscored_unit(row):
    """Avoid default pandas/Kaggle null parsing for non-scored unit sentinels.

    This is only transport repair. Never modify answer_value or citations.
    """
    updated = dict(row)
    unit = str(updated.get("answer_unit", "") or "").strip()
    if unit.casefold() in ("", "na", "n/a", "nan", "none", "null"):
        updated["answer_unit"] = "is_blank"
    return updated


def recover_candidate_unanchored(raw, question, passages, numeric):
    """Retain answer-value candidates after a failed exact-quote check.

    Provenance states remain distinct: these source IDs are proposed by the
    LLM, NOT independently verified as supporting the answer. The serialized
    evidence contains only verbatim PDF excerpts, never invented quotations.
    """
    if not isinstance(raw, dict):
        return dict(numeric)
    value = str(raw.get("answer_value", "")).strip()
    if not value or value.casefold() in (
            "is_blank", "unknown", "na", "n/a", "nan", "none", "null"):
        return dict(numeric)
    indices = raw.get("source_indices")
    if not isinstance(indices, list) or not indices:
        indices = [raw.get("source_index")]
    selected=[]
    seen=set()
    for idx in indices:
        if type(idx) is not int or not 0 <= idx < len(passages):
            continue
        item=passages[idx]
        if item["ref_id"] in seen:
            continue
        selected.append(item)
        seen.add(item["ref_id"])
        if len(selected) == 3:
            break
    if not selected:
        selected=list(passages[:1])
    if not selected:
        return dict(numeric)
    result=dict(numeric)
    result["answer_value"]=value
    result["answer"]=str(raw.get("answer", value) or value)[:800]
    result["answer_unit"]=str(raw.get("answer_unit", "is_blank") or "is_blank")
    result["ref_id"]=repr([p["ref_id"] for p in selected])
    result["ref_url"]=repr([p["url"] for p in selected])
    # Exact excerpt is copied from the retrieved source, so readers can see
    # the provisional grounding. It is NOT falsely certified as an answer
    # entailment or as the model's quotation.
    result["supporting_materials"]=repr(
        [p["text"][:320] for p in selected])
    result["explanation"]=(
        "CANDIDATE_UNVERIFIED: LLM answer value retained after exact page-"
        "quotation check failed; document identity proposed by model's "
        "source index; displayed snippets are verbatim source text. "
        "Scientific entailment and citation correctness are UNKNOWN."
    )
    return normalize_unscored_unit(result)


def pinned_data(archive):
    with zipfile.ZipFile(archive) as z:
        for name, expected in EXPECTED.items():
            actual=hashlib.sha256(z.read(name)).hexdigest()
            if actual!=expected:
                raise ValueError("Official " + name + " has changed; do not submit")
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str})
        sources=pd.read_csv(io.BytesIO(z.read("metadata.csv")),
                            keep_default_na=False,dtype={"id":str})
        test=pd.read_csv(io.BytesIO(z.read("test_Q.csv")),
                         keep_default_na=False,dtype={"id":str})
    if len(train)!=245 or len(sources)!=122 or len(test)!=EXPECTED_TEST_ROWS:
        raise ValueError("Pinned question/source counts changed")
    if test["id"].duplicated().any():
        raise ValueError("Duplicate test question IDs")
    return train,sources,test


def corpus(train,sources,folder):
    docs={str(r["id"]):r for r in sources.to_dict("records")}
    dev=train[~train["id"].astype(str).map(is_holdout)]
    selected=base.selected_sources(dev,docs)
    if len(selected)!=base.SOURCE_BUDGET:
        raise ValueError("Incomplete pinned arXiv source registry")
    chunks=[]
    arxiv_digests=[]
    arxiv_errors=Counter()
    cache_counts=Counter()
    cache_root=Path(os.environ['WATTBOT_PDF_CACHE']) if os.environ.get('WATTBOT_PDF_CACHE') else None
    for i,ref in enumerate(selected):
        if i:time.sleep(3.1)
        path=folder/("arxiv_"+str(i)+".pdf")
        try:
            digest,_,reused=cached_download(str(docs[ref]["url"]),path,cache_root)
            cache_counts["hit" if reused else "miss"]+=1
            found=chunks_from_pages(ref,str(docs[ref]["url"]),path)
            if not found:
                raise ValueError("Source PDF has no extractable text")
            chunks.extend(found)
            arxiv_digests.append(digest)
        except (requests.RequestException,OSError,RuntimeError,ValueError) as exc:
            arxiv_errors[type(exc).__name__]+=1
            arxiv_digests.append("UNKNOWN")
        if i in (23,47,79,113):
            print("WATTBOT_SUBMISSION_ARXIV_ACQUISITION="+json.dumps(
                {"attempted":i+1,"chunks":len(chunks),"errors":dict(arxiv_errors)},
                sort_keys=True),flush=True)
    arxiv_manifest=hashlib.sha256("\n".join(arxiv_digests).encode()).hexdigest()
    if arxiv_manifest!=ARXIV_MANIFEST:
        raise RuntimeError("Pinned arXiv source bytes or failure pattern changed; requalify")
    reports=[d for d in docs.values() if str(d.get("type","")).lower()=="report"]
    if len(reports)!=8:
        raise ValueError("Pinned report-source registry changed")
    report_digests=[]
    report_errors=Counter()
    for i,item in enumerate(reports):
        if i:time.sleep(2)
        try:
            result=download_report(str(item["id"]),str(item["url"]))
            if not result["chunks"]:
                raise RuntimeError("Report is not extractable")
            chunks.extend(result["chunks"])
            report_digests.append(result["sha256"])
        except (requests.RequestException,OSError,RuntimeError,ValueError) as exc:
            report_errors[type(exc).__name__]+=1
            report_digests.append("UNKNOWN")
    # Historical full_reader pin hashes a LITERAL backslash+n separator.
    # Use exactly that declared encoding, not a newline; otherwise SHA differs.
    report_manifest=hashlib.sha256("\\n".join(report_digests).encode()).hexdigest()
    if report_manifest!=REPORT_MANIFEST:
        raise RuntimeError("Pinned report bytes or failed report pattern changed; requalify")
    metadata_chunks=[{"ref_id":d["id"],"url":d["url"],"page":0,
                      "text":" ".join(str(d.get(k,"") or "")
                                    for k in ("title","citation","year","venue"))}
                     for d in docs.values()]
    return docs, metadata_chunks+chunks, {
        "arxiv_attempted":len(selected),"arxiv_failures":dict(arxiv_errors),
        "arxiv_cached_pdf_reuse":dict(cache_counts),
        "reports_attempted":len(reports),"report_failures":dict(report_errors),
        "source_page_chunks":len(chunks),"arxiv_sha256":arxiv_manifest,
        "reports_sha256":report_manifest,
    }


def predict_rows(tests,docs,index,policy,key,rate):
    import full_reader
    if policy not in ("prefix","window"):
        raise ValueError("Unknown excerpt policy")
    if len(tests)!=EXPECTED_TEST_ROWS:
        raise ValueError("Protected-test question count unexpected")
    predictions=[]
    status=Counter()
    spend_reserved=0.0
    spend_observed=0.0
    for row_i,item in tests.iterrows():
        question=make_question(item)
        passages,hits=base.passages_for(question["question"],index)
        numeric=build_candidate(question,hits,docs)
        assert numeric["id"]==question["id"]
        if policy=="window":
            excerpt=window_passages(question["question"],passages,base.MAX_EXCERPT)
            for original,replaced in zip(passages,excerpt):
                for k in ("ref_id","url","page"):
                    if original[k]!=replaced[k]:
                        raise AssertionError("Evidence identity/order changed")
                if replaced["text"]!=original["text"][
                    replaced["excerpt_start"]:replaced["excerpt_end"]]:
                    raise AssertionError("Evidence excerpt is not a source substring")
            passages=excerpt
        selected=numeric
        if passages:
            prompt=json.dumps({"question":question["question"],
                 "passages":[{"source_index":j,"ref_id":p["ref_id"],
                              "page":p["page"],"text":p["text"][:base.MAX_EXCERPT]}
                             for j,p in enumerate(passages)]},
                 ensure_ascii=False,separators=(",",":"))
            estimate=base.conservative_charge(
                 base.SYSTEM+prompt,rate,base.MAX_OUTPUT_TOKENS)
            if spend_reserved+estimate > MAX_API_COST_USD:
                raise RuntimeError("Price ceiling would be exceeded: no submission")
            response,reason,bound,actual=base.call_reader(
                key,question["question"],passages,rate)
            spend_reserved+=bound
            spend_observed+=actual
            status[reason]+=1
            if reason in ("HTTP_401","HTTP_403","HTTP_429","PROVIDER_ERROR"):
                raise RuntimeError("Provider authorization/rate error: no submission")
            if reason=="OK":
                checked,result=base.try_checked(response,question,passages,docs)
                status[result]+=1
                if checked is not None:
                    selected=checked
                    status["VERIFIED_PAGE_QUOTE_ADMITTED"]+=1
                else:
                    unverified=recover_candidate_unanchored(
                        response,question,passages,numeric)
                    if unverified["answer_value"]!=numeric["answer_value"]:
                        selected=unverified
                        status["UNVERIFIED_ANSWER_VALUE_RETAINED"]+=1
                    else:
                        status["NO_UNVERIFIED_VALUE_RECOVERY"]+=1
        else:
            status["NO_PASSAGES"]+=1
        selected = normalize_unscored_unit(selected)
        if not selected.get("explanation") or not selected.get("answer_value"):
            raise ValueError("Unqualified candidate has a blank required field")
        predictions.append(selected)
        if row_i and row_i%50==0:
            print("WATTBOT_TEST_INFERENCE_PROGRESS="+json.dumps({
                "prepared_rows":len(predictions),"attempted":EXPECTED_TEST_ROWS,
                "budget_reserved_usd":round(spend_reserved,6),
                "nonblank_values":sum(x["answer_value"]!="is_blank" for x in predictions)
            },sort_keys=True),flush=True)
        time.sleep(base.REQUEST_PAUSE_SECONDS)
    if len(predictions)!=EXPECTED_TEST_ROWS:
        raise RuntimeError("Incomplete Kaggle test predictions")
    return predictions,{"status":dict(status),"reserved_usd":round(spend_reserved,6),
                        "reported_usd":round(spend_observed,6)}


def run(archive,out,policy):
    key=os.environ.get("OPENROUTER_API_KEY","")
    if not key:
        raise RuntimeError("Missing OpenRouter API key")
    if not (base.K==6 and base.MAX_EXCERPT==1100 and
            base.MODEL=="google/gemini-2.5-flash-lite"):
        raise RuntimeError("Reader configuration differs from measured candidate")
    rate=base.verify_price_ceiling()
    train,sources,tests=pinned_data(archive)
    with tempfile.TemporaryDirectory(prefix="wattbot_full_test_") as td:
        folder=Path(td)
        docs,index,manifest=corpus(train,sources,folder)
        predictions,usage=predict_rows(tests[["id","question"]],
                                         docs,index,policy,key,rate)
    destination=Path(out)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(base.blank_submission(tests).columns),
                              extrasaction="raise")
        writer.writeheader()
        writer.writerows(predictions)
    verified=validate_submission(destination,tests["id"].astype(str).tolist())
    print("WATTBOT_FULL_READER_TEST_READY="+json.dumps({
        "policy":policy,
        "scorer_pin":EXPECTED["Score.py"],
        "scoped_rows":EXPECTED_TEST_ROWS,
        "nonblank_predictions":sum(x["answer_value"]!="is_blank" for x in predictions),
        "manifest":manifest,"inference":usage,
        "submission":verified,
        "scope":"Official TEST question text only; page-verified quotes separated from unverified model-value/source candidates; no hidden labels",
    },sort_keys=True),flush=True)


def self_test():
    assert EXPECTED_TEST_ROWS==317
    assert set(EXPECTED)=={"Score.py","metadata.csv","train_QA.csv","test_Q.csv"}
    assert base.MODEL=="google/gemini-2.5-flash-lite"
    question=make_question({"id":"sample","question":"What energy was used?"})
    assert question=={"id":"sample","question":"What energy was used?"}
    repaired = normalize_unscored_unit({"answer_value":"12","ref_id":"['a']","answer_unit":"NA"})
    assert repaired["answer_unit"] == "is_blank"
    assert repaired["answer_value"] == "12" and repaired["ref_id"] == "['a']"
    assert normalize_unscored_unit({"answer_unit":"MWh"})["answer_unit"] == "MWh"
    numeric={"id":"sample","question":"What energy was used?",
             "answer":"is_blank","answer_value":"is_blank",
             "answer_unit":"is_blank","ref_id":"is_blank","ref_url":"is_blank",
             "supporting_materials":"is_blank","explanation":"No source."}
    passages=[
        {"ref_id":"p1","url":"https://arxiv.org/abs/2401.00001",
         "page":1,"text":"Reported training electricity 12 MWh."},
        {"ref_id":"p2","url":"https://arxiv.org/abs/2401.00002",
         "page":2,"text":"A different source."}]
    recovered=recover_candidate_unanchored({
        "answer":"12 MWh","answer_value":"12","answer_unit":"NA",
        "source_index":0,
        "supporting_quote":"fabricated unsupported quotation"},
        question,passages,numeric)
    assert recovered["answer_value"]=="12"
    assert recovered["answer_unit"]=="is_blank"
    assert recovered["ref_id"]=="['p1']"
    assert "Reported training electricity" in recovered["supporting_materials"]
    assert "fabricated unsupported quotation" not in recovered["supporting_materials"]
    assert "CANDIDATE_UNVERIFIED" in recovered["explanation"]
    assert recover_candidate_unanchored({
        "answer_value":"is_blank"},question,passages,numeric)==numeric
    print("WATTBOT_V4_UNVERIFIED_RECOVERY_SELF_TEST=PASS")
    print("WATTBOT_FULL_TEST_SELF_TEST=PASS")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip")
    p.add_argument("--out")
    p.add_argument("--policy",choices=["prefix","window"],default="prefix")
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip and a.out:run(a.official_zip,a.out,a.policy)
    else:p.error("Provide --self-test or both --official-zip and --out")
