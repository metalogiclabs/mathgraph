#!/usr/bin/env python3
"""WattBot source-quotient citation policies; answer values held FIXED.

Every returned source comes from the six already selected public PDF pages.
All policies are label-free and inspect only the question, model proposal,
and retrieved passages. Provisional associations are never called verified.
"""
from __future__ import annotations

from collections import Counter
import re

from wattbot import NUM_RE, as_fraction, norm, tokens

SIGNIFICANT = frozenset(("the a an in on of to for by with from and or is was were "
                        "this that which study paper studies papers data results result "
                        "table figure estimated estimate reported according using model").split())


def canonical(value):
    try:
        return as_fraction(str(value).strip())
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def selected_sources(raw, pages):
    picks = raw.get("source_indices")
    if not isinstance(picks,list) or not picks:
        picks=[raw.get("source_index")]
    seen=set()
    selected=[]
    for k in picks:
        if type(k) is int and 0<=k<len(pages) and pages[k]["ref_id"] not in seen:
            selected.append(pages[k])
            seen.add(pages[k]["ref_id"])
        if len(selected)>=3:
            break
    return selected if selected else list(pages[:1])


def unique_sources(pages, count=3):
    seen=set()
    found=[]
    for p in pages:
        if p["ref_id"] not in seen:
            found.append(p)
            seen.add(p["ref_id"])
        if len(found)>=count: break
    return found


def literal_matching_sources(raw,pages):
    target=canonical(raw.get("answer_value",""))
    if target is None:return []
    eligible=[]
    for p in pages:
        if p["page"]<1:continue
        for hit in NUM_RE.finditer(p["text"]):
            try:
                literal=as_fraction(hit.group())
            except (ValueError,TypeError,ZeroDivisionError):
                continue
            if literal==target:
                eligible.append(p)
                break
    return unique_sources(eligible,3)


def quote_words(raw):
    quotes=raw.get("supporting_quotes")
    if not isinstance(quotes,list) or not quotes:
        quotes=[raw.get("supporting_quote","")]
    words=Counter()
    for quote in quotes[:3]:
        for t in set(tokens(str(quote or "").casefold()))-SIGNIFICANT:
            if len(t)>=3 or t.isdigit():words[t]+=1
    return words


def quote_matching_sources(raw,pages):
    quote=quote_words(raw)
    if len(quote)<3:
        return []
    ranked=[]
    for p in pages:
        if p["page"]<1:continue
        page_words=set(tokens(p["text"].casefold()))-SIGNIFICANT
        matching=sum(v for key,v in quote.items() if key in page_words)
        coverage=matching/max(1,sum(quote.values()))
        ranked.append((coverage,matching,p))
    ranked.sort(key=lambda x:(-x[0],-x[1],pages.index(x[2])))
    if not ranked or ranked[0][0]<.50 or ranked[0][1]<3:return []
    first=ranked[0]
    # Demand source-unique evidence for confident rerouting of a model citation.
    if any(item[2]["ref_id"]!=first[2]["ref_id"] and
           item[0]>=first[0]-.13 for item in ranked[1:]):
        return []
    return [first[2]]


def cross_source_question(question):
    q=question.casefold()
    return bool(re.search(
       r"\b(?:both|two|multiple|several|different)\s+"
       r"(?:articles?|papers?|studies|reports?|publications?)\b|"
       r"\b(?:across|compare|comparing|comparison|reconcile|between)\s+"
       r"(?:both|two|the two|multiple|different)\s+"
       r"(?:papers?|studies|reports?|sources?)\b",q))


def choose(raw,question,pages,policy):
    original=selected_sources(raw,pages)
    if policy=="model":return original
    if policy=="top1":return unique_sources(pages,1)
    if policy=="literal":
        found=literal_matching_sources(raw,pages)
        return found[:1] if found else original
    if policy=="quote":
        found=quote_matching_sources(raw,pages)
        return found if found else original
    if policy=="dual":
        if not cross_source_question(question) or len(original)>1:return original
        second=next((p for p in unique_sources(pages,6)
                     if p["ref_id"]!=original[0]["ref_id"]),None)
        return (original+[second]) if second else original
    if policy=="hybrid":
        found=quote_matching_sources(raw,pages)
        if found:return found
        found=literal_matching_sources(raw,pages)
        if found and any(p["ref_id"] in {x["ref_id"] for x in original}
                         for p in found):return original
        if found and len(found)==1:return found
        if cross_source_question(question):
            return choose(raw,question,pages,"dual")
        return original
    raise ValueError("Policy not in frozen admissible alphabet")


def retarget(row,raw,question,pages,policy):
    if not isinstance(raw,dict) or str(raw.get("answer_value","")).strip().casefold() in (
        "", "is_blank", "na", "n/a", "nan", "none", "unknown", "null"):
        return dict(row)
    sources=choose(raw,question,pages,policy)
    selected=dict(row)
    if not sources: return selected
    selected["ref_id"]=repr([p["ref_id"] for p in sources])
    selected["ref_url"]=repr([p["url"] for p in sources])
    # These are NOT certified quoted answer evidence. Do not launder them.
    selected["supporting_materials"]="is_blank"
    selected["explanation"]=(
        "UNVERIFIED SOURCE PROPOSAL: "+policy+
        " over frozen retrieved PDF pages. Scientific entailment UNKNOWN.")
    return selected


def self_test():
    pages=[
        {"ref_id":"a","page":1,"url":"https://arxiv.org/abs/2601.00001",
         "text":"Solar energy generation was 13 MWh."},
        {"ref_id":"b","page":2,"url":"https://arxiv.org/abs/2601.00002",
         "text":"Wind energy generation was 24 MWh."},
    ]
    raw={"answer_value":"24","source_index":0,
         "supporting_quote":"Wind energy generation was 24 MWh."}
    assert [x["ref_id"] for x in choose(raw,"What was wind energy?",pages,"literal")]==["b"]
    assert [x["ref_id"] for x in choose(raw,"What was wind energy?",pages,"quote")]==["b"]
    assert [x["ref_id"] for x in choose(raw,"What was wind energy?",pages,"model")]==["a"]
    assert cross_source_question("Compare both studies' electricity use.")
    assert not cross_source_question("Difference between training and inference energy.")
    original={"answer":"24","answer_value":"24","ref_id":"['a']",
              "ref_url":"['https://arxiv.org/abs/2601.00001']",
              "supporting_materials":"is_blank","explanation":"not warranted"}
    changed=retarget(original,raw,"What was wind energy?",pages,"literal")
    assert changed["answer_value"]=="24" and changed["ref_id"]=="['b']"
    assert "UNVERIFIED" in changed["explanation"]
    assert retarget(original,{"answer_value":"is_blank"},
                    "What?",pages,"literal")==original
    print("WATTBOT_SOURCE_QUOTIENT_CITATION_SELF_TEST=PASS")


if __name__=="__main__":
    self_test()
