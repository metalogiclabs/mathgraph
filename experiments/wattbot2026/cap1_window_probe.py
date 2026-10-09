#!/usr/bin/env python3
"""WattBot: frozen per-document evidence distinction in the real reader.

Exactly one changed factor vs the earlier successful 0.49709 candidate:
choose at most one page per document among the same top-100 BM25
candidates, BEFORE the unchanged 1100-character question-centred
windowing. The numeric fallback still uses exactly the same top-100 hits.

The chosen cap-one policy was selected from development TRAIN labels by
the separate source_refinement_probe.py. TRAIN 63-question holdout is
reused and therefore not independent. No Kaggle TEST scoring or submission.
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

BASE_BLOB = "4e1350ef72a44a333862dec23c737a2262ab99bc"
OFFICIAL_SHA = {
    "Score.py": "e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075",
    "metadata.csv": "b54eb64f7747493443465a58822f87bc12655ee8aab9be83b0958222bb3c1ca1",
    "train_QA.csv": "9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca",
}
SOURCE_SHA = "4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
OLD_SCORE = .49708995
OLD_RUN = 37968840780
SELECTED_BY_DEV_RUN = 37971417821


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest()


def cap_one_window(question, passages, top_k=6, excerpt=1100):
    seen = set()
    selected = []
    for source in passages:
        if source["page"] < 1 or source["ref_id"] in seen:
            continue
        seen.add(source["ref_id"])
        selected.append(source)
        if len(selected) == top_k:
            break
    return window_passages(question, selected, excerpt)


def self_test():
    assert git_blob(Path(base.__file__).read_bytes()) == BASE_BLOB
    assert base.SOURCE_BUDGET == 114
    assert base.K == 6 and base.MAX_EXCERPT == 1100
    assert base.MODEL == "google/gemini-2.5-flash-lite"
    ranked = [
        dict(ref_id="a", page=1, url="a", text="alpha "+
             "intro "*180+"energy used 100 MWh"),
        dict(ref_id="a", page=2, url="a", text="alpha extra"),
        dict(ref_id="b", page=1, url="b", text="beta MWh"),
        dict(ref_id="c", page=0, url="c", text="metadata only"),
        dict(ref_id="c", page=3, url="c", text="gamma MWh"),
    ]
    windows = cap_one_window("energy used", ranked)
    assert [c["ref_id"] for c in windows] == ["a","b","c"]
    assert all(len(c["text"]) <= base.MAX_EXCERPT for c in windows)
    # This experiment holds the original window policy FIXED; numeric right-edge
    # cropping is a separate residual, not silently repaired in a cap-one test.
    assert "energy used" in windows[0]["text"]
    for p, q in zip([ranked[0],ranked[2],ranked[4]], windows):
        assert q["text"] == p["text"][q["excerpt_start"]:q["excerpt_end"]]
        assert all(p[k] == q[k] for k in ("ref_id","url","page"))
    print("WATTBOT_CAP1_WINDOW_SELF_TEST=PASS")


def run(archive):
    self_test()
    with zipfile.ZipFile(archive) as z:
        for path, expected in OFFICIAL_SHA.items():
            if hashlib.sha256(z.read(path)).hexdigest() != expected:
                raise RuntimeError("Official pinned data changed: " + path)

    prior = base.passages_for
    audit = Counter()
    def replace(question, all_chunks):
        original, all_hits = prior(question, all_chunks)
        selected = cap_one_window(question, all_hits,
                                  base.K, base.MAX_EXCERPT)
        audit["questions"] += 1
        audit["selected_pages"] += len(selected)
        audit["distinct_selected_sources"] += len({x["ref_id"] for x in selected})
        audit["windows_shifted"] += sum(x["excerpt_start"] > 0 for x in selected)
        audit["baseline_unique_sources"] += len({x["ref_id"] for x in original})
        # Enforce no candidate outside the original ranked corpus.
        assert all(any(x["ref_id"]==y["ref_id"] and x["page"]==y["page"]
                       and x["url"]==y["url"] and
                       x["text"]==y["text"][x["excerpt_start"]:x["excerpt_end"]]
                       for y in all_hits) for x in selected)
        assert len(selected) == len(original) == base.K
        return selected, all_hits

    output = io.StringIO()
    try:
        base.passages_for = replace
        with redirect_stdout(output):
            base.run(archive)
    finally:
        base.passages_for = prior
    prefix="WATTBOT_FULL_READER_HOLDOUT="
    rows = [json.loads(x[len(prefix):]) for x in output.getvalue().splitlines()
            if x.startswith(prefix)]
    if len(rows) != 1:
        raise RuntimeError("No complete original scorer result")
    score = rows[0]
    if score["source_manifest_sha256"] != SOURCE_SHA:
        raise RuntimeError("Corpus SHA mismatch")
    if score["holdout_rows"] != 63 or audit["questions"] != 63:
        raise RuntimeError("Holdout definition changed")
    result = {
        "status":"CANDIDATE",
        "scope":"Reused 63-question TRAIN holdout with exact official Score.py",
        "selected_policy":"cap1 chosen by TRAIN development labels only",
        "policy_selection_run":SELECTED_BY_DEV_RUN,
        "matched_source_corpus_sha256":SOURCE_SHA,
        "baseline_historical_score":OLD_SCORE,
        "baseline_historical_run":OLD_RUN,
        "same_run_model_pairing":False,
        "score":score["scores"]["reader_then_numeric_fallback"],
        "delta_vs_historical":round(score["scores"]["reader_then_numeric_fallback"]-OLD_SCORE,8),
        "scores":score["scores"],
        "outcomes":score["outcomes"],
        "retrieval_audit":dict(audit),
        "reserved_usd":score["max_reserved_usd"],
        "observed_api_usd":score["observed_api_usd"],
        "boundary":"TRAIN labels score only after predictions; no Kaggle test submission. "
                   "PDF quote checks are provenance, not semantic entailment.",
    }
    print("WATTBOT_CAP1_WINDOW_HOLDOUT="+json.dumps(result, sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    a=p.parse_args()
    if a.self_test:
        self_test()
    elif a.official_zip:
        run(a.official_zip)
    else:
        p.error("Provide --self-test or --official-zip")
