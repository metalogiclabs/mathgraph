#!/usr/bin/env python3
"""Scoring-component ablations on labelled WattBot 2026 TRAIN ONLY.

Oracle arms copy train gold answers and/or citations solely to diagnose the
published scorer. They MUST NOT be used as predictions or published leaderboard
claims. Only aggregate scalar scores are printed. Protected test rows ignored.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import zipfile

import pandas as pd
from train_probe import parse_refs, score_metadata

EXPECTED_SCORER_SHA256 = "e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075"
COLUMNS = ["id", "question", "answer", "answer_value", "answer_unit",
           "ref_id", "ref_url", "supporting_materials", "explanation"]


def load_score(z, directory):
    body = z.read("Score.py")
    sha = hashlib.sha256(body).hexdigest()
    if sha != EXPECTED_SCORER_SHA256:
        raise ValueError("Unexpected scorer SHA256 "+sha)
    path = Path(directory) / "Score.py"
    path.write_bytes(body)
    spec = importlib.util.spec_from_file_location("wattbot_official_scorer_ablation", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load scorer")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.score


def blank_submission(train):
    # Question and ID are the only fields copied from the gold dataframe.
    result = pd.DataFrame(index=train.index)
    for name in COLUMNS:
        if name in ("id", "question"):
            result[name] = train[name].astype(str)
        elif name == "answer":
            result[name] = "Unable to answer from available evidence."
        elif name == "explanation":
            result[name] = "Non-informative baseline, no claims."
        else:
            result[name] = "is_blank"
    return result[COLUMNS].copy()


def run(path):
    with zipfile.ZipFile(path) as z, tempfile.TemporaryDirectory() as td:
        train = pd.read_csv(io.BytesIO(z.read("train_QA.csv")), keep_default_na=False)
        metadata = pd.read_csv(io.BytesIO(z.read("metadata.csv")), keep_default_na=False)
        docs = metadata.to_dict("records")
        lookup = {str(d["id"]): str(d["url"]) for d in docs}
        score_fn = load_score(z, td)
        def scored(candidate):
            return round(float(score_fn(train.copy(deep=True), candidate.copy(deep=True),
                                        row_id_column_name="id", verbose=False)), 8)
        blank = blank_submission(train)
        oracle_refs = blank.copy(deep=True)
        oracle_answer = blank.copy(deep=True)
        lexical_refs = blank.copy(deep=True)
        for i, row in train.iterrows():
            refs = parse_refs(row["ref_id"])
            gold_ref_urls = [lookup[r] for r in refs if r in lookup]
            oracle_refs.at[i, "ref_id"] = repr(refs) if refs else "is_blank"
            oracle_refs.at[i, "ref_url"] = repr(gold_ref_urls) if refs else "is_blank"
            for col in ("answer", "answer_value", "answer_unit"):
                oracle_answer.at[i, col] = str(row[col])
            # This intentionally ignores all gold fields in the lexical arm.
            predicted = score_metadata(str(row["question"]), docs, top_k=3)
            lexical_refs.at[i, "ref_id"] = repr(predicted) if predicted else "is_blank"
            lexical_refs.at[i, "ref_url"] = repr([lookup[r] for r in predicted]) if predicted else "is_blank"
        oracle_answer_and_refs = oracle_answer.copy(deep=True)
        for col in ("ref_id", "ref_url"):
            oracle_answer_and_refs[col] = oracle_refs[col]
        oracle_answer_lexical = oracle_answer.copy(deep=True)
        for col in ("ref_id", "ref_url"):
            oracle_answer_lexical[col] = lexical_refs[col]
        arms = {
            "all_blank": blank,
            "oracle_gold_references_plus_blank_answer": oracle_refs,
            "metadata_top3_references_plus_blank_answer": lexical_refs,
            "oracle_gold_answer_plus_blank_references": oracle_answer,
            "oracle_gold_answer_plus_metadata_top3_references": oracle_answer_lexical,
            "oracle_gold_answer_plus_gold_references": oracle_answer_and_refs,
        }
        result = {name: scored(df) for name, df in arms.items()}
        print("WATTBOT_OFFICIAL_SCORER_ABLATIONS="+json.dumps({
            "n_train":len(train),"scorer_sha256":EXPECTED_SCORER_SHA256,
            "scores":result,
            "interpretation":"Oracle arms access TRAIN labels for diagnostic upper bounds; not deployable predictions",
        },sort_keys=True))


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip",required=True)
    args=p.parse_args()
    run(args.official_zip)
