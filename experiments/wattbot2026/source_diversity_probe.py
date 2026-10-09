#!/usr/bin/env python3
"""WattBot deterministic six-passage source-diversity audit.

Experiment, not a submission. All retrieval candidates use only questions and
official pinned public PDFs. TRAIN gold ref_id is consulted *after* retrieval
has frozen, solely to measure the source-coverage consequences. No model calls
or protected test labels. The reused hash holdout is not pristine.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import tempfile
import zipfile

import pandas as pd

import full_reader as reader
from holdout_probe import is_holdout
from submit_full_reader import EXPECTED, corpus, pinned_data
from train_probe import parse_refs

K = reader.K
POLICIES = ("baseline", "cap1", "cap2")


def choose_pages(hits, policy, k=K):
    """A permutation-preserving selection; no new or synthetic evidence."""
    if policy not in POLICIES:
        raise ValueError("Unknown policy")
    if not isinstance(k, int) or k < 1:
        raise ValueError("k must be positive")
    pdf_hits = [x for x in hits if int(x.get("page", 0)) > 0]
    if policy == "baseline":
        return pdf_hits[:k]
    cap = int(policy[-1])
    result = []
    counts = Counter()
    for page in pdf_hits:
        if len(result) >= k:
            break
        ref = page["ref_id"]
        if counts[ref] >= cap:
            continue
        result.append(page)
        counts[ref] += 1
    if len(result) < k:
        selected = {id(x) for x in result}
        result.extend([p for p in pdf_hits if id(p) not in selected][:k - len(result)])
    assert len(result) == min(k, len(pdf_hits))
    assert len({id(x) for x in result}) == len(result)
    assert all(x in pdf_hits for x in result)
    return result


def evaluate(rows, index, available_sources):
    totals = {p: Counter() for p in POLICIES}
    paired = {p: Counter() for p in POLICIES if p != "baseline"}
    eligible = 0
    missing_gold_source = 0
    multi_source = 0
    for _, entry in rows.iterrows():
        q = str(entry["question"])
        gold = set(parse_refs(str(entry.get("ref_id", ""))))
        if not gold:
            continue
        eligible += 1
        multi_source += len(gold) > 1
        missing_gold_source += bool(gold - available_sources)
        # Identical frozen BM25 ranking for every policy; no gold labels used.
        _, ranking = reader.passages_for(q, index)
        selections = {p: choose_pages(ranking, p) for p in POLICIES}
        hits = {}
        all_hits = {}
        for p, pages in selections.items():
            refs = {x["ref_id"] for x in pages}
            overlap = len(gold & refs)
            hits[p] = bool(overlap)
            all_hits[p] = gold <= refs
            counter = totals[p]
            counter["any"] += hits[p]
            counter["all"] += all_hits[p]
            counter["covered_sources"] += overlap
            counter["total_gold_sources"] += len(gold)
            counter["pages"] += len(pages)
            counter["distinct_refs"] += len(refs)
            # Diagnostic selector-only citation F1: NOT the LLM's output.
            counter["citation_f1_millionths"] += round(
                (2 * overlap / (len(refs) + len(gold))) * 1_000_000
            ) if (refs or gold) else 0
        for p in paired:
            for what, results in (("any", hits), ("all", all_hits)):
                if results[p] and not results["baseline"]:
                    paired[p][what+"_gained"] += 1
                if results["baseline"] and not results[p]:
                    paired[p][what+"_lost"] += 1
    if eligible == 0:
        raise RuntimeError("Empty labelled TRAIN evaluation")
    summary = {}
    for p, c in totals.items():
        summary[p] = {
            "questions_with_gold_refs": eligible,
            "gold_any_at_six": c["any"],
            "gold_all_at_six": c["all"],
            "gold_source_recall": round(c["covered_sources"]/c["total_gold_sources"], 6),
            "selected_distinct_refs_per_question": round(c["distinct_refs"]/eligible, 5),
            "selector_only_citation_f1": round(c["citation_f1_millionths"]/eligible/1e6, 6),
            "average_pages": round(c["pages"]/eligible, 5),
        }
    return {
        "eligible_answerable_rows":eligible,
        "multi_gold_source_questions":multi_source,
        "questions_missing_at_least_one_accessible_source":missing_gold_source,
        "policies": summary,
        "paired_vs_baseline": {p:dict(c) for p,c in paired.items()},
    }


def self_test():
    a = {"ref_id":"a","page":1,"text":"first"}
    b = {"ref_id":"a","page":2,"text":"second"}
    c = {"ref_id":"a","page":3,"text":"third"}
    d = {"ref_id":"b","page":1,"text":"fourth"}
    e = {"ref_id":"c","page":2,"text":"fifth"}
    f = {"ref_id":"d","page":3,"text":"sixth"}
    g = {"ref_id":"e","page":3,"text":"seventh"}
    hits = [{"ref_id":"meta","page":0,"text":"not a PDF"},a,b,c,d,e,f,g]
    assert choose_pages(hits,"baseline",4)==[a,b,c,d]
    assert choose_pages(hits,"cap1",4)==[a,d,e,f]
    assert choose_pages(hits,"cap2",4)==[a,b,d,e]
    assert choose_pages(hits,"cap1",6)==[a,d,e,f,g,b]
    assert choose_pages(hits,"cap2",8)==[a,b,d,e,f,g,c]
    assert choose_pages(hits,"cap1",4)==choose_pages(hits,"cap1",4)
    assert choose_pages(hits[:1],"cap1",6)==[]
    try:
        choose_pages(hits,"unknown")
    except ValueError:
        pass
    else:
        raise AssertionError("Unregistered retrieval variant allowed")
    print("WATTBOT_SOURCE_DIVERSITY_SELF_TEST=PASS",flush=True)


def run(archive):
    self_test()
    with zipfile.ZipFile(archive) as z:
        for name, target in EXPECTED.items():
            if hashlib.sha256(z.read(name)).hexdigest() != target:
                raise RuntimeError("Official WattBot file pin changed: "+name)
    train, source_table, _ = pinned_data(archive)
    with tempfile.TemporaryDirectory(prefix="wattbot_diversity_") as folder:
        docs, index, manifest = corpus(train,source_table,Path(folder))
        available = {x["ref_id"] for x in index if int(x["page"])>0}
        dev=train[~train["id"].astype(str).map(is_holdout)]
        hold=train[train["id"].astype(str).map(is_holdout)]
        result = {
            "scope": ("Official TRAIN labels for retrospective source coverage only; "
                      "not a model answer score, unseen holdout or Kaggle result"),
            "dataset_sha256": EXPECTED["train_QA.csv"],
            "reader_top_pages":K,
            "retriever":"Frozen reader.passages_for BM25 top100; only reorders/quotas same candidate pages",
            "source_manifest":manifest,
            "pdf_source_count":len(available),
            "dev":evaluate(dev,index,available),
            "reused_holdout":evaluate(hold,index,available),
        }
        print("WATTBOT_SOURCE_DIVERSITY_AUDIT="+json.dumps(result,sort_keys=True),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--official-zip")
    args=parser.parse_args()
    if args.self_test:
        self_test()
    elif args.official_zip:
        run(args.official_zip)
    else:
        parser.error("Specify --self-test or --official-zip")
