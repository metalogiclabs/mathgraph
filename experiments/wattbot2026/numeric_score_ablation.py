#!/usr/bin/env python3
"""Matched 8-vs-24 PDF numeric baseline, decomposed with official Score.py.

All model inputs are question text + development-selected source documents.
Only the pinned scorer sees heldout gold answers/references. No hidden test.
"""
from __future__ import annotations

import argparse
from collections import Counter
import io
import json
from pathlib import Path
import tempfile
import time
from urllib.parse import urlparse
import zipfile

import pandas as pd
import requests

from holdout_probe import is_holdout, ARXIV_HOSTS
from pdf_probe import download_one
from numeric_answer_probe import build_candidate
from score_ablation import blank_submission, load_score
from train_probe import load_csv, parse_refs
from wattbot import chunks_from_pages, ranked


def run(official_zip):
    with zipfile.ZipFile(official_zip) as z:
        docs_list=load_csv(z,"metadata.csv")
        docs={str(d["id"]):d for d in docs_list}
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str})
        dev=train[~train["id"].map(is_holdout)].copy()
        held=train[train["id"].map(is_holdout)].copy()
        counts=Counter(ref for _,r in dev.iterrows()
                       for ref in parse_refs(r["ref_id"]))
        eligible=[ref for ref in counts if ref in docs
                  and (urlparse(docs[ref]["url"]).hostname or "").lower() in ARXIV_HOSTS]
        eligible.sort(key=lambda x:(-counts[x],x))
        selected=eligible[:24]
        with tempfile.TemporaryDirectory(prefix="wattbot_ablate_") as folder:
            score_fn=load_score(z,folder)
            chunks_by_ref={}
            failures=Counter()
            for i,ref in enumerate(selected):
                if i:time.sleep(3.1)
                pdf=Path(folder)/f"paper_{i}.pdf"
                try:
                    download_one(docs[ref]["url"],pdf)
                    chunks=chunks_from_pages(ref,docs[ref]["url"],pdf)
                    if not chunks:raise ValueError("No PDF text")
                    chunks_by_ref[ref]=chunks
                except (requests.RequestException,ValueError,RuntimeError,OSError) as exc:
                    failures[type(exc).__name__]+=1
            meta_chunks=[{"ref_id":d["id"],"url":d["url"],"page":0,
                          "text":" ".join(str(d.get(k,"") or "") for k in
                          ("title","citation","year","venue"))} for d in docs_list]
            blank=blank_submission(held).reset_index(drop=True)
            def official(frame):
                return round(float(score_fn(held.copy(deep=True),
                    frame.copy(deep=True),row_id_column_name="id",verbose=False)),8)
            experiments={}
            for n in (8,24):
                index=meta_chunks+[c for ref in selected[:n]
                                   for c in chunks_by_ref.get(ref,[])]
                output=[]
                for _,r in held.iterrows():
                    row={"id":str(r["id"]),"question":str(r["question"])}
                    hits=ranked(row["question"],index,min(100,len(index)))
                    output.append(build_candidate(row,hits,docs))
                preds=pd.DataFrame(output,columns=list(blank.columns))
                value_only=preds.copy(deep=True)
                citation_only=preds.copy(deep=True)
                for col in ("ref_id","ref_url","supporting_materials"):
                    value_only[col]="is_blank"
                for col in ("answer","answer_value","answer_unit"):
                    citation_only[col]="is_blank"
                experiments[f"pdf_{n}"]={
                    "pdfs_downloaded":sum(ref in chunks_by_ref for ref in selected[:n]),
                    "nonblank_value_candidates":int((preds["answer_value"]!="is_blank").sum()),
                    "score_complete_candidate":official(preds),
                    "score_answer_only":official(value_only),
                    "score_citations_only":official(citation_only),
                }
            print("WATTBOT_MATCHED_NUMERIC_ABLATION="+json.dumps({
                "holdout_rows":len(held),"dev_rows":len(dev),
                "selection":"same fixed development-only source selection",
                "blank_score":official(blank),
                "source_fetch_failure_types":dict(failures),
                "experiments":experiments,
                "interpretation":"Training-subset official scorer; answer/citation ablations are diagnostics, not leaderboard submissions",
            },sort_keys=True))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip",required=True)
    run(p.parse_args().official_zip)
