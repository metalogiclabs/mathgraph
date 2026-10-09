#!/usr/bin/env python3
"""Development-only nearest-question transfer on WattBot official train.

Retrieves similar labelled development questions; only copies an example answer
when a frozen question-similarity threshold is satisfied. Evaluates official
scorer on the previously inspected 63-row train holdout. Not a Kaggle score,
nor semantic equivalence, and NEVER uses Kaggle test labels.
"""
from __future__ import annotations
import argparse
import ast
import io
import json
import re
import tempfile
import zipfile

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from holdout_probe import is_holdout
from score_ablation import blank_submission, load_score
from train_probe import parse_refs

THRESHOLDS = (0.55,0.65,0.75,0.85,0.93,0.98)
WEIGHTS = (0.0, 0.5, 1.0)
# Thresholds and features frozen by source before evaluation.


def train_match(dev, hold, word_weight: float):
    questions = dev["question"].astype(str).tolist() + hold["question"].astype(str).tolist()
    n = len(dev)
    a = TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True,stop_words="english",min_df=1)
    b = TfidfVectorizer(analyzer="char_wb",ngram_range=(3,5),sublinear_tf=True,min_df=1)
    A=a.fit_transform(questions)
    B=b.fit_transform(questions)
    similarities = word_weight*cosine_similarity(A[n:],A[:n]) + (1-word_weight)*cosine_similarity(B[n:],B[:n])
    best = np.argmax(similarities,axis=1)
    sims = similarities[np.arange(len(hold)),best]
    return best,sims


def transfer(hold,dev,indices,confidence,threshold):
    pred=blank_submission(hold).reset_index(drop=True)
    source=dev.reset_index(drop=True)
    chosen=0
    for i,(j,score) in enumerate(zip(indices,confidence)):
        if score<threshold:
            continue
        orig=source.iloc[int(j)]
        for col in ("answer","answer_value","answer_unit","ref_id","ref_url","supporting_materials"):
            value=str(orig.get(col,"is_blank"))
            pred.at[i,col]=value if value else "is_blank"
        pred.at[i,"explanation"]="Automated nearest labelled DEVELOPMENT question transfer; similarity only, not semantic equivalence."
        chosen+=1
    return pred,chosen


def test():
    assert THRESHOLDS[0]<THRESHOLDS[-1]
    assert all(0<=v<=1 for v in WEIGHTS)
    assert len(THRESHOLDS)==6
    q=["energy used for training","how much coal was used","water consumption"]
    a,b=train_match(pd.DataFrame({"question":q[:2]}),pd.DataFrame({"question":[q[0]]}),.5)
    assert a.tolist()==[0] and abs(b[0]-1)<1e-8
    print("NEARESTQA_SELF_TEST=PASS")


def run(zip_path):
    with zipfile.ZipFile(zip_path) as z,tempfile.TemporaryDirectory() as temp:
        data=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),keep_default_na=False,dtype={"id":str})
        dev=data[~data["id"].map(is_holdout)].reset_index(drop=True)
        held=data[data["id"].map(is_holdout)].reset_index(drop=True)
        score=load_score(z,temp)
        def official(frame):
            return float(score(held.copy(deep=True),frame.copy(deep=True),
                               row_id_column_name="id",verbose=False))
        baseline=blank_submission(held)
        results={}
        for word in WEIGHTS:
            idx,sims=train_match(dev,held,word)
            for threshold in THRESHOLDS:
                frame,nonblank=transfer(held,dev,idx,sims,threshold)
                label=f"word_{word:.2f}_threshold_{threshold:.2f}"
                results[label]={"official_score":round(official(frame),8),
                                "transferred_rows":nonblank,
                                "mean_match":round(float(sims.mean()),4),
                                "maximum_match":round(float(sims.max()),4)}
        print("WATTBOT_NEARESTQA_FROZEN_GRID="+json.dumps({
            "dev_rows":len(dev),"holdout_rows":len(held),
            "baseline_official_score":round(official(baseline),8),
            "results":results,
            "boundary":"Exploratory train-heldout diagnostic; similarity is not entailment; all thresholds reported; no test labels or new Kaggle submission",
        },sort_keys=True))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    args=p.parse_args()
    if args.self_test:test()
    elif args.official_zip:run(args.official_zip)
    else:p.error("Choose --self-test or --official-zip")
