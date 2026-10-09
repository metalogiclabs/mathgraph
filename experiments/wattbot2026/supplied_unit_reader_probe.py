#!/usr/bin/env python3
"""WattBot: use the answer_unit supplied to contestants in official TEST.

One factor changes relative to the fully-qualified 0.49708995 TRAIN holdout:
tell the SAME Flash-Lite reader which normalized output unit the official
question file already provides. Source retrieval, chunk order, 1100-char
question-centred windows, exact-quote verifier, fallback, cost cap, and official
Score.py remain identical. This is task input, not answer leakage.

TRAIN labels are used only AFTER inference by pinned Score.py. The 63-question
holdout has been inspected previously and is not independent leaderboard
evidence. No Kaggle TEST inference or Kaggle submission in this experiment.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import zipfile
import pandas as pd

import full_reader as base
from holdout_probe import is_holdout
from query_window import window_passages

BASE_BLOB="4e1350ef72a44a333862dec23c737a2262ab99bc"
EXPECTED={
 "Score.py":"e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
 "train_QA.csv":"9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
 "test_Q.csv":"26038b21cb09588a39b0e95e5516e3827dadd499c85c3792d0ea46c10ae7066a",
}
SOURCE_SHA="4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
HISTORICAL_SCORE=.49708995
HISTORICAL_RUN=37968840780
SOURCE_BUDGET=114
NO_UNIT=frozenset(("","is_blank","NA","N/A","nan","None","null"))


def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()


def question_with_unit(question, unit):
    if unit.strip().casefold() in {x.casefold() for x in NO_UNIT}:
        return question + (
          "\nOFFICIAL INPUT: answer_unit=is_blank. This does NOT imply "
          "unanswerable; categorical answers, counts and True/False may "
          "still have a definite answer_value. Respect the original question."
        )
    return question + (
      "\nOFFICIAL INPUT: target answer_unit=" + unit
      + ". Express answer_value IN THAT UNIT, converting source units with "
        "correct arithmetic when necessary. Return only the normalized "
        "number, exact term, TRUE/FALSE, or source-requested (low,high) "
        "interval; never include a unit inside answer_value. "
        "Do not invent a conversion or fact that evidence cannot support."
    )


def self_test():
    assert git_blob(Path(base.__file__).read_bytes())==BASE_BLOB
    assert base.MODEL=="google/gemini-2.5-flash-lite"
    assert base.K==6 and base.MAX_EXCERPT==1100 and base.MAX_REQUESTS==63
    q=question_with_unit("What electricity?","MWh")
    assert "target answer_unit=MWh" in q
    assert "converting source units" in q
    assert "answer_unit=is_blank" in question_with_unit("What?","is_blank")
    print("WATTBOT_SUPPLIED_UNIT_PROMPT_SELF_TEST=PASS")


def run(archive):
    self_test()
    with zipfile.ZipFile(archive) as z:
        for name,digest in EXPECTED.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=digest:
                raise RuntimeError("Official pinned dataset changed "+name)
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str})
        test=pd.read_csv(io.BytesIO(z.read("test_Q.csv")),
                         keep_default_na=False,dtype={"id":str})
    # Unit is supplied as a non-protected TEST question-side feature.
    if "answer_unit" not in test or "answer_unit" not in train:
        raise RuntimeError("Official answer_unit feature missing")
    hold=train[train["id"].map(is_holdout)].reset_index(drop=True)
    if len(hold)!=63 or len(test)!=317:
        raise RuntimeError("Frozen task/split changed")
    unit_by_question={str(item["question"]):str(item["answer_unit"])
                      for item in hold.to_dict("records")}
    if len(unit_by_question)!=63:
        raise RuntimeError("Duplicate question text would make unit mapping ambiguous")
    original_passages=base.passages_for
    original_model=base.call_reader
    summary=Counter()
    precommitted=[0.]
    def replacement_passages(question,chunks):
        original,all_hits=original_passages(question,chunks)
        windowed=window_passages(question,original,base.MAX_EXCERPT)
        summary["questions"]+=1
        summary["pages"]+=len(windowed)
        summary["shifted"]+=sum(x["excerpt_start"]>0 for x in windowed)
        for a,b in zip(original,windowed):
            for name in ("ref_id","page","url"):
                assert a[name]==b[name]
            assert b["text"]==a["text"][b["excerpt_start"]:b["excerpt_end"]]
        return windowed,all_hits
    def supplied_unit_model(key,question,passages,rate):
        if question not in unit_by_question:
            raise RuntimeError("Unexpected or unlabeled TRAIN question")
        unit=unit_by_question[question]
        enriched=question_with_unit(question,unit)
        # Conservative extra input tokens counted and guarded before API call.
        prompt=json.dumps({"question":enriched,
             "passages":[{"source_index":j,"ref_id":s["ref_id"],
                         "page":s["page"],"text":s["text"][:base.MAX_EXCERPT]}
                        for j,s in enumerate(passages)]},
            ensure_ascii=False,separators=(",",":"))
        charge=base.conservative_charge(base.SYSTEM+prompt,rate,base.MAX_OUTPUT_TOKENS)
        if precommitted[0]+charge>base.MAX_BUDGET_USD:
            raise RuntimeError("Adapted prompt exceeds frozen model budget")
        candidate,status,reserved,actual=original_model(key,enriched,passages,rate)
        precommitted[0]+=reserved
        summary["model_requests"]+=1
        summary["unit_supplied"]+=int(unit.strip().casefold() not in
                                       {x.casefold() for x in NO_UNIT})
        summary[status]+=1
        if candidate is not None and isinstance(candidate,dict):
            model_unit=str(candidate.get("answer_unit","")).casefold().strip()
            summary["model_unit_agrees"]+=int(model_unit==unit.casefold().strip())
        return candidate,status,reserved,actual
    output=io.StringIO()
    try:
        base.passages_for=replacement_passages
        base.call_reader=supplied_unit_model
        with redirect_stdout(output):
            base.run(archive)
    finally:
        base.passages_for=original_passages
        base.call_reader=original_model

    prefix="WATTBOT_FULL_READER_HOLDOUT="
    scored=[json.loads(s[len(prefix):]) for s in output.getvalue().splitlines()
            if s.startswith(prefix)]
    if len(scored)!=1:
        raise RuntimeError("Missing official TRAIN score")
    result=scored[0]
    if result["source_manifest_sha256"]!=SOURCE_SHA:
        raise RuntimeError("Pinned PDF corpus changed")
    if result["holdout_rows"]!=63 or summary["questions"]!=63:
        raise RuntimeError("Scored dataset changed")
    if precommitted[0]>base.MAX_BUDGET_USD:
        raise RuntimeError("Cost safety boundary breached")
    value=result["scores"]["reader_then_numeric_fallback"]
    print("WATTBOT_SUPPLIED_UNIT_READER_HOLDOUT="+json.dumps({
        "status":"CANDIDATE",
        "scope":"Previously inspected 63 TRAIN questions, not Kaggle TEST",
        "input_feature":"answer_unit is already provided in official TEST",
        "one_factor":"append supplied target unit to otherwise frozen model prompt",
        "model":base.MODEL,
        "score":value,
        "delta_vs_historical":round(value-HISTORICAL_SCORE,8),
        "historical_comparator":HISTORICAL_SCORE,
        "historical_run":HISTORICAL_RUN,
        "same_run_paired_control":False,
        "scores":result["scores"],
        "outcomes":result["outcomes"],
        "model_and_unit_audit":dict(summary),
        "pinned_corpus_sha256":SOURCE_SHA,
        "reserved_usd":result["max_reserved_usd"],
        "observed_api_usd":result["observed_api_usd"],
        "boundary":"No test labels or submissions; source quote checks do not imply "
                   "scientific entailment, numeric answers remain candidates."
    },sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Specify --self-test or --official-zip")
