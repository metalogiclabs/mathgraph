#!/usr/bin/env python3
"""WattBot explicit pinned-arXiv 24-vs-48 source coverage audit.

This fetches at most 48 distinct metadata-pinned arXiv URLs, serially, with
3.1-second intervals; it is NOT an exploratory arXiv crawler. No PDFs, QAs,
or raw source text enter public logs or Git. Frozen prior train holdout is
exploratory, not an independent protected competition score.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import urlparse
import zipfile

import numpy as np
import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer

from holdout_probe import is_holdout, ARXIV_HOSTS
from pdf_probe import download_one
from train_probe import parse_refs
from wattbot import chunks_from_pages

N_SOURCES=48
SLEEP=3.1

def selected(dev,metadata):
    counts=Counter(r for txt in dev["ref_id"] for r in parse_refs(txt))
    docs={str(x["id"]):x for x in metadata}
    arxiv=set(k for k,v in docs.items()
              if (urlparse(str(v["url"])).hostname or "").lower() in ARXIV_HOSTS)
    # Do not use holdout references or answers to choose source acquisition.
    ids=sorted(arxiv,key=lambda r:(-counts[r],r))
    return ids[:N_SOURCES]

def build_index(meta, corpus):
    entries=[(d["id"]," ".join(str(d.get(k,"") or "")
               for k in ("title","citation","venue","year")))
             for d in meta]
    for doc_id in corpus:
        entries.extend((doc_id,c["text"]) for c in corpus[doc_id])
    vectorizer=TfidfVectorizer(analyzer="word",ngram_range=(1,2),
                               stop_words="english",sublinear_tf=True,max_features=160000)
    matrix=vectorizer.fit_transform([t for _,t in entries])
    return entries,vectorizer,matrix

def evaluate(held,meta,corpus,ids):
    truncated={key:corpus[key] for key in ids if key in corpus}
    entries,vectorizer,matrix=build_index(meta,truncated)
    questions=held["question"].astype(str).tolist()
    sim=(vectorizer.transform(questions)@matrix.T).tocsr()
    source_names=[str(key) for key,_ in entries]
    all_expected=[set(parse_refs(r)) for r in held["ref_id"]]
    eligible=[i for i,x in enumerate(all_expected) if x]
    metrics={}
    for k in (1,3,8):
        any_hit=all_hit=0
        for i in eligible:
            lo,hi=sim.indptr[i],sim.indptr[i+1]
            order=sorted(zip(sim.data[lo:hi],sim.indices[lo:hi]),
                         key=lambda x:(-float(x[0]),source_names[x[1]],x[1]))
            distinct=[]
            for score,index in order:
                ref=source_names[index]
                if ref not in distinct:
                    distinct.append(ref)
                if len(distinct)>=k:
                    break
            got=set(distinct)
            any_hit+=bool(got&all_expected[i])
            all_hit+=all_expected[i]<=got
        n=len(eligible)
        metrics[str(k)]={"answerable_rows":n,"any_gold":round(any_hit/n,4),
                         "all_gold":round(all_hit/n,4)}
    available=set(truncated)
    complete=sum(bool(refs) and refs<=available for refs in all_expected)
    at_least_one=sum(bool(refs&available) for refs in all_expected)
    return {"downloaded_papers":len(truncated),
            "indexed_chunks":len(entries)-len(meta),"coverage_any":at_least_one,
            "coverage_all":complete,"scores":metrics}

def run(archive):
    with zipfile.ZipFile(archive) as z:
        metadata=pd.read_csv(io.BytesIO(z.read("metadata.csv")),keep_default_na=False,dtype={"id":str}).to_dict("records")
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),keep_default_na=False,dtype={"id":str})
    dev=train[~train["id"].map(is_holdout)].copy()
    hold=train[train["id"].map(is_holdout)].copy().reset_index(drop=True)
    docs={str(x["id"]):x for x in metadata}
    ids=selected(dev,metadata)
    if len(ids)!=N_SOURCES:
        raise ValueError("Fewer than 48 pinned arXiv sources discovered")
    gathered={}
    checksums={}
    reasons=Counter()
    with TemporaryDirectory(prefix="wattbot_48_pinned_") as folder:
        for i,doc_id in enumerate(ids):
            if i:time.sleep(SLEEP)
            path=Path(folder)/("paper_"+str(i)+".pdf")
            try:
                checksum,_=download_one(str(docs[doc_id]["url"]),path)
                chunks=chunks_from_pages(doc_id,str(docs[doc_id]["url"]),path)
                if not chunks:raise ValueError("Empty searchable text")
                checksums[doc_id]=checksum
                gathered[doc_id]=chunks
            except (requests.RequestException,ValueError,RuntimeError,OSError) as error:
                reasons[type(error).__name__]+=1
    print("WATTBOT_48_SOURCE_ACQUISITION="+json.dumps({
        "attempted":len(ids),"succeeded":len(gathered),
        "failure_types":dict(reasons),
        "sha256_manifest":hashlib.sha256(
            "\n".join(checksums.get(i,"MISSING") for i in ids).encode()).hexdigest(),
        "protocol":"48 explicitly pinned arXiv documents, 3.1s serial pacing, no dataset publication"
    },sort_keys=True),flush=True)
    outputs={}
    for n in (24,48):
        outputs[str(n)]=evaluate(hold,metadata,gathered,ids[:n])
    print("WATTBOT_48_SOURCE_RETRIEVAL="+json.dumps({
        "dev_rows":len(dev),"holdout_rows":len(hold),
        "label_use":"DEV source-selection only; HOLDOUT gold for scoring after freeze",
        "retriever":"unchanged TFIDF word+bigram maximum-score chunk ranking",
        "arm_24":outputs["24"],"arm_48":outputs["48"],
        "boundary":"Reused TRAIN holdout; no protected test labels, no leaderboard accuracy"
    },sort_keys=True),flush=True)

def test():
    examples=[{"id":"a","url":"https://arxiv.org/abs/2301.00001","title":"Radiation emissions"},
              {"id":"b","url":"https://arxiv.org/abs/2301.00002","title":"Cats"}]
    docs,vectorizer,matrix=build_index(examples,{"a":[{"text":"Radiation emissions energy 40 MWh"}]})
    assert len(docs)==3
    assert matrix.shape[0]==3
    assert vectorizer.transform(["radiation energy"]).nnz>0
    print("WATTBOT_48_SELF_TEST=PASS")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--official-zip")
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:test()
    elif args.official_zip:run(args.official_zip)
    else:parser.error("Choose --self-test or --official-zip")
