#!/usr/bin/env python3
"""Frozen WattBot full-corpus, question-window SCIENTIFIC READER model ablation.

Only the model changes relative to the successful full-corpus query-window
experiment. TRAIN-only 63-row previously inspected holdout: not independent,
not a Kaggle submission, not a verified scientific entailment claim.

Pin the original official corpus and full_reader semantics. Abort if live
pricing exceeds declared per-token ceiling or total conservative reservation.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import zipfile

import requests

import full_reader as base
from query_window import window_passages

MODEL = "openai/gpt-6-sol"
MAX_RATE_PROMPT = 0.000002
MAX_RATE_COMPLETION = 0.00001
MAX_RESERVED_USD = 1.55
BASE_READER_GIT_BLOB = "4e1350ef72a44a333862dec23c737a2262ab99bc"
OFFICIAL_SHAS = {
    "Score.py": "e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
    "metadata.csv": "b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1",
    "train_QA.csv": "9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
}
CORPUS_SHA = "4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
HISTORICAL_COMPARATOR_SCORE = 0.49708995
HISTORICAL_COMPARATOR_RUN_ID = 37968840780


def git_blob(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + bytes([0]) + data
    ).hexdigest()


def get_model_price():
    response = requests.get("https://openrouter.ai/api/v1/models", timeout=(8, 30))
    response.raise_for_status()
    candidates = [m for m in response.json().get("data", []) if m.get("id") == MODEL]
    if len(candidates) != 1:
        raise RuntimeError("Target model missing or ambiguous in live catalog")
    item = candidates[0]
    pricing = item.get("pricing") or {}
    prompt = float(pricing.get("prompt", "nan"))
    completion = float(pricing.get("completion", "nan"))
    if not (0 <= prompt <= MAX_RATE_PROMPT
            and 0 <= completion <= MAX_RATE_COMPLETION):
        raise RuntimeError("Live target model pricing changed; no model calls")
    return {"prompt": prompt, "completion": completion}


def self_test():
    assert base.K == 6 and base.MAX_EXCERPT == 1100
    assert base.MAX_REQUESTS == 63 and base.MAX_BUDGET_USD == .12
    assert base.SOURCE_BUDGET == 114
    assert base.MODEL == "google/gemini-2.5-flash-lite"
    assert git_blob(Path(base.__file__).read_bytes()) == BASE_READER_GIT_BLOB
    sample = {"ref_id": "doc1", "page": 4, "url": "https://arxiv.org/abs/2601.12345",
              "text": "boilerplate " * 150 + "specific cooling consumption 214.5 MWh."}
    shifted = window_passages("cooling consumption MWh", [sample], base.MAX_EXCERPT)
    assert len(shifted) == 1
    s = shifted[0]
    assert "214.5 MWh" in s["text"]
    assert s["text"] == sample["text"][s["excerpt_start"]:s["excerpt_end"]]
    assert (s["ref_id"], s["page"], s["url"]) == (
        sample["ref_id"], sample["page"], sample["url"])
    print("WATTBOT_GPT6_SOL_SELF_TEST=PASS")


def run(archive):
    self_test()
    with zipfile.ZipFile(archive) as z:
        for name, digest in OFFICIAL_SHAS.items():
            if hashlib.sha256(z.read(name)).hexdigest() != digest:
                raise RuntimeError("Pinned WattBot data changed; abort: " + name)

    before_passages = base.passages_for
    before_model = base.MODEL
    before_budget = base.MAX_BUDGET_USD
    before_pricing = base.verify_price_ceiling
    controls = {"questions": 0, "pages": 0, "shifted": 0}

    def passages(question, chunks):
        old, numeric_hits = before_passages(question, chunks)
        selected = window_passages(question, old, base.MAX_EXCERPT)
        for a,b in zip(old,selected):
            for key in ("ref_id", "page", "url"):
                assert a[key] == b[key]
            assert b["text"] == a["text"][b["excerpt_start"]:b["excerpt_end"]]
            assert len(b["text"]) <= base.MAX_EXCERPT
            controls["pages"] += 1
            controls["shifted"] += int(b["excerpt_start"] != 0)
        assert len(old) == len(selected)
        controls["questions"] += 1
        return selected, numeric_hits

    stdout = io.StringIO()
    try:
        # Identical retrieval, output schema, quote validation and numeric
        # fallback. Only the model and bounded rate are allowed to change.
        base.passages_for = passages
        base.MODEL = MODEL
        base.MAX_BUDGET_USD = MAX_RESERVED_USD
        base.verify_price_ceiling = get_model_price
        with redirect_stdout(stdout):
            base.run(archive)
    finally:
        base.passages_for = before_passages
        base.MODEL = before_model
        base.MAX_BUDGET_USD = before_budget
        base.verify_price_ceiling = before_pricing
    matches = [
        json.loads(l.split("WATTBOT_FULL_READER_HOLDOUT=",1)[1])
        for l in stdout.getvalue().splitlines()
        if l.startswith("WATTBOT_FULL_READER_HOLDOUT=")
    ]
    if len(matches) != 1:
        raise RuntimeError("No qualified reader result")
    result = matches[0]
    if result["source_manifest_sha256"] != CORPUS_SHA or result["holdout_rows"] != 63:
        raise RuntimeError("Pinned source/human holdout changed")
    if controls["questions"] != 63 or controls["pages"] != 378:
        raise RuntimeError("Expected protected TRAIN scoring scope changed")
    if result["max_reserved_usd"] > MAX_RESERVED_USD:
        raise RuntimeError("Exceeded conservative model cost cap")
    score = result["scores"]["reader_then_numeric_fallback"]
    answer = {
        "status": "CANDIDATE",
        "scope": "Previously inspected 63-row TRAIN holdout, not Kaggle TEST or leaderboard",
        "intervention": "Scientific reader model only",
        "model": MODEL, "price_ceiling_usd": MAX_RESERVED_USD,
        "score": score, "historical_comparator_score": HISTORICAL_COMPARATOR_SCORE,
        "score_delta_vs_historical": round(score-HISTORICAL_COMPARATOR_SCORE,8),
        "historical_comparator_run": HISTORICAL_COMPARATOR_RUN_ID,
        "same_run_paired_model_control": False,
        "scores": result["scores"],
        "outcomes": result["outcomes"],
        "coverage_audit": controls,
        "pinned_arxiv_sha256": result["source_manifest_sha256"],
        "pinned_reports_sha256": result["report_hash_manifest_sha256"],
        "reserved_usd": result["max_reserved_usd"],
        "reported_api_usd": result["observed_api_usd"],
        "boundary": "TRAIN labels only after predictions via official scorer; citations checked "
                    "as literal page quotations, not semantic entailment. No Kaggle TEST or submission.",
    }
    print("WATTBOT_GPT6_SOL_SCIENTIFIC_HOLDOUT="+json.dumps(answer,sort_keys=True),flush=True)


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--official-zip")
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:self_test()
    elif a.official_zip:run(a.official_zip)
    else:p.error("Specify --self-test or --official-zip")
