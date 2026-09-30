"""Bounded structural selector over already-warranted proof-constructor classes.

The selector does not prove formulas and does not introduce new constructor
classes. It assigns a candidate constructor class from normalized formula
structure only. Source theorem names are not inputs.

Every selection remains CANDIDATE until an independently generated or supplied
consumer checks in Lean and the source occurrence has native authority.
"""

from __future__ import annotations

import re
from typing import Any, Sequence

from mathgraph.cross_prover_family_discovery import normalize_surface
from mathgraph.cross_prover_surface_boundary import classify_real_object_surface


WARRANTED_SCHEMAS = frozenset({
    "explicit_witness",
    "quadratic_implication",
    "sum_of_squares",
    "algebraic_root_witness",
    "quantifier_witness_duality",
    "composed_algebraic_witness",
    "bounded_intermediate_value",
})


def _quantifier_prefix(surface: str) -> list[tuple[str, str]]:
    return re.findall(
        r"\b(FORALL|EXISTS) \(([A-Za-z_]\w*):\s*real\):",
        normalize_surface(surface),
    )


def _matrix(surface: str) -> str:
    s=normalize_surface(surface)
    while True:
        m=re.match(r"^(FORALL|EXISTS) \([A-Za-z_]\w*: real\):\s*(.*)$",s)
        if not m:
            break
        s=m.group(2).strip()
    if s.startswith("NOT (") and s.endswith(")"):
        return s
    return s


def select_constructor_schema(
    surface: str,
    *,
    available_schemas: Sequence[str] | None = None,
) -> dict[str, Any]:
    boundary=classify_real_object_surface(surface)
    if boundary["status"]!="OBJECT_LEVEL_CLOSED_REAL_ARITHMETIC":
        return {
            "status":"UNKNOWN_OUTSIDE_OBJECT_LEVEL_BOUNDARY",
            "schema":None,
            "reason":"surface is not closed explicit real arithmetic",
        }

    s=normalize_surface(surface)
    prefix=_quantifier_prefix(s)
    matrix=_matrix(s)
    qs=[q for q,_ in prefix]
    vars_=[v for _,v in prefix]

    selected: str | None=None
    reason="no bounded structural rule"

    # Negated quantified claims are routed to polarity/witness contradiction.
    if s.startswith("NOT "):
        selected="quantifier_witness_duality"
        reason="top-level negation of a quantified real claim"

    # Universal implication between polynomial inequalities.
    elif "IMPLIES" in matrix and "EXISTS" not in qs:
        selected="quadratic_implication"
        reason="universal polynomial implication"

    # A dependent existential square-root style witness: a universal parameter
    # precedes an existential variable whose square/mul-self is constrained by equality.
    elif "EXISTS" in qs:
        first_e=qs.index("EXISTS")
        evar=vars_[first_e]
        has_prior_forall="FORALL" in qs[:first_e]
        root_eq=(
            re.search(rf"\b{re.escape(evar)}\s*\^\s*2\s*=",matrix) is not None
            or re.search(rf"\b{re.escape(evar)}\s*\*\s*{re.escape(evar)}\s*=",matrix) is not None
        )
        if has_prior_forall and root_eq:
            selected="algebraic_root_witness"
            reason="dependent existential square-root/equation witness"
        else:
            selected="explicit_witness"
            reason="existential witness without dependent root signature"

    # Closed universal polynomial inequalities are routed to SOS-style
    # nonnegativity certificates. This is only a constructor-class proposal.
    elif qs and all(q=="FORALL" for q in qs) and any(op in matrix for op in (">","<")):
        selected="sum_of_squares"
        reason="unconditional universal polynomial inequality"

    if selected is None:
        return {
            "status":"UNKNOWN_NO_CONSTRUCTOR_SELECTION",
            "schema":None,
            "reason":reason,
            "quantifier_prefix":prefix,
        }

    allowed=set(WARRANTED_SCHEMAS if available_schemas is None else available_schemas)
    if selected not in allowed:
        return {
            "status":"UNKNOWN_MISSING_CONSTRUCTOR",
            "schema":selected,
            "reason":reason,
            "quantifier_prefix":prefix,
        }

    return {
        "status":"CANDIDATE_CONSTRUCTOR_SELECTION",
        "schema":selected,
        "reason":reason,
        "quantifier_prefix":prefix,
    }
