#!/usr/bin/env python3
"""WattBot exact-URL arXiv corpus coverage and evidence retrieval experiment.

Downloads at most 48 pinned arXiv sources, one by one, >=3.1s spacing, only
from official metadata. No arbitrary arXiv crawling; no licensed PDF bytes in
git/artifacts. Evaluate source recall on the SAME previously inspected 62-row
answerable training holdout. No test label access and no submission.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import tempfile
import time
from urllib.parse import urlparse
import zipfile

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from holdout_probe import is_holdout, ARXIV_HOSTS
from pdf_probe import download_one
from train_probe import parse_refs
from wattbot import chunks_from_pages

DEFAULT_CAP=48
CAPS=(0,24,48)

def source_ranking(index:list[dict], questions:list[str], k:int=8):
    """Return unique source ranks using maximum source-chunk word TF-IDF."""
    if not index:
        return [[] for _ in questions]
    vec=TfidfVectorizer(
        token_pattern=r"(?u)\b\w+\b",
        ngram_range=(1,2),
        sublinear_tf=True,
        max_features=120000
    )
    mat=vec.fit_transform([c["text"] for c in index])
    queries=vec.transform(questions)
    sim=(queries@mat.T).tocsr()
    output=[]
    for i in range(len(questions)):
        start,end=sim.indptr[i],sim.indptr[i+1]
        best={}
        for j,v in zip(sim.indices[start:end],sim.data[start:end]):
            ref=index[j]["ref_id"]
            if v>best.get(ref,-1):
                best[ref]=float(v)
        ordered=sorted(best,key=lambda ref:(-best[ref],str(ref)))
        output.append(ordered[:k])
    return output

def measure(metadata,held, chunks_by_ref,source_prefix):
    root=[{"ref_id":m["id"],"url":m["url"],"page":0,
           "text":" ".join(str(m.get(k,"") or "")
              for k in ("title","citation","year","venue"))} for m in metadata]
    for ref in source_prefix:
        root+=chunks_by_ref.get(ref,[])
    rows=[r for r in held if parse_refs(r.get("ref_id",""))]
    questions=[r["question"] for r in rows]
    rank=source_ranking(root,questions,k=8)
    hit_counts={}
    for k in (1,3,8):
        any_hits=all_hits=0
        for row,preds in zip(rows,rank):
            expected=set(parse_refs(row["ref_id"]))
            predicted=set(preds[:k])
            any_hits+=bool(expected&predicted)
            all_hits+=expected<=predicted
        hit_counts[str(k)]={"any_gold":round(any_hits/len(rows),4),
                            "all_gold":round(all_hits/len(rows),4)}
    known=set(source_prefix)
    return {"answerable_holdout_rows":len(rows),
            "source_count":len(metadata),
            "pdf_sources":len(source_prefix),
            "pdf_chunks":sum(len(chunks_by_ref.get(ref,[])) for ref in source_prefix),
            "holdout_any_gold_in_pdf_set":sum(bool(set(parse_refs(r["ref_id"]))&known) for r in rows),
            "holdout_all_gold_in_pdf_set":sum(set(parse_refs(r["ref_id"]))<=known for r in rows),
            "recall":hit_counts}

def main(zip_path,max_docs):
    if max_docs!=DEFAULT_CAP:
        raise ValueError("Fixed experiment only accepts exactly 48 attempted URLs")
    with zipfile.ZipFile(zip_path) as z:
        metadata=pd.read_csv(io.BytesIO(z.read("metadata.csv")),
                             keep_default_na=False,dtype={"id":str}).to_dict("records")
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str}).to_dict("records")
    dev=[r for r in train if not is_holdout(r["id"])]
    held=[r for r in train if is_holdout(r["id"])]
    docs={d["id"]:d for d in metadata}
    counts=Counter(ref for r in dev for ref in parse_refs(r.get("ref_id","")))
    arxiv=[d["id"] for d in metadata
           if (urlparse(d.get("url","")).hostname or "").lower() in ARXIV_HOSTS]
    arxiv.sort(key=lambda r:(-counts[r],r))
    selected=arxiv[:max_docs]
    if len(selected)!=max_docs:
        raise ValueError("Insufficient approved pinned arXiv URLs")
    print("WATTBOT_EXPANDED_BOUNDARY="+json.dumps({
        "train_development_rows":len(dev),"holdout_rows":len(held),
        "metadata_sources":len(metadata),
        "arxiv_sources":len(arxiv),"attempted_pinned_urls":max_docs,
        "source_selection":"dev citation counts then metadata ID only",
        "retrieval":"word TF-IDF 1-2 grams, source ranked by maximum chunk score",
        "protected_test_labels_used":False,
        "holdout_status":"reused, diagnostic, not prospective"
    },sort_keys=True),flush=True)
    chunks={}
    errors=Counter()
    digests=[]
    with tempfile.TemporaryDirectory(prefix="wattbot_corpus48_") as td:
        for i,ref in enumerate(selected):
            if i:time.sleep(3.1)
            path=Path(td)/f"source_{i}.pdf"
            try:
                digest,_=download_one(docs[ref]["url"],path)
                pages=chunks_from_pages(ref,docs[ref]["url"],path)
                if not pages:
                    errors["no_extractable_text"]+=1
                    continue
                chunks[ref]=pages
                digests.append(digest)
            except Exception as e:
                # No fabricated substitute; named acquisition failures remain.
                errors[type(e).__name__]+=1
            if i in (23,47):
                print("WATTBOT_DOWNLOAD_PROGRESS="+json.dumps({
                    "attempted":i+1,"valid":len(chunks),
                    "failure_types":dict(errors)},sort_keys=True),flush=True)
        stages={}
        for budget in CAPS:
            prefix=[ref for ref in selected[:budget] if ref in chunks]
            stages[str(budget)]=measure(metadata,held,chunks,prefix)
        print("WATTBOT_48_PDF_SOURCE_COVERAGE="+json.dumps({
            "attempted":max_docs,"valid":len(chunks),
            "errors":dict(errors),
            "hashes_manifest_sha256":hashlib.sha256(
                ("\n".join(digests)).encode()).hexdigest(),
            "comparisons":stages,
            "boundary":"Previously inspected train holdout; not final model answer accuracy or leaderboard result",
        },sort_keys=True),flush=True)


def self_test():
    x=[{"ref_id":"a","text":"server electricity power","url":"https://arxiv.org","page":1},
       {"ref_id":"b","text":"water pollution monitoring","url":"https://arxiv.org","page":1}]
    out=source_ranking(x,["electricity usage","water pollution"],k=2)
    assert out[0][0]=="a" and out[1][0]=="b"
    print("WATTBOT_EXPANDED_SELF_TEST=PASS")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip")
    p.add_argument("--max-docs",type=int,default=DEFAULT_CAP)
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test:self_test()
    elif args.official_zip:main(args.official_zip,args.max_docs)
    else:p.error("Provide --self-test or --official-zip")
