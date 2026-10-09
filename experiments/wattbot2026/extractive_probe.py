#!/usr/bin/env python3
"""First WattBot extractive answer candidate; ONLY sourced PDFs, not test labels.

Fixed prior 182/63 train-only split. Source selection uses development labels
only; answer generation uses questions and eight public PDFs. Holdout gold
labels are supplied ONLY to pinned official Score.py after predictions freeze.
This holdout was previously inspected by other experiments, so this is a
candidate benchmark, not an untouched global test.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlparse
import zipfile

import pandas as pd
import requests

from pdf_probe import download_one
from holdout_probe import is_holdout
from wattbot import chunks_from_pages, ranked, norm
from train_probe import parse_refs
from score_ablation import load_score, blank_submission

ARXIV_HOSTS = {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}
MODEL = "distilbert/distilbert-base-cased-distilled-squad"
THRESHOLD = 0.35  # declared before observing heldout model predictions
COLUMNS = ["id","question","answer","answer_value","answer_unit",
           "ref_id","ref_url","supporting_materials","explanation"]


def sources_from_development(train, docs, max_docs=8):
    dev = train[~train["id"].astype(str).map(is_holdout)]
    counts = Counter(ref for refs in dev["ref_id"].map(parse_refs) for ref in refs)
    options = [d for d in counts if d in docs
               and (urlparse(str(docs[d]["url"])).hostname or "").lower() in ARXIV_HOSTS]
    options.sort(key=lambda d:(-counts[d],d))
    return options[:max_docs]


def candidate_for_question(question, chunks, qa, threshold):
    hits = ranked(question,chunks,top_k=5)
    if not hits:
        return None
    best = None
    for source in hits[:3]:
        context = source["text"][:1800]
        output = qa(question=question,context=context,
                    max_answer_len=45, handle_impossible_answer=True)
        answer = str(output.get("answer","")).strip()
        confidence = float(output.get("score",0))
        if answer and norm(answer) in norm(context):
            if best is None or confidence > best["score"]:
                best = {"answer":answer,"score":confidence,"source":source}
    if best is None or best["score"] < threshold:
        return None
    return best


def run(official_zip):
    from transformers import pipeline
    from huggingface_hub import HfApi
    with zipfile.ZipFile(official_zip) as z:
        train = pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                            keep_default_na=False,dtype={"id":str})
        metadata = pd.read_csv(io.BytesIO(z.read("metadata.csv")),
                               keep_default_na=False,dtype={"id":str})
        docs = {str(d["id"]):d for d in metadata.to_dict("records")}
        selected = sources_from_development(train,docs,8)
        held = train[train["id"].map(is_holdout)].copy()
        assert len(held) > 0 and len(selected)==8
        print("EXTRACTIVE_BOUNDARY="+json.dumps({
            "n_dev":int(len(train)-len(held)), "n_holdout":int(len(held)),
            "source_count":len(selected),"selection":"development labels only",
            "predictions":"question text + pinned eight PDFs only",
            "threshold":THRESHOLD,
            "warning":"Previously inspected holdout, candidate not pristine evaluation",
        },sort_keys=True))
        source_chunks=[]
        with tempfile.TemporaryDirectory(prefix="wattbot_extractive_") as td:
            for i,doc_id in enumerate(selected):
                if i: time.sleep(2)
                dest=Path(td)/(str(i)+".pdf")
                digest,_=download_one(str(docs[doc_id]["url"]),dest)
                source_chunks.extend(chunks_from_pages(doc_id,str(docs[doc_id]["url"]),dest))
            info=HfApi().model_info(MODEL)
            sha=info.sha
            print("MODEL_SNAPSHOT="+json.dumps({"id":MODEL,"revision":sha,
                "pdf_chunks":len(source_chunks)}))
            qa=pipeline("question-answering",model=MODEL,tokenizer=MODEL,
                        revision=sha,device=-1)
            predictions=blank_submission(held).reset_index(drop=True)
            answered=0
            cited=0
            conf=[]
            for i,row in predictions.iterrows():
                question=str(row["question"])
                match=candidate_for_question(question,source_chunks,qa,THRESHOLD)
                if match is None:
                    continue
                src=match["source"]
                answer=match["answer"]
                # Not every extractive span is semantically entailed.
                # Never call an accepted source quotation a verified answer.
                predictions.at[i,"answer"]=answer
                predictions.at[i,"answer_value"]=answer
                unit=re.search(r"(?:%|kWh|MWh|GWh|TWh|kg|tons?|tonnes?|years?|liters?|litres?)",
                               answer,flags=re.I)
                predictions.at[i,"answer_unit"]=unit.group(0) if unit else "is_blank"
                predictions.at[i,"ref_id"]=repr([src["ref_id"]])
                predictions.at[i,"ref_url"]=repr([src["url"]])
                predictions.at[i,"supporting_materials"]=repr([answer])
                predictions.at[i,"explanation"]=(
                    f"Extractive span from source page {src['page']} (model confidence "
                    f"{match['score']:.3f}); semantic entailment not independently checked.")
                assert norm(answer) in norm(src["text"])
                answered+=1
                cited+=1
                conf.append(match["score"])
            score_fn=load_score(z,td)
            def official(df):
                return float(score_fn(held.copy(deep=True),df.copy(deep=True),
                    row_id_column_name="id",verbose=False))
            blank=blank_submission(held).reset_index(drop=True)
            print("EXTRACTIVE_OFFICIAL_SCORE="+json.dumps({
                "all_blank_holdout_score":round(official(blank),8),
                "extractive_holdout_score":round(official(predictions),8),
                "holdout_rows":len(held),
                "nonblank_predicted":answered,
                "anchored_ref_predictions":cited,
                "mean_accepted_confidence":round(sum(conf)/len(conf),4) if conf else None,
                "scoring_authority":"Official WattBot2026 Score.py SHA-256 pinned in score_ablation.py",
                "boundary":"Train-only reused holdout; not official competition leaderboard or verified scientific truth",
            },sort_keys=True))


def self_test():
    assert THRESHOLD > 0 and THRESHOLD < 1
    assert len(COLUMNS)==9
    assert is_holdout("a")==is_holdout("a")
    print("EXTRACTIVE_SELF_TEST=PASS")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip")
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test: self_test()
    elif args.official_zip: run(args.official_zip)
    else: p.error("Supply --official-zip or --self-test")
