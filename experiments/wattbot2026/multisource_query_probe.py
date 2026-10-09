#!/usr/bin/env python3
"""WattBot consequence-protected multi-source question retrieval diagnostic.

Generate retrieval expansions solely from CURRENT question wording, not gold
source IDs/answers. Compare the unchanged lexical six PDF pages to a
query-decomposed, source-diverse six-page policy. Once both policies freeze,
use TRAIN citations to score whether all required source IDs are present.

Scientific consequences remain UNKNOWN: finding the right document does NOT
mean the right measurements or answer are present in the model excerpts.
No TEST labels, model calls or Kaggle submission.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import zipfile

import pandas as pd

from holdout_probe import is_holdout
from train_probe import parse_refs
from wattbot import ranked
import submit_full_reader as base

PINNED={
 "Score.py":"e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
 "metadata.csv":"b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1",
 "train_QA.csv":"9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca"
}
SOURCE_MANIFEST="4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
MAX_Q=3
K=6
TERM_SPLIT=re.compile(r"\b(?:whereas|while|but|another|in contrast|as opposed to|versus|vs\.?|compared with|compared to)\b",re.I)
CROSS=re.compile(r"\b(?:both|two|multiple|different)\s+(?:studies|papers|reports)\b|"
    r"\b(?:compare|comparison|reconcile|reconciliation|contradict|difference)\b|"
    r"\b(?:household[-\s]?years?|per\s+household)\b|"
    r"\b(?:across|between)\s+(?:the\s+)?(?:two|both|multiple)\s+"
    r"(?:papers|studies|reports)\b",re.I)

def source_questions(q):
    """Frozen query-only subproblem decomposition; no named-paper overrides."""
    full=" ".join(str(q).split())
    if not CROSS.search(full):
        return []
    queries=[]
    pieces=[s.strip(" ,;:.") for s in TERM_SPLIT.split(full) if len(s.strip())>12]
    if len(pieces)>1:
        queries.extend(pieces[:3])
    # Generic measurement bridges, never question-ID- or source-ID-specific.
    text=full.lower()
    if "household" in text:
        queries.append("U.S. household electricity consumption MWh households per year")
    if "carbon intensity" in text or "emissions factor" in text:
        queries.append("electricity generation kg CO2 equivalent per kWh emission factor")
    if "power" in text and "energy" in text:
        queries.append("power consumption electrical energy workload duration model")
    if "water" in text and "electricity" in text:
        queries.append("datacenter cooling water usage electricity generation withdrawal consumption")
    if not queries and ("compare" in text or "both" in text or "between" in text):
        # Whole-question query is retained as a distinct source request;
        # retrieval diversity will use different documents rather than
        # repeatedly taking near-duplicate passages.
        queries.append(full)
    return list(dict.fromkeys(queries))[:MAX_Q]


def select_pages(q,index,k=K):
    baseline=[x for x in ranked(q,index,min(100,len(index)))
              if x.get("page",0)>0][:k]
    if len(baseline)!=k:
        return baseline,baseline,False
    subqueries=source_questions(q)
    if not subqueries:
        return baseline,baseline,False
    candidate_lists=[]
    for sub in subqueries:
        hits=[x for x in ranked(sub,index,min(60,len(index)))
              if x.get("page",0)>0]
        candidate_lists.append(hits)
    chosen=[]
    seen_pages=set()
    source_counts=Counter()
    def insert(p,source_cap=2):
        key=(p["ref_id"],p["page"],p["text"][:60])
        if key in seen_pages or source_counts[p["ref_id"]] >= source_cap:
            return False
        chosen.append(p)
        seen_pages.add(key)
        source_counts[p["ref_id"]]+=1
        return True

    # Give the full-question strongest paper one page, then reserve slots
    # for independent subquestion viewpoints, prior to filling by BM25.
    insert(baseline[0])
    for hits in candidate_lists:
        # Prioritize a distinct document for each independent subquery.
        for hit in hits:
            if source_counts[hit["ref_id"]]==0 and insert(hit):
                break
        if len(chosen)==k: break
    for page in baseline:
        if len(chosen)==k:break
        insert(page)
    # When full BM25 dominated one document, fill from the other source-
    # specific rankings; never fabricate a source not in pinned metadata.
    for hits in candidate_lists:
        for page in hits:
            if len(chosen)==k:break
            insert(page)
        if len(chosen)==k:break
    if len(chosen)<k:
        # Fall back to original six only, rather than silently modifying
        # excerpt count or inventing a model input.
        return baseline,baseline,False
    assert len(chosen)==k
    return chosen,baseline,True


def count(rows,index):
    by_type=defaultdict(lambda:Counter())
    exemplar_shapes=Counter()
    seen_triggers=Counter()
    for row in rows:
        question=str(row["question"])
        chosen,original,routed=select_pages(question,index)
        if len(original)!=K or len(chosen)!=K:
            raise RuntimeError("Frozen corpus did not return K6 pages")
        refs=set(parse_refs(str(row.get("ref_id",""))))
        original_docs={r["ref_id"] for r in original}
        selected_docs={r["ref_id"] for r in chosen}
        if any(r["ref_id"] not in selected_docs for r in chosen):
            raise AssertionError("Citation invariant")
        from_gold=bool(refs)
        tagged=str(row.get("CrossPaper","")).casefold().strip() in ("true","1","yes","x")
        group="cross_paper" if tagged else "other"
        row_kind="routed" if routed else "default"
        for bucket in ("all",group,row_kind,group+"_"+row_kind):
            c=by_type[bucket]
            c["n"]+=1
            c["has_gold"]+=int(from_gold)
            c["routed"]+=int(routed)
            if from_gold:
                c["any_gold_original"]+=int(bool(original_docs & refs))
                c["any_gold_candidate"]+=int(bool(selected_docs & refs))
                c["all_gold_original"]+=int(refs<=original_docs)
                c["all_gold_candidate"]+=int(refs<=selected_docs)
                c["gold_sources_original"]+=len(original_docs&refs)
                c["gold_sources_candidate"]+=len(selected_docs&refs)
            c["distinct_docs_original"]+=len(original_docs)
            c["distinct_docs_candidate"]+=len(selected_docs)
        exemplar_shapes["different_page_sequence"]+=int([
            (p["ref_id"],p["page"]) for p in chosen] !=
            [(p["ref_id"],p["page"]) for p in original])
        if routed:seen_triggers["routed"]+=1
    return {
        "cohorts":{k:dict(v) for k,v in sorted(by_type.items())},
        "modified_retrieval":dict(exemplar_shapes),
        "question_routing":dict(seen_triggers),
    }


def self_test():
    examples=[
      {"ref_id":"alpha","page":1,"text":"GPU high end accelerators efficient batch",
       "url":"https://arxiv.org/abs/2601.00001"},
      {"ref_id":"alpha","page":2,"text":"GPU high end accelerators efficient batches",
       "url":"https://arxiv.org/abs/2601.00001"},
      {"ref_id":"beta","page":1,"text":"older GPU lower power drawing intertoken latency",
       "url":"https://arxiv.org/abs/2601.00002"},
      {"ref_id":"gamma","page":1,"text":"households consume electrical energy in MWh yearly",
       "url":"https://arxiv.org/abs/2601.00003"},
      {"ref_id":"delta","page":1,"text":"environmental lifecycle studies on AI energy",
       "url":"https://arxiv.org/abs/2601.00004"},
      {"ref_id":"epsilon","page":1,"text":"electricity power consumption in data centers",
       "url":"https://arxiv.org/abs/2601.00005"},
      {"ref_id":"zeta","page":1,"text":"system carbon and water accounting",
       "url":"https://arxiv.org/abs/2601.00006"},
    ]
    q="One study finds a GPU efficient while another reports lower power at strict latency"
    chosen,baseline,routed=select_pages(q,examples)
    assert routed and len(chosen)==len(baseline)==6
    assert len(set(p["ref_id"] for p in chosen))>=4
    plain="What power was reported for GPU acceleration?"
    assert not source_questions(plain)
    assert not select_pages(plain,examples)[2]
    assert "household" in " ".join(source_questions(
        "How many household-years of electricity training would consume?"))
    print("WATTBOT_MULTISOURCE_QUERY_SELF_TEST=PASS")


def run(archive):
    self_test()
    with zipfile.ZipFile(archive) as z:
        for name,sha in PINNED.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=sha:
                raise RuntimeError("Official TRAIN or scorer pin moved")
    train,sources,tests=base.pinned_data(archive)
    assert len(tests)==317 and len(train)==245 and len(sources)==122
    with tempfile.TemporaryDirectory(prefix="wattbot_sources_") as tmp:
        docs,index,manifest=base.corpus(train,sources,Path(tmp))
        if manifest["arxiv_sha256"]!=SOURCE_MANIFEST:
            raise RuntimeError("Pinned source manifest changed")
        raw=train.to_dict("records")
        dev=[x for x in raw if not is_holdout(str(x["id"]))]
        hold=[x for x in raw if is_holdout(str(x["id"]))]
        if len(dev)!=182 or len(hold)!=63:
            raise RuntimeError("Development split changed")
        result={
            "scope":"Frozen TRAIN labels scored only AFTER question-only retrieval",
            "dev":count(dev,index),
            "reused_holdout":count(hold,index),
            "pinned_source_manifest":SOURCE_MANIFEST,
            "K":K,
            "test_gold_answer_or_citations_accessed":0,
            "test_questions_scored":0,
            "boundary":"Source IDs overlap not scientific entailment. Cross-paper "
               "task flags used only to report outcomes, never to route questions. "
               "No model calls or Kaggle submission; original numeric fallback "
               "and PDF source authority unchanged."
        }
        print("WATTBOT_MULTISOURCE_QUERY_RECALL="+json.dumps(
            result,sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Provide --self-test or --official-zip")
