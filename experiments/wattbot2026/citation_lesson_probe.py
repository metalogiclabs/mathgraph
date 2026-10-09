#!/usr/bin/env python3
"""WattBot source-capability compiler, development labels isolated from targets.

Learn reusable question->source patterns from 182 labeled DEVELOPMENT rows.
Source IDs are training labels for retrieval only, never answer values or PDF
quotations. For each development evaluation target, leave that exact question
and answer/citation row out of the exemplar universe; freeze policy selection
using development leave-one-out coverage, then inspect the already-reused
63-question holdout ONCE as a diagnostic. Nothing uses hidden TEST answers.

The representation is a query feature quotient: two questions may reuse a
source relationship if their weighted lexical features remain sufficiently
similar. A learned source is still a candidate, not a verified consequence,
and must point to a real page of a pinned document. Same six source pages
budget; no model calls or Kaggle submission.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import math
from pathlib import Path
import tempfile
import zipfile

import pandas as pd

from holdout_probe import is_holdout
from train_probe import parse_refs
from source_refinement_probe import FrozenBM25
import submit_full_reader as source
from wattbot import ranked, tokens

PIN = {
    "train_QA.csv":"9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
    "metadata.csv":"b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1",
    "Score.py":"e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
}
ARXIV_DIGEST="4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
STOP=set(("what when where how much many who which is was were did does do "
          "a an the of in from for on to with and or by as at this that its "
          "according report reports study studies paper papers data results result "
          "model models calculated calculation give using use their one two "
          "across compare compared difference between both according to how "
          "reported values value").split())
K=6
NEIGHBOURS=8
LEARNED_POLICIES={
  "legacy":(0,1.,0),
  "one_weak":(1,.13,4),
  "one_medium":(1,.22,4),
  "one_strong":(1,.34,4),
  "two_medium":(2,.22,3),
  "two_strong":(2,.34,3),
}
MULTISOURCE_TERMS=set(("compare comparing comparison versus vs both two another "
                      "between different multiple together across reconcile "
                      "reconciliation difference relative").split())


def words(text):
    return [t for t in tokens(str(text)) if t not in STOP and len(t)>=3]


def query_features(q):
    w=words(q)
    f=Counter("w:"+t for t in w)
    f.update("b:"+a+"_"+b for a,b in zip(w,w[1:]))
    return f


class SourceLessons:
    """Small, finite training-only query feature/source relation."""
    def __init__(self, training):
        self.examples=[]
        for row in training:
            refs=tuple(dict.fromkeys(parse_refs(str(row.get("ref_id","")))))
            if not refs:continue
            feats=query_features(row["question"])
            if not feats:continue
            self.examples.append((str(row["id"]),str(row["question"]),refs,feats))
        n=max(1,len(self.examples))
        df=Counter()
        for _,_,_,feat in self.examples:
            df.update(feat.keys())
        self.idf={t:math.log(1+(n-d+.5)/(d+.5))
                  for t,d in df.items()}
        self.index=[]
        self.source_occurrences=Counter()
        for id_,q,refs,feat in self.examples:
            weighted={t:(1+math.log(tf))*self.idf[t] for t,tf in feat.items()}
            length=math.sqrt(sum(x*x for x in weighted.values()))
            if length:
                self.index.append((id_,q,refs,weighted,length))
                self.source_occurrences.update(set(refs))

    def infer(self,q,forbidden_id=None):
        f=query_features(q)
        weights={t:(1+math.log(tf))*self.idf[t]
                 for t,tf in f.items() if t in self.idf}
        size=math.sqrt(sum(x*x for x in weights.values()))
        if not size or not self.index:
            return [],0.,0
        neighbours=[]
        qnorm=" ".join(str(q).casefold().split())
        for ident,old,refs,weighted,norm in self.index:
            if ident==forbidden_id:
                continue
            if " ".join(old.casefold().split())==qnorm:
                # Even a different row with identical question cannot
                # act as a source label oracle for a developmental target.
                continue
            sim=sum(v*weighted.get(t,0) for t,v in weights.items())/(size*norm)
            if sim>0:
                neighbours.append((sim,ident,refs))
        neighbours.sort(key=lambda x:(-x[0],x[1]))
        top=neighbours[:NEIGHBOURS]
        scores=defaultdict(float)
        for rank,(similarity,ident,refs) in enumerate(top):
            strength=similarity**2.0/(1+.12*rank)
            for ref in refs:
                # Gentle frequency correction prevents popular references
                # from overwhelming distinctive question/source relationships.
                prior=1/math.sqrt(1+math.log1p(self.source_occurrences[ref]))
                scores[ref]+=strength*prior
        predicted=sorted(scores,key=lambda ref:(-scores[ref],ref))
        return predicted,(top[0][0] if top else 0.),len(top)


def pick(question, hits, lessons, policy, forbidden_id=None):
    original=[x for x in hits if x["page"]>0][:K]
    if len(original)!=K:
        raise RuntimeError("Source corpus cannot supply frozen K6 pages")
    if policy=="legacy":
        return original,False,0.,0
    slots,threshold,kept=LEARNED_POLICIES[policy]
    proposed,confidence,nn=lessons.infer(question,forbidden_id)
    if confidence<threshold or not proposed:
        return original,False,confidence,nn
    present={x["ref_id"] for x in original}
    best_by_source={}
    for hit in hits:
        if hit["page"]>0 and hit["ref_id"] not in best_by_source:
            best_by_source[hit["ref_id"]]=hit
    newcomers=[]
    for ref in proposed:
        if ref in present or ref not in best_by_source:
            continue
        source_hit=best_by_source[ref]
        # Avoid inserting a page with no lexical relevance merely because
        # a frequent development source happened to be labeled nearby.
        if source_hit["score"]<=0:
            continue
        newcomers.append(source_hit)
        if len(newcomers)>=slots:
            break
    if not newcomers:
        return original,False,confidence,nn
    chosen=[]
    fingerprints=set()
    def add(p):
        mark=(p["ref_id"],p["page"],p["text"][:100])
        if mark not in fingerprints:
            chosen.append(p)
            fingerprints.add(mark)
    for p in original[:kept]:
        add(p)
    for p in newcomers:
        add(p)
    for p in original[kept:]:
        if len(chosen)==K:break
        add(p)
    if len(chosen)!=K:
        raise RuntimeError("Cannot preserve six-page model budget")
    changed=any((a["ref_id"],a["page"],a["text"][:100]) !=
                (b["ref_id"],b["page"],b["text"][:100])
                for a,b in zip(original,chosen))
    return chosen,changed,confidence,nn


def summarize(rows,learners,source_index,policies,development_loo=False):
    totals={name:Counter() for name in policies}
    subgroups={name:defaultdict(Counter) for name in policies}
    for row in rows:
        question=str(row["question"])
        query_id=str(row["id"]) if development_loo else None
        # All-page rank is computed ONCE using fixed corpus facts, before
        # any training gold references for the evaluated question are read.
        hits=source_index.ranked(question,len(source_index.chunks))
        relevant=[h for h in hits if h["page"]>0]
        baseline=relevant[:K]
        if len(baseline)!=K:
            raise RuntimeError("Insufficient question evidence pages")
        refs=set(parse_refs(str(row["ref_id"])))
        group=("multi" if len(refs)>1 else "single" if len(refs)==1 else "NA")
        cross=("cross" if str(row.get("CrossPaper","")).casefold() in
               ("true","yes","1","x") else "other")
        for policy in policies:
            pages,changed,conf,nns=pick(question,hits,learners,policy,query_id)
            chosen={p["ref_id"] for p in pages}
            baseline_ids={p["ref_id"] for p in baseline}
            c=totals[policy]
            c["n"]+=1
            c["changed"]+=int(changed)
            c["source_count"]+=len(chosen)
            c["predicted_examples_available"]+=int(nns>0)
            c["learned_confident"]+=int(conf>=LEARNED_POLICIES[policy][1]
                                       if policy!="legacy" else False)
            if not refs:
                c["NA"]+=1
                continue
            c["gold_n"]+=len(refs)
            c["reference_hits"]+=len(refs&chosen)
            c["baseline_reference_hits"]+=len(refs&baseline_ids)
            c["all_gold"]+=int(refs<=chosen)
            c["baseline_all_gold"]+=int(refs<=baseline_ids)
            c["any_gold"]+=int(bool(refs&chosen))
            c["baseline_any_gold"]+=int(bool(refs&baseline_ids))
            if changed:
                c["changed_gain_gold_refs"]+=len(refs&chosen)-len(refs&baseline_ids)
                c["changed_gain_full_gold"]+=int(refs<=chosen)-int(refs<=baseline_ids)
            for g in (group,cross):
                gc=subgroups[policy][g]
                gc["n"]+=1
                gc["all_gold"]+=int(refs<=chosen)
                gc["baseline_all_gold"]+=int(refs<=baseline_ids)
                gc["gold_n"]+=len(refs)
                gc["reference_hits"]+=len(refs&chosen)
    result={}
    for p,c in totals.items():
        sub={key:dict(value) for key,value in subgroups[p].items()}
        result[p]={"totals":dict(c),"by_source_count_and_type":sub}
    return result


def decide(results):
    # Predeclared dev-LOO objective. More complete answerable source sets
    # outweigh partial gains; ties prefer fewer differences from verified
    # lexical ranker, never arbitrary higher model complexity.
    def objective(policy):
        d=results[policy]["totals"]
        return (d["all_gold"],d["reference_hits"],
                -max(0,d["changed"]),-list(LEARNED_POLICIES).index(policy))
    return max(LEARNED_POLICIES,key=objective)


def self_test():
    dev=[
        {"id":"d1","question":"solar photovoltaics electric power greenhouse gases",
         "ref_id":"['solar']"},
        {"id":"d2","question":"solar photovoltaic energy consumption",
         "ref_id":"['solar']"},
        {"id":"d3","question":"wind turbine production annual power",
         "ref_id":"['wind']"},
        {"id":"d4","question":"water desalination efficiency power",
         "ref_id":"['water']"},
    ]
    lesson=SourceLessons(dev)
    sources,conf,count=lesson.infer("solar photovoltaic electricity")
    assert sources and sources[0]=="solar" and count>0 and conf>0
    src,conf,count=lesson.infer("solar photovoltaic electricity",forbidden_id="d1")
    assert "solar" in src and count>0
    sample=[
        {"ref_id":"wind","page":1,"text":"solar photovoltaic wind turbine power study",
         "url":"https://arxiv.org/abs/2601.00001","score":9.0},
        {"ref_id":"wind","page":2,"text":"photovoltaic power turbine energy",
         "url":"https://arxiv.org/abs/2601.00001","score":8.0},
        {"ref_id":"wind","page":3,"text":"photovoltaic power field",
         "url":"https://arxiv.org/abs/2601.00001","score":7.0},
        {"ref_id":"wind","page":4,"text":"solar power field",
         "url":"https://arxiv.org/abs/2601.00001","score":6.0},
        {"ref_id":"wind","page":5,"text":"photovoltaic power dataset",
         "url":"https://arxiv.org/abs/2601.00001","score":5.0},
        {"ref_id":"wind","page":6,"text":"photovoltaic wind performance",
         "url":"https://arxiv.org/abs/2601.00001","score":4.0},
        {"ref_id":"solar","page":1,"text":"solar photovoltaic energy experiment",
         "url":"https://arxiv.org/abs/2601.00002","score":3.0},
    ]
    chosen,changed,_,_=pick("solar photovoltaic electricity",sample,lesson,
                             "one_weak")
    assert changed and len(chosen)==6
    assert chosen[-2]["ref_id"]=="solar",chosen
    assert len([p for p in chosen if p["ref_id"]=="solar"])==1
    original,changed,_,_=pick("wind speed high power",sample,lesson,"legacy")
    assert not changed and len(original)==6
    print("WATTBOT_CITATION_LESSON_SELF_TEST=PASS")


def run(official_zip):
    self_test()
    with zipfile.ZipFile(official_zip) as archive:
        for name,digest in PIN.items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=digest:
                raise RuntimeError("Pinned official source/scorer changed")
    train,sources,tests=source.pinned_data(official_zip)
    dev=train[~train["id"].map(is_holdout)].copy()
    hold=train[train["id"].map(is_holdout)].copy()
    if len(dev)!=182 or len(hold)!=63 or len(tests)!=317:
        raise RuntimeError("Question scope changed")
    rawdev=dev.to_dict("records")
    rawhold=hold.to_dict("records")
    with tempfile.TemporaryDirectory(prefix="wattbot_citation_lessons_") as td:
        docs,index,manifest=source.corpus(train,sources,Path(td))
        if manifest["arxiv_sha256"]!=ARXIV_DIGEST:
            raise RuntimeError("Original source manifest changed")
        cache=FrozenBM25(index)
        # Every dev target is excluded from supervised source-example
        # training when it is evaluated. Its labels are consulted only in
        # the AFTER-THE-FACT recall evaluator.
        loo={}
        lesson_all=SourceLessons(rawdev)
        policy_names=tuple(LEARNED_POLICIES)
        for candidate in policy_names:
            loo[candidate]={"totals":Counter(),"by_source_count_and_type":defaultdict(Counter)}
        # Build a separate source-only lesson model per development target.
        # This costs no LLM calls and prevents accidental target citation
        # memorization, even if the source feature vector is similar.
        for row in rawdev:
            other=[x for x in rawdev if str(x["id"])!=str(row["id"])]
            model=SourceLessons(other)
            score=summarize([row],model,cache,policy_names,development_loo=True)
            for name,cohort in score.items():
                loo[name]["totals"].update(cohort["totals"])
                for k,v in cohort["by_source_count_and_type"].items():
                    loo[name]["by_source_count_and_type"][k].update(v)
        dev_results={p:{"totals":dict(v["totals"]),
                        "by_source_count_and_type":{
                            g:dict(c) for g,c in v["by_source_count_and_type"].items()}}
                     for p,v in loo.items()}
        selected=decide(dev_results)
        # Policy selected only by LOO development source coverage BEFORE
        # the heldout labels are consulted.
        hold_scores=summarize(rawhold,lesson_all,cache,(selected,"legacy"))
    b=hold_scores["legacy"]["totals"]
    a=hold_scores[selected]["totals"]
    out={
        "authority":"TRAIN dev source labels learned, dev LOO selected policy, "
                    "official 63 reused TRAIN holdout assessed after selection",
        "pinned_arxiv_sha256":ARXIV_DIGEST,
        "source_page_chunks":manifest["source_page_chunks"],
        "dev_rows":len(dev),"holdout_rows":len(hold),
        "trained_source_patterns":len(lesson_all.index),
        "selected_policy":selected,
        "dev_leave_one_out":dev_results,
        "holdout_score":hold_scores,
        "holdout_delta":{
            "all_required_gold_sources":a["all_gold"]-b["all_gold"],
            "individual_gold_reference_hits":a["reference_hits"]-b["reference_hits"],
            "promoted_pages":a["changed"],
        },
        "scope":"Source-ID coverage only, not a scored scientific answer or Kaggle submission",
        "boundary":"Development TRAIN gold source IDs used solely to compile"
                   "source retrieval lessons, never target answer/source in LOO "
                   "or heldout model prompts. Reused 63 TRAIN holdout not pristine. "
                   "Exact document page quotation still requires independent "
                   "source verification; source-ID inclusion is NOT entailment. "
                   "Protected TEST answer/citation labels never read."
    }
    print("WATTBOT_SOURCE_LESSON_COMPILER="+json.dumps(out,sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    args=p.parse_args()
    if args.self_test:self_test()
    elif args.official_zip:run(args.official_zip)
    else:p.error("Provide --self-test or --official-zip")
