"""Corpus-wide conservative Lean bridge scouting.

This extends the bounded file-level Crystal bridge discovery experiment to the
public theorem/API surfaces of multiple independently developed Lean corpora.

The scout is deliberately non-authoritative. It may discover candidate
semantic overlaps and consequence routes, but every route remains UNKNOWN until
a separate verifier-backed qualification promotes it.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from mathgraph.lean_bridge_discovery import (
    SourcePin,
    discover,
    extract_declarations,
    git_blob_sha,
)


@dataclass(frozen=True)
class CorpusSpec:
    corpus: str
    role: str
    repository: str
    commit: str
    include_prefixes: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CorpusSpec":
        return cls(
            corpus=str(value["corpus"]),
            role=str(value["role"]),
            repository=str(value["repository"]),
            commit=str(value["commit"]),
            include_prefixes=tuple(str(x) for x in value["include_prefixes"]),
        )


@dataclass(frozen=True)
class CorpusScanSummary:
    corpus: str
    role: str
    repository: str
    commit: str
    file_count: int
    source_bytes: int
    declaration_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_corpus_manifest(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _iter_lean_files(root: Path, prefixes: Sequence[str]) -> list[Path]:
    files: list[Path] = []
    for prefix in prefixes:
        base = root / prefix
        if not base.exists():
            raise FileNotFoundError(base)
        for p in base.rglob("*.lean"):
            if any(part in {".lake", "build"} for part in p.parts):
                continue
            files.append(p)
    return sorted(set(files))


def scan_local_corpus(root: str | Path, spec: CorpusSpec) -> tuple[
    list[tuple[SourcePin, str]], CorpusScanSummary
]:
    root_path = Path(root)
    source_texts: list[tuple[SourcePin, str]] = []
    source_bytes = 0
    declaration_count = 0

    for path in _iter_lean_files(root_path, spec.include_prefixes):
        data = path.read_bytes()
        text = data.decode("utf-8")
        rel = str(path.relative_to(root_path))
        pin = SourcePin(
            corpus=spec.corpus,
            role=spec.role,
            repository=spec.repository,
            commit=spec.commit,
            path=rel,
            blob_sha=git_blob_sha(data),
        )
        source_texts.append((pin, text))
        source_bytes += len(data)
        declaration_count += len(extract_declarations(pin, text))

    summary = CorpusScanSummary(
        corpus=spec.corpus,
        role=spec.role,
        repository=spec.repository,
        commit=spec.commit,
        file_count=len(source_texts),
        source_bytes=source_bytes,
        declaration_count=declaration_count,
    )
    return source_texts, summary


def _candidate_key(candidate: Mapping[str, Any]) -> str:
    if candidate.get("kind") == "shared_semantic_head":
        return "equiv:" + str(candidate["canonical_symbol"])
    return (
        "impl:"
        + str(candidate.get("source_symbol", ""))
        + "->"
        + str(candidate.get("target_symbol", ""))
        + ":"
        + str(candidate.get("producer", {}).get("corpus", ""))
        + "->"
        + str(candidate.get("consumer", {}).get("corpus", ""))
        + ":"
        + str(candidate.get("producer", {}).get("declaration", ""))
        + "->"
        + str(candidate.get("consumer", {}).get("declaration", ""))
    )


def rank_equivalence_candidates(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = [dict(x) for x in rows]
    out.sort(
        key=lambda x: (
            -len(x.get("corpora", ())),
            -len(x.get("evidence", ())),
            str(x.get("canonical_symbol", "")),
        )
    )
    for i, row in enumerate(out, 1):
        row["rank"] = i
        row["candidate_id"] = _candidate_key(row)
        row["qualification_status"] = "UNKNOWN_UNQUALIFIED"
    return out


def rank_implication_candidates(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = [dict(x) for x in rows]
    out.sort(
        key=lambda x: (
            str(x.get("source_symbol", "")),
            str(x.get("target_symbol", "")),
            str(x.get("producer", {}).get("corpus", "")),
            str(x.get("consumer", {}).get("corpus", "")),
            str(x.get("producer", {}).get("declaration", "")),
            str(x.get("consumer", {}).get("declaration", "")),
        )
    )
    for i, row in enumerate(out, 1):
        row["rank"] = i
        row["candidate_id"] = _candidate_key(row)
        row["qualification_status"] = "UNKNOWN_UNQUALIFIED"
    return out


def build_scout_report(
    *,
    corpus_roots: Mapping[str, str | Path],
    manifest: Mapping[str, Any],
    bridge_texts: Sequence[tuple[SourcePin, str]],
    top_k: int | None = None,
) -> dict[str, Any]:
    source_texts: list[tuple[SourcePin, str]] = []
    summaries: list[CorpusScanSummary] = []

    for row in manifest["corpora"]:
        spec = CorpusSpec.from_mapping(row)
        if spec.corpus not in corpus_roots:
            raise KeyError(f"missing local corpus root: {spec.corpus}")
        texts, summary = scan_local_corpus(corpus_roots[spec.corpus], spec)
        source_texts.extend(texts)
        summaries.append(summary)

    discovery = discover([*source_texts, *bridge_texts])
    equivalence = rank_equivalence_candidates(discovery["equivalence_candidates"])
    implication = rank_implication_candidates(discovery["implication_candidates"])

    k = int(top_k if top_k is not None else manifest.get("top_k", 20))
    top_equivalence = equivalence[:k]
    top_implication = implication[:k]
    all_ids = [x["candidate_id"] for x in equivalence] + [x["candidate_id"] for x in implication]

    return {
        "schema": "mathgraph.lean-corpus-bridge-scout.v1",
        "status": "CANDIDATE_SCOUT_ONLY",
        "trust_boundary": (
            "Corpus-wide source scanning and deterministic ranking are advisory. "
            "Every candidate is UNKNOWN until separately qualified by Lean."
        ),
        "corpora": [x.to_dict() for x in summaries],
        "totals": {
            "corpus_file_count": sum(x.file_count for x in summaries),
            "corpus_source_bytes": sum(x.source_bytes for x in summaries),
            "corpus_declaration_count": sum(x.declaration_count for x in summaries),
            "bridge_file_count": len(bridge_texts),
            "parsed_declaration_count_including_bridge": discovery["declaration_count"],
            "alias_rule_count": len(discovery["alias_rules"]),
            "implication_rule_count": len(discovery["implication_rules"]),
            "equivalence_candidate_count": len(equivalence),
            "implication_candidate_count": len(implication),
            "unqualified_candidate_count": len(all_ids),
        },
        "alias_rules": discovery["alias_rules"],
        "implication_rules": discovery["implication_rules"],
        "top_equivalence_candidates": top_equivalence,
        "top_implication_candidates": top_implication,
        "all_candidate_ids": all_ids,
        "default_disposition": "UNKNOWN_UNQUALIFIED",
    }


def write_report(report: Mapping[str, Any], out_path: str | Path) -> None:
    Path(out_path).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
