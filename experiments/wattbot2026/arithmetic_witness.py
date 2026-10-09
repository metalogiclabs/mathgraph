#!/usr/bin/env python3
"""WattBot exact arithmetic witness: typed consequence, not semantic assertion.

Given a frozen model answer CANDIDATE and six already-retrieved PDF excerpts,
seek a short source-carrying exact Fraction calculation of the proposed value.
Question wording constrains the operation alphabet before the candidate value
is inspected. Every operand must be visible in a literal source-page quote.
The independent WattBot derivation verifier checks arithmetic and provenance.

This DOES NOT establish that the chosen operands are scientifically relevant
or that the answer follows semantically from the study. The claim remains
CANDIDATE. No TRAIN or TEST gold labels/refs are needed.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
import itertools
import re

from wattbot import NUM_RE, as_fraction, tokens, verify_candidate

STOP = frozenset(("a an the is was what how much many in of for from to by on and or "
                  "are were which their its according as at during with using does "
                  "did this that per about than study paper papers research report "
                  "reported results result value values estimated estimate").split())
MAX_PER_PASSAGE = 24
MAX_OPERANDS = 72
MAX_ABS_VALUE = 10**15
OPERATORS = ("a+b", "a-b", "a*b", "a/b", "100*a/b", "100*(a-b)/b", "(a+b)/2")
CROSS = frozenset(("across", "between", "both", "two", "studies", "papers"))
NO_ANSWER = frozenset(("is_blank", "unknown", "na", "n/a", "nan", "none", "null", ""))


@dataclass(frozen=True)
class Operand:
    number: Fraction
    literal: str
    passage: int
    position: int
    quote: str
    relevance: int


def operation_grammar(question: str) -> tuple[str, ...]:
    """Allow only operators whose requested role is signaled by the question."""
    q = question.casefold()
    words = set(tokens(q))
    ops = set()
    if words & {"sum", "total", "combined", "together", "aggregate", "cumulative",
                "add", "adding", "addition"}:
        ops.add("a+b")
    if words & {"difference", "differ", "gap", "change", "increase", "decrease",
                "reduction", "reduced", "higher", "lower", "less", "more",
                "subtract", "minus", "saved", "savings", "remaining"}:
        ops.add("a-b")
    if words & {"multiply", "multiplied", "product", "times", "scale"}:
        ops.add("a*b")
    if words & {"per", "ratio", "relative", "divided", "divide", "quotient",
                "equivalent", "equivalence", "household", "households",
                "years", "yearly", "annual", "annually", "rate"}:
        ops.add("a/b")
    if words & {"percentage", "percent", "share", "proportion", "fraction"} or "%" in q:
        ops.update(("a/b", "100*a/b"))
    if (words & {"percent", "percentage", "change", "increase", "decrease",
                "relative", "reduction"}) and (
                words & {"change", "increase", "decrease", "relative",
                         "reduction", "difference"}):
        ops.add("100*(a-b)/b")
    if words & {"average", "mean"}:
        ops.add("(a+b)/2")
    return tuple(op for op in OPERATORS if op in ops)


def numeric_operands(question: str, passages: list[dict]) -> list[Operand]:
    expected = set(tokens(question.casefold())) - STOP
    found = []
    for source_idx, page in enumerate(passages):
        if page.get("page", 0) < 1:
            continue
        body = str(page.get("text", ""))[:1800]
        scoped = []
        for hit in NUM_RE.finditer(body):
            raw = hit.group().strip()
            try:
                value = as_fraction(raw)
            except ValueError:
                continue
            if abs(value) > MAX_ABS_VALUE or value.denominator > 10_000_000:
                continue
            if 1900 <= value <= 2100 and "year" not in expected and "date" not in expected:
                continue
            left = max(0, hit.start() - 105)
            right = min(len(body), hit.end() + 105)
            excerpt = body[left:right].strip()
            keyset = set(tokens(excerpt.casefold())) - STOP
            match = len(expected.intersection(keyset))
            if match < 1:
                continue
            scoped.append(Operand(value, raw, source_idx, hit.start(),
                                  excerpt, match))
        # Keep question-nearest numbers; this is frozen without gold labels.
        scoped.sort(key=lambda v: (-v.relevance, v.position))
        found.extend(scoped[:MAX_PER_PASSAGE])
    found.sort(key=lambda v: (-v.relevance, v.passage, v.position))
    return found[:MAX_OPERANDS]


def eval_formula(op: str, a: Fraction, b: Fraction) -> Fraction | None:
    if op == "a+b": return a + b
    if op == "a-b": return a - b
    if op == "a*b": return a * b
    if op == "a/b": return a / b if b else None
    if op == "100*a/b": return 100 * a / b if b else None
    if op == "100*(a-b)/b": return 100 * (a-b) / b if b else None
    if op == "(a+b)/2": return (a + b) / 2
    raise ValueError("Undeclared operator")


def try_arithmetic_witness(generated: dict, question: dict, passages: list[dict],
                           docs: dict) -> tuple[dict | None, str]:
    """Produce provenance+arithmetic verified candidate, or named residual."""
    if not isinstance(generated, dict):
        return None, "INVALID_MODEL_SHAPE"
    target = str(generated.get("answer_value", "")).strip()
    if target.casefold() in NO_ANSWER:
        return None, "NO_ANSWER_VALUE"
    try:
        claimed = as_fraction(target)
    except (ValueError, TypeError):
        return None, "NONSCALAR_VALUE"
    grammar = operation_grammar(str(question["question"]))
    if not grammar:
        return None, "NO_QUESTION_OPERATOR"
    operands = numeric_operands(str(question["question"]), passages)
    if len(operands) < 2:
        return None, "INSUFFICIENT_GROUNDED_OPERANDS"
    question_tokens = set(tokens(str(question["question"]).casefold()))
    cross_requested = bool(question_tokens & CROSS)
    candidates = []
    for first, second in itertools.permutations(operands, 2):
        if first.passage == second.passage and first.position == second.position:
            continue
        p1, p2 = passages[first.passage], passages[second.passage]
        if cross_requested and p1["ref_id"] == p2["ref_id"]:
            continue
        for op in grammar:
            result = eval_formula(op, first.number, second.number)
            if result is None or result != claimed:
                continue
            # Prefer evidence matching more question content, fewer papers,
            # then higher original retriever rank. No gold reference is read.
            priority = (
                -(first.relevance + second.relevance),
                len({p1["ref_id"], p2["ref_id"]}),
                first.passage + second.passage,
                first.position + second.position,
            )
            candidates.append((priority, first, second, op))
    if not candidates:
        return None, "NO_EXACT_GROUNDED_DERIVATION"
    candidates.sort(key=lambda x: x[0])
    for _, first, second, op in candidates[:32]:
        p1, p2 = passages[first.passage], passages[second.passage]
        refs = list(dict.fromkeys([p1["ref_id"], p2["ref_id"]]))
        evidence = [
            {"ref_id":p1["ref_id"], "page":int(p1["page"]), "quote":first.quote},
            {"ref_id":p2["ref_id"], "page":int(p2["page"]), "quote":second.quote},
        ]
        candidate = {
            "id":question["id"],
            "answer":str(generated.get("answer") or target)[:800],
            "answer_value":target,
            "ref_ids":refs,
            "evidence":evidence,
            "derivation":{"expression":op, "inputs":{
                "a":{"value":first.literal, "evidence_index":0},
                "b":{"value":second.literal, "evidence_index":1}}},
            "explanation":"CANDIDATE: exact arithmetic and literal source-page "
                          "operand provenance verified. Whether these are the "
                          "scientifically intended quantities remains UNKNOWN.",
        }
        try:
            checked = verify_candidate(candidate,question,docs,passages)
        except (ValueError, TypeError, KeyError, ZeroDivisionError):
            continue
        unit = str(generated.get("answer_unit", "is_blank") or "is_blank").strip()
        checked["answer_unit"] = (unit if unit.casefold() not in NO_ANSWER
                                  else "is_blank")
        return checked, "ARITHMETIC_LITERAL_CERTIFIED"
    return None, "INDEPENDENT_DERIVATION_CHECK_REJECTED"


def self_test():
    assert operation_grammar("What is the combined total energy?") == ("a+b",)
    assert "a/b" in operation_grammar("How many household years per MWh?")
    assert "100*a/b" in operation_grammar("What percentage share of supply?")
    assert not operation_grammar("What was the reported energy?")

    docs = {
        "a":{"url":"https://arxiv.org/abs/2601.11111"},
        "b":{"url":"https://arxiv.org/abs/2601.22222"},
    }
    passages = [
        {"ref_id":"a","page":2,"url":docs["a"]["url"],
         "text":"Solar electricity generation was 12 MWh in the study."},
        {"ref_id":"b","page":7,"url":docs["b"]["url"],
         "text":"Wind electricity generation was 18 MWh in the same period."},
    ]
    question={"id":"case","question":"What was the combined electricity generation across both studies?"}
    raw={"answer":"30 MWh","answer_value":"30","answer_unit":"MWh",
         "source_indices":[0,1]}
    result,status=try_arithmetic_witness(raw,question,passages,docs)
    assert status=="ARITHMETIC_LITERAL_CERTIFIED", status
    assert result and result["answer_value"]=="30",result
    assert "['a', 'b']" == result["ref_id"]
    assert "scientifically intended" in result["explanation"]
    no,why=try_arithmetic_witness(dict(raw,answer_value="45"),question,passages,docs)
    assert no is None and why=="NO_EXACT_GROUNDED_DERIVATION", why
    no,why=try_arithmetic_witness(raw,{"id":"case","question":"What energy did they report?"},
                                  passages,docs)
    assert no is None and why=="NO_QUESTION_OPERATOR",why
    print("WATTBOT_EXACT_ARITHMETIC_WITNESS_SELF_TEST=PASS")


if __name__ == "__main__":
    self_test()
