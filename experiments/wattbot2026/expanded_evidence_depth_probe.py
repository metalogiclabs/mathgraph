#!/usr/bin/env python3
"""WattBot: single-factor expanded evidence depth on pinned TRAIN holdout.

Compare K=10 page excerpts with prior K=6 window reader, retaining all other
grounded reader policies, corpus PDF hashes, model, scorer and numeric fallback.
This is a historical non-paired LLM comparator; never claim leaderboard gain
from a training score. Test labels and source ids are not injected into prompts.
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

import full_reader as base
from query_window import window_passages

SOURCE_BLOB = "4e1350ef72a44a333862dec23c737a2262ab99bc"
OFFICIAL_PINS = {
  "Score.py":"e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
  "train_QA.csv":"9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
  "metadata.csv":"b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1",
}
CORPUS_PIN = "4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
K_NEW=10
MAX_RESERVE=.25
PREVIOUS_SCORE=.49708995
PREVIOUS_RUN=37968840780

def git_blob(path):
    data=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+bytes([0])+data).hexdigest()

def self_test():
    assert git_blob(base.__file__)==SOURCE_BLOB
    assert base.K==6 and base.MAX_EXCERPT==1100
    assert base.SOURCE_BUDGET==114 and base.MAX_BUDGET_USD==.12
    assert base.MODEL=="google/gemini-2.5-flash-lite"
    p={"ref_id":"a","page":1,"url":"https://arxiv.org/abs/2601.00001",
       "text":"old "*320+"The query-specific energy consumption was 129 MWh."}
    q=window_passages("energy consumption", [p], 1100)
    assert "129 MWh" in q[0]["text"]
    assert q[0]["text"]==p["text"][q[0]["excerpt_start"]:q[0]["excerpt_end"]]
    print("WATTBOT_EVIDENCE_DEPTH_SELF_TEST=PASS")

def run(official_zip):
    self_test()
    with zipfile.ZipFile(official_zip) as z:
        for name,sha in OFFICIAL_PINS.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=sha:
                raise RuntimeError("Pinned official corpus changed: "+name)
    before=base.passages_for
    oldk=base.K
    oldbudget=base.MAX_BUDGET_USD
    trace=Counter()
    def expanded(question,all_chunks):
        original,all_hits=before(question,all_chunks)
        selected=window_passages(question,original,base.MAX_EXCERPT)
        assert len(selected)==K_NEW
        trace["questions"]+=1
        trace["pages"]+=len(selected)
        trace["distinct_sources"]+=len({p["ref_id"] for p in selected})
        trace["windows_shifted"]+=sum(p["excerpt_start"]!=0 for p in selected)
        for a,b in zip(original,selected):
            assert (a["ref_id"],a["page"],a["url"]) == (
                b["ref_id"],b["page"],b["url"])
            assert b["text"]==a["text"][b["excerpt_start"]:b["excerpt_end"]]
        return selected,all_hits
    data=io.StringIO()
    try:
        base.K=K_NEW
        base.MAX_BUDGET_USD=MAX_RESERVE
        base.passages_for=expanded
        with redirect_stdout(data):
            base.run(official_zip)
    finally:
        base.passages_for=before
        base.K=oldk
        base.MAX_BUDGET_USD=oldbudget
    marker="WATTBOT_FULL_READER_HOLDOUT="
    results=[json.loads(line.split(marker,1)[1]) for line in data.getvalue().splitlines()
             if line.startswith(marker)]
    if len(results)!=1:
        raise RuntimeError("One exact official scorer outcome required")
    result=results[0]
    if result["source_manifest_sha256"]!=CORPUS_PIN:
        raise RuntimeError("Pinned PDF evidence changed")
    if result["holdout_rows"]!=63 or trace["questions"]!=63:
        raise RuntimeError("TRAIN holdout changed")
    if result["max_reserved_usd"]>MAX_RESERVE:
        raise RuntimeError("Cost cap breached")
    value=result["scores"]["reader_then_numeric_fallback"]
    print("WATTBOT_EXPANDED_DEPTH_QUALIFICATION="+json.dumps({
       "scope":"Previously inspected frozen 63 TRAIN, official pinned scorer; no TEST",
       "intervention":"K 6 to 10 page excerpts ONLY",
       "comparison_run":PREVIOUS_RUN,"comparison_historical":PREVIOUS_SCORE,
       "historical_difference":round(value-PREVIOUS_SCORE,8),
       "paired_model_responses":False,
       "model":base.MODEL,"full_corpus_manifest":CORPUS_PIN,
       "scores":result["scores"],
       "outcomes":result["outcomes"],
       "retrieval_metrics":dict(trace),
       "conservative_reserve":result["max_reserved_usd"],
       "observed_cost_usd":result["observed_api_usd"],
       "boundary":"Exact source quotations are provenance only; no scientific entailment, "
                  "no hidden TEST labels, no external leaderboard submission.",
    },sort_keys=True),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Provide --self-test or --official-zip")
