"""Route unsupported cross-prover formulas to the cheapest next certificate family.

This is diagnostic routing only. It does not create semantic warrant.
"""

from __future__ import annotations

from collections import Counter
import re
from typing import Any, Mapping


OPAQUE_TOKENS=("sqrt(","f(","g(","P(","member(","length(","cons?")


def route_surface(surface: str) -> str:
    s=surface.replace(" ","")
    if any(tok.replace(" ","") in s for tok in OPAQUE_TOKENS):
        return "OPAQUE_OR_NONPOLYNOMIAL"
    if "posreal" in surface or "nnreal" in surface:
        return "SUBTYPE_RANGE"
    if surface.startswith("NOT ") and "EXISTS" in surface:
        return "NEGATED_EXISTENTIAL"
    # A quantified premise is a stronger residual than a plain existential.
    if re.search(r"\(FORALL .*\).*IMPLIES",surface):
        return "QUANTIFIED_PREMISE"
    if re.search(r"\(EXISTS .*\).*IMPLIES",surface):
        return "EXISTENTIAL_PREMISE"
    if "IMPLIES EXISTS" in surface or "IMPLIES (FORALL" in surface and "EXISTS" in surface:
        return "EXISTENTIAL_CONSEQUENT"
    if "EXISTS" in surface:
        return "EXISTENTIAL_WITNESS"
    return "POLYNOMIAL_CERTIFICATE_GAP"


def route_discovery(discovery: Mapping[str,Any]) -> dict[str,Any]:
    rows=[]
    for row in discovery["unsupported_occurrences"]:
        routed=dict(row)
        routed["residual_class"]=route_surface(str(row["normalized_surface"]))
        rows.append(routed)
    counts=Counter(x["residual_class"] for x in rows)
    ordered=sorted(counts.items(),key=lambda kv:(-kv[1],kv[0]))
    next_class=ordered[0][0] if ordered else None
    return {
        "schema":"mathgraph.cross-prover-residual-routing.v1",
        "status":"ROUTED_NOT_QUALIFIED",
        "unsupported_count":len(rows),
        "residual_counts":dict(sorted(counts.items())),
        "dominant_residual_class":next_class,
        "dominant_residual_count":counts.get(next_class,0) if next_class else 0,
        "rows":rows,
        "next_experiment":(
            "compile bounded witness certificates before widening the semantic grammar"
            if next_class in {"EXISTENTIAL_WITNESS","EXISTENTIAL_CONSEQUENT"}
            else "attack the dominant routed class only"
        ),
        "boundary":"Routing is source-shape metadata only; every formula remains UNKNOWN until its native and consumer verifiers qualify it.",
    }
