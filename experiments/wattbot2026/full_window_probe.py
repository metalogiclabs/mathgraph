#!/usr/bin/env python3
"""Question-centred excerpts on the COMPLETE pinned WattBot corpus.

Only page-excerpt selection changes. Reuses the independently green
full_reader.py unchanged: same ordered sources, K=6, model, price ceiling,
verifier, numeric fallback and official Score.py. Synthetic tests check that
every excerpt is an exact source substring. This is a *previously inspected*
TRAIN holdout; external Kaggle submission is a separate authority.
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

BASE_READER_BLOB = "4e1350ef72a44a333862dec23c737a2262ab99bc"
OFFICIAL_SHA = {
    "Score.py": "e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
    "metadata.csv": "b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1",
    "train_QA.csv": "9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
}
BASELINE_RUN_ID = 37893341832
BASELINE_COMBINED_SCORE = 0.42142857
BASELINE_CORPUS_SHA256 = "4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()


def self_test():
    assert base.K == 6 and base.MAX_EXCERPT == 1100
    assert base.SOURCE_BUDGET == 114 and base.MAX_BUDGET_USD == 0.12
    assert git_blob(Path(base.__file__).read_bytes()) == BASE_READER_BLOB
    original = [
        {"ref_id": "p1", "url": "https://arxiv.org/abs/2601.00001",
         "page": 1, "text": "background " * 300 + "cooling power was 112 MW."},
        {"ref_id": "p2", "url": "https://arxiv.org/abs/2601.00002",
         "page": 2, "text": "The energy was 44 GWh."},
    ]
    shifted = window_passages("What was cooling power?", original, 1100)
    assert "112 MW" in shifted[0]["text"]
    assert original[0]["text"].startswith("background ")
    assert shifted[0]["text"] == original[0]["text"][
        shifted[0]["excerpt_start"]:shifted[0]["excerpt_end"]]
    assert [(x["ref_id"], x["page"]) for x in original] == [
        (x["ref_id"], x["page"]) for x in shifted]
    print("WATTBOT_FULL_WINDOW_SELF_TEST=PASS")


def run(official_zip: str):
    self_test()
    with zipfile.ZipFile(official_zip) as z:
        for name, expected in OFFICIAL_SHA.items():
            observed = hashlib.sha256(z.read(name)).hexdigest()
            if observed != expected:
                raise RuntimeError("Official WattBot file changed: " + name)

    base_passages = base.passages_for
    counters = Counter()
    observed_questions = set()

    def replacement(question, chunks):
        original_pages, numeric_hits = base_passages(question, chunks)
        windowed = window_passages(question, original_pages, base.MAX_EXCERPT)
        if len(original_pages) != len(windowed):
            raise AssertionError("Source list length changed")
        for x, y in zip(original_pages, windowed):
            for key in ("ref_id", "page", "url"):
                if x[key] != y[key]:
                    raise AssertionError("Source identity/order changed")
            if y["text"] != x["text"][y["excerpt_start"]:y["excerpt_end"]]:
                raise AssertionError("Window is not exact source substring")
            if len(y["text"]) > base.MAX_EXCERPT:
                raise AssertionError("Prompt context budget exceeded")
            counters["original_context_characters"] += min(len(x["text"]), base.MAX_EXCERPT)
            counters["window_context_characters"] += len(y["text"])
            counters["windows_shifted"] += (y["excerpt_start"] != 0)
            counters["pages_preserved"] += 1
        digest = hashlib.sha256(question.encode("utf-8")).hexdigest()
        if digest in observed_questions:
            raise AssertionError("Question duplicate in heldout excerpt selection")
        observed_questions.add(digest)
        counters["questions"] += 1
        # Numeric answer candidates still see identical full chunks from original
        # ranking, so only the LLM's local view is modified.
        return windowed, numeric_hits

    base.passages_for = replacement
    stream = io.StringIO()
    try:
        with redirect_stdout(stream):
            base.run(official_zip)
    finally:
        base.passages_for = base_passages

    marker = "WATTBOT_FULL_READER_HOLDOUT="
    lines = [json.loads(line[len(marker):]) for line in stream.getvalue().splitlines()
             if line.startswith(marker)]
    if len(lines) != 1:
        raise RuntimeError("Expected one completed, scored result from full reader")
    result = lines[0]
    if result.get("source_manifest_sha256") != BASELINE_CORPUS_SHA256:
        raise RuntimeError("Pinned arXiv source bytes changed; historical comparison invalid")
    if result.get("holdout_rows") != 63 or counters["questions"] != 63:
        raise RuntimeError("Frozen holdout or question count changed")
    result["intervention"] = "question_centered_exact_substring_1100"
    result["unchanged_full_reader_git_blob"] = BASE_READER_BLOB
    result["comparator_run"] = BASELINE_RUN_ID
    result["historical_comparator_score"] = BASELINE_COMBINED_SCORE
    result["same_run_llm_pairing"] = False
    result["score_delta_vs_historical"] = round(
        result["scores"]["reader_then_numeric_fallback"]-BASELINE_COMBINED_SCORE, 8)
    result["window_audit"] = dict(counters)
    result["authority_boundary"] = ("Previous TRAIN holdout, same pinned corpus/model/prompt"
        " and numeric policy; historical rather than same-run model control; no leaderboard claim")
    print("WATTBOT_COMPLETE_WINDOW_QUALIFICATION=" +
          json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--official-zip")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif args.official_zip:
        run(args.official_zip)
    else:
        parser.error("Specify --official-zip or --self-test")
