#!/usr/bin/env python3
"""WattBot V5: verified development lessons with V4 candidate/warrant boundary.

V4's complete source-pinned corpus, lexical ranker, six question-centered PDF
excerpts, Flash-Lite model, source quote checker, provisional answer recovery,
numeric fallback, source hash check, and CSV gate are unchanged. Only the
question text sent to the model is augmented with TWO allowed DEV TRAIN
worked examples. The original TEST question, row IDs, evidence passages and
citation checker do not see any worked-example gold as source evidence.

Evidence: first paired TRAIN qualification run 37985937618: 0.61058201 ->
0.69074074, with identical first replies and six source pages. This is a
candidate prior to an independent public Kaggle score; never conflate scopes.

No automatic Kaggle submission; running this script generates a privately
stored CSV only, after pinned input + exact byte transport gates. Conservatively
reserve every enriched prompt BEFORE each API call and fail closed on budget.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path

import full_reader as base
from holdout_probe import is_holdout
import submit_full_reader as v4
from verified_lesson import illustrate, self_test as lessons_self_test

EXPECTED_V4_GIT_BLOB="509da00a860c403c71f484de481aa4458dc0c954"
EXPECTED_LESSON_BLOB="99189ba7c9be96909279f9fc5e5590dc6f317772"
QUALIFICATION_RUN=37985937618
TRAIN_FIRST_PROVISIONAL=.61058201
TRAIN_WORKED_LESSONS=.69074074
EXPECTED_DEV=182
EXPECTED_TEST=317


def git_blob(path):
    raw=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")
                        +bytes([0])+raw).hexdigest()


def prepare_dev(train):
    required={"id","question","answer_value","answer_unit","explanation",
              "CrossPaper","Math","Quote","Figure","Table"}
    if not required.issubset(train.columns):
        raise RuntimeError("Pinned DEV example schema changed")
    rows=train.to_dict("records")
    if len(rows)!=245 or len({str(r["id"]) for r in rows})!=245:
        raise RuntimeError("Official TRAIN row identities changed")
    dev=[r for r in rows if not is_holdout(str(r["id"]))]
    if len(dev)!=EXPECTED_DEV:
        raise RuntimeError("DEV/HOLDOUT hash partition changed")
    if any(is_holdout(str(r["id"])) for r in dev):
        raise RuntimeError("Protected holdout leaked into exemplar memory")
    return dev


def build_enriched(question,passages,dev):
    if not isinstance(question,str) or not isinstance(passages,list):
        raise TypeError("Question and passages must be typed")
    if len(passages)!=base.K:
        raise RuntimeError("Requested model corpus depth changed")
    worked=illustrate(question,dev)
    # The examples are returned as a separate instruction append; the
    # preserved source texts remain byte-identical in the actual model JSON.
    enriched=question+worked
    source_slots=[{
       "source_index":i,"ref_id":p["ref_id"],"page":p["page"],
       "text":p["text"][:base.MAX_EXCERPT]}
       for i,p in enumerate(passages)]
    prompt=json.dumps({"question":enriched,"passages":source_slots},
                      ensure_ascii=False,separators=(",",":"))
    return enriched,prompt


def self_test():
    v4.self_test()
    lessons_self_test()
    assert git_blob(v4.__file__)==EXPECTED_V4_GIT_BLOB
    assert git_blob(Path(__file__).with_name("verified_lesson.py"))==EXPECTED_LESSON_BLOB
    assert (v4.EXPECTED_TEST_ROWS==EXPECTED_TEST and
            v4.MAX_API_COST_USD==.65)
    assert base.MODEL=="google/gemini-2.5-flash-lite"
    assert base.K==6 and base.MAX_EXCERPT==1100
    assert base.MAX_OUTPUT_TOKENS==650
    assert v4.REPORT_MANIFEST=="a1720d14806ff219eaac8e0e8b8a5c8d6e87f596bba1a852505374ab4343b77d"
    assert v4.ARXIV_MANIFEST=="4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"

    # Synthetic context integrity: changing only the question slot must
    # not rewrite literal scientific source bytes or ref_id/page/url.
    import pandas as pd
    # A minimal 245-row schema fixture is not needed; the dev selector is
    # independently qualified by lesson self_test and live pinned file gate.
    sample=[
      {"id":"synthetic1","question":"What total energy?","answer_value":"30",
       "answer_unit":"MWh","explanation":"12+18",
       "Math":"True","CrossPaper":"False","Table":"False",
       "Figure":"False","Quote":"False"},
      {"id":"synthetic2","question":"How much reported power?","answer_value":"20",
       "answer_unit":"MW","explanation":"source measurement",
       "Math":"False","CrossPaper":"False","Table":"False",
       "Figure":"False","Quote":"True"},
      {"id":"synthetic3","question":"Compare two studies' energy?","answer_value":"1.5",
       "answer_unit":"ratio","explanation":"30/20",
       "Math":"True","CrossPaper":"True","Table":"False",
       "Figure":"False","Quote":"False"}
    ]
    # Synthetic IDs must not pretend to be allowable holdout exemplars.
    for x in sample:
        while is_holdout(x["id"]): x["id"]+="_dev"
    pages=[{"ref_id":"ref_"+str(k),"page":k+1,
            "url":"https://arxiv.org/abs/2601.00001",
            "text":"The reported energy was "+str(k+10)+" MWh."}
           for k in range(base.K)]
    untouched=json.dumps(pages,sort_keys=True)
    question="What was the combined energy use in 2025?"
    enriched,prompt=build_enriched(question,pages,sample)
    parsed=json.loads(prompt)
    assert parsed["question"]==enriched and enriched.startswith(question)
    assert len(parsed["passages"])==6
    assert "TRAIN DEVELOPMENT ONLY" in enriched
    for i,page in enumerate(pages):
        for key in ("ref_id","page","text"):
            assert parsed["passages"][i][key]==page[key]
    assert json.dumps(pages,sort_keys=True)==untouched
    assert sum(is_holdout(row["id"]) for row in sample)==0
    print("WATTBOT_VERIFIED_LESSONS_V5_SELF_TEST=PASS")


def run(archive,out):
    self_test()
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("Missing authorized model key, no inference")
    train,metadata,tests=v4.pinned_data(archive)
    if len(tests)!=EXPECTED_TEST:
        raise RuntimeError("Protected TEST question count unexpectedly changed")
    dev=prepare_dev(train)
    # Cryptographic, content-addressed lesson memory, never log worked labels.
    ids="|".join(sorted(str(r["id"]) for r in dev))
    dev_sha=hashlib.sha256(ids.encode("utf-8")).hexdigest()
    old_reader=base.call_reader
    costs=[0.0,0.0]
    stats=Counter()

    def worked_reader(key,question,passages,price):
        enriched,prompt=build_enriched(question,passages,dev)
        reserve=base.conservative_charge(
            base.SYSTEM+prompt,price,base.MAX_OUTPUT_TOKENS)
        if costs[0]+reserve>v4.MAX_API_COST_USD:
            raise RuntimeError("Enriched V5 model cost guard would be exceeded; no release")
        answer,status,bound,actual=old_reader(
            key,enriched,passages,price)
        if abs(reserve-bound)>0.00000001:
            raise RuntimeError("Enriched prompt reserve diverges from authoritative reader")
        costs[0]+=bound
        costs[1]+=actual
        stats["model_calls"]+=1
        stats[status]+=1
        stats["total_exemplar_characters"]+=len(enriched)-len(question)
        if costs[0]>v4.MAX_API_COST_USD:
            raise RuntimeError("Conservative model budget violated")
        return answer,status,bound,actual

    try:
        base.call_reader=worked_reader
        v4.run(archive,out,policy="window")
    finally:
        base.call_reader=old_reader
    if stats["model_calls"]!=EXPECTED_TEST:
        raise RuntimeError("V5 prepared incomplete official TEST predictions")
    result={
       "status":"CANDIDATE_RELEASE_CSV_PREPARED",
       "authority":"No official Kaggle score; never call it #1",
       "train_qualification_run":QUALIFICATION_RUN,
       "train_first_provisional":TRAIN_FIRST_PROVISIONAL,
       "train_lesson_policy":TRAIN_WORKED_LESSONS,
       "same_response_train_delta":round(
           TRAIN_WORKED_LESSONS-TRAIN_FIRST_PROVISIONAL,8),
       "source_reader_parent_blob":EXPECTED_V4_GIT_BLOB,
       "lesson_compiler_blob":EXPECTED_LESSON_BLOB,
       "development_row_count":len(dev),
       "development_ids_sha256":dev_sha,
       "protected_test_rows":len(tests),
       "cost_reserved_usd":round(costs[0],7),
       "cost_reported_usd":round(costs[1],7),
       "model_stats":dict(stats),
       "boundary":"Two examples from development TRAIN only; no hidden TEST label "
          "or holdout gold in prompt. Full PDF source hash, quotation checks, "
          "provisional answer status, and all-cell Kaggle CSV validation "
          "inherited unchanged from V4. No Kaggle submission in this run.",
    }
    print("WATTBOT_VERIFIED_LESSONS_V5_ADMISSION="+json.dumps(
        result,sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip")
    p.add_argument("--out")
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip and a.out:run(a.official_zip,a.out)
    else:p.error("Use --self-test or both --official-zip and --out")
