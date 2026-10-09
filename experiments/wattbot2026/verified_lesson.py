#!/usr/bin/env python3
"""WattBot developmental example compiler: transfer validated answer CONVENTIONS.

Only the 182 development TRAIN examples can be used. The frozen 63 TRAIN
holdout and protected TEST answers are never eligible for exemplars.
Examples teach how to format and derive answer_value, not source evidence
for the live question. They are not treated as a source of ground truth
about a new scientific claim. No handwritten per-question answer mapping.
"""
from __future__ import annotations
import hashlib
import math
import re

from holdout_probe import is_holdout
from wattbot import tokens

STOP=frozenset(("the a an in on of to for by with from and or is was were "
                "what how much many which according according-to a at as "
                "this that did does do paper study papers studies reporting "
                "reported about using use if it its").split())

TYPES=("CrossPaper","Math","Table","Figure","Quote")


def task_type(question):
    q=question.casefold()
    if re.search(r"\b(both|two|multiple)\s+(papers?|studies|reports?)\b|"
                 r"\bacross\s+(?:the\s+)?(?:two|both)\s+"
                 r"(?:papers?|studies|reports?)\b|"
                 r"\b(?:compare|comparison|reconcile|reconciliation)\s+"
                 r"(?:the\s+)?(?:studies|papers|reports|estimates)\b",q):
        return "CrossPaper"
    if re.search(r"\b(percentage|percent|ratio|fraction|difference|"
                 r"calculate|compute|derive|arithmetic|average|mean|"
                 r"divide|times|per\s+household|household-years|"
                 r"percent\s+change|range\s+of|equivalent|"
                 r"upper\s+bound|lower\s+bound)\b",q):
        return "Math"
    if re.search(r"\b(table|tabulated|row|column)\b",q):
        return "Table"
    if re.search(r"\b(figure|plot|graph|chart|bar)\b",q):
        return "Figure"
    return "Quote"


def sig_words(text):
    return set(tokens(str(text).casefold())) - STOP


def similarity(a,b):
    aa,bb=sig_words(a),sig_words(b)
    if not aa or not bb:return 0.
    return len(aa&bb)/math.sqrt(len(aa)*len(bb))


def examples_for(question, dev_rows, max_examples=3):
    """Query-only deterministic selector over allowed development demonstrations."""
    if not 0<max_examples<=3:
        raise ValueError("Bounded exemplar count is 1..3")
    target=task_type(question)
    options=[]
    qnorm=" ".join(str(question).casefold().split())
    for row in dev_rows:
        if is_holdout(str(row["id"])):
            raise RuntimeError("Protected holdout encountered in exemplar memory")
        other=str(row["question"])
        if " ".join(other.casefold().split())==qnorm:
            continue
        value=str(row.get("answer_value","")).strip()
        if not value or value.casefold() in ("is_blank","na","n/a","nan","none"):
            continue
        pool=str(row.get(target,"")).strip().lower()
        same=(pool in ("1","true","yes","y","x"))
        lexical=similarity(question,other)
        # Exclude near duplicates; we are transferring a lesson, not copying
        # a nearly identical target question/answer.
        if lexical>=.90:
            continue
        salt=hashlib.sha256(("wattbot-demonstration-v1|"+str(row["id"])).encode()).hexdigest()
        rank=(-int(same),-lexical,salt)
        options.append((rank,row))
    options.sort(key=lambda p:p[0])
    return [item for _,item in options[:max_examples]]


def illustrate(question, dev_rows):
    selections=examples_for(question,dev_rows)
    if len(selections)!=3:
        raise RuntimeError("Too few development-only worked examples")
    demo=[]
    for row in selections:
        demo.append({
            "worked_question":str(row["question"])[:230],
            "worked_answer_value":str(row["answer_value"])[:100],
            "worked_answer_unit":str(row.get("answer_unit","is_blank"))[:50],
            "worked_explanation":str(row.get("explanation",""))[:280],
        })
    # This text is sent as INSTRUCTION EXAMPLES only, not test/evidence.
    import json
    return (
        "\n\nFORMATTING AND SCIENTIFIC REASONING EXAMPLES (TRAIN DEVELOPMENT ONLY):\n"
        +json.dumps(demo,ensure_ascii=False,separators=(",",":"))
        +"\nThe worked questions and their numbers are NOT evidence for "
         "the current question. Never copy a worked answer value, paper, "
         "or supporting citation into the current answer. Use only the "
         "current question's separately supplied source passages. "
         "Apply the same output convention: exact scalar, correct range "
         "format, normalized units, or is_blank where evidence is absent. "
         "If deriving a number, name its actual current-source inputs and "
         "carry out the arithmetic. Return independent verbatim supporting "
         "quotes for the current question; no invented precision."
    )


def self_test():
    assert task_type("Compare both studies' carbon impact.")=="CrossPaper"
    assert task_type("What ratio of water use to electricity?")=="Math"
    assert task_type("What does Figure 3 plot?")=="Figure"
    assert task_type("How many tons were reported?")=="Quote"
    sample=[
       {"id":"d1","question":"What percent decrease was observed?",
        "Math":"True","CrossPaper":"False","answer_value":"19.6",
        "answer_unit":"percent","explanation":"Exactly 100*(a-b)/a."},
       {"id":"d2","question":"How much energy use was measured?",
        "Math":"False","Quote":"True","answer_value":"10",
        "answer_unit":"MWh","explanation":"Direct measurement."},
       {"id":"d3","question":"What did Table 4 indicate?",
        "Table":"True","answer_value":"23","answer_unit":"MWh",
        "explanation":"Table row was read."},
    ]
    # The synthetic fixture IDs must be genuinely on the DEVELOPMENT side
    # of the official hash split; refuse to weaken that invariant for tests.
    for row in sample:
        while is_holdout(str(row["id"])):
            row["id"]+="_dev"
    chosen=examples_for("What was the percent decrease?",sample)
    assert len(chosen)==3 and chosen[0]["id"]=="d1"
    text=illustrate("What was the percent decrease?",sample)
    assert "TRAIN DEVELOPMENT ONLY" in text
    assert "NOT evidence" in text
    assert "19.6" in text
    print("WATTBOT_VERIFIED_LESSON_ARITY3_SELF_TEST=PASS")


if __name__=="__main__":
    self_test()
