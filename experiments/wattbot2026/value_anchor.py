#!/usr/bin/env python3
"""Exact-value source quotation repair from independently green TRAIN ablation.

Copied without policy changes from verified
wattbot-value-anchor-repair-v1: value_anchor_repair_probe.py Git blob
3df3470fa301df6101e156d77242a373fb77da0f, run 37971044770, same-response 0.50899471 -> 0.57830688.
The original source data and model replies are untrusted; only literal page
provenance is certified. Semantic entailment of the answer remains unverified.
No gold TRAIN or protected TEST labels are imported by this module.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import re
import full_reader as base
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



if __name__=="__main__":
    self_test()
