#!/usr/bin/env python3
"""Minimal question-only answer-type router; 182 dev -> 63 fixed train holdout.

No test labels and no answer text available to model. Question text only;
labels are inferred from TRAIN answer_value, never leaked to feature building.
"""
from __future__ import annotations
import argparse
import io
import json
import zipfile

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix

from holdout_probe import is_holdout
from answer_types import kind

LABELS = ["blank","number","short_text","structured_list","long_text","boolean","percentage"]


def run(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        train = pd.read_csv(io.BytesIO(z.read("train_QA.csv")),keep_default_na=False,dtype={"id":str})
    dev=train[~train["id"].map(is_holdout)].copy()
    held=train[train["id"].map(is_holdout)].copy()
    X_train=dev["question"].astype(str).tolist()
    X_hold=held["question"].astype(str).tolist()
    y_train=dev["answer_value"].map(kind).tolist()
    y_hold=held["answer_value"].map(kind).tolist()
    # Hyperparameters frozen before looking at this classifier's results.
    tfidf=TfidfVectorizer(analyzer="char_wb",ngram_range=(2,5),min_df=2,max_features=40000)
    A=tfidf.fit_transform(X_train)
    B=tfidf.transform(X_hold)
    model=LogisticRegression(class_weight="balanced",max_iter=1500,C=1.0,random_state=2026)
    model.fit(A,y_train)
    y_pred=model.predict(B).tolist()
    majority=max(set(y_train),key=y_train.count)
    confusion=pd.crosstab(pd.Series(y_hold,name="actual"),pd.Series(y_pred,name="predicted"),dropna=False)
    output={
        "dev_rows":len(dev), "holdout_rows":len(held),
        "train_class_counts":pd.Series(y_train).value_counts().to_dict(),
        "holdout_class_counts":pd.Series(y_hold).value_counts().to_dict(),
        "majority_guess":majority,
        "majority_accuracy":round(sum(y==majority for y in y_hold)/len(y_hold),4),
        "type_router_accuracy":round(float(accuracy_score(y_hold,y_pred)),4),
        "type_router_macro_f1":round(float(f1_score(y_hold,y_pred,average="macro",zero_division=0)),4),
        "confusion_aggregate":{str(k):{str(kk):int(vv) for kk,vv in v.items()}
                               for k,v in confusion.to_dict("index").items()},
        "boundary":"Same previously inspected TRAIN holdout; candidate predictive diagnostic only",
    }
    print("WATTBOT_QUESTION_TYPE_ROUTER="+json.dumps(output,sort_keys=True))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip",required=True)
    run(p.parse_args().official_zip)
