#!/usr/bin/env python3
"""WattBot: preserve justified 'is_blank' as a distinct consequence class.

Official scoring requires answer_value and all evidence columns to be
is_blank when a question is unanswerable. A failure of an LLM quote or a
weak retrieved passage is NOT proof of unanswerability. This module exposes
bounded, label-free policies to evaluate that distinction post inference.

Any percentile decision uses only corpus-retrieval scores for the current
question set, never gold answers/citations or protected TEST labels.
"""
from __future__ import annotations
from math import ceil

NA={"", "is_blank", "n/a", "na", "nan", "none", "null", "unknown"}


def explicit_model_refusal(raw):
    return (isinstance(raw,dict) and "answer_value" in raw and
            str(raw["answer_value"]).strip().casefold() in NA)


def retrieval_threshold(scores, fraction):
    if not 0<=fraction<=1:
        raise ValueError("Quantile must be in 0..1")
    ordered=sorted(float(x) for x in scores)
    if not ordered:return 0.
    index=max(0,min(len(ordered)-1,ceil(fraction*len(ordered))-1))
    return ordered[index]


def refusal_row(blank_row, reason):
    """No citation is manufactured for a refusal."""
    d=dict(blank_row)
    d.update({
        "answer":"Unable to answer with confidence from the provided documents.",
        "answer_value":"is_blank",
        "answer_unit":"is_blank",
        "ref_id":"is_blank",
        "ref_url":"is_blank",
        "supporting_materials":"is_blank",
        "explanation":"UNKNOWN: "+reason+
            ". Evidence is insufficient; no source assertion is made.",
    })
    return d


def policy_row(policy, blank, first, raw, max_score, thresholds):
    if policy=="never_blank":
        return dict(first)
    refuse=explicit_model_refusal(raw)
    weak5=max_score<=thresholds["p05"]
    weak10=max_score<=thresholds["p10"]
    weak40=max_score<=thresholds["p40"]
    if policy=="model_explicit":
        abstain=refuse
    elif policy=="model_explicit_weak40":
        abstain=refuse and weak40
    elif policy=="model_explicit_weak10":
        abstain=refuse and weak10
    elif policy=="weak_retrieval5":
        abstain=weak5
    elif policy=="weak_retrieval10":
        abstain=weak10
    elif policy=="explicit_or_weak5":
        abstain=refuse or weak5
    else:
        raise ValueError("Unregistered abstention policy")
    return (refusal_row(blank,policy) if abstain else dict(first))


def self_test():
    blank={
        "id":"q","question":"How much does a unicorn weigh?",
        "answer":"Unable","answer_value":"is_blank","answer_unit":"is_blank",
        "ref_id":"is_blank","ref_url":"is_blank",
        "supporting_materials":"is_blank","explanation":"No evidence",
    }
    numeric=dict(blank,answer="50 kg",answer_value="50",ref_id="['x']")
    thresholds={"p05":1.,"p10":2.,"p40":5.}
    raw={"answer_value":"is_blank"}
    assert explicit_model_refusal(raw)
    assert not explicit_model_refusal({"answer_value":"0"})
    assert retrieval_threshold([4,1,3,2,5],.4)==2
    assert policy_row("model_explicit",blank,numeric,9.,thresholds)["ref_id"]=="is_blank"
    assert policy_row("model_explicit_weak40",blank,numeric,9.,thresholds)==numeric
    assert policy_row("explicit_or_weak5",blank,numeric,9.,thresholds)["answer_value"]=="is_blank"
    assert policy_row("weak_retrieval5",blank,numeric,9.,thresholds)==numeric
    assert policy_row("never_blank",blank,numeric,0.,thresholds)==numeric
    d=refusal_row(blank,"closed without invented citations")
    assert all(d[k]=="is_blank" for k in (
        "answer_value","ref_id","ref_url","supporting_materials"))
    assert d["explanation"]
    print("WATTBOT_ABSTENTION_BOUNDARY_SELF_TEST=PASS")


if __name__=="__main__":
    self_test()
