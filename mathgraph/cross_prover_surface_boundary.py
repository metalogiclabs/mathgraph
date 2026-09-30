"""Typed boundary between object-level real claims and prover-internal surfaces.

The classifier is lexical/structural, not theorem-name based. A surface is
accepted into the closed real-arithmetic object language only when every
identifier is either a logical keyword, the type name real, or a variable
bound by an explicit FORALL/EXISTS real quantifier.

Everything else remains typed UNKNOWN at this layer.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from mathgraph.cross_prover_family_discovery import extract_pvs_lemmas, normalize_surface


LOGIC_IDENTIFIERS = {
    "FORALL", "EXISTS", "NOT", "AND", "OR", "IMPLIES", "IFF",
    "TRUE", "FALSE", "real",
}


def classify_real_object_surface(surface: str) -> dict[str, Any]:
    s = normalize_surface(surface)
    bound = set(re.findall(
        r"(?:FORALL|EXISTS) \(([A-Za-z_]\w*):\s*real\):",
        s,
    ))
    identifiers = set(re.findall(r"\b[A-Za-z_]\w*\b", s))
    unsupported = sorted(identifiers - LOGIC_IDENTIFIERS - bound)
    if unsupported:
        return {
            "status": "UNKNOWN_PROVER_INTERNAL_OR_UNSUPPORTED_SYMBOL",
            "normalized_surface": s,
            "bound_real_variables": sorted(bound),
            "unsupported_identifiers": unsupported,
        }
    return {
        "status": "OBJECT_LEVEL_CLOSED_REAL_ARITHMETIC",
        "normalized_surface": s,
        "bound_real_variables": sorted(bound),
        "unsupported_identifiers": [],
    }


def classify_source_family(sources: Mapping[str, str]) -> dict[str, Any]:
    object_level: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    for theory, source in sorted(sources.items()):
        for formula, surface in extract_pvs_lemmas(source):
            c = classify_real_object_surface(surface)
            row = {
                "theory": theory,
                "formula": formula,
                **c,
            }
            if c["status"] == "OBJECT_LEVEL_CLOSED_REAL_ARITHMETIC":
                object_level.append(row)
            else:
                unknown.append(row)
    return {
        "schema": "mathgraph.cross-prover-surface-boundary.v1",
        "status": "CANDIDATE_TYPED_SURFACE_BOUNDARY",
        "source_lemma_count": len(object_level)+len(unknown),
        "object_level_count": len(object_level),
        "typed_unknown_count": len(unknown),
        "object_level": object_level,
        "typed_unknown": unknown,
        "boundary": (
            "This is a bounded lexical/closure classifier for explicit real "
            "arithmetic. UNKNOWN is preserved for prover-internal or unsupported "
            "symbols; UNKNOWN is not a refutation."
        ),
    }
