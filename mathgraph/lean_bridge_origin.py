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
    environment_by_corpus: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    qualified = set(qualified_candidate_ids)
    rows: list[dict[str, Any]] = []

    for candidate in report["top_equivalence_candidates"]:
        symbol = str(candidate["canonical_symbol"])
        corpora = tuple(str(x) for x in candidate.get("corpora", ()))
        all_presence = dict(upstream_presence_by_symbol.get(symbol, {}))
        if environment_by_corpus:
            relevant_envs = tuple(
                environment_by_corpus[c]
                for c in corpora
                if c in environment_by_corpus
            )
            presence = {
                env: all_presence.get(env, False)
                for env in relevant_envs
            }
        else:
            relevant_envs = tuple(all_presence)
            presence = all_presence
        row = classify_origin(
            symbol,
            corpus_uses=corpora,
            upstream_presence=presence,
            local_definitions=local_definition_evidence.get(symbol, ()),
        )
        row["upstream_environments"] = list(relevant_envs)
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


def load_short_declaration_probe_files(
    paths: Sequence[str | Path],
) -> dict[str, dict[str, bool]]:
    by_symbol: dict[str, dict[str, bool]] = defaultdict(dict)
    for path in paths:
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
        env = str(obj["environment"])
        for symbol, present in obj.get("short_declaration_presence", {}).items():
            by_symbol[str(symbol)][env] = bool(present)
    return dict(by_symbol)


def load_short_declaration_count_probe_files(
    paths: Sequence[str | Path],
) -> dict[str, dict[str, int]]:
    by_symbol: dict[str, dict[str, int]] = defaultdict(dict)
    for path in paths:
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
        env = str(obj["environment"])
        for symbol, count in obj.get("short_declaration_count", {}).items():
            by_symbol[str(symbol)][env] = int(count)
    return dict(by_symbol)


def load_short_declaration_name_probe_files(
    paths: Sequence[str | Path],
) -> dict[str, dict[str, tuple[str, ...]]]:
    by_symbol: dict[str, dict[str, tuple[str, ...]]] = defaultdict(dict)
    for path in paths:
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
        env = str(obj["environment"])
        for symbol, names in obj.get("short_declaration_names", {}).items():
            by_symbol[str(symbol)][env] = tuple(sorted(str(x) for x in names))
    return dict(by_symbol)


def _is_dependent_member_symbol(symbol: str) -> bool:
    if "." not in symbol:
        return False
    first = symbol.split(".", 1)[0]
    return first[:1].islower() or len(first) == 1


def refine_origin_classification(
    classification: Mapping[str, Any],
    *,
    short_declaration_presence_by_symbol: Mapping[str, Mapping[str, bool]],
    short_declaration_count_by_symbol: Mapping[str, Mapping[str, int]] | None = None,
    short_declaration_names_by_symbol: Mapping[
        str, Mapping[str, Sequence[str]]
    ] | None = None,
) -> dict[str, Any]:
    rows = [dict(x) for x in classification["candidates"]]

    for row in rows:
        symbol = str(row["symbol"])
        all_short_presence = dict(
            short_declaration_presence_by_symbol.get(symbol, {})
        )
        relevant_envs = tuple(row.get("upstream_environments", all_short_presence))
        short_presence = {
            env: all_short_presence.get(env, False)
            for env in relevant_envs
        }
        short_all = bool(short_presence) and all(short_presence.values())
        all_short_counts = dict(
            (short_declaration_count_by_symbol or {}).get(symbol, {})
        )
        short_counts = {
            env: int(all_short_counts.get(env, 0))
            for env in relevant_envs
        }
        row["upstream_short_declaration_counts"] = short_counts
        max_short_count = max(short_counts.values(), default=0)
        all_short_names = (
            (short_declaration_names_by_symbol or {}).get(symbol, {})
        )
        short_names = {
            env: tuple(sorted(str(x) for x in all_short_names.get(env, ())))
            for env in relevant_envs
        }
        row["upstream_short_declaration_names"] = {
            env: list(names) for env, names in short_names.items()
        }
        common_full_names: set[str] = set()
        if short_names and all(short_names.values()):
            sets = [set(names) for names in short_names.values()]
            if sets:
                common_full_names = set.intersection(*sets)
        row["upstream_common_full_names"] = sorted(common_full_names)
        local_defs = list(row.get("local_definitions", ()))
        local_full_names = sorted({
            str(x["declaration"]) for x in local_defs
        })

        row["upstream_short_declaration_presence"] = short_presence

        # A short-name match between different local constants is not an
        # equivalence candidate. Reopen under the fully-qualified names instead.
        if len(local_full_names) >= 2:
            row["origin_class"] = "SHORT_NAME_COLLISION"
            row["bridge_action"] = "REJECT_SHORT_NAME_EQUIVALENCE_REDISCOVER_FULL_NAMES"
            row["collision_full_names"] = local_full_names
            continue

        # One project-local declaration plus a ubiquitous upstream declaration
        # of the same short name is also unsafe to unify by spelling alone.
        if len(local_full_names) == 1 and short_all:
            row["origin_class"] = "MIXED_LOCAL_UPSTREAM_COLLISION"
            row["bridge_action"] = "REJECT_SHORT_NAME_EQUIVALENCE_RESOLVE_FULL_NAME"
            row["collision_full_names"] = local_full_names
            continue

        if row["origin_class"] == "AMBIGUOUS" and short_all:
            if len(common_full_names) == 1:
                resolved = next(iter(common_full_names))
                row["origin_class"] = "SAME_UPSTREAM_RESOLVED_REFERENCE"
                row["bridge_action"] = "NO_PROJECT_BRIDGE_NEEDED"
                row["resolved_upstream_name"] = resolved
            elif len(common_full_names) > 1 or max_short_count > 1:
                row["origin_class"] = "UPSTREAM_SHORT_NAME_COLLISION"
                row["bridge_action"] = "REJECT_SHORT_NAME_EQUIVALENCE_RESOLVE_FULL_NAME"
            elif _is_dependent_member_symbol(symbol):
                row["origin_class"] = "UPSTREAM_DEPENDENT_MEMBER_REFERENCE"
                row["bridge_action"] = "RESOLVE_RECEIVER_BEFORE_ANY_BRIDGE_SEARCH"
            else:
                row["origin_class"] = "SAME_UPSTREAM_NAMESPACE_REFERENCE"
                row["bridge_action"] = "NO_PROJECT_BRIDGE_NEEDED_RESOLVE_NAMESPACE_IF_USED"
            continue

        if row["origin_class"] == "AMBIGUOUS" and any(short_presence.values()):
            row["origin_class"] = "UPSTREAM_SHORTNAME_VERSION_SKEW"
            row["bridge_action"] = "QUALIFY_VERSION_NAMESPACE_TRANSPORT_IF_NEEDED"

    counts: dict[str, int] = defaultdict(int)
    residual_counts: dict[str, int] = defaultdict(int)
    qualified = []
    for row in rows:
        counts[row["origin_class"]] += 1
        if row.get("already_qualified_reusable"):
            qualified.append(row)
        else:
            residual_counts[row["origin_class"]] += 1

    non_bridge_classes = {
        "SAME_UPSTREAM",
        "SAME_UPSTREAM_NAMESPACE_REFERENCE",
        "SAME_UPSTREAM_DEPENDENT_REFERENCE",
        "SAME_UPSTREAM_RESOLVED_REFERENCE",
        "UPSTREAM_DEPENDENT_MEMBER_REFERENCE",
    }
    collision_classes = {
        "SHORT_NAME_COLLISION",
        "MIXED_LOCAL_UPSTREAM_COLLISION",
        "UPSTREAM_SHORT_NAME_COLLISION",
    }
    project_bridge_classes = {
        "PORTED_LINEAGE",
        "PROJECT_LOCAL_SHARED",
        "PROJECT_LOCAL_SINGLE",
        "UPSTREAM_VERSION_SKEW",
        "UPSTREAM_SHORTNAME_VERSION_SKEW",
        "AMBIGUOUS",
    }

    non_bridge = [
        x for x in rows
        if not x.get("already_qualified_reusable")
        and x["origin_class"] in non_bridge_classes
    ]
    collisions = [
        x for x in rows
        if not x.get("already_qualified_reusable")
        and x["origin_class"] in collision_classes
    ]
    project_residual = [
        x for x in rows
        if not x.get("already_qualified_reusable")
        and x["origin_class"] in project_bridge_classes
    ]

    return {
        "schema": "mathgraph.lean-bridge-origin-classification.v2",
        "status": "ORIGIN_REFINED_NOT_SEMANTIC_WARRANT",
        "boundary": (
            "This is routing and candidate-rejection evidence, not a proof of "
            "cross-version semantic equality. Common upstream references require "
            "no project-to-project bridge unless a downstream consequence needs "
            "version-specific qualification."
        ),
        "candidate_count": len(rows),
        "qualified_reusable_count": len(qualified),
        "origin_counts": dict(sorted(counts.items())),
        "residual_origin_counts": dict(sorted(residual_counts.items())),
        "no_project_bridge_needed_count": len(non_bridge),
        "short_name_collision_count": len(collisions),
        "project_bridge_residual_count": len(project_residual),
        "project_bridge_residual": project_residual,
        "short_name_collisions": collisions,
        "no_project_bridge_needed": non_bridge,
        "candidates": rows,
    }
