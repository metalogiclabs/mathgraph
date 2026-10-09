#!/usr/bin/env python3
"""WattBot TRAIN-only answer accessibility diagnosis on complete pinned PDFs.

Do not inject gold TRAIN values or citations into retrieval. First run frozen
BM25 for each question, then AFTER retrieval compare known TRAIN value and
source IDs with indexed full/source pages. No protected TEST labels or Kaggle
submission. An exact literal's presence is not semantic entailment.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import zipfile
import pandas as pd

import full_reader as reader
from holdout_probe import is_holdout
from train_probe import parse_refs
from wattbot import NUM_RE, as_fraction, ranked, norm
from query_window import window_passages

OFFICIAL_SHA={
  "metadata.csv":"b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1",
  "train_QA.csv":"9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
}
SOURCE_SHA="4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
FLAGS=("Quote","Table","Figure","Math","CrossPaper","Reconcile","is_NA")


def target_spec(text):
    value=str(text or "").strip()
    low=value.casefold()
    if low in ("is_blank","na","nan","none",""):
        return ("na",[])
    try:
        return ("scalar",[as_fraction(value)])
    except ValueError:
        pass
    try:
        item=ast.literal_eval(value)
    except (SyntaxError,ValueError,TypeError,MemoryError):
        item=None
    if isinstance(item,(list,tuple)) and len(item)==2:
        try:
            targets=[as_fraction(str(x)) for x in item]
            return ("band_or_range",targets)
        except ValueError:
            pass
    if isinstance(item,(list,tuple)):
        return ("list",[str(x).strip().casefold() for x in item if str(x).strip()])
    return ("term",[low])


def present(kind, parts, passage):
    body=str(passage or "")
    if kind=="na":
        return False
    if kind in ("scalar","band_or_range"):
        matches=[]
        for m in NUM_RE.finditer(body):
            try:
                matches.append(as_fraction(m.group()))
            except ValueError:
                continue
        return all(v in matches for v in parts)
    if kind=="term":
        return norm(parts[0]) in norm(body)
    if kind=="list":
        return all(norm(p) in norm(body) for p in parts)
    return False


def stats(rows):
    metrics=Counter()
    for r in rows:
        metrics["n"]+=1
        for key,value in r.items():
            if key in ("n","kind"):continue
            if isinstance(value,(int,bool)):
                metrics[key]+=int(value)
        metrics["kind_"+r["kind"]]+=1
    return dict(metrics)


def evaluate(cohort, chunks):
    counts=Counter()
    by_type=defaultdict(list)
    by_flag=defaultdict(list)
    by_multisource=defaultdict(list)
    all_page_by_ref=defaultdict(list)
    for item in chunks:
        if item["page"]>0:
            all_page_by_ref[item["ref_id"]].append(item)
    for row in cohort.to_dict("records"):
        q=str(row["question"])
        k,expected=target_spec(row.get("answer_value",""))
        refs=set(parse_refs(str(row["ref_id"])))
        ranked_hits=ranked(q,chunks,min(100,len(chunks)))
        top=[x for x in ranked_hits if x["page"]>0]
        top6=top[:6]
        top10=top[:10]
        windows6=window_passages(q,top6,1100)
        windows10=window_passages(q,top10,1100)
        goldpages=[x for ref in refs for x in all_page_by_ref.get(ref,[])]
        snapshot={
            "kind":k,
            "answerable":int(k!="na"),
            "gold_refs_n":len(refs),
            "gold_source_accessible":int(all(ref in all_page_by_ref for ref in refs)),
            "gold_any_in_top6":int(bool(refs & {x["ref_id"] for x in top6})),
            "gold_all_in_top6":int(bool(refs) and refs <= {x["ref_id"] for x in top6}),
            "gold_all_in_top10":int(bool(refs) and refs <= {x["ref_id"] for x in top10}),
            "literal_in_gold_full":int(any(present(k,expected,x["text"]) for x in goldpages)),
            "literal_in_any_full":int(any(present(k,expected,x["text"]) for x in chunks if x["page"]>0)),
            "literal_in_top100":int(any(present(k,expected,x["text"]) for x in top)),
            "literal_in_top6_full":int(any(present(k,expected,x["text"]) for x in top6)),
            "literal_in_top6_window":int(any(present(k,expected,x["text"]) for x in windows6)),
            "literal_in_top10_window":int(any(present(k,expected,x["text"]) for x in windows10)),
        }
        # The diagnostic values (gold) do not affect the ranked source contexts.
        by_type[k].append(snapshot)
        nrefs="multi" if len(refs)>1 else "single" if len(refs)==1 else "zero"
        by_multisource[nrefs].append(snapshot)
        for f in FLAGS:
            if str(row.get(f,"")).casefold() in ("true","1","yes","x"):
                by_flag[f].append(snapshot)
        counts["total"]+=1
    return {
        "n_questions":counts["total"],
        "by_answer_shape":{k:stats(v) for k,v in sorted(by_type.items())},
        "by_gold_ref_count":{k:stats(v) for k,v in sorted(by_multisource.items())},
        "by_evidence_flag":{k:stats(v) for k,v in sorted(by_flag.items())},
        "summary":stats([x for group in by_type.values() for x in group]),
    }


def self_test():
    assert target_spec("1,287")==("scalar",[Fraction(1287)])
    assert target_spec("is_blank")[0]=="na"
    assert target_spec("(1,2)")==("band_or_range",[Fraction(1),Fraction(2)])
    assert target_spec("TRUE")==("term",["true"])
    assert present("scalar",[Fraction(1287)],"Consumption was 1,287 MWh.")
    assert not present("scalar",[Fraction(12)],"The year was 2012.")
    assert present("list",["apple","orange"],"Apple and orange were studied.")
    print("WATTBOT_ACCESSIBILITY_SELF_TEST=PASS")


def run(official_zip):
    self_test()
    with zipfile.ZipFile(official_zip) as z:
        for name,sha in OFFICIAL_SHA.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=sha:
                raise RuntimeError("Official data pin moved")
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
            dtype={"id":str},keep_default_na=False)
        meta=pd.read_csv(io.BytesIO(z.read("metadata.csv")),
            dtype={"id":str},keep_default_na=False)
    dev=train[~train["id"].map(is_holdout)]
    hold=train[train["id"].map(is_holdout)]
    assert len(dev)==182 and len(hold)==63
    from submit_full_reader import corpus
    with tempfile.TemporaryDirectory(prefix="wattbot_answer_access_") as td:
        docs,chunks,manifest=corpus(train,meta,Path(td))
        assert manifest["arxiv_sha256"]==SOURCE_SHA
        result={
            "corpus_manifest":manifest,
            "dev":evaluate(dev,chunks),
            "holdout":evaluate(hold,chunks),
            "scope":"TRAIN labels used ONLY AFTER deterministic retrieval, no protected TEST",
            "boundary":"Literal presence is a necessary extractive opportunity, NOT evidence "
                       "that the text entails the requested answer. Absence may "
                       "indicate mathematical derivation, figures/tables or missing source.",
        }
    print("WATTBOT_ANSWER_ACCESSIBILITY="+json.dumps(result,sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Provide --self-test or --official-zip")
