#!/usr/bin/env python3
"""WattBot complete-corpus quoted-value repair, same-response causal ablation.

Use the unchanged full-corpus question-centred reader and its pinned model.
If a proposed quotation fails exact source-page verification, try admitting the
already proposed answer ONLY when its literal numeric or textual value is
uniquely anchored in an authorized passage, with nearby question context.
Otherwise preserve UNKNOWN and the original numeric fallback. No response is
regenerated and no gold TRAIN value/reference enters candidate generation.

The evaluation uses previously inspected TRAIN holdout (63 rows). It is NOT
an independent test, leaderboard result, nor a semantic entailment proof.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import redirect_stdout
from decimal import Decimal
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import zipfile

import pandas as pd

import full_reader as base
import full_window_probe as window
from holdout_probe import is_holdout
from score_ablation import load_score
from wattbot import NUM_RE, as_fraction, norm, tokens, verify_candidate

STOP = frozenset(("a an the is was what how much many in of for from to by on "
    "and or are were which their its according as at during with using does did "
    "this that per about than the paper study model source reported estimate").split())
REPAIRABLE = frozenset(("QUOTATION_NOT_ANCHORED","QUOTATION_TOO_SHORT",
                        "MISSING_SOURCE_INDEX"))
SOURCE_READER_BLOB = "4e1350ef72a44a333862dec23c737a2262ab99bc"
WINDOW_BLOB = "8b3e37e4e1b0ebd36bb157ec73f8d51354e5cdf7"


def git_blob(path):
    data=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def locate_numeric(value, passage):
    """Return spans of exactly equivalent Decimal literal values only."""
    try:
        requested=as_fraction(str(value))
    except (ValueError, TypeError):
        return []
    result=[]
    for match in NUM_RE.finditer(passage):
        try:
            parsed=as_fraction(match.group())
        except (ValueError, TypeError):
            continue
        if parsed==requested:
            result.append((match.start(),match.end()))
    return result


def locate_text(value, passage):
    value=str(value).strip()
    if len(value)<10 or len(value)>120:
        return []
    return [(m.start(),m.end()) for m in
            re.finditer(re.escape(value),passage,flags=re.I)]


def repaired_by_value(generated,question,passages,docs,original_reason):
    if original_reason not in REPAIRABLE or not isinstance(generated,dict):
        return None,"NOT_REPAIRABLE"
    value=str(generated.get("answer_value","")).strip()
    if not value or value.casefold() in ("is_blank","unknown","n/a","nan"):
        return None,"ABSTAIN"
    # Never erase a declared multi-paper premise with a single-paper quote.
    explicit=generated.get("source_indices")
    if isinstance(explicit,list) and len(explicit)>1:
        return None,"MULTIPAPER_REQUIREMENT"
    unit=str(generated.get("answer_unit","") or "").strip()
    unit_needed=unit.casefold() not in ("","is_blank","n/a","nan")
    focus=set(tokens(str(question.get("question",""))))-STOP
    candidates=[]
    numeric = bool(locate_numeric(value,"0 "+value+" "))
    for passage in passages:
        body=str(passage.get("text",""))
        if not body or int(passage.get("page",0))<1:
            continue
        spans=(locate_numeric(value,body) if numeric
               else locate_text(value,body))
        for left,right in spans:
            start=max(0,left-125)
            end=min(len(body),right+125)
            quote=body[start:end].strip()
            if len(quote)<12:
                continue
            if unit_needed and unit.casefold() not in quote.casefold():
                continue
            matching=focus.intersection(set(tokens(quote)))
            if len(matching)<2:
                continue
            candidates.append((len(matching),passage,quote,left))
    sources={p["ref_id"] for _,p,_,_ in candidates}
    if len(sources)!=1:
        return None,("AMBIGUOUS_SOURCE" if sources else "NO_UNIQUE_LITERAL")
    # Deterministic choice within one source: most question words, then page,
    # then first local literal. No gold references/answers are consulted.
    candidates.sort(key=lambda x:(-x[0],int(x[1]["page"]),x[3]))
    _, source, quote, _ = candidates[0]
    candidate={
        "id":str(question["id"]),
        "answer":str(generated.get("answer") or value),
        "answer_value":value,
        "ref_ids":[source["ref_id"]],
        "evidence":[{"ref_id":source["ref_id"],"page":int(source["page"]),"quote":quote}],
        "explanation":("Candidate literal answer located in one uniquely anchored "
           "authorized source page; semantic implication and unit meaning not proved"),
    }
    try:
        checked=verify_candidate(candidate,question,docs,passages)
        checked["answer_unit"]=unit if unit_needed else "is_blank"
        return checked,"VALUE_LITERAL_PAGE_ANCHORED"
    except (ValueError,KeyError,TypeError,ZeroDivisionError):
        return None,"INDEPENDENT_CHECK_REJECTED"


def self_test():
    assert base.K==6 and base.MAX_EXCERPT==1100
    assert git_blob(base.__file__)==SOURCE_READER_BLOB
    assert git_blob(Path(__file__).with_name("query_window.py"))==WINDOW_BLOB
    url="https://arxiv.org/abs/2601.00001"
    good={"ref_id":"p1","url":url,"page":2,"text":
       "The cooling electricity use in this study was 1,287 MWh for the year 2025."}
    question={"id":"q","question":"What was the cooling electricity use in MWh?"}
    generated={"answer":"1287 MWh","answer_value":"1287","answer_unit":"MWh"}
    checked,status=repaired_by_value(generated,question,[good],{"p1":{"url":url}},
                                       "QUOTATION_NOT_ANCHORED")
    assert status=="VALUE_LITERAL_PAGE_ANCHORED" and checked is not None
    assert checked["answer_value"]=="1287" and checked["ref_id"]=="['p1']"
    another=dict(good,ref_id="p2",url="https://arxiv.org/abs/2601.00002")
    bad,why=repaired_by_value(generated,question,[good,another],
               {"p1":{"url":url},"p2":{"url":another["url"]}},
               "QUOTATION_NOT_ANCHORED")
    assert bad is None and why=="AMBIGUOUS_SOURCE"
    bad,why=repaired_by_value({"answer_value":"9999","answer_unit":"MWh"},
               question,[good],{"p1":{"url":url}},"QUOTATION_NOT_ANCHORED")
    assert bad is None and why=="NO_UNIQUE_LITERAL"
    bad,why=repaired_by_value(dict(generated,source_indices=[0,1]),
               question,[good],{"p1":{"url":url}},"QUOTATION_NOT_ANCHORED")
    assert bad is None and why=="MULTIPAPER_REQUIREMENT"
    assert repaired_by_value(generated,question,[good],{"p1":{"url":url}},
                             "AMBIGUOUS_QUOTATION_SOURCE")[0] is None
    print("VALUE_ANCHOR_SELF_TEST=PASS")


def run(official_zip):
    self_test()
    numeric={}
    original={}
    repairs={}
    outcomes=Counter()
    original_build=base.build_candidate
    original_checked=base.try_checked
    def record_numeric(question,hits,docs):
        result=original_build(question,hits,docs)
        numeric.setdefault(str(question["id"]),result)
        return result
    def checked_then_repair(generated,question,passages,docs):
        question_id=str(question["id"])
        candidate,reason=original_checked(generated,question,passages,docs)
        if candidate is not None:
            original[question_id]=candidate
            return candidate,reason
        repaired,status=repaired_by_value(
            generated,question,passages,docs,reason)
        outcomes[reason]+=1
        outcomes[status]+=1
        if repaired is not None:
            repairs[question_id]=repaired
            return repaired,status
        return candidate,reason
    base.build_candidate=record_numeric
    base.try_checked=checked_then_repair
    output=io.StringIO()
    try:
        with redirect_stdout(output):
            window.run(official_zip)
    finally:
        base.build_candidate=original_build
        base.try_checked=original_checked
    messages=[json.loads(line.split("=",1)[1])
             for line in output.getvalue().splitlines()
             if line.startswith("WATTBOT_COMPLETE_WINDOW_QUALIFICATION=")]
    if len(messages)!=1:
        raise RuntimeError("Expected one fully scored complete-corpus result")
    reported=messages[0]
    if reported.get("source_manifest_sha256")!=window.BASELINE_CORPUS_SHA256:
        raise RuntimeError("PDF source bytes changed")
    with zipfile.ZipFile(official_zip) as z, tempfile.TemporaryDirectory() as td:
        gold=pd.read_csv(io.BytesIO(z.read("train_QA.csv")),
                         keep_default_na=False,dtype={"id":str})
        hold=gold[gold["id"].map(is_holdout)].copy().reset_index(drop=True)
        ids=hold["id"].astype(str).tolist()
        if len(ids)!=63 or set(numeric)!=set(ids):
            raise RuntimeError("Frozen holdout numeric candidates not fully captured")
        columns=list(base.blank_submission(hold).columns)
        control=[original.get(item,numeric[item]) for item in ids]
        intervention=[repairs.get(item,original.get(item,numeric[item]))
                      for item in ids]
        scorer=load_score(z,td)
        def official(rows):
            df=pd.DataFrame(rows,columns=columns)
            return round(float(scorer(hold.copy(deep=True),df,
                      row_id_column_name="id",verbose=False)),8)
        before=official(control)
        after=official(intervention)
    if abs(after-reported["scores"]["reader_then_numeric_fallback"])>0.00000002:
        raise RuntimeError("Paired reconstructed intervention differs from full reader score")
    print("WATTBOT_VALUE_ANCHOR_REPAIR="+json.dumps({
        "basis":"same actual model replies, same 63 previously inspected train questions",
        "baseline_without_repair":before,
        "same_response_repaired":after,
        "measured_delta":round(after-before,8),
        "old_page_anchored":len(original),
        "newly_repaired":len(repairs),
        "rejection_counts":dict(outcomes),
        "pinned_source_manifest":reported["source_manifest_sha256"],
        "unchanged_model":"google/gemini-2.5-flash-lite",
        "qualified_query_window_source_run":37968840780,
        "model_observed_cost_usd":reported["observed_api_usd"],
        "boundary":"Training-only same-response ablation; literal occurrence certifies provenance, not implication; no Kaggle score",
    },sort_keys=True),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--official-zip")
    args=p.parse_args()
    if args.self_test:self_test()
    elif args.official_zip:run(args.official_zip)
    else:p.error("Use --self-test or --official-zip")
