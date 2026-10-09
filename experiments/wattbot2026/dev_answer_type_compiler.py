#!/usr/bin/env python3
"""WattBot answer-type developmental capability compiler.

Predict the form of answer_value from QUESTION text, using exclusively the
182 permitted development TRAIN labeled examples. On each development
evaluation question the entire target row is removed from training BEFORE
features/priors/examples are computed. The reused 63 TRAIN holdout is read
only after policy selection. Protected TEST answer/citation labels are absent.

Protected-future types: numeric scalar (including gold numeric tolerance
bands), source-declared tuple range, categorical text, and unanswerable.
The classifier never licenses a claim that an answer is unavailable;
is_blank must still be supported by an independent model/source judgment.
No model calls, PDF downloads or Kaggle submissions.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter,defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
import re
import zipfile

import pandas as pd
from holdout_probe import is_holdout
from wattbot import tokens
from verified_lesson import examples_for

TRAIN_SHA="9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca"
TEST_SHA="26038b21cb09588a39b0e95e5516e3827dadd499c85c3792d0ea46c10ae7066a"
CLASSES=("number","term","range")
POLICIES=("majority","lesson_vote","bayes_alpha1","bayes_alpha3","bayes_alpha8")
NO_ANSWER=set(("","is_blank","na","n/a","nan","null","none"))
STOP=set(("the a an is was were what in from for of on to by and or this "
          "that results result reported paper papers study studies a which "
          "between using with their as at values value based according").split())
RANGE_CUES=re.compile(
    r"\b(?:range|minimum\s+and\s+maximum|lower\s+(?:and|to)\s+upper\s+bound|"
    r"(?:both|the)\s+(?:minimum|lower)\s+and\s+(?:maximum|upper)|"
    r"endpoints)\b",re.I)


def shape(answer_value):
    raw=str(answer_value or "").strip()
    if raw.casefold() in NO_ANSWER:return "na"
    try:
        number=Decimal(raw.replace(",",""))
        if number.is_finite():return "number"
    except (InvalidOperation,ValueError,TypeError):
        pass
    try:
        parsed=ast.literal_eval(raw)
    except (ValueError,TypeError,SyntaxError,MemoryError):
        parsed=None
    if isinstance(parsed,tuple) and len(parsed)==2:
        return "range"
    if isinstance(parsed,list) and len(parsed)==2:
        try:
            if all(Decimal(str(x)).is_finite() for x in parsed):
                return "number" # Official TRAIN list is a tolerance band.
        except (ValueError,TypeError,InvalidOperation):
            pass
    return "term"


def features(q):
    tok=[t for t in tokens(str(q)) if t not in STOP and len(t)>1]
    bag=Counter("w:"+t for t in tok)
    bag.update("b:"+a+"_"+b for a,b in zip(tok,tok[1:]))
    if RANGE_CUES.search(q):
        bag["q:source_range"]=3
    if re.search(r"\bwhich\b",str(q),re.I):
        bag["q:which"]=2
    if re.search(r"\b(?:how many|how much)\b",str(q),re.I):
        bag["q:how_many"]=2
    return bag


def bayes(train,q,alpha):
    """Finite multinomial Bayes with smoothing across a common vocabulary.

    Each development target is removed before this is fitted; unlike the
    earlier incomplete Bernoulli formula, the denominator accounts for the
    shared whole-vocabulary size instead of rewarding tiny rare classes
    merely because a token has never been seen.
    """
    records=[(shape(item["answer_value"]),features(item["question"]))
             for item in train]
    records=[(klass,f) for klass,f in records if klass in CLASSES]
    count=Counter(k for k,_ in records)
    perclass=defaultdict(Counter)
    vocab=set()
    for klass,f in records:
        perclass[klass].update(f)
        vocab.update(f.keys())
    vocab_n=max(1,len(vocab))
    sizes={cls:sum(perclass[cls].values()) for cls in CLASSES}
    input_features=features(q)
    # Only tokens learned from development contribute evidence.
    observed={t:min(3,n) for t,n in input_features.items() if t in vocab}
    scores={}
    n=len(records)
    for klass in CLASSES:
        prior=math.log((count[klass]+.5)/(n+len(CLASSES)*.5))
        denom=sizes[klass]+alpha*vocab_n
        total=prior
        for term,frequency in observed.items():
            probability=(perclass[klass][term]+alpha)/denom
            total+=frequency*math.log(probability)
        scores[klass]=total
    best=max(CLASSES,key=lambda k:(scores[k],-CLASSES.index(k)))
    upper=max(scores.values())
    shifted={k:math.exp(scores[k]-upper) for k in CLASSES}
    confidence=shifted[best]/sum(shifted.values())
    return best,confidence


def lesson_vote(train,q):
    # Identical source of lessons as the official V5 development compiler.
    selected=examples_for(q,train,max_examples=2)
    if len(selected)!=2:return "number",0.
    forms=[shape(ex["answer_value"]) for ex in selected]
    if forms[0]==forms[1]:
        return forms[0],.85
    if RANGE_CUES.search(q) and "range" in forms:
        return "range",.70
    if "term" in forms and "number" not in forms and "range" in forms:
        return "term",.55
    return "number",.50


def predict(train,q,policy):
    if policy=="majority":return "number",.75
    if policy=="lesson_vote":return lesson_vote(train,q)
    if policy.startswith("bayes_alpha"):
        return bayes(train,q,float(policy.split("alpha")[1]))
    raise ValueError("Unknown developmental format policy")


def measure(pairs):
    counts=Counter()
    confusion=defaultdict(Counter)
    predicted_confident=Counter()
    for actual,pred,conf in pairs:
        if actual=="na":
            counts["NA_separate"]+=1
            continue
        counts["n"]+=1
        counts["correct"]+=int(actual==pred)
        counts["confidence_ge_085"]+=int(conf>=.85)
        counts["high_confidence_correct"]+=int(conf>=.85 and actual==pred)
        counts["confidence_ge_070"]+=int(conf>=.70)
        counts["medium_confidence_correct"]+=int(conf>=.70 and actual==pred)
        confusion[actual][pred]+=1
        predicted_confident[pred]+=int(conf>=.85)
    return {
        "counts":dict(counts),
        "accuracy":round(counts["correct"]/max(1,counts["n"]),6),
        "precision_at_085":round(
            counts["high_confidence_correct"]/max(1,counts["confidence_ge_085"]),6),
        "coverage_at_085":round(counts["confidence_ge_085"]/max(1,counts["n"]),6),
        "precision_at_070":round(
            counts["medium_confidence_correct"]/max(1,counts["confidence_ge_070"]),6),
        "coverage_at_070":round(counts["confidence_ge_070"]/max(1,counts["n"]),6),
        "confusion":{k:dict(v) for k,v in confusion.items()},
        "high_confidence_by_prediction":dict(predicted_confident),
    }


def frozen_choice(loo):
    # Favor accuracy on all answerable developmental tasks, then precision
    # where confidence is high, coverage, and simpler models for ties.
    def key(policy):
        m=loo[policy]
        return (m["accuracy"],m["precision_at_085"],
                m["coverage_at_085"],-POLICIES.index(policy))
    return max(POLICIES,key=key)


def self_test():
    assert shape("is_blank")=="na"
    assert shape("1287")=="number"
    assert shape("[116,121]")=="number"
    assert shape("(116,121)")=="range"
    assert shape("nan")=="na"
    assert shape("FALSE")=="term"
    assert shape("carbon intensity")=="term"
    sample=[
        {"id":"d1","question":"Which power supply technology was used?",
         "answer_value":"solar","CrossPaper":"False"},
        {"id":"d2","question":"How much electricity was consumed?",
         "answer_value":"17.5","Math":"False"},
        {"id":"d3","question":"What range of consumption was measured?",
         "answer_value":"(11,23)","Math":"True"},
        {"id":"d4","question":"How many households were supplied?",
         "answer_value":"45","Math":"True"}
    ]
    for x in sample:
        while is_holdout(str(x["id"])):
            x["id"]+="_dev"
    assert predict(sample,"How much electricity was used?","majority")[0]=="number"
    assert len(predict(sample,"What range of water consumption?","bayes_alpha3"))==2
    assert len(predict(sample,"Which energy source was selected?","lesson_vote"))==2
    assert all(shape(x["answer_value"]) in CLASSES for x in sample)
    print("WATTBOT_DEV_ANSWER_TYPE_SELF_TEST=PASS")


def run(archive):
    self_test()
    with zipfile.ZipFile(archive) as z:
        if hashlib.sha256(z.read("train_QA.csv")).hexdigest()!=TRAIN_SHA:
            raise RuntimeError("Official TRAIN digest changed")
        if hashlib.sha256(z.read("test_Q.csv")).hexdigest()!=TEST_SHA:
            raise RuntimeError("Official TEST question metadata digest changed")
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str})
        test=pd.read_csv(io.BytesIO(z.read("test_Q.csv")),
                         keep_default_na=False,dtype={"id":str})
    dev=train[~train["id"].map(is_holdout)].to_dict("records")
    hold=train[train["id"].map(is_holdout)].to_dict("records")
    if len(dev)!=182 or len(hold)!=63 or len(test)!=317:
        raise RuntimeError("Official split and authorized question count changed")
    # Per-development-target LOO eliminates both self-example and self-prior.
    result={}
    for policy in POLICIES:
        checked=[]
        for row in dev:
            target_id=str(row["id"])
            others=[ex for ex in dev if str(ex["id"])!=target_id]
            if len(others)!=181 or any(str(ex["id"])==target_id for ex in others):
                raise RuntimeError("Development self-label leakage")
            predicted,confidence=predict(others,row["question"],policy)
            checked.append((shape(row["answer_value"]),predicted,confidence))
        result[policy]=measure(checked)
    chosen=frozen_choice(result)
    # Only selected developmental decision rule sees the fixed reused TRAIN
    # holdout; target labels remain unknown until post-prediction scoring.
    held=[(shape(r["answer_value"]),*predict(dev,r["question"],chosen))
          for r in hold]
    heldout=measure(held)
    test_choices=Counter()
    for q in test["question"].astype(str).tolist():
        predicted,conf=predict(dev,q,chosen)
        test_choices[predicted]+=1
    print("WATTBOT_DEV_ANSWER_TYPE_COMPILER="+json.dumps({
        "authority":"Official pinned TRAIN values for AFTER-prediction developmental evaluation",
        "dev_rows":len(dev),"reused_train_holdout":len(hold),
        "test_question_side_rows":len(test),
        "answerable_dev_loo":{"policies":result},
        "selected_on_dev_loo":chosen,
        "heldout_after_selection":heldout,
        "test_question_only_predicted_type_counts":dict(test_choices),
        "boundary":"Answer FORM prediction only, never scientific correctness "
                   "or evidence/source license. Entire dev target removed "
                   "from its own classifier and exemplars before inference. "
                   "Official 63 TRAIN holdout reused and labels scored only "
                   "after classification; protected TEST answer/citation "
                   "labels not visible or used. No model calls or Kaggle "
                   "submission.",
    },sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Specify --self-test or --official-zip")
