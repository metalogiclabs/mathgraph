"""Representation-only semantic normalization for exact cross-prover reuse.

This layer does not add theorem schemas.  It canonicalizes harmless surface
variation before looking up already-warranted canonical claims:
- grouped real binders,
- alpha-renaming of quantified real variables,
- redundant parentheses immediately under a top-level NOT.

If normalization makes two different warranted claim IDs collide, the key is
ambiguous and no reuse is allowed.
"""

from __future__ import annotations

from collections import defaultdict
import re
from typing import Any, Mapping

from mathgraph.cross_prover_family_discovery import (
    SPECS,
    extract_pvs_lemmas,
    extract_pvs_proved_formulas,
    normalize_surface,
)


def _expand_grouped_real_binders(surface: str) -> str:
    s = surface
    pat = re.compile(
        r"\b(FORALL|EXISTS) \(([A-Za-z_]\w*),\s*([A-Za-z_]\w*):\s*real\):"
    )
    while True:
        m = pat.search(s)
        if not m:
            return s
        q, a, b = m.group(1), m.group(2), m.group(3)
        s = s[:m.start()] + f"{q} ({a}: real): {q} ({b}: real):" + s[m.end():]


def _normalize_top_not_parentheses(surface: str) -> str:
    s = surface.strip()
    if s.startswith("NOT (") and s.endswith(")"):
        inner = s[5:-1].strip()
        if inner.startswith("FORALL ") or inner.startswith("EXISTS "):
            return "NOT " + inner
    return s


def semantic_shape_key(surface: str) -> str:
    s = normalize_surface(surface)
    s = _expand_grouped_real_binders(s)
    s = normalize_surface(s)
    s = _normalize_top_not_parentheses(s)

    names = re.findall(r"(?:FORALL|EXISTS) \(([A-Za-z_]\w*): real\):", s)
    mapping: dict[str, str] = {}
    next_id = 0
    for name in names:
        if name not in mapping:
            mapping[name] = f"v{next_id}"
            next_id += 1
    for name, replacement in mapping.items():
        s = re.sub(rf"\b{re.escape(name)}\b", replacement, s)
    return normalize_surface(s)


def semantic_shape_index() -> dict[str, tuple[str, ...]]:
    by_key: dict[str, set[str]] = defaultdict(set)
    for surface, spec in SPECS.items():
        by_key[semantic_shape_key(surface)].add(spec.claim_id)
    return {key: tuple(sorted(ids)) for key, ids in by_key.items()}


def discover_normalized_exact_reuse(
    sources: Mapping[str, str],
    proofs: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    index = semantic_shape_index()
    proved = {
        theory: extract_pvs_proved_formulas(text)
        for theory, text in (proofs or {}).items()
    }
    matched: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []

    for theory, source in sorted(sources.items()):
        for formula, surface in extract_pvs_lemmas(source):
            key = semantic_shape_key(surface)
            ids = index.get(key, ())
            row = {
                "theory": theory,
                "formula": formula,
                "semantic_shape_key": key,
                "source_proof_status": (
                    None if proofs is None else
                    "PINNED_PROOF_PRESENT"
                    if formula in proved.get(theory, set()) else
                    "NO_PINNED_PROOF"
                ),
            }
            if len(ids) == 1:
                matched.append({
                    **row,
                    "status": "CANDIDATE_NORMALIZED_EXACT_REUSE",
                    "claim_id": ids[0],
                })
            elif len(ids) > 1:
                ambiguous.append({
                    **row,
                    "status": "UNKNOWN_NORMALIZATION_COLLISION",
                    "claim_ids": list(ids),
                })
            else:
                unresolved.append({
                    **row,
                    "status": "UNKNOWN_NO_NORMALIZED_EXACT_MATCH",
                })

    registry_collisions = {
        key: list(ids)
        for key, ids in index.items()
        if len(ids) > 1
    }
    return {
        "schema": "mathgraph.cross-prover-normalized-exact-reuse.v1",
        "status": "CANDIDATE_REPRESENTATION_REPAIR_ONLY",
        "source_lemma_count": len(matched)+len(unresolved)+len(ambiguous),
        "matched_occurrence_count": len(matched),
        "unresolved_occurrence_count": len(unresolved),
        "ambiguous_occurrence_count": len(ambiguous),
        "registry_collision_count": len(registry_collisions),
        "registry_collisions": registry_collisions,
        "matched": matched,
        "unresolved": unresolved,
        "ambiguous": ambiguous,
        "boundary": (
            "No new theorem schema or canonical claim is introduced. Reuse is "
            "allowed only when representation normalization maps to exactly one "
            "already-warranted claim ID."
        ),
    }
