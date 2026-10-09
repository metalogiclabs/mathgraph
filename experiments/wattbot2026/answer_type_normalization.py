#!/usr/bin/env python3
"""WattBot typed answer values: scalar vs reported range vs grading band.

Do not expose or infer TRAIN/TEST scoring bands from ground truth at
prediction time. The solver's answer_value is only normalized according
to QUESTION wording plus its own proposed value. Actual source-reported
ranges are preserved as two endpoints; a proposed pair when asked for one
derived number is a malformed candidate, for which explicit bounded
normalization policies may be evaluated (never automatically warranted).
"""
from __future__ import annotations
import ast
from decimal import Decimal, InvalidOperation
import re

NO_VALUE={"is_blank","n/a","na","nan","unknown","null","none",""}
RANGE_REQUEST=re.compile(
    r"\b(?:reported|stated|observed|given|specified|estimated)?\s*range\b|"
    r"\b(?:lower\s+(?:and|or)\s+upper|upper\s+(?:and|or)\s+lower)\b|"
    r"\b(?:minimum\s+and\s+maximum|minimum\s+to\s+maximum)\b|"
    r"\b(?:low[- ]end\s+and\s+high[- ]end)\b|"
    r"\binterval\s+from\b",re.I)
APPROX_PREFIX=re.compile(
    r"^\s*(?:~|≈|about\s+|approximately\s+|around\s+|roughly\s+|circa\s+)",
    re.I)
NUMERIC_SCALAR=re.compile(
    r"^[+-]?(?:\d[\d,]*(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?%?$")


def parse_decimal(s):
    try:
        value=Decimal(str(s).strip().replace(",",""))
        if value.is_finite():return value
    except (InvalidOperation,ValueError,TypeError):
        pass
    return None


def printable(num):
    if num is None or not num.is_finite():
        raise ValueError("Non-finite scalar")
    # Deterministic decimal representation preserving at least 12 decimal
    # significant places, enough for the official +/-0.1% numeric scoring.
    if num == 0:return "0"
    x=num.normalize()
    out=format(x,"f")
    if len(out)>64:
        out=format(x,".12E")
    return out


def parse_pair(value):
    raw=str(value or "").strip()
    if not ((raw.startswith("[") and raw.endswith("]")) or
            (raw.startswith("(") and raw.endswith(")"))):
        return None
    try:
        parsed=ast.literal_eval(raw)
    except (ValueError,TypeError,SyntaxError,MemoryError):
        return None
    if not isinstance(parsed,(list,tuple)) or len(parsed)!=2:
        return None
    a=parse_decimal(parsed[0])
    b=parse_decimal(parsed[1])
    if a is None or b is None:
        return None
    return a,b


def is_reported_range_question(question):
    return bool(RANGE_REQUEST.search(str(question)))


def normalize_answer(question, value, policy="typed"):
    raw=str(value or "").strip()
    if raw.casefold() in NO_VALUE:
        return "is_blank" if raw else raw
    if policy not in ("typed","preserve_range","first","last"):
        raise ValueError("Unregistered answer-normalization policy")

    pair=parse_pair(raw)
    if pair is not None:
        a,b=pair
        if is_reported_range_question(question):
            low,high=sorted((a,b))
            return "("+printable(low)+","+printable(high)+")"
        if policy=="first":
            return printable(a)
        if policy=="last":
            return printable(b)
        if policy=="preserve_range":
            low,high=sorted((a,b))
            return "("+printable(low)+","+printable(high)+")"
        return printable((a+b)/2)

    # Only strip unambiguous approximate numerals or percentages, never
    # extract an arbitrary number from an unsupported paragraph.
    removed=APPROX_PREFIX.sub("",raw).strip()
    if removed!=raw or raw.endswith("%"):
        candidate=removed.rstrip("%").strip()
        if NUMERIC_SCALAR.fullmatch(candidate) and (
            value:=parse_decimal(candidate)) is not None:
            return printable(value)

    if re.search(r"\btrue\s*(?:or|\/)\s*false\b",question,re.I):
        if raw.casefold() in ("yes","correct","true","affirmative"):
            return "TRUE"
        if raw.casefold() in ("no","incorrect","false","negative"):
            return "FALSE"
    return raw


def rewrite_row(row,question,policy="typed"):
    output=dict(row)
    output["answer_value"]=normalize_answer(question,row.get("answer_value",""),policy)
    if output["answer_value"]!=str(row.get("answer_value","")).strip():
        output["explanation"]=str(output.get("explanation",""))+(
            " TYPE_CANDIDATE: output syntax normalized without adding "
            "scientific evidence or asserting entailment.")
    return output


def self_test():
    assert is_reported_range_question("What range does the source state?")
    assert not is_reported_range_question("How many household-years?")
    assert normalize_answer("How many household-years?","[116,122]")=="119"
    assert normalize_answer("What reported range?","[14,29]")=="(14,29)"
    assert normalize_answer("What interval from 5 to 8?","(8,5)")=="(5,8)"
    assert normalize_answer("What percent was reported?","~53%")=="53"
    assert normalize_answer("What was the power?","about 1,287")=="1287"
    assert normalize_answer("True or False: Is X equal to Y?","no")=="FALSE"
    assert normalize_answer("What energy?","is_blank")=="is_blank"
    assert normalize_answer("What?","solar and wind")=="solar and wind"
    row={"answer_value":"[3,7]","explanation":"No semantics yet"}
    changed=rewrite_row(row,"What was the estimated mean?")
    assert changed["answer_value"]=="5" and row["answer_value"]=="[3,7]"
    assert "TYPE_CANDIDATE" in changed["explanation"]
    print("WATTBOT_ANSWER_TYPE_NORMALIZATION_SELF_TEST=PASS")


if __name__=="__main__":
    self_test()
