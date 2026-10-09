#!/usr/bin/env python3
"""WattBot: score the exact ANSWER-VALUE residual without pretending provenance.

Replays the pinned 63-row TRAIN holdout with the already-qualified
full-corpus Flash-Lite reader and question-centred evidence windows.
Makes exactly one bounded LLM call per question. Scores alternative
UNVERIFIED answer transport arms from the SAME responses using immutable
official Score.py AFTER outputs are frozen. No Kaggle TEST or submission.

An answer whose quotation cannot be independently located is CANDIDATE,
never PAGE_QUOTE_VERIFIED. Experimental citation arms are explicitly
labelled and cannot be promoted as science evidence.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import zipfile

import pandas as pd

import full_reader as base
from citation_refinement import retarget, self_test as citation_self_test
from holdout_probe import is_holdout
from query_window import window_passages
from score_ablation import load_score

BASE_BLOB = "4e1350ef72a44a333862dec23c737a2262ab99bc"
SOURCE_PIN = "4081ce09ef2f62a7ef0faf577f1fe201108ff5789a7b8659d64380cd7f9724a9"
TRAIN_SHA = "9cbc25a9cb6133e1ef833fad6eb7fe43f9b72c1533b39d3b1ae94b3172407dca"
SCORER_SHA = "e5050458932b7a3fc0f4040303d3ae7c0459a786cf0efbb52c2f1ac338bbd075"
HISTORICAL_WINDOW_SCORE = .49708995
HISTORICAL_WINDOW_RUN = 37968840780
BLANK = {"is_blank", "unknown", "na", "n/a", "nan", "null", "none", ""}


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + bytes([0]) + data).hexdigest()


def usable(raw):
    return (isinstance(raw, dict) and
            str(raw.get("answer_value", "")).strip().casefold() not in BLANK)


def answer_fields(raw):
    value = str(raw["answer_value"]).strip()
    unit = str(raw.get("answer_unit", "is_blank") or "").strip()
    if unit.casefold() in BLANK:
        unit = "is_blank"
    return {
        "answer": str(raw.get("answer", value) or value).strip()[:800],
        "answer_value": value,
        "answer_unit": unit,
        "explanation": "UNVERIFIED MODEL CANDIDATE: answer text has not earned page provenance",
    }


def chosen_refs(raw, passages):
    # A model-supplied index is provisional and NOT a verified quote.
    picks = raw.get("source_indices")
    if not isinstance(picks, list) or not picks:
        picks = [raw.get("source_index")]
    selected = []
    seen = set()
    for idx in picks:
        if type(idx) is int and 0 <= idx < len(passages):
            p = passages[idx]
            if p["ref_id"] not in seen:
                selected.append(p)
                seen.add(p["ref_id"])
        if len(selected) >= 3:
            break
    return selected if selected else list(passages[:1])


def raw_variant(blank_row, raw, numeric, passages, refs_mode):
    if not usable(raw):
        return dict(numeric)
    result = dict(blank_row)
    result.update(answer_fields(raw))
    if refs_mode == "numeric":
        for k in ("ref_id", "ref_url", "supporting_materials"):
            result[k] = numeric[k]
        result["explanation"] += "; citations are unchanged independent numeric fallback candidates"
    elif refs_mode == "selected":
        cited = chosen_refs(raw, passages)
        result["ref_id"] = repr([p["ref_id"] for p in cited]) if cited else "is_blank"
        result["ref_url"] = repr([p["url"] for p in cited]) if cited else "is_blank"
        # DO NOT copy unsupported model quotations and pretend to verify them.
        result["supporting_materials"] = "is_blank"
        result["explanation"] += "; provisional model-indexed source IDs (no quote certificate)"
    elif refs_mode != "none":
        raise ValueError("Unexpected refs_mode")
    return result


def self_test():
    citation_self_test()
    assert git_blob(Path(base.__file__).read_bytes()) == BASE_BLOB
    assert base.MODEL == "google/gemini-2.5-flash-lite"
    assert base.K == 6 and base.MAX_EXCERPT == 1100 and base.MAX_REQUESTS == 63
    q = {
        "id":"1","question":"What energy was used?", "answer":"no evidence",
        "answer_value":"is_blank", "answer_unit":"is_blank",
        "ref_id":"is_blank", "ref_url":"is_blank", "supporting_materials":"is_blank",
        "explanation":"Unknown"
    }
    num=dict(q, answer="23 MWh",answer_value="23",
             ref_id="['a']",ref_url="['https://arxiv.org/abs/2601.00001']")
    raw={"answer":"31 MWh", "answer_value":"31", "answer_unit":"NA", "source_index":1}
    pages=[
        {"ref_id":"a","url":"https://arxiv.org/abs/2601.00001","page":2,"text":"evidence"},
        {"ref_id":"b","url":"https://arxiv.org/abs/2601.00002","page":3,"text":"evidence"},
    ]
    assert raw_variant(q,raw,num,pages,"none")["ref_id"]=="is_blank"
    assert raw_variant(q,raw,num,pages,"numeric")["ref_id"]=="['a']"
    t=raw_variant(q,raw,num,pages,"selected")
    assert t["ref_id"]=="['b']" and t["supporting_materials"]=="is_blank"
    assert t["answer_value"]=="31" and t["answer_unit"]=="is_blank"
    assert raw_variant(q,{"answer_value":"is_blank"},num,pages,"selected")==num
    print("WATTBOT_VALUE_RESIDUAL_SELF_TEST=PASS")


def run(archive):
    self_test()
    with zipfile.ZipFile(archive) as z:
        if hashlib.sha256(z.read("train_QA.csv")).hexdigest()!=TRAIN_SHA:
            raise RuntimeError("Official TRAIN data changed")
        if hashlib.sha256(z.read("Score.py")).hexdigest()!=SCORER_SHA:
            raise RuntimeError("Official Score.py changed")

    original_passages = base.passages_for
    original_reader = base.call_reader
    original_numeric = base.build_candidate
    original_check = base.try_checked
    response_map = {}
    passage_map = {}
    numeric_map = {}
    checked_map = {}
    counters = Counter()
    def windowed(question, chunks):
        original, hits = original_passages(question, chunks)
        pages = window_passages(question, original, base.MAX_EXCERPT)
        counters["questions"] += 1
        counters["pages"] += len(pages)
        counters["shifted"] += sum(p["excerpt_start"] != 0 for p in pages)
        for first, second in zip(original, pages):
            for key in ("ref_id", "page", "url"):
                assert first[key] == second[key]
            assert second["text"] == first["text"][
                second["excerpt_start"]:second["excerpt_end"]]
        return pages,hits
    def record_model(key, question, passages, pricing):
        raw, status, reserve, actual = original_reader(key, question, passages, pricing)
        if question in response_map:
            raise RuntimeError("Question duplicated")
        response_map[question] = (raw,status)
        passage_map[question] = list(passages)
        return raw,status,reserve,actual
    def record_numeric(question, hits, docs):
        result=original_numeric(question,hits,docs)
        # First call is all-pinned-corpus numeric, later calls are controls.
        if question["id"] not in numeric_map:
            numeric_map[question["id"]]=result
        return result
    def record_checked(raw, question, passages, docs):
        candidate, status=original_check(raw,question,passages,docs)
        checked_map[question["id"]]=(candidate,status)
        return candidate,status

    captured=io.StringIO()
    try:
        base.passages_for = windowed
        base.call_reader = record_model
        base.build_candidate = record_numeric
        base.try_checked = record_checked
        with redirect_stdout(captured):
            base.run(archive)
    finally:
        base.passages_for=original_passages
        base.call_reader=original_reader
        base.build_candidate=original_numeric
        base.try_checked=original_check

    marker="WATTBOT_FULL_READER_HOLDOUT="
    original_scores=[json.loads(s[len(marker):]) for s in captured.getvalue().splitlines()
                     if s.startswith(marker)]
    if len(original_scores)!=1:
        raise RuntimeError("Expected exactly one frozen baseline official scorer result")
    baseline=original_scores[0]
    if baseline["source_manifest_sha256"]!=SOURCE_PIN or baseline["holdout_rows"]!=63:
        raise RuntimeError("Source authority changed")
    if counters["questions"]!=63 or len(numeric_map)!=63 or len(response_map)!=63:
        raise RuntimeError("Unexpected partial model cohort")
    if counters["pages"]!=378:
        raise RuntimeError("Frozen evidence page count changed")

    with zipfile.ZipFile(archive) as z:
        train=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                          keep_default_na=False,dtype={"id":str})
        hold=train[train["id"].map(is_holdout)].reset_index(drop=True)
        blank=base.blank_submission(hold).reset_index(drop=True)
        original_columns=list(blank.columns)
        modes={
            "raw_no_refs":[],
            "raw_numeric_refs":[],
            "raw_model_source_refs":[],
            "strict_then_raw_no_refs":[],
            "strict_then_raw_numeric_refs":[],
            "strict_then_raw_model_refs":[],
            "strict_then_raw_top1_refs":[],
            "strict_then_raw_literal_refs":[],
            "strict_then_raw_quote_refs":[],
            "strict_then_raw_dual_refs":[],
            "strict_then_raw_hybrid_refs":[],
        }
        diagnosis=Counter()
        for _,row in blank.iterrows():
            question=str(row["question"])
            ident=str(row["id"])
            if question not in response_map:
                raise RuntimeError("Question source missing model record")
            response, api_status = response_map[question]
            passages=passage_map[question]
            numeric=numeric_map[ident]
            strict,check=checked_map.get(ident,(None,"NOT_ADMITTED"))
            diagnosis[api_status]+=1
            diagnosis[check]+=1
            diagnosis["usable_raw"]+=int(usable(response))
            diagnosis["rescued_unanchored"]+=int(usable(response) and strict is None)
            for mode,key in (
                ("raw_no_refs","none"),
                ("raw_numeric_refs","numeric"),
                ("raw_model_source_refs","selected"),
            ):
                candidate=raw_variant(row,response,numeric,passages,key)
                modes[mode].append(candidate)
                strict_mode="strict_then_"+("raw_model_refs" if key=="selected"
                              else "raw_numeric_refs" if key=="numeric" else "raw_no_refs")
                modes[strict_mode].append(dict(strict) if strict is not None else candidate)
            original=raw_variant(row,response,numeric,passages,"selected")
            for policy,name in (
                ("top1","strict_then_raw_top1_refs"),
                ("literal","strict_then_raw_literal_refs"),
                ("quote","strict_then_raw_quote_refs"),
                ("dual","strict_then_raw_dual_refs"),
                ("hybrid","strict_then_raw_hybrid_refs"),
            ):
                proposal=retarget(original,response,question,passages,policy)
                diagnosis[policy+"_source_changed"]+=int(
                    proposal["ref_id"]!=original["ref_id"])
                if proposal["answer_value"]!=original["answer_value"]:
                    raise RuntimeError("Source-only policy changed an answer value")
                modes[name].append(dict(strict) if strict is not None else proposal)

        with tempfile.TemporaryDirectory(prefix="wattbot_value_score_") as tmp:
            scorer=load_score(z,tmp)
            def official(rows):
                df=pd.DataFrame(rows,columns=original_columns)
                return round(float(scorer(hold.copy(deep=True),df,
                    row_id_column_name="id",verbose=False)),8)
            scores={}
            invalid={}
            for name,rows in modes.items():
                try:
                    scores[name]=official(rows)
                except (ValueError,TypeError,KeyError,AssertionError) as err:
                    invalid[name]=type(err).__name__
    comparison=baseline["scores"]["reader_then_numeric_fallback"]
    improvements={k:round(v-comparison,8) for k,v in scores.items()}
    source_only_delta={k:round(v-scores["strict_then_raw_model_refs"],8)
                       for k,v in scores.items() if k.startswith("strict_then_raw_")
                       and k not in ("strict_then_raw_model_refs",
                                     "strict_then_raw_numeric_refs",
                                     "strict_then_raw_no_refs")}
    result={
       "status":"EXPLORATORY_CANDIDATE",
       "scope":"Same 63 historic TRAIN questions and same LLM responses for all arms",
       "model":base.MODEL,
       "source_manifest_sha256":SOURCE_PIN,
       "base_reader_same_run":baseline["scores"],
       "same_run_baseline":comparison,
       "historical_window_baseline":HISTORICAL_WINDOW_SCORE,
       "historical_window_run":HISTORICAL_WINDOW_RUN,
       "alternative_scores":scores,
       "score_delta_vs_same_run_baseline":improvements,
       "source_policy_deltas_vs_same_raw_model_source":source_only_delta,
       "invalid_modes":invalid,
       "counters":dict(diagnosis),
       "contexts":dict(counters),
       "observed_api_usd":baseline["observed_api_usd"],
       "reserved_api_usd":baseline["max_reserved_usd"],
       "boundary":"Same model response AND answer_value across citation-only "
                  "policies. Independent literal/quote overlap can suggest a source "
                  "but does not certify semantic entailment. The original page "
                  "quotation verifier retains authority for strict policies. "
                  "TRAIN scorer used only after outputs are frozen; no hidden "
                  "TEST labels or Kaggle submission.",
    }
    print("WATTBOT_SOURCE_QUOTIENT_ABLATION="+json.dumps(result,sort_keys=True),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--official-zip")
    args=parser.parse_args()
    if args.self_test:
        self_test()
    elif args.official_zip:
        run(args.official_zip)
    else:
        parser.error("Provide --self-test or --official-zip")
