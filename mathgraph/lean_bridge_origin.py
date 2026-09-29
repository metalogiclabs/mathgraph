"""Classify Crystal bridge candidates by semantic origin.

Origin classification is not theorem qualification. It answers a cheaper
question first: is the shared symbol actually project-local, or are multiple
corpora merely referring to a common upstream Mathlib declaration?

This lets Crystal avoid spending prover effort on false "bridge" residuals.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from mathgraph.lean_bridge_discovery import extract_declarations
from mathgraph.lean_corpus_bridge_scout import CorpusSpec, scan_local_corpus


PORTED_RE = re.compile(r"\bported\s+from\b", re.IGNORECASE)


@dataclass(frozen=True)
class LocalDefinitionEvidence:
    corpus: str
    file: str
    declaration: str
    kind: str
    ported_marker: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _name_matches(full_name: str, symbol: str) -> bool:
    return full_name == symbol or full_name.endswith("." + symbol)


def collect_local_definition_evidence(
    corpus_roots: Mapping[str, str | Path],
    manifest: Mapping[str, Any],
    symbols: Sequence[str],
) -> dict[str, list[LocalDefinitionEvidence]]:
    wanted = set(symbols)
    out: dict[str, list[LocalDefinitionEvidence]] = defaultdict(list)

    for row in manifest["corpora"]:
        spec = CorpusSpec.from_mapping(row)
        root = Path(corpus_roots[spec.corpus])
        source_texts, _ = scan_local_corpus(root, spec)
        for pin, text in source_texts:
            has_ported_marker = bool(PORTED_RE.search(text))
            for decl in extract_declarations(pin, text):
                for symbol in wanted:
                    if _name_matches(decl.full_name, symbol):
                        out[symbol].append(LocalDefinitionEvidence(
                            corpus=spec.corpus,
                            file=pin.path,
                            declaration=decl.full_name,
                            kind=decl.kind,
                            ported_marker=has_ported_marker,
                        ))
    return dict(out)


def classify_origin(
    symbol: str,
    *,
    corpus_uses: Sequence[str],
    upstream_presence: Mapping[str, bool],
    local_definitions: Sequence[LocalDefinitionEvidence],
) -> dict[str, Any]:
    upstream_present = sorted(k for k, v in upstream_presence.items() if v)
    upstream_missing = sorted(k for k, v in upstream_presence.items() if not v)
    local_corpora = sorted({x.corpus for x in local_definitions})
    ported = any(x.ported_marker for x in local_definitions)

    if upstream_presence and all(upstream_presence.values()):
        origin = "SAME_UPSTREAM"
        bridge_action = "NO_PROJECT_BRIDGE_NEEDED"
    elif upstream_present:
        origin = "UPSTREAM_VERSION_SKEW"
        bridge_action = "QUALIFY_VERSION_TRANSPORT_IF_NEEDED"
    elif len(local_corpora) >= 2 and ported:
        origin = "PORTED_LINEAGE"
        bridge_action = "QUALIFY_PRESERVATION_NOT_INDEPENDENT_EQUIVALENCE"
    elif len(local_corpora) >= 2:
        origin = "PROJECT_LOCAL_SHARED"
        bridge_action = "QUALIFY_PROJECT_LOCAL_RECONCILIATION"
    elif len(local_corpora) == 1:
        origin = "PROJECT_LOCAL_SINGLE"
        bridge_action = "FIND_OR_QUALIFY_CONSUMER_ADAPTER"
    else:
        origin = "AMBIGUOUS"
        bridge_action = "RESOLVE_ORIGIN_BEFORE_PROOF_SEARCH"

    return {
        "symbol": symbol,
        "candidate_id": f"equiv:{symbol}",
        "origin_class": origin,
        "bridge_action": bridge_action,
        "corpus_uses": sorted(set(corpus_uses)),
        "upstream_present_in": upstream_present,
        "upstream_missing_in": upstream_missing,
        "local_definition_corpora": local_corpora,
        "local_definitions": [x.to_dict() for x in local_definitions],
        "ported_marker": ported,
        "qualification_status": "ORIGIN_ONLY_NOT_SEMANTIC_WARRANT",
    }


def classify_report(
    report: Mapping[str, Any],
    *,
    upstream_presence_by_symbol: Mapping[str, Mapping[str, bool]],
    local_definition_evidence: Mapping[str, Sequence[LocalDefinitionEvidence]],
    qualified_candidate_ids: Sequence[str] = (),
) -> dict[str, Any]:
    qualified = set(qualified_candidate_ids)
    rows: list[dict[str, Any]] = []

    for candidate in report["top_equivalence_candidates"]:
        symbol = str(candidate["canonical_symbol"])
        row = classify_origin(
            symbol,
            corpus_uses=candidate.get("corpora", ()),
            upstream_presence=upstream_presence_by_symbol.get(symbol, {}),
            local_definitions=local_definition_evidence.get(symbol, ()),
        )
        row["scout_rank"] = candidate.get("rank")
        row["already_qualified_reusable"] = row["candidate_id"] in qualified
        rows.append(row)

    counts: dict[str, int] = defaultdict(int)
    residual_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["origin_class"]] += 1
        if not row["already_qualified_reusable"]:
            residual_counts[row["origin_class"]] += 1

    genuine_bridge_classes = {
        "PORTED_LINEAGE",
        "PROJECT_LOCAL_SHARED",
        "PROJECT_LOCAL_SINGLE",
        "AMBIGUOUS",
        "UPSTREAM_VERSION_SKEW",
    }
    bridge_residual = [
        row for row in rows
        if not row["already_qualified_reusable"]
        and row["origin_class"] in genuine_bridge_classes
    ]
    upstream_non_bridge = [
        row for row in rows
        if not row["already_qualified_reusable"]
        and row["origin_class"] == "SAME_UPSTREAM"
    ]

    return {
        "schema": "mathgraph.lean-bridge-origin-classification.v1",
        "status": "ORIGIN_CLASSIFIED_NOT_SEMANTICALLY_QUALIFIED",
        "boundary": (
            "Origin classification is routing metadata only. SAME_UPSTREAM means "
            "the pinned Mathlib environments contain the same declaration name; "
            "it does not by itself prove cross-version definitional equality."
        ),
        "candidate_count": len(rows),
        "origin_counts": dict(sorted(counts.items())),
        "residual_origin_counts": dict(sorted(residual_counts.items())),
        "same_upstream_non_bridge_count": len(upstream_non_bridge),
        "genuine_bridge_residual_count": len(bridge_residual),
        "same_upstream_non_bridge": upstream_non_bridge,
        "genuine_bridge_residual": bridge_residual,
        "candidates": rows,
    }


def load_probe_files(paths: Sequence[str | Path]) -> dict[str, dict[str, bool]]:
    by_symbol: dict[str, dict[str, bool]] = defaultdict(dict)
    for path in paths:
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
        env = str(obj["environment"])
        for symbol, present in obj["presence"].items():
            by_symbol[str(symbol)][env] = bool(present)
    return dict(by_symbol)
