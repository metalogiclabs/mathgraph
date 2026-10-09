#!/usr/bin/env python3
"""WattBot evidence-preserving answer-value shape compiler.

The official Score.py distinguishes a numerical tolerance band around a
derived answer (submit one number) from a source-stated range (submit both
endpoints). This module uses question text and the MODEL's own output only,
never gold labels or citations. No new measurements or range endpoints
can be inferred from absent text; all semantic correctness remains UNKNOWN.
"""
from __future__ import annotations
import ast
from decimal import Decimal, InvalidOperation
import re

NONE=frozenset(("","is_blank","na","n/a","nan","null","none","unknown"))
NUMERIC = re.compile(r"^\s*[~≈]?\s*([-+]?(?:\d[\d,]*)(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(?:%|MWh|GWh|kWh|MW|GW|kg|tonnes?|litres?|L|USD|tCO2e|kgCO2e)?\s*$",re.I)
APPROX = re.compile(r"^\s*(?:about|approximately|roughly|around|circa)\s+",re.I)
BOUNDS = re.compile(r"(?:range\s+(?:of|from|between)|(?:what|which|give|provide|report)\s+.*\brange\b|(?:both|the)\s+(?:lower|upper|minimum|maximum)\s+(?:and|or)\s+(?:upper|lower|maximum|minimum)|\b(?:minimum|lowest)\s+and\s+(?:maximum|highest)\b|\blower\s+(?:and|to)\s+upper\s+bound)",re.I)

def requested_source_range(question: str) -> bool:
    return bool(BOUNDS.search(str(question)))

def finite_decimal(s):
    try:
        v=Decimal(str(s).strip().replace(",",""))
        return v if v.is_finite() else None
    except (ValueError,InvalidOperation,TypeError):
        return None

def plain_decimal(n):
    if not n.is_finite() or abs(n)>Decimal("1e40"):
        return None
    z=format(n,"f")
    if "." in z:
        z=z.rstrip("0").rstrip(".")
    if z=="-0":z="0"
    return z

def numeric_pair(s):
    val=str(s or "").strip()
    if not (len(val)>=5 and val[0] in "[(" and val[-1] in "])"):
        return None
    try:
        parsed=ast.literal_eval(val)
    except (SyntaxError,ValueError,TypeError,MemoryError):
        return None
    if not isinstance(parsed,(list,tuple)) or len(parsed)!=2:
        return None
    a,b=(finite_decimal(x) for x in parsed)
    return (a,b) if a is not None and b is not None else None

def canonical_scalar(s):
    raw=APPROX.sub("",str(s or "").strip())
    match=NUMERIC.fullmatch(raw)
    if not match:return None
    number=finite_decimal(match.group(1))
    return plain_decimal(number) if number is not None else None

def normalize_value(value,question,policy):
    if policy not in ("none","scalar_cleanup","range_only","collapse_band","all"):
        raise ValueError("Unregistered output form policy")
    original=str(value or "").strip()
    if original.casefold() in NONE or policy=="none":
        return original
    pair=numeric_pair(original)
    is_range=requested_source_range(question)
    if pair is not None:
        a,b=pair
        if is_range and policy in ("range_only","all"):
            first,second=sorted((a,b))
            x,y=plain_decimal(first),plain_decimal(second)
            return f"({x},{y})" if x is not None and y is not None else original
        if not is_range and policy in ("collapse_band","all"):
            midpoint=plain_decimal((a+b)/2)
            return midpoint if midpoint is not None else original
        return original
    if policy in ("scalar_cleanup","all"):
        plain=canonical_scalar(original)
        return plain if plain is not None else original
    return original

def repair_row(row,question,policy):
    """Only answer_value changes. Citations, quote and unit are untouched."""
    result=dict(row)
    original=str(result.get("answer_value",""))
    revised=normalize_value(original,question,policy)
    result["answer_value"]=revised
    if revised!=original:
        why=str(result.get("explanation","")).strip()
        result["explanation"]=(why+" Candidate answer-value FORM normalized "
            "without inventing measurements or certifying semantic correctness.").strip()
    return result

def self_test():
    assert requested_source_range("What range of power does the report state?")
    assert requested_source_range("Give both lower and upper bound.")
    assert not requested_source_range("What fraction of the measured systems?")
    assert normalize_value("~1,287 MWh","How much electricity?","scalar_cleanup")=="1287"
    assert normalize_value("about 119","How many household-years?","all")=="119"
    assert normalize_value("[116,121]","What is the derived household-year usage?","all")=="118.5"
    assert normalize_value("[116,121]","What range of usage is stated?","all")=="(116,121)"
    assert normalize_value("(121,116)","Give the lower and upper bound.","range_only")=="(116,121)"
    assert normalize_value("['energy','water']","Which measurements?","all")=="['energy','water']"
    assert normalize_value("FALSE","True or False?","all")=="FALSE"
    assert normalize_value("is_blank","What was not documented?","all")=="is_blank"
    original={"answer_value":"~1,287 MWh","ref_id":"['a']",
              "ref_url":"['url']","supporting_materials":"is_blank","answer_unit":"MWh",
              "explanation":"CANDIDATE_UNVERIFIED"}
    changed=repair_row(original,"How much electricity?","all")
    assert changed["answer_value"]=="1287"
    assert all(changed[k]==original[k] for k in (
        "ref_id","ref_url","supporting_materials","answer_unit"))
    print("WATTBOT_ANSWER_SHAPE_COMPILER_SELF_TEST=PASS")

if __name__=="__main__": self_test()
