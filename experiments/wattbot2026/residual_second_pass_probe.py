#!/usr/bin/env python3
"""WattBot: one extra source-reading attempt only after certified quote failure.

Change the minimum consequential part of the six-excerpt Flash-Lite pipeline:
when a first-pass model answer is rejected because its quotation cannot be
verified, expand to TEN independently indexed source-page excerpts and ask
the same model once more. A second answer is admitted only if the ORIGINAL
independent exact-page verifier accepts its evidence. Otherwise preserve
numeric fallback, never silently relabel unverified evidence.

Paired TRAIN test: first-pass model outputs are identical in baseline and
rescue arms. Only the rescue arm spends extra model calls. Official Score.py
is applied after all answers freeze. This is a reused 63-row TRAIN holdout,
not an independent Kaggle score or scientific entailment proof.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import zipfile

import pandas as pd

import full_reader as base
from holdout_probe import is_holdout
from query_window import window_passages
from score_ablation import load_score

READER_BLOB="4e1350ef72a44a333862dec23c737a2262ab99bc"
SOURCE_SHA="4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
PINNED={
 "Score.py":"e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
 "train_QA.csv":"9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
 "metadata.csv":"b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1"
}
RECOVERABLE=frozenset(("QUOTATION_NOT_ANCHORED","QUOTATION_TOO_SHORT",
                       "PAGE_CHECK_REJECTED","MISSING_SOURCE_INDEX"))
SECONDARY_MAX_RESERVED=.16
SECONDARY_PASSAGES=10
COMPARATOR_RUN=37968840780

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()


def self_test():
    assert git_blob(Path(base.__file__).read_bytes())==READER_BLOB
    assert base.K==6 and base.MAX_EXCERPT==1100
    assert base.MAX_REQUESTS==63 and base.MAX_BUDGET_USD==.12
    assert base.MODEL=="google/gemini-2.5-flash-lite"
    sample=[
      {"ref_id":"d"+str(i),"page":i+1,"url":"https://arxiv.org/abs/2601.00001",
       "text":"context "*250+"energy consumption was 23.7 MWh"}
      for i in range(12)]
    selected=window_passages("What was energy consumption?",sample[:10],1100)
    assert len(selected)==10
    for a,b in zip(sample,selected):
        assert all(a[k]==b[k] for k in ("ref_id","page","url"))
        assert b["text"]==a["text"][b["excerpt_start"]:b["excerpt_end"]]
        assert len(b["text"])<=1100
    assert "MODEL_ABSTAINED" not in RECOVERABLE
    print("WATTBOT_SECOND_PASS_SELF_TEST=PASS")


def run(official_zip):
    self_test()
    with zipfile.ZipFile(official_zip) as z:
        for f,h in PINNED.items():
            if hashlib.sha256(z.read(f)).hexdigest()!=h:
                raise RuntimeError("Official input changed: "+f)
    key=os.environ.get("OPENROUTER_API_KEY","")
    if not key:raise RuntimeError("Missing bounded model key")
    rate=base.verify_price_ceiling()

    original_passages=base.passages_for
    original_checker=base.try_checked
    original_numeric=base.build_candidate
    first_checked={}
    numeric={}
    ranked_map={}
    stats=Counter()
    cost=[0.0,0.0]
    def windowed(question,index):
        pages,allhits=original_passages(question,index)
        focus=window_passages(question,pages,base.MAX_EXCERPT)
        ranked_map[question]=allhits
        stats["questions"]+=1
        stats["first_pass_pages"]+=len(focus)
        return focus,allhits
    def numeric_capture(question,hits,docs):
        candidate=original_numeric(question,hits,docs)
        if question["id"] not in numeric:
            numeric[question["id"]]=candidate
        return candidate
    def checked_then_rescue(generated,question,passages,docs):
        first,reason=original_checker(generated,question,passages,docs)
        first_checked[question["id"]]=(first,reason)
        stats["original_"+reason]+=1
        if first is not None or reason not in RECOVERABLE:
            return first,reason
        # Certified residual: the reported quotation does not anchor to any
        # authorized source page. The previous answer remains an unverified
        # candidate, not a false mathematical statement.
        full=ranked_map.get(question["question"],[])
        original_pages=[x for x in full if x["page"]>0][:SECONDARY_PASSAGES]
        if len(original_pages)!=SECONDARY_PASSAGES:
            stats["INSUFFICIENT_ADDITIONAL_SOURCE_PAGES"]+=1
            return first,reason
        expanded=window_passages(question["question"],original_pages,base.MAX_EXCERPT)
        assert len(expanded)==SECONDARY_PASSAGES
        prior_value=str(generated.get("answer_value","is_blank"))
        prompt=(question["question"]+"\nThe previous answer_value candidate was "
                +prior_value+
                ", but its claimed quotation was not found verbatim in the "
                "six cited excerpts. Treat that answer as UNVERIFIED, not "
                "as a fact. Re-examine these ten independently retrieved "
                "source passages. Return a corrected value and a verbatim "
                "supporting quotation with its matching source_index. "
                "If no source supports a value, return is_blank.")
        context=json.dumps({"question":prompt,"passages":[
              {"source_index":i,"ref_id":p["ref_id"],"page":p["page"],
               "text":p["text"][:base.MAX_EXCERPT]}
               for i,p in enumerate(expanded)]},separators=(",",":"),
               ensure_ascii=False)
        reserve=base.conservative_charge(base.SYSTEM+context,rate,
                                         base.MAX_OUTPUT_TOKENS)
        if cost[0]+reserve>SECONDARY_MAX_RESERVED:
            stats["SECOND_PASS_BUDGET_CAP"]+=1
            return first,reason
        candidate,status,bound,reported=base.call_reader(key,prompt,expanded,rate)
        cost[0]+=bound
        cost[1]+=reported
        stats["second_"+status]+=1
        if status!="OK":
            return first,reason
        checked,status2=original_checker(candidate,question,expanded,docs)
        stats["second_"+status2]+=1
        if checked is None:
            return first,reason
        # The existing source-page quote verifier, not the model, is the
        # admission authority. Scientific entailment remains unproved.
        checked["explanation"]=(
           "Second-pass answer with independently anchored exact source-page "
           "quotation; scientific entailment is still a candidate.")
        return checked,"PAGE_QUOTE_VERIFIED_SECOND_PASS"

    stdout=io.StringIO()
    try:
        base.passages_for=windowed
        base.try_checked=checked_then_rescue
        base.build_candidate=numeric_capture
        with redirect_stdout(stdout):
            base.run(official_zip)
    finally:
        base.passages_for=original_passages
        base.try_checked=original_checker
        base.build_candidate=original_numeric
    marker="WATTBOT_FULL_READER_HOLDOUT="
    rows=[json.loads(s[len(marker):]) for s in stdout.getvalue().splitlines()
          if s.startswith(marker)]
    if len(rows)!=1:
        raise RuntimeError("No complete protected TRAIN scoring result")
    score=rows[0]
    if score["holdout_rows"]!=63 or score["source_manifest_sha256"]!=SOURCE_SHA:
        raise RuntimeError("Source/heldout data changed")
    if stats["questions"]!=63 or len(numeric)!=63:
        raise RuntimeError("Partial primary evaluator")
    if cost[0]>SECONDARY_MAX_RESERVED:
        raise RuntimeError("Secondary budget exceeded")

    with zipfile.ZipFile(official_zip) as z:
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
             dtype={"id":str},keep_default_na=False)
        hold=train[train["id"].map(is_holdout)].reset_index(drop=True)
        blank=base.blank_submission(hold).reset_index(drop=True)
        baseline=[]
        for _,item in blank.iterrows():
            source_id=str(item["id"])
            verified,_=first_checked.get(source_id,(None,"FIRST_PASS_NOT_CHECKED"))
            baseline.append(dict(verified) if verified is not None else numeric[source_id])
        with tempfile.TemporaryDirectory(prefix="wattbot_rescue_score_") as temp:
            scorer=load_score(z,temp)
            frame=pd.DataFrame(baseline,columns=list(blank.columns))
            initial=round(float(scorer(hold.copy(deep=True),frame,
                 row_id_column_name="id",verbose=False)),8)
    improved=score["scores"]["reader_then_numeric_fallback"]
    print("WATTBOT_RESIDUAL_SECOND_PASS="+json.dumps({
       "scope":"Same original 63 TRAIN first-pass responses; official pinned scorer",
       "baseline_same_run":initial,
       "second_pass_qualified":improved,
       "same_run_gain":round(improved-initial,8),
       "primary_model":"google/gemini-2.5-flash-lite",
       "intervention":"Only source quote failures receive a second K10 source view",
       "historical_unpaired_run":COMPARATOR_RUN,
       "counters":dict(stats),"baseline_outcomes":score["outcomes"],
       "secondary_reserved_usd":round(cost[0],7),
       "secondary_reported_usd":round(cost[1],7),
       "primary_reported_usd":score["observed_api_usd"],
       "source_manifest_sha256":SOURCE_SHA,
       "boundary":"Quotation presence is independently verified; semantic entailment "
                  "is UNKNOWN. Existing correct admissions preserved; no "
                  "protected TEST labels or Kaggle submission.",
    },sort_keys=True),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Specify --self-test or --official-zip")
