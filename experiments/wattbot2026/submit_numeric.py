#!/usr/bin/env python3
"""MathGraph WattBot 2026 source-anchored first-submission candidate.

Uses TRAIN development references only for which arXiv papers to download.
Predicts 317 TEST answers from id/question + pinned PDFs, NEVER test labels.
No model training on holdout answers and no manually hard-coded answers.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import time
import zipfile
from urllib.parse import urlparse
import requests
import pandas as pd

from holdout_probe import is_holdout, ARXIV_HOSTS
from pdf_probe import download_one
from numeric_answer_probe import build_candidate
from train_probe import load_csv, parse_refs
from wattbot import chunks_from_pages, ranked, COLUMNS

# Frozen official file authorities, from qualified schema and scorer CI.
PINNED = {
    "Score.py": "e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
    "metadata.csv": "b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1",
    "train_QA.csv": "9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
    "test_Q.csv": "26038b21cb09588a39b0e95e5516e3827dadd499c85c3792d0ea46c10ae7066a",
}


def produce(zip_path: str, output_path: str) -> None:
    with zipfile.ZipFile(zip_path) as z:
        for name, expected in PINNED.items():
            actual = hashlib.sha256(z.read(name)).hexdigest()
            if actual != expected:
                raise ValueError(f"Official file {name} changed: {actual}; re-qualify before submission")
        metadata=load_csv(z,"metadata.csv")
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str})
        tests=[{"id":r["id"],"question":r["question"]} for r in load_csv(z,"test_Q.csv")]
    if len(tests)!=317 or len({r["id"] for r in tests})!=317:
        raise ValueError("Unexpected protected-test question count or duplicate IDs")
    docs={d["id"]:d for d in metadata}
    dev=train[~train["id"].map(is_holdout)]
    counts=Counter(ref for _,r in dev.iterrows()
                   for ref in parse_refs(str(r["ref_id"])))
    source_ids=sorted((ref for ref in counts
                       if ref in docs and
                       (urlparse(docs[ref]["url"]).hostname or "").lower() in ARXIV_HOSTS),
                      key=lambda r:(-counts[r],r))[:24]
    if len(source_ids)!=24:
        raise ValueError("Frozen dev-only source policy selected fewer than 24 sources")
    rows=[]
    with tempfile.TemporaryDirectory(prefix="wattbot_sub_v1_") as folder:
        chunks=[]
        source_digests=[]
        for i,ref in enumerate(source_ids):
            if i:
                time.sleep(3.1)
            path=Path(folder)/(str(i)+".pdf")
            digest,_=download_one(docs[ref]["url"],path)
            page_chunks=chunks_from_pages(ref,docs[ref]["url"],path)
            if not page_chunks:
                raise ValueError("Missing text in selected source; do not submit an incomplete corpus")
            source_digests.append(digest)
            chunks.extend(page_chunks)
        meta_chunks=[{"ref_id":d["id"],"url":d["url"],"page":0,
                      "text":" ".join(str(d.get(k,"") or "")
                      for k in ("title","citation","year","venue"))} for d in metadata]
        index=meta_chunks+chunks
        answers=0
        for item in tests:
            hits=ranked(item["question"],index,min(len(index),100))
            proposal=build_candidate(item,hits,docs)
            if proposal["id"]!=item["id"]:
                raise ValueError("Prediction row changed the test ID")
            if proposal["answer_value"]!="is_blank":
                answers+=1
            rows.append(proposal)
    output=Path(output_path)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(COLUMNS),extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    # Reopen and enforce exact competition schema and no missing fields.
    with output.open(encoding="utf-8",newline="") as f:
        reader=csv.DictReader(f)
        reread=list(reader)
        if reader.fieldnames!=list(COLUMNS) or len(reread)!=317:
            raise ValueError("Submission format invalid")
        if any(not row.get("explanation") or not row.get("answer_value") for row in reread):
            raise ValueError("Submission contains empty explanation or answer_value")
    print("WATTBOT_SUBMISSION_V1_READY="+json.dumps({
        "rows":len(rows),"nonblank_predictions":answers,
        "source_pdfs":len(source_ids),"source_pages_or_chunks":len(chunks),
        "source_manifest_sha256":hashlib.sha256("\n".join(source_digests).encode()).hexdigest(),
        "file_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
        "evidence":"Pinned official metadata/train/test/specific score code and arXiv PDFs",
        "scope":"Full test QUESTIONS only. No test labels, no oracle, no hand-coded answers.",
        "warning":"This does not claim the predictions are semantically correct or verified proofs.",
    },sort_keys=True))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    produce(a.official_zip,a.out)
