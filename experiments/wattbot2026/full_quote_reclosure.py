#!/usr/bin/env python3
"""WattBot full-corpus exact-quotation reclosure after a six-window verifier failure.

The model's own answer and quote were generated BEFORE this procedure.
Every proposed quote is searched only in independently pinned PDF page
chunks. A source is newly admitted only when every quote is exactly
present in a single, unambiguous authorized source document and passes
the original source-page verifier. No model guesses, source-ID training
labels, or gold answers can authorize a certificate.

Literal occurrence is verified; scientific entailment of the answer is not.
No hidden TEST labels and no new model calls or Kaggle submission.
"""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path

from wattbot import norm,verify_candidate

NO_VALUE=frozenset(("","is_blank","unknown","n/a","na","nan","none","null"))
REPAIRABLE=frozenset((
  "QUOTATION_NOT_ANCHORED","QUOTATION_TOO_SHORT","MISSING_SOURCE_INDEX",
  "BAD_PROVENANCE_SHAPE","AMBIGUOUS_QUOTATION_SOURCE","PAGE_CHECK_REJECTED"
))
MAX_QUOTES=3
MIN_QUOTE_LENGTH=12


def model_quotes(raw):
    if not isinstance(raw,dict):
        return []
    group=raw.get("supporting_quotes")
    if not isinstance(group,list) or not group:
        group=[raw.get("supporting_quote","")]
    if not 1<=len(group)<=MAX_QUOTES:
        return []
    quotes=[str(x or "").strip() for x in group]
    return quotes if all(len(x)>=MIN_QUOTE_LENGTH for x in quotes) else []


def frozen_pages(chunks):
    """Keep exact original source/page/text and normalized matching view."""
    return [(c,norm(c["text"])) for c in chunks if int(c.get("page",0))>0]


def reclose(raw,question,all_pages,docs,failure_reason):
    if failure_reason not in REPAIRABLE:
        return None,"NOT_A_QUOTATION_RESIDUAL"
    if not isinstance(raw,dict):
        return None,"NO_MODEL_CANDIDATE"
    value=str(raw.get("answer_value","")).strip()
    if value.casefold() in NO_VALUE:
        return None,"MODEL_REFUSED"
    quotes=model_quotes(raw)
    if not quotes:
        return None,"NO_VALID_QUOTE"
    citations=[]
    ref_ids=[]
    for literal in quotes:
        candidate_text=norm(literal)
        found=[c for c,nc in all_pages if candidate_text in nc]
        if not found:
            return None,"EXACT_QUOTE_ABSENT_FROM_PINNED_CORPUS"
        refs={c["ref_id"] for c in found}
        if len(refs)!=1:
            # Disambiguation by a model's claimed source_index is forbidden:
            # that would convert its guess into independent authority.
            return None,"AMBIGUOUS_DOCUMENT_FOR_QUOTE"
        page=min(found,key=lambda c:(int(c["page"]),c["text"][:80]))
        if page["ref_id"] not in docs:
            return None,"SOURCE_NOT_IN_PINNED_METADATA"
        if str(page["url"]) != str(docs[page["ref_id"]]["url"]):
            return None,"SOURCE_URL_MISMATCH"
        citations.append({
            "ref_id":page["ref_id"],
            "page":int(page["page"]),
            "quote":literal,
        })
        if page["ref_id"] not in ref_ids:
            ref_ids.append(page["ref_id"])
    proposal={
        "id":str(question["id"]),
        "answer":str(raw.get("answer") or value)[:800],
        "answer_value":value,
        "ref_ids":ref_ids,
        "evidence":citations,
        "explanation":"CANDIDATE: model answer retained, supporting quotation "
                      "independently located verbatim in a unique full-corpus "
                      "authorized PDF source page beyond the first six excerpts. "
                      "Scientific relevance and entailment remain UNKNOWN.",
    }
    try:
        # The *same* independent checker used for ordinary page evidence,
        # but now with the full pinned PDF source universe rather than only
        # six model windows.
        checked=verify_candidate(proposal,question,docs,
                                 [p for p,_ in all_pages])
    except (ValueError,TypeError,KeyError,ZeroDivisionError):
        return None,"INDEPENDENT_SOURCE_CHECK_REFUSED"
    unit=str(raw.get("answer_unit","is_blank") or "is_blank").strip()
    checked["answer_unit"]=unit if unit.casefold() not in NO_VALUE else "is_blank"
    return checked,"UNIQUE_FULL_CORPUS_QUOTE_CERTIFIED"


def self_test():
    docs={
        "a":{"url":"https://arxiv.org/abs/2601.11111"},
        "b":{"url":"https://arxiv.org/abs/2601.22222"},
    }
    src=[
      {"ref_id":"a","page":1,"url":docs["a"]["url"],
       "text":"Introduction to energy study."},
      {"ref_id":"a","page":8,"url":docs["a"]["url"],
       "text":"Electricity used in the evaluation was 1,287 MWh during 2025."},
      {"ref_id":"b","page":3,"url":docs["b"]["url"],
       "text":"Water consumed during evaluation was 280 litres."},
    ]
    raw={"answer":"1287 MWh","answer_value":"1287","answer_unit":"MWh",
         "source_index":0,
         "supporting_quote":"Electricity used in the evaluation was 1,287 MWh"}
    question={"id":"case","question":"How much electricity was used?"}
    found,reason=reclose(raw,question,frozen_pages(src),docs,"QUOTATION_NOT_ANCHORED")
    assert reason=="UNIQUE_FULL_CORPUS_QUOTE_CERTIFIED"
    assert found and found["answer_value"]=="1287"
    assert found["ref_id"]=="['a']" and found["answer_unit"]=="MWh"
    assert "remain UNKNOWN" in found["explanation"]
    no,reason=reclose(raw,question,frozen_pages(src[:1]),docs,
                     "QUOTATION_NOT_ANCHORED")
    assert no is None and reason=="EXACT_QUOTE_ABSENT_FROM_PINNED_CORPUS"
    twin=dict(src[1],ref_id="b",url=docs["b"]["url"])
    no,reason=reclose(raw,question,frozen_pages(src+[twin]),docs,
                     "QUOTATION_NOT_ANCHORED")
    assert no is None and reason=="AMBIGUOUS_DOCUMENT_FOR_QUOTE"
    no,reason=reclose(raw,question,frozen_pages(src),docs,"MODEL_ABSTAINED")
    assert no is None and reason=="NOT_A_QUOTATION_RESIDUAL"
    assert not model_quotes({"supporting_quote":"short","answer_value":"12"})
    print("WATTBOT_EXACT_FULL_QUOTE_RECLOSURE_SELF_TEST=PASS")


if __name__=="__main__":
    self_test()
