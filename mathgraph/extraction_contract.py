"""Declarative source-to-formal extraction contracts.

This module is deliberately verifier-agnostic and source-agnostic. It does not
parse mathematics from prose. Instead, it checks an explicit proposed binding:
source markers + normalization policy + formal payload + relation + falsifiers.
Authority still comes from the declared external verification boundary.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from mathgraph.crystal import content_id
from mathgraph.math_claim import MathClaimPayload, VerifiedClaimRelation


class ExtractionContractMismatch(ValueError):
    pass


_ALLOWED_NORMALIZERS = {"lower", "collapse_ws", "strip_tex_dollars"}


def normalize_source(text: str, normalizers: list[str] | tuple[str, ...]) -> str:
    value = text
    for normalizer in normalizers:
        if normalizer not in _ALLOWED_NORMALIZERS:
            raise ValueError(f"unsupported extraction normalizer: {normalizer}")
        if normalizer == "lower":
            value = value.lower()
        elif normalizer == "collapse_ws":
            value = " ".join(value.split())
        elif normalizer == "strip_tex_dollars":
            value = value.replace("$", "")
    return value


def _tuple_context(raw: list[list[str]] | tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    return tuple((str(name), str(kind)) for name, kind in raw)


def apply_extraction_contract(
    contract: Mapping[str, Any],
    source_text: str,
    *,
    evidence_ref: str,
) -> dict[str, Any]:
    matching = contract["matching"]
    normalized = normalize_source(source_text, matching.get("normalizers", []))
    compact = re.sub(r"\s+", "", normalized)

    missing = [
        marker
        for marker in matching.get("required_markers", [])
        if marker not in normalized
    ]
    missing_compact = [
        marker
        for marker in matching.get("required_compact_markers", [])
        if marker not in compact
    ]
    if missing or missing_compact:
        raise ExtractionContractMismatch(
            f"source contract mismatch: markers={missing}, compact={missing_compact}"
        )

    source_spec = contract["source_claim"]
    source_obj = MathClaimPayload(
        claim_id=source_spec["claim_id"],
        dialect=source_spec["dialect"],
        context=_tuple_context(source_spec.get("context", [])),
        assumptions=tuple(source_spec.get("assumptions", [])),
        statement=source_spec["statement"],
        source_ref=source_spec["source_ref"],
    ).semantic_object()

    formal = contract["formal_claim"]
    formal_obj = MathClaimPayload(
        claim_id=formal["claim_id"],
        dialect=formal["dialect"],
        context=_tuple_context(formal.get("context", [])),
        assumptions=tuple(formal.get("assumptions", [])),
        statement=formal["statement"],
        source_ref=formal["source_ref"],
    ).semantic_object()

    expected_source = contract.get("expected_source_object_id")
    expected_formal = contract.get("expected_formal_object_id")
    if expected_source and source_obj.id != expected_source:
        raise AssertionError(
            f"source object drift: expected {expected_source}, got {source_obj.id}"
        )
    if expected_formal and formal_obj.id != expected_formal:
        raise AssertionError(
            f"formal object drift: expected {expected_formal}, got {formal_obj.id}"
        )

    relation = VerifiedClaimRelation(
        source_obj.id,
        formal_obj.id,
        contract["relation"],
        (evidence_ref,),
    )

    contract_id = content_id(json.loads(json.dumps(contract, sort_keys=True)), prefix="extraction-contract")
    return {
        "contract_id": contract_id,
        "source_object_id": source_obj.id,
        "formal_object_id": formal_obj.id,
        "relation_id": relation.id,
        "relation": relation.relation,
        "glossary_assumptions": tuple(contract.get("glossary_assumptions", [])),
    }


def apply_literal_mutation(text: str, mutation: Mapping[str, str]) -> str:
    old = mutation["old"]
    new = mutation["new"]
    count = text.count(old)
    if count != 1:
        raise AssertionError(
            f"literal falsifier must match exactly once: {old!r}, count={count}"
        )
    return text.replace(old, new, 1)


def qualify_falsifiers(
    contract: Mapping[str, Any],
    source_text: str,
    *,
    evidence_ref: str,
) -> tuple[str, ...]:
    rejected: list[str] = []
    for falsifier in contract.get("falsifiers", []):
        if falsifier.get("kind") != "literal":
            raise ValueError("only literal falsifiers are supported in v1")
        mutated = apply_literal_mutation(source_text, falsifier)
        try:
            apply_extraction_contract(contract, mutated, evidence_ref=evidence_ref)
        except ExtractionContractMismatch:
            rejected.append(falsifier["label"])
            continue
        raise AssertionError(
            f"semantic perturbation unexpectedly survived: {falsifier['label']}"
        )
    return tuple(rejected)
