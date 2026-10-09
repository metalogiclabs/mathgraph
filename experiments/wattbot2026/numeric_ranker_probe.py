#!/usr/bin/env python3
"""Train-only supervised numeric-evidence selector for WattBot 2026.

DEV answers are labels; HOLDOUT answer and citation labels are never used to
form predictions. Document choice uses DEV gold references only, as in the
existing 24-source baseline. Holdout is previously explored across variants
and therefore this is diagnostic, not pristine prospective evidence.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import io
import json
import math
from pathlib import Path
import tempfile
import time
from urllib.parse import urlparse
import zipfile

import pandas as pd
import requests
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from holdout_probe import is_holdout, ARXIV_HOSTS
from pdf_probe import download_one
from numeric_answer_probe import numeric_candidates, build_candidate
from score_ablation import load_score, blank_submission
from train_probe import parse_refs
from wattbot import as_fraction, chunks_from_pages, ranked, tokens, verify_candidate

SOURCE_BUDGET=24
TOP_CHUNKS=100
CANDIDATES_PER_QUESTION=30
RANDOM_STATE=2026


def rows_to_candidates(question, corpus):
    found=ranked(question,corpus,min(TOP_CHUNKS,len(corpus)))
    return numeric_candidates(question,found)[:CANDIDATES_PER_QUESTION]


def features(question, rank, entry):
    priority, chunk, raw, quote, unit = entry
    from fractions import Fraction
    value=as_fraction(raw)
    q=set(tokens(question))
    quoted=set(tokens(quote))
    overlap=len(q & quoted)
    q_lower=question.lower()
    unit_lower=unit.lower()
    same_unit=(unit_lower != "is_blank" and unit_lower in q_lower)
    possible_year=1900 <= float(value) <= 2100
    return [
        math.log1p(max(0,float(priority))),
        math.log1p(max(0,float(chunk.get("score",0)))),
        1.0/(1+rank),
        overlap/max(1,len(q)),
        math.log10(max(1.,abs(float(value)))),
        float(value.denominator==1),
        float(unit!="is_blank"),
        float(same_unit),
        float(possible_year),
        float("percent" in q_lower or "%" in q_lower),
        float("year" in q_lower or "date" in q_lower),
        float("energy" in q_lower or "power" in q_lower),
        float("water" in q_lower),
        float("emission" in q_lower),
        math.log1p(max(0,len(quote))),
        float(rank < 5),
    ]


def numeric_equal(a, b):
    try:
        x, y = as_fraction(str(a)), as_fraction(str(b))
        return abs(x-y) <= max(abs(y)/1000,1/1000000)
    except (ValueError,ZeroDivisionError,TypeError):
        return False


def to_verified_candidate(item, entry, docs, corpus):
    _,chunk,raw,quote,unit=entry
    row={"id":str(item["id"]),"question":str(item["question"])}
    candidate={
        "id":row["id"],
        "answer":raw if unit=="is_blank" else raw+" "+unit,
        "answer_value":raw,
        "ref_ids":[chunk["ref_id"]],
        "evidence":[{"ref_id":chunk["ref_id"],"page":chunk["page"],"quote":quote}],
        "derivation":{"expression":"x","inputs":{
            "x":{"value":raw,"evidence_index":0}}},
        "explanation":"Candidate numeric literal with pinned PDF page and exact identity arithmetic; semantic entailment unknown",
    }
    valid=verify_candidate(candidate,row,docs,corpus)
    valid["answer_unit"]=unit
    return valid


def run(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")), keep_default_na=False,dtype={"id":str})
        meta=pd.read_csv(io.BytesIO(z.read("metadata.csv")),keep_default_na=False,dtype={"id":str})
        dev=train[~train["id"].map(is_holdout)].copy()
        held=train[train["id"].map(is_holdout)].copy().reset_index(drop=True)
        docs={str(r["id"]):r for r in meta.to_dict("records")}
        ref_counts=Counter(ref for refs in dev["ref_id"].map(parse_refs) for ref in refs)
        choices=[rid for rid in ref_counts if rid in docs and (
            urlparse(str(docs[rid]["url"])).hostname or "").lower() in ARXIV_HOSTS]
        choices.sort(key=lambda rid:(-ref_counts[rid],rid))
        selected=choices[:SOURCE_BUDGET]
        if len(selected)!=SOURCE_BUDGET:
            raise ValueError("Insufficient eligible sources")
        with tempfile.TemporaryDirectory(prefix="wattbot_numeric_ranker_") as folder:
            td=Path(folder)
            pdf_chunks=[]
            hashes=[]
            for i,rid in enumerate(selected):
                if i: time.sleep(3.1)
                filepath=td/f"{i}.pdf"
                sha,_=download_one(str(docs[rid]["url"]),filepath)
                pages=chunks_from_pages(rid,str(docs[rid]["url"]),filepath)
                if not pages: raise ValueError("Pinned PDF missing extracted text")
                pdf_chunks.extend(pages)
                hashes.append(sha)
            meta_chunks=[{"ref_id":r["id"],"url":r["url"],"page":0,
                          "text":" ".join(str(r.get(k,"") or "") for k in
                                         ("title","citation","year","venue"))}
                         for r in meta.to_dict("records")]
            corpus=meta_chunks+pdf_chunks
            X,Y=[],[]
            positives_by_question=0
            labeled_numeric_dev=0
            for _,item in dev.iterrows():
                expected=item["answer_value"]
                if not numeric_equal(expected,expected):continue
                labeled_numeric_dev+=1
                positive=False
                entries=rows_to_candidates(str(item["question"]),corpus)
                for j,entry in enumerate(entries):
                    good=numeric_equal(entry[2],expected)
                    X.append(features(str(item["question"]),j,entry))
                    Y.append(int(good))
                    positive |= good
                positives_by_question += positive
            labels=Counter(Y)
            print("NUMERIC_RANKER_BOUNDARY="+json.dumps({
                "dev_rows":len(dev),"heldout_rows":len(held),
                "numeric_dev_rows":labeled_numeric_dev,
                "numeric_dev_with_candidate_gold_value":positives_by_question,
                "candidate_labels":dict(labels),
                "pdf_source_count":len(selected),
                "pdf_chunks":len(pdf_chunks),
                "source_manifest_sha256":hashlib.sha256("\n".join(hashes).encode()).hexdigest(),
                "note":"Training labels not used to create holdout candidates, fixed 24-source corpus"
            },sort_keys=True),flush=True)
            if not 0 in labels or not 1 in labels:
                raise ValueError("Cannot train ranker without both numeric classes")
            learner=make_pipeline(
                StandardScaler(),
                LogisticRegression(class_weight="balanced",C=.25,
                                   max_iter=1200,random_state=RANDOM_STATE)
            )
            learner.fit(X,Y)
            baseline=[]
            predicted=[]
            n_select_different=0
            selected_probs=[]
            for _,item in held.iterrows():
                item={"id":str(item["id"]),"question":str(item["question"])}
                found=ranked(item["question"],corpus,min(TOP_CHUNKS,len(corpus)))
                baseline.append(build_candidate(item,found,docs))
                options=numeric_candidates(item["question"],found)[:CANDIDATES_PER_QUESTION]
                if not options:
                    predicted.append(baseline[-1]);continue
                scored=learner.predict_proba([
                    features(item["question"],j,c)
                    for j,c in enumerate(options)])[:,1].tolist()
                order=sorted(range(len(options)),key=lambda j:(-scored[j],j))
                chosen=None
                for j in order:
                    try:
                        chosen=to_verified_candidate(item,options[j],docs,found)
                        selected_probs.append(scored[j])
                        break
                    except (KeyError,ValueError,TypeError,ZeroDivisionError):
                        pass
                candidate=chosen if chosen is not None else baseline[-1]
                n_select_different += candidate["answer_value"]!=baseline[-1]["answer_value"]
                predicted.append(candidate)
            original=blank_submission(held).reset_index(drop=True)
            def df(items):return pd.DataFrame(items,columns=list(original.columns))
            baseline=df(baseline);predicted=df(predicted)
            score_fn=load_score(z,str(td))
            def score(candidate):
                return round(float(score_fn(held.copy(deep=True),candidate.copy(deep=True),
                                      row_id_column_name="id",verbose=False)),8)
            no_cites=predicted.copy(deep=True)
            for col in ("ref_id","ref_url","supporting_materials"):
                no_cites[col]="is_blank"
            baseline_answer=baseline.copy(deep=True)
            for col in ("ref_id","ref_url","supporting_materials"):
                baseline_answer[col]="is_blank"
            print("NUMERIC_RANKER_OFFICIAL_ABLATION="+json.dumps({
                "all_blank":score(original),
                "frozen_heuristic":score(baseline),
                "supervised_ranker":score(predicted),
                "heuristic_answer_only":score(baseline_answer),
                "ranker_answer_only":score(no_cites),
                "changed_answers":n_select_different,
                "selected_probability_mean":round(sum(selected_probs)/len(selected_probs),4) if selected_probs else None,
                "scope":"Exploratory reused TRAIN holdout; NOT Kaggle leaderboard, labels never used for holdout predictions",
            },sort_keys=True),flush=True)


def self_test():
    assert numeric_equal("123","123.0000")
    assert not numeric_equal("123","124")
    entry=(7.0,{"score":3.0,"ref_id":"d","page":1},"42","a 42 kWh energy source","kWh")
    assert len(features("How many kWh of energy?",0,entry))==16
    print("NUMERIC_RANKER_SELF_TEST=PASS")


if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--official-zip")
    a.add_argument("--self-test",action="store_true")
    args=a.parse_args()
    if args.self_test: self_test()
    elif args.official_zip: run(args.official_zip)
    else: a.error("--official-zip or --self-test required")
