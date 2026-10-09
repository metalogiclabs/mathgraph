#!/usr/bin/env python3
"""V5 WattBot compiled-development-lesson candidate on frozen 122-source registry.

Exactly the qualified K6 1100-character question-centred source evidence and
Flash-Lite model used by V4. The ONLY generative difference is a deterministic
two-example formatting/scientific-derivation lesson compiled from 182 official
TRAIN development rows; the held-out 63 TRAIN questions and all protected
TEST answers/citations are excluded. No target labels enter selection.

The independently verified page quotations and provisional answer/source
proposals remain separate epistemic states. All 317 Kaggle TEST questions
pass the independent all-column null transport gate BEFORE any submission.

This generator does not submit to Kaggle and never publishes raw question,
PDF or generated-answer artifacts. Run the separate explicitly dispatched
release gate only after a clean preflight and quota check.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile

import full_reader as base
import submit_full_reader as v4
from holdout_probe import is_holdout
from verified_lesson import illustrate, self_test as lessons_self_test

READER_BLOB="4e1350ef72a44a333862dec23c737a2262ab99bc"
LESSON_BLOB="99189ba7c9be96909279f9fc5e5590dc6f317772"
V4_GENERATOR_BLOB="509da00a860c403c71f484de481aa4458dc0c954"
MAX_TOTAL_RESERVED_USD=.75
MAX_EVALUATION_ROWS=317


def git_blob(path):
    raw=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()


def self_test():
    lessons_self_test()
    v4.self_test()
    assert base.MODEL=="google/gemini-2.5-flash-lite"
    assert base.K==6 and base.MAX_EXCERPT==1100
    assert git_blob(base.__file__)==READER_BLOB
    assert git_blob(Path(__file__).with_name("verified_lesson.py"))==LESSON_BLOB
    assert git_blob(v4.__file__)==V4_GENERATOR_BLOB
    assert MAX_TOTAL_RESERVED_USD>.337436
    assert MAX_TOTAL_RESERVED_USD<1.
    print("WATTBOT_V5_VERIFIED_LESSON_SELF_TEST=PASS",flush=True)


def inspect_official_questions(archive):
    # The pin/hash authority is owned by the already-qualified V4 generator.
    train,sources,tests=v4.pinned_data(archive)
    if len(sources)!=122 or len(tests)!=MAX_EVALUATION_ROWS:
        raise RuntimeError("Pinned official source or TEST cohort changed")
    rows=[row for row in train.to_dict("records")
          if not is_holdout(str(row["id"]))]
    if len(rows)!=182:
        raise RuntimeError("TRAIN development source count changed")
    if any(is_holdout(str(row["id"])) for row in rows):
        raise RuntimeError("Protected 63-row holdout entered example bank")
    # Only question-side information from TEST is read; no hidden answers or
    # citations can be obtained by this path.
    questions=tests["question"].astype(str).tolist()
    if len(questions)!=MAX_EVALUATION_ROWS:
        raise RuntimeError("Incomplete official TEST questions")
    lengths=[]
    for question in questions:
        block=illustrate(question,rows)
        if "TRAIN DEVELOPMENT ONLY" not in block or "NOT evidence" not in block:
            raise RuntimeError("Worked-examples epistemic separation missing")
        if len(block)>3200:
            raise RuntimeError("Unexpected lesson expansion size")
        lengths.append(len(block))
    print("WATTBOT_V5_LESSON_PREFLIGHT="+json.dumps({
        "scope":"Development TRAIN examples and official TEST question-side text only",
        "official_test_question_count":len(questions),
        "example_bank_rows":len(rows),
        "max_illustration_characters":max(lengths),
        "mean_illustration_characters":round(sum(lengths)/len(lengths),1),
        "source_budget":base.SOURCE_BUDGET,
        "policy":"Two development-only examples; no target answers, labels or citations",
        "protected_TEST_answer_labels_read":0,
        "protected_TEST_citation_labels_read":0,
        "authority":"Pinned corpus and official V4 CSV release gate, not a score claim",
    },sort_keys=True),flush=True)
    return rows


def run(archive,out):
    self_test()
    examples=inspect_official_questions(archive)
    # Ensure original V4 preflight and exact-source quote validator run unchanged.
    previous_model=base.call_reader
    previous_budget=v4.MAX_API_COST_USD
    counters=Counter()
    reserve=[0.,0.]
    def learned_reader(key,question,passages,rate):
        if len(passages)!=base.K:
            raise RuntimeError("Reader source-page budget changed")
        enriched=question+illustrate(question,examples)
        prompt=json.dumps({
            "question":enriched,
            "passages":[{"source_index":i,"ref_id":p["ref_id"],
                "page":p["page"],"text":p["text"][:base.MAX_EXCERPT]}
                for i,p in enumerate(passages)]},
            ensure_ascii=False,separators=(",",":"))
        charge=base.conservative_charge(
            base.SYSTEM+prompt,rate,base.MAX_OUTPUT_TOKENS)
        if reserve[0]+charge>MAX_TOTAL_RESERVED_USD:
            raise RuntimeError("Conservative model price budget exceeded before call")
        response,status,bound,observed=previous_model(
            key,enriched,passages,rate)
        if abs(bound-charge)>1e-9:
            raise RuntimeError("Model charge differs from independently calculated reservation")
        reserve[0]+=bound
        reserve[1]+=observed
        counters["requests"]+=1
        counters[status]+=1
        return response,status,bound,observed
    try:
        base.call_reader=learned_reader
        v4.MAX_API_COST_USD=MAX_TOTAL_RESERVED_USD
        # Previously qualified V4 source/quote/provisional-value and CSV
        # transport logic; no protected TEST labels or output publication.
        v4.run(archive,out,policy="window")
    finally:
        base.call_reader=previous_model
        v4.MAX_API_COST_USD=previous_budget
    if counters["requests"]!=MAX_EVALUATION_ROWS:
        raise RuntimeError("Incomplete 317-row model qualification")
    if reserve[0]>MAX_TOTAL_RESERVED_USD:
        raise RuntimeError("Exceeded the source-model spending ceiling")
    print("WATTBOT_V5_VERIFIED_LESSON_TEST_READY="+json.dumps({
        "status":"TRANSPORT_QUALIFIED_ONLY",
        "inference":dict(counters),
        "reserve_ceiling_usd":MAX_TOTAL_RESERVED_USD,
        "reservation_usd":round(reserve[0],7),
        "reported_model_usd":round(reserve[1],7),
        "scoped_rows":MAX_EVALUATION_ROWS,
        "source_reader_blob":READER_BLOB,
        "lesson_source_blob":LESSON_BLOB,
        "v4_generator_blob":V4_GENERATOR_BLOB,
        "qualifying_train_run":37985937618,
        "same_response_train_score_candidate":.69074074,
        "Kaggle_TEST_score":"UNKNOWN (no Kaggle submission)",
        "science_boundary":"Exact page quotations retain independently checked provenance. "
          "All model answer values remain scientific candidates. No trained "
          "lesson comes from target holdout or protected TEST answers.",
    },sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--preflight-official-zip")
    p.add_argument("--official-zip")
    p.add_argument("--out")
    a=p.parse_args()
    if a.self_test:
        self_test()
    elif a.preflight_official_zip:
        self_test()
        inspect_official_questions(a.preflight_official_zip)
    elif a.official_zip and a.out:
        run(a.official_zip,a.out)
    else:
        p.error("Supply --self-test, --preflight-official-zip or "
                "--official-zip and --out")
