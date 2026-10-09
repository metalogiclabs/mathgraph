#!/usr/bin/env python3
"""WattBot source-anchored numeric/extractive answer routing experiment.

All answer generation uses only question text and pinned source-PDF bytes.
Training labels feed DEV source selection and DEV question-type classifier only.
Official scorer sees the heldout labels solely after frozen predictions.
The 63-row holdout has been examined in prior work: diagnostic, NOT pristine
prospective competition or leaderboard evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlparse
import zipfile

import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from answer_types import kind
from holdout_probe import is_holdout, ARXIV_HOSTS
from pdf_probe import download_one
from numeric_answer_probe import build_candidate
from score_ablation import blank_submission, load_score
from train_probe import parse_refs
from wattbot import chunks_from_pages, ranked, norm

MODEL = "distilbert/distilbert-base-cased-distilled-squad"
PINNED_MODEL_REVISION = "564e9b582944a57a3e586bbb98fd6f0a4118db7f"
QA_MIN_CONFIDENCE = 0.35
SOURCE_BUDGET = 24
UNIT_RE = re.compile(
    r"(?:%|kWh|MWh|GWh|TWh|kg|tons?|tonnes?|years?|liters?|litres?)", re.I
)
VALUE_COLUMNS = ("answer", "answer_value", "answer_unit")
REFERENCE_COLUMNS = ("ref_id", "ref_url", "supporting_materials")


def model_from_development(dev: pd.DataFrame):
    """Identical question-only router architecture as prior measured candidate."""
    vectorizer = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(2, 5),
        min_df=2, max_features=40000,
    )
    features = vectorizer.fit_transform(dev["question"].astype(str).tolist())
    labels = dev["answer_value"].map(kind).tolist()
    model = LogisticRegression(
        class_weight="balanced", max_iter=1500, C=1.0, random_state=2026
    )
    model.fit(features, labels)
    return vectorizer, model


def qa_candidate(question: str, chunks: list[dict], qa):
    """Faithfully reproduce the earlier eight-/24-PDF extraction policy."""
    hits = ranked(question, chunks, top_k=5)
    best = None
    for source in hits[:3]:
        context = source["text"][:1800]
        answer = qa(question=question, context=context,
                    max_answer_len=45, handle_impossible_answer=True)
        span = str(answer.get("answer", "")).strip()
        confidence = float(answer.get("score", 0))
        if span and norm(span) in norm(context):
            if best is None or confidence > best["score"]:
                best = {"answer":span, "score":confidence, "source":source}
    if not best or best["score"] < QA_MIN_CONFIDENCE:
        return None
    return best


def merge_candidate(row: dict, match):
    if match is None:
        return row
    src = match["source"]
    span = match["answer"]
    unit = UNIT_RE.search(span)
    output = dict(row)
    output.update({
        "answer":span,
        "answer_value":span,
        "answer_unit":unit.group(0) if unit else "is_blank",
        "ref_id":repr([src["ref_id"]]),
        "ref_url":repr([src["url"]]),
        "supporting_materials":repr([span]),
        "explanation":(
            f"Source-page {src['page']} literal-span candidate, confidence "
            f"{match['score']:.3f}; semantic entailment unverified"
        )
    })
    assert norm(span) in norm(src["text"])
    return output


def simulate(official_zip: str):
    from transformers import pipeline

    with zipfile.ZipFile(official_zip) as z:
        train = pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                            keep_default_na=False, dtype={"id": str})
        metadata = pd.read_csv(io.BytesIO(z.read("metadata.csv")),
                               keep_default_na=False, dtype={"id": str})
        dev = train[~train["id"].map(is_holdout)].copy()
        hold = train[train["id"].map(is_holdout)].copy().reset_index(drop=True)
        refs = Counter(
            source for raw in dev["ref_id"] for source in parse_refs(raw)
        )
        docs = {str(row["id"]): row for row in metadata.to_dict("records")}
        allowed = [
            r for r in refs
            if r in docs and (urlparse(str(docs[r]["url"])).hostname or "").lower()
            in ARXIV_HOSTS
        ]
        allowed.sort(key=lambda r: (-refs[r], r))
        selected = allowed[:SOURCE_BUDGET]
        if len(selected) != SOURCE_BUDGET:
            raise ValueError("Not enough eligible pinned PDFs")
        vectorizer, classifier = model_from_development(dev)
        kinds = classifier.predict(
            vectorizer.transform(hold["question"].astype(str).tolist())
        ).tolist()

        print("WATTBOT_FUSION_BOUNDARY=" + json.dumps({
            "dev_rows": len(dev), "holdout_rows":len(hold),
            "source_budget":SOURCE_BUDGET,
            "type_router_training":"development labels, question text only",
            "model_revision":PINNED_MODEL_REVISION,
            "retrieval":"metadata plus 24 pinned arXiv PDFs for numeric, PDF-only for QA",
            "holdout":"reused / previously inspected; do not promote to prospective",
        }, sort_keys=True), flush=True)

        with tempfile.TemporaryDirectory(prefix="mathgraph_wattbot_fusion_") as folder:
            td = Path(folder)
            chunks = []
            pdf_hashes = []
            for i, doc_id in enumerate(selected):
                if i: time.sleep(3.1)
                path = td / f"source_{i}.pdf"
                digest, _ = download_one(str(docs[doc_id]["url"]), path)
                extracted = chunks_from_pages(doc_id, str(docs[doc_id]["url"]), path)
                if not extracted:
                    raise ValueError(f"Pinned source {i} has no extractable text")
                chunks.extend(extracted)
                pdf_hashes.append(digest)
            print("WATTBOT_FUSION_SOURCE_PIN=" + json.dumps({
                "downloaded_valid_pdfs":len(pdf_hashes),
                "pdf_chunks":len(chunks),
                "hash_manifest_digest":hashlib.sha256(
                    "\n".join(pdf_hashes).encode()).hexdigest()
            },sort_keys=True), flush=True)

            # Fixed model revision: no auto-latest downloads or private models.
            qa = pipeline("question-answering", model=MODEL,
                          tokenizer=MODEL, revision=PINNED_MODEL_REVISION,
                          device=-1)
            meta_chunks = [{
                "ref_id":d["id"], "url":d["url"], "page":0,
                "text":" ".join(str(d.get(k, "") or "")
                                for k in ("title", "citation", "year", "venue"))
            } for d in metadata.to_dict("records")]
            index = meta_chunks + chunks
            baseline = blank_submission(hold).reset_index(drop=True)

            numeric_rows = []
            extractive_rows = []
            typed_rows = []
            typed_with_list_fallback_rows = []
            for i, item in baseline.iterrows():
                row = {"id":str(item["id"]), "question":str(item["question"])}
                hits = ranked(row["question"], index, min(100, len(index)))
                numeric = build_candidate(row, hits, docs)
                extractive = merge_candidate(
                    dict(item), qa_candidate(row["question"], chunks, qa)
                )
                # Strict type-router: numeric -> numeric literal; short text
                # -> extractive span; blank/list -> explicit abstention. The
                # list extractor is not capable of validating multi-item lists.
                chosen = dict(item)
                if kinds[i] == "number":
                    chosen = numeric
                elif kinds[i] == "short_text":
                    chosen = extractive
                typed_rows.append(chosen)
                # Separate arm: allow extractor for lists, without claiming
                # it is a correct complete list.
                allowed_list = chosen
                if kinds[i] == "structured_list":
                    allowed_list = extractive
                typed_with_list_fallback_rows.append(allowed_list)
                numeric_rows.append(numeric)
                extractive_rows.append(extractive)

            def as_frame(rows):
                return pd.DataFrame(rows, columns=list(baseline.columns))
            arms = {
                "all_blank":baseline,
                "numeric_24":as_frame(numeric_rows),
                "extractive_24":as_frame(extractive_rows),
                "type_gated_abstain_on_list":as_frame(typed_rows),
                "type_gated_extractive_list_fallback":as_frame(
                    typed_with_list_fallback_rows),
            }
            score_fn = load_score(z, folder)
            def scored(frame):
                return round(float(score_fn(
                    hold.copy(deep=True), frame.copy(deep=True),
                    row_id_column_name="id", verbose=False
                )), 8)
            scores = {k:scored(frame) for k, frame in arms.items()}
            counts = {k:int((frame["answer_value"]!="is_blank").sum())
                      for k,frame in arms.items()}
            answer_only = arms["type_gated_abstain_on_list"].copy(deep=True)
            reference_only = answer_only.copy(deep=True)
            for col in REFERENCE_COLUMNS: answer_only[col] = "is_blank"
            reference_only["answer"] = "Unable to determine answer."
            for col in ("answer_value","answer_unit"): reference_only[col] = "is_blank"
            scores["type_gated_answers_only"] = scored(answer_only)
            scores["type_gated_citations_only"] = scored(reference_only)
            print("WATTBOT_FUSION_OFFICIAL_COMPONENTS=" + json.dumps({
                "scores":scores,
                "nonblank_counts":counts,
                "router_predictions":dict(Counter(kinds)),
                "train_holdout_rows":len(hold),
                "source_budget":len(selected),
                "scope":"Pin-verified source-anchored CANDIDATE score; not public Kaggle rank, not semantic proof",
            },sort_keys=True),flush=True)


def self_test():
    assert SOURCE_BUDGET == 24
    assert 0 < QA_MIN_CONFIDENCE < 1
    dummy = {"answer_value":"is_blank"}
    fake = {"answer":"123 MWh","score":.9,
            "source":{"ref_id":"p","url":"https://arxiv.org/abs/2601.00001",
                      "page":2,"text":"Energy 123 MWh."}}
    row = merge_candidate(dummy,fake)
    assert row["answer_value"] == "123 MWh"
    assert row["answer_unit"] == "MWh"
    assert row["ref_id"] == "['p']"
    assert dummy["answer_value"] == "is_blank"
    print("FUSION_SELF_TEST=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--official-zip")
    args = parser.parse_args()
    if args.self_test: self_test()
    elif args.official_zip: simulate(args.official_zip)
    else: parser.error("Choose --official-zip or --self-test")
