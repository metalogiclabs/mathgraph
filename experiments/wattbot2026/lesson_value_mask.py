#!/usr/bin/env python3
"""Counterfactual developmental-memory treatment: mask gold worked answer values.

In all arms, two examples originate ONLY from 182 development TRAIN questions,
with target 63 holdout excluded by hash. The original examples' answer values
and answer-bearing explanations are withheld in this treatment,
while retaining the question, type and output-unit structure. The same six
PDF evidence passages and current question remain unchanged.

The treatment has no access to evaluation labels and emits no per-row answers.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from verified_lesson import (illustrate, self_test as lessons_self_test)

PREFIX="\n\nFORMATTING AND SCIENTIFIC REASONING EXAMPLES (TRAIN DEVELOPMENT ONLY):\n"
SEPARATOR="\nThe worked questions and their numbers are NOT evidence for "
NUMBERS=re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\w.])")


def value_shape(value):
    s=str(value or "").strip()
    if s.casefold() in ("","is_blank","na","n/a","none","null","nan"):
        return "UNANSWERABLE_OUTPUT"
    try:
        num=Decimal(s.replace(",",""))
        if num.is_finite():
            return "NUMERIC_SCALAR_OUTPUT"
    except (InvalidOperation,ValueError):
        pass
    if s.startswith(("[","(")) and s.endswith(("]",")")):
        return "STRUCTURED_RANGE_OR_LIST_OUTPUT"
    return "SHORT_TEXT_OUTPUT"


def mask_worked_values(compiled):
    if not isinstance(compiled,str) or not compiled.startswith(PREFIX):
        raise RuntimeError("Unrecognized certified lesson envelope")
    body=compiled[len(PREFIX):]
    if SEPARATOR not in body:
        raise RuntimeError("Lesson boundary missing; do not insert unverified data")
    payload,suffix=body.split(SEPARATOR,1)
    examples=json.loads(payload)
    if len(examples)!=2:
        raise RuntimeError("Certified two-example development memory changed")
    shapes=[]
    for example in examples:
        original=str(example["worked_answer_value"])
        shape=value_shape(original)
        shapes.append(shape)
        example["worked_answer_value"]=shape+"__LABEL_WITHHELD"
        # Gold explanations can restate text, ranges, numbers or labels.
        # Withhold the entire answer-bearing explanation; retaining even
        # nonnumeric prose would leak exact categorical answers.
        example["worked_explanation"]="EXPLANATION_WITHHELD"
        if original and (original in example["worked_answer_value"] or
                         original in example["worked_explanation"]):
            raise RuntimeError("Development worked-answer literal leaked into treatment")
    result=PREFIX+json.dumps(examples,ensure_ascii=False,separators=(",",":"))+SEPARATOR+suffix
    if "TRAIN DEVELOPMENT ONLY" not in result or "NOT evidence" not in result:
        raise RuntimeError("Evidence boundary changed")
    return result


def self_test():
    lessons_self_test()
    examples=[
        {"id":"testing01","question":"What percent decrease was observed?",
         "Math":"True","answer_value":"19.6",
         "answer_unit":"percent","explanation":"Compute 19.6 from the report."},
        {"id":"testing02","question":"How much energy use was measured?",
         "Quote":"True","answer_value":"10",
         "answer_unit":"MWh","explanation":"A source gave 10 MWh."},
        {"id":"testing03","question":"What did Table 4 indicate?",
         "Table":"True","answer_value":"23",
         "answer_unit":"MWh","explanation":"Table row 23 was read."},
    ]
    from holdout_probe import is_holdout
    for row in examples:
        while is_holdout(row["id"]):
            row["id"]+="_dev"
    original=illustrate("What was the percent decrease?",examples)
    masked=mask_worked_values(original)
    assert "19.6" in original and "19.6" not in masked
    assert "NUMERIC_SCALAR_OUTPUT__LABEL_WITHHELD" in masked
    assert "worked_answer_unit" in masked and "percent" in masked
    assert masked.count("worked_question")==2
    assert "not test/evidence" not in masked.casefold()
    print("WATTBOT_LESSON_MASKED_VALUES_SELF_TEST=PASS")


if __name__=="__main__":
    self_test()
