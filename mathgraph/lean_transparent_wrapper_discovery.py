"""Conservative discovery of differently-named transparent Lean wrappers.

V1 targets a deliberately narrow but mechanically checkable grammar:
one-field `class`/`structure` propositions whose field proposition appears
as an explicit/implicit binder type in a theorem or definition from another
corpus.

This is candidate generation only. A match never creates semantic warrant;
Lean qualification is still required before promotion.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from mathgraph.lean_bridge_discovery import (
    LeanDeclaration,
    SourcePin,
    extract_declarations,
)
from mathgraph.lean_corpus_bridge_scout import CorpusSpec, scan_local_corpus


_DECL_START_RE = re.compile(
    r"(?m)^[ \t]*(?P<kind>class|structure)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_'.]*)\b"
)
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*")
_FIELD_RE = re.compile(
    r"^[ \t]+(?P<name>[A-Za-z_][A-Za-z0-9_']*)\s*:\s*(?P<type>.+?)\s*$"
)
_COMMENT_BLOCK_RE = re.compile(r"/-[\s\S]*?-/")
_COMMENT_LINE_RE = re.compile(r"--[^\n]*")


@dataclass(frozen=True)
class TransparentWrapper:
    corpus: str
    file: str
    kind: str
    name: str
    full_name: str
    parameters: tuple[str, ...]
    field_name: str
    field_type: str
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WrapperConsumerCandidate:
    source_corpus: str
    wrapper: str
    wrapper_file: str
    field_name: str
    canonical_field_type: str
    fingerprint: str
    consumer_corpus: str
    consumer_file: str
    consumer_declaration: str
    consumer_kind: str
    consumer_premise_name: str
    consumer_premise_type: str
    status: str = "CANDIDATE_REQUIRES_VERIFIER"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _strip_comments(text: str) -> str:
    return _COMMENT_LINE_RE.sub(" ", _COMMENT_BLOCK_RE.sub(" ", text))


def _matching_close(ch: str) -> str:
    return {"(": ")", "{": "}", "[": "]"}[ch]


def _top_level_groups(text: str) -> list[tuple[str, str]]:
    """Return balanced top-level binder-like groups with their delimiters."""

    out: list[tuple[str, str]] = []
    stack: list[str] = []
    start: int | None = None
    opener = ""
    for i, ch in enumerate(text):
        if ch in "({[":
            if not stack:
                start = i
                opener = ch
            stack.append(_matching_close(ch))
        elif ch in ")}]":
            if not stack or ch != stack[-1]:
                continue
            stack.pop()
            if not stack and start is not None:
                out.append((opener, text[start + 1 : i]))
                start = None
                opener = ""
    return out


def _split_top_level_colon(text: str) -> tuple[str, str] | None:
    stack: list[str] = []
    for i, ch in enumerate(text):
        if ch in "({[":
            stack.append(_matching_close(ch))
        elif ch in ")}]" and stack and ch == stack[-1]:
            stack.pop()
        elif ch == ":" and not stack:
            if i + 1 < len(text) and text[i + 1] == "=":
                continue
            return text[:i], text[i + 1 :]
    return None


def _binder_names(text: str) -> tuple[str, ...]:
    names: list[str] = []
    for _, group in _top_level_groups(text):
        split = _split_top_level_colon(group)
        if not split:
            continue
        left, _ = split
        for token in _IDENT_RE.findall(left):
            if "." not in token and token != "_":
                names.append(token)
    # Stable de-duplication.
    return tuple(dict.fromkeys(names))


def _semantic_token_count(expr: str, variables: Sequence[str]) -> int:
    varset = set(variables)
    count = 0
    for token in _IDENT_RE.findall(expr):
        short = token.split(".")[-1]
        if token in varset or short in varset:
            continue
        if token in {"Prop", "Type", "Type*", "Sort", "True", "False"}:
            continue
        count += 1
    return count


def normalize_proposition(expr: str, variables: Sequence[str]) -> str:
    """Alpha-normalize local binder names while retaining semantic constants."""

    expr = _strip_comments(expr).strip()
    # Remove harmless outer whitespace, not structural parentheses.
    for name in sorted(set(variables), key=len, reverse=True):
        expr = re.sub(
            rf"(?<![A-Za-z0-9_'.]){re.escape(name)}(?![A-Za-z0-9_'])",
            "□",
            expr,
        )
    expr = re.sub(r"\s+", "", expr)
    return expr


def _namespace_at(text: str, pos: int) -> tuple[str, ...]:
    """Small source-level namespace stack before a declaration position."""

    namespace: list[str] = []
    for line in text[:pos].splitlines():
        m = re.match(r"^\s*namespace\s+([A-Za-z_][A-Za-z0-9_'.]*)\s*$", line)
        if m:
            namespace.append(m.group(1))
            continue
        m = re.match(r"^\s*end(?:\s+([A-Za-z_][A-Za-z0-9_'.]*))?\s*$", line)
        if m and namespace:
            wanted = m.group(1)
            if wanted is None:
                namespace.pop()
            else:
                while namespace:
                    got = namespace.pop()
                    if got == wanted or got.endswith("." + wanted):
                        break
    return tuple(namespace)


def extract_transparent_wrappers(pin: SourcePin, text: str) -> list[TransparentWrapper]:
    """Extract single-field Prop wrappers from one Lean source file."""

    cleaned = _strip_comments(text)
    lines = cleaned.splitlines(keepends=True)
    offsets: list[int] = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line)

    out: list[TransparentWrapper] = []
    for m in _DECL_START_RE.finditer(cleaned):
        start = m.start()
        # Restrict to the current declaration header + indented body.
        line_start = cleaned.rfind("\n", 0, start) + 1
        header_end = cleaned.find("\n", start)
        if header_end < 0:
            header_end = len(cleaned)

        # Support multi-line headers up to ": Prop where".
        probe_end = min(len(cleaned), start + 2500)
        probe = cleaned[start:probe_end]
        marker = re.search(r":\s*Prop\s+where\s*(?:\n|$)", probe)
        if not marker:
            continue
        header_abs_end = start + marker.end()
        header = cleaned[start : start + marker.start()]
        if "extends" in header:
            continue

        body_lines: list[str] = []
        body_start = header_abs_end
        for line in cleaned[body_start:].splitlines():
            if not line.strip():
                if body_lines:
                    break
                continue
            if not line[:1].isspace():
                break
            body_lines.append(line)

        fields = []
        for line in body_lines:
            fm = _FIELD_RE.match(line)
            if fm:
                fields.append((fm.group("name"), fm.group("type").strip()))
        if len(fields) != 1:
            continue

        # Header binders are enough for the narrow transparent-wrapper grammar.
        params = _binder_names(header)
        field_name, field_type = fields[0]
        if _semantic_token_count(field_type, params) < 2:
            continue

        fingerprint = normalize_proposition(field_type, params)
        ns = _namespace_at(cleaned, line_start)
        name = m.group("name")
        full_name = name if "." in name or not ns else ".".join((*ns, name))
        out.append(TransparentWrapper(
            corpus=pin.corpus,
            file=pin.path,
            kind=m.group("kind"),
            name=name,
            full_name=full_name,
            parameters=params,
            field_name=field_name,
            field_type=field_type,
            fingerprint=fingerprint,
        ))
    return out


def declaration_premises(
    declaration: LeanDeclaration,
) -> list[tuple[str, str, str]]:
    """Return binder premise name, raw type, and alpha-normalized fingerprint."""

    statement = _strip_comments(declaration.statement)
    names = _binder_names(statement)
    out: list[tuple[str, str, str]] = []
    for _, group in _top_level_groups(statement):
        split = _split_top_level_colon(group)
        if not split:
            continue
        left, right = split
        left_names = [
            x for x in _IDENT_RE.findall(left)
            if "." not in x and x != "_"
        ]
        if not left_names:
            continue
        right = right.strip()
        if _semantic_token_count(right, names) < 2:
            continue
        out.append((
            left_names[-1],
            right,
            normalize_proposition(right, names),
        ))
    return out


def discover_transparent_wrapper_candidates(
    source_texts: Sequence[tuple[SourcePin, str]],
    *,
    source_corpora: Sequence[str] | None = None,
) -> dict[str, Any]:
    wrappers: list[TransparentWrapper] = []
    declarations: list[LeanDeclaration] = []

    for pin, text in source_texts:
        declarations.extend(extract_declarations(pin, text))
        if source_corpora is None or pin.corpus in source_corpora:
            wrappers.extend(extract_transparent_wrappers(pin, text))

    candidates: list[WrapperConsumerCandidate] = []
    seen: set[tuple[str, str, str, str]] = set()

    for wrapper in wrappers:
        for decl in declarations:
            if decl.corpus == wrapper.corpus:
                continue
            for premise_name, premise_type, fingerprint in declaration_premises(decl):
                if fingerprint != wrapper.fingerprint:
                    continue
                key = (
                    wrapper.corpus,
                    wrapper.full_name,
                    decl.corpus,
                    decl.full_name,
                )
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(WrapperConsumerCandidate(
                    source_corpus=wrapper.corpus,
                    wrapper=wrapper.full_name,
                    wrapper_file=wrapper.file,
                    field_name=wrapper.field_name,
                    canonical_field_type=wrapper.field_type,
                    fingerprint=wrapper.fingerprint,
                    consumer_corpus=decl.corpus,
                    consumer_file=decl.file,
                    consumer_declaration=decl.full_name,
                    consumer_kind=decl.kind,
                    consumer_premise_name=premise_name,
                    consumer_premise_type=premise_type,
                ))

    candidates.sort(key=lambda x: (
        x.source_corpus,
        x.wrapper,
        x.consumer_corpus,
        x.consumer_declaration,
    ))
    return {
        "schema":"mathgraph.transparent-wrapper-discovery.v1",
        "status":"CANDIDATE_DISCOVERY_ONLY",
        "boundary":(
            "Exact alpha-normalized one-field Prop wrapper matching only. "
            "Every candidate requires independent Lean qualification."
        ),
        "wrapper_count":len(wrappers),
        "candidate_count":len(candidates),
        "wrappers":[x.to_dict() for x in wrappers],
        "candidates":[x.to_dict() for x in candidates],
    }


def scan_local_roots(
    manifest: Mapping[str, Any],
    roots: Mapping[str, str | Path],
    *,
    source_corpora: Sequence[str] | None=None,
) -> dict[str, Any]:
    texts: list[tuple[SourcePin,str]] = []
    for row in manifest["corpora"]:
        spec=CorpusSpec.from_mapping(row)
        if spec.corpus not in roots:
            raise KeyError(f"missing root for {spec.corpus}")
        corpus_texts,_=scan_local_corpus(roots[spec.corpus],spec)
        texts.extend(corpus_texts)
    return discover_transparent_wrapper_candidates(
        texts,
        source_corpora=source_corpora,
    )
