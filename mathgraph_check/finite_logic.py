"""Bounded Boolean semantic adapter for MathGraph Check.

All conclusions are confined to a supplied finite Bool^n interpretation.
This module does not interpret English, audit Lean, or promote mathematical truth.
The independent Lean and bitset benchmark live in research/, not here.
"""
from __future__ import annotations

from itertools import product
from typing import Any

from .preflight import check_manifest

MAX_VARIABLES = 5
MAX_NODES = 120
MAX_DEPTH = 20
_BINARY = frozenset(("and", "or", "implies", "xor", "iff"))


class UnsupportedFiniteGrammar(ValueError):
    """The requested meaning is not representable by this exact finite grammar."""


def _validate(formula: Any, variables: tuple[str, ...], depth: int = 0,
              count: list[int] | None = None) -> None:
    if count is None:
        count = [0]
    count[0] += 1
    if count[0] > MAX_NODES or depth > MAX_DEPTH:
        raise UnsupportedFiniteGrammar("formula complexity exceeds bounded grammar")
    if not isinstance(formula, dict) or len(formula) != 1:
        raise UnsupportedFiniteGrammar("formula must be a single-key expression object")
    op, arg = next(iter(formula.items()))
    if op == "var":
        if type(arg) is not str or arg not in variables:
            raise UnsupportedFiniteGrammar("undeclared variable")
    elif op == "const":
        if type(arg) is not bool:
            raise UnsupportedFiniteGrammar("constant must be a Boolean")
    elif op == "not":
        _validate(arg, variables, depth + 1, count)
    elif op in _BINARY:
        if not isinstance(arg, list) or len(arg) != 2:
            raise UnsupportedFiniteGrammar("binary connective requires two children")
        _validate(arg[0], variables, depth + 1, count)
        _validate(arg[1], variables, depth + 1, count)
    else:
        raise UnsupportedFiniteGrammar("unsupported operation: " + str(op)[:80])


def _value(formula: dict[str, Any], state: dict[str, bool]) -> bool:
    op, arg = next(iter(formula.items()))
    if op == "var":
        return state[arg]
    if op == "const":
        return arg
    if op == "not":
        return not _value(arg, state)
    left = _value(arg[0], state)
    right = _value(arg[1], state)
    if op == "and":
        return left and right
    if op == "or":
        return left or right
    if op == "implies":
        return (not left) or right
    if op == "xor":
        return left != right
    if op == "iff":
        return left == right
    raise AssertionError("validated formula contained unsupported operator")


def compare_finite_formulas(source: Any, formal: Any,
                            variables: list[str]) -> dict[str, Any]:
    """Compare full truth signatures on Bool^n, never claim source fidelity.

    Unsupported formula structure produces explicit UNKNOWN. This is a
    representation-limited result, not a proof that the claimed theorem is false.
    """
    if (not isinstance(variables, list) or not 1 <= len(variables) <= MAX_VARIABLES
            or any(type(v) is not str or not v.isidentifier() for v in variables)
            or len(set(variables)) != len(variables)):
        raise UnsupportedFiniteGrammar("1–5 distinct identifier variables required")
    names = tuple(variables)
    scope = {"variables": variables, "domain": "Bool^" + str(len(variables))}
    epistemic = {
        "natural_language_fidelity": "UNKNOWN",
        "general_infinite_domain_extension": "UNKNOWN",
        "truth_promotion": False,
        "lean_kernel_verified_for_this_query": False,
        "verified_badge": "NOT_ISSUED",
    }
    try:
        _validate(source, names)
        _validate(formal, names)
    except UnsupportedFiniteGrammar as exc:
        return {
            "schema": "mathgraph.finite-semantics.v1",
            "scope": scope,
            "result": "UNKNOWN_UNSUPPORTED_GRAMMAR",
            "reason": str(exc),
            "witness": None,
            "epistemic": epistemic,
        }
    vals = list(product((False, True), repeat=len(variables)))
    source_signature = []
    formal_signature = []
    witness = None
    for values in vals:
        state = dict(zip(variables, values))
        a = _value(source, state)
        b = _value(formal, state)
        source_signature.append("1" if a else "0")
        formal_signature.append("1" if b else "0")
        if a != b and witness is None:
            witness = {"assignment": state, "source": a, "formal": b}
    manifest = {
        "schema": "mathgraph.check.v0",
        "title": "Finite Boolean consequence comparison",
        "source_contract_origin": "MANUAL_UNREVIEWED",
        "source": {"anchor": "finite-dsl:source", "dimensions": {
            "bool_signature": source_signature}},
        "formal": {"anchor": "finite-dsl:formal", "dimensions": {
            "bool_signature": formal_signature}},
        "protected_dimensions": ["bool_signature"],
    }
    check = check_manifest(manifest)
    assert check["epistemic"]["truth_promotion"] is False
    return {
        "schema": "mathgraph.finite-semantics.v1",
        "scope": scope,
        "result": (
            "FINITE_COUNTEREXAMPLE" if witness else "FINITE_MATCH_ON_DECLARED_DOMAIN"
        ),
        "witness": witness,
        "evaluated_assignments": len(vals),
        "source_signature": "".join(source_signature),
        "formal_signature": "".join(formal_signature),
        "contract_audit_status": check["comparison"]["status"],
        "epistemic": epistemic,
    }
