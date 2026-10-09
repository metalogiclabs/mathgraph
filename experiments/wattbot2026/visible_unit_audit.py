#!/usr/bin/env python3
"""Audit the visible WattBot TEST answer_unit as authorized metadata.

No model inference, TEST answer labels, web source crawling or submission.
Gold TRAIN answer values are used ONLY after grouping visible TRAIN units to
estimate whether unit metadata is useful, including negative controls.
The declared TEST answer_unit is legitimate visible task input, not the
protected TEST answer_value; never infer a protected answer from it alone.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import io
import json
import zipfile

import pandas as pd

from holdout_probe import is_holdout
from score_ablation import EXPECTED_SCORER_SHA256
from wattbot import as_fraction

EXPECTED = {
    "Score.py":"e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
    "metadata.csv":"b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1",
    "train_QA.csv":"9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
    "test_Q.csv":"26038b21cb09588a39b0e95e5516e3827dadd499c85c3792d0ea46c10ae7066a",
}
BLANK = frozenset(("", "is_blank", "na", "n/a", "nan", "none", "null"))
EXPECTED_TRAIN,EXPECTED_TEST = 245,317

def norm_unit(unit):
    return str(unit or "").strip().casefold()

def provided(unit):
    return norm_unit(unit) not in BLANK

def gold_is_na(flag):
    return str(flag or "").strip().casefold() in ("true","1","1.0","yes")

def gold_type(value, is_na=False):
    s=str(value).strip()
    if is_na or s.casefold() in BLANK:
        return "gold_unanswerable"
    try:
        as_fraction(s)
        return "answerable_single_number"
    except (ValueError,TypeError):
        return "answerable_other"

def summarize(labelled,visible_units):
    groups=Counter()
    for _,r in labelled.iterrows():
        units=provided(r["answer_unit"])
        kind=gold_type(r["answer_value"],gold_is_na(r["is_NA"]))
        groups[("known_unit" if units else "blank_unit",kind)]+=1
    known={t:int(n) for (u,t),n in groups.items() if u=="known_unit"}
    unknown={t:int(n) for (u,t),n in groups.items() if u=="blank_unit"}
    return {
      "n":len(labelled),
      "known_unit_gold_kind_counts":known,
      "blank_unit_gold_kind_counts":unknown,
      "known_unit_rows":sum(known.values()),
      "blank_unit_rows":sum(unknown.values()),
      "fraction_gold_unanswerable_if_known_unit":round(
          known.get("gold_unanswerable",0)/max(1,sum(known.values())),5),
      "fraction_gold_unanswerable_if_blank_unit":round(
          unknown.get("gold_unanswerable",0)/max(1,sum(unknown.values())),5),
    }

def self_test():
    assert provided("MWh")
    assert provided("kgCO2e")
    assert not provided("is_blank")
    assert not provided("N/A")
    assert gold_type("10.5")=="answerable_single_number"
    assert gold_type("is_blank")=="gold_unanswerable"
    assert gold_type("False")=="answerable_other"
    assert gold_is_na(True) and gold_is_na("1") and not gold_is_na(False)
    assert gold_type("n/a",True)=="gold_unanswerable"
    assert EXPECTED_SCORER_SHA256==EXPECTED["Score.py"]
    print("WATTBOT_VISIBLE_UNIT_AUDIT_SELF_TEST=PASS",flush=True)

def run(archive):
    self_test()
    with zipfile.ZipFile(archive) as z:
        for path,expected in EXPECTED.items():
            if hashlib.sha256(z.read(path)).hexdigest()!=expected:
                raise RuntimeError("Pinned official dataset drift: "+path)
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str})
        test=pd.read_csv(io.BytesIO(z.read("test_Q.csv")),
                         keep_default_na=False,dtype={"id":str})
    if (len(train),len(test))!=(EXPECTED_TRAIN,EXPECTED_TEST):
        raise RuntimeError("Frozen train/test sizes changed")
    if "is_NA" not in train:
        raise RuntimeError("TRAIN authority is_NA flag absent")
    if "answer_unit" not in train or "answer_unit" not in test:
        raise RuntimeError("Official visible unit field absent")
    if train["id"].duplicated().any() or test["id"].duplicated().any():
        raise RuntimeError("Question ID collision")
    dev=train[~train["id"].astype(str).map(is_holdout)]
    hold=train[train["id"].astype(str).map(is_holdout)]
    unit_counts=Counter(norm_unit(x) for x in test["answer_unit"])
    training_unit_counts=Counter(norm_unit(x) for x in train["answer_unit"])
    test_known=sum(provided(x) for x in test["answer_unit"])
    train_known=sum(provided(x) for x in train["answer_unit"])
    result={
      "authority":"Pinned official Kaggle TEST-visible answer_unit only; TRAIN gold solely for retrospective audit",
      "train_sha256":EXPECTED["train_QA.csv"],
      "train_flagged_unanswerable":sum(gold_is_na(x) for x in train["is_NA"]),
      "reused_holdout_flagged_unanswerable":sum(gold_is_na(x) for x in hold["is_NA"]),
      "test_sha256":EXPECTED["test_Q.csv"],
      "test_rows":len(test),
      "test_with_visible_known_unit":test_known,
      "test_visible_unit_nonblank_fraction":round(test_known/len(test),6),
      "test_distinct_visible_unit_strings":len(unit_counts),
      "train_with_known_unit":train_known,
      "train_visible_unit_nonblank_fraction":round(train_known/len(train),6),
      "train_distinct_unit_strings":len(training_unit_counts),
      "train_gold_signal":summarize(train,train["answer_unit"]),
      "reused_holdout_gold_signal":summarize(hold,hold["answer_unit"]),
      "dev_gold_signal":summarize(dev,dev["answer_unit"]),
      "never_use": "Do not copy TRAIN answer_value to TEST or assume units uniquely identify answers",
      "science_boundary":"Unit metadata may help normalize but does not entail an answer or identify sources"
    }
    print("WATTBOT_VISIBLE_UNIT_AUDIT="+json.dumps(result,sort_keys=True),flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--official-zip")
    parser.add_argument("--self-test",action="store_true")
    a=parser.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:parser.error("Provide --self-test or --official-zip")
