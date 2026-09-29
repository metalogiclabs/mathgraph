"""Conservative cross-corpus Lean semantic bridge discovery.

This module proposes candidate bridges from exact, content-pinned Lean source.
Discovery is advisory only. A candidate becomes warranted only after a Lean
qualification gate checks the proposed transport in a concrete environment.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import Iterable, Mapping, Sequence

DECL_RE = re.compile(
    r"^\s*(?P<kind>theorem|lemma|def|abbrev|structure)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_'.]*)\b"
)
NAMESPACE_RE = re.compile(r"^\s*namespace\s+([A-Za-z_][A-Za-z0-9_'.]*)\s*$")
END_RE = re.compile(r"^\s*end(?:\s+([A-Za-z_][A-Za-z0-9_'.]*))?\s*$")
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*")
ALIAS_RHS_RE = re.compile(r":=\s*([A-Za-z_][A-Za-z0-9_'.]*)")
EXTENDS_RE = re.compile(r"\bextends\s+([A-Za-z_][A-Za-z0-9_'.]*)")

COMMON_SYMBOLS = {
    "Type", "Type*", "Prop", "Nat", "Int", "Rat", "List", "Fin", "Set",
    "Finset", "Module", "CommRing", "Ring", "Semiring", "Nontrivial",
    "True", "False", "Classical", "Function", "Ideal", "Submodule",
    "WithBot", "WithTop", "ENat", "Fact", "Prime",
}


@dataclass(frozen=True)
class SourcePin:
    corpus: str
    role: str
    repository: str
    commit: str
    path: str
    blob_sha: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "SourcePin":
        return cls(*(str(value[k]) for k in (
            "corpus", "role", "repository", "commit", "path", "blob_sha"
        )))

    @property
    def raw_url(self) -> str:
        return (
            "https://raw.githubusercontent.com/"
            f"{self.repository}/{self.commit}/{self.path}"
        )


@dataclass(frozen=True)
class LeanDeclaration:
    corpus: str
    role: str
    file: str
    kind: str
    name: str
    full_name: str
    statement: str
    symbols: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AliasRule:
    corpus: str
    alias: str
    target: str
    evidence: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ImplicationRule:
    source: str
    target: str
    evidence: str
    corpus: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def fetch_pin(pin: SourcePin, *, timeout: float = 30.0) -> str:
    req = urllib.request.Request(
        pin.raw_url, headers={"User-Agent": "mathgraph-crystal-bridge-discovery"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read()
    got = git_blob_sha(data)
    if got != pin.blob_sha:
        raise AssertionError(
            f"source pin mismatch for {pin.repository}:{pin.path}: {got} != {pin.blob_sha}"
        )
    return data.decode("utf-8")


def load_manifest(path: str | Path) -> list[SourcePin]:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    return [SourcePin.from_mapping(x) for x in obj["sources"]]


def _qualify(namespace: Sequence[str], name: str) -> str:
    if "." in name or not namespace:
        return name
    return ".".join((*namespace, name))


def _declaration_window(lines: Sequence[str], start: int, limit: int = 40) -> str:
    out: list[str] = []
    for i in range(start, min(len(lines), start + limit)):
        line = lines[i]
        if i > start and DECL_RE.match(line):
            break
        out.append(line.strip())
        joined = " ".join(out)
        if ":=" in joined or re.search(r"\bwhere\b", joined):
            break
    return " ".join(x for x in out if x)


def semantic_symbol_key(token: str) -> str | None:
    token = token.strip(".'")
    if not token:
        return None
    last = token.split(".")[-1]
    if last in COMMON_SYMBOLS:
        return None
    if len(last) < 5:
        return None
    # Semantic heads in Lean tend to be CamelCase / mixed-case identifiers.
    upper_count = sum(ch.isupper() for ch in last)
    if not last[0].isupper() or upper_count < 2:
        return None
    return last


def extract_declarations(pin: SourcePin, text: str) -> list[LeanDeclaration]:
    lines = text.splitlines()
    namespace: list[str] = []
    out: list[LeanDeclaration] = []
    for i, line in enumerate(lines):
        ns = NAMESPACE_RE.match(line)
        if ns:
            namespace.append(ns.group(1))
            continue
        end = END_RE.match(line)
        if end and namespace:
            wanted = end.group(1)
            if wanted is None:
                namespace.pop()
            else:
                # Conservative namespace unwinding.
                while namespace:
                    top = namespace.pop()
                    if top == wanted or top.endswith("." + wanted):
                        break
            continue
        m = DECL_RE.match(line)
        if not m:
            continue
        kind, name = m.group("kind"), m.group("name")
        statement = _declaration_window(lines, i)
        full_name = _qualify(namespace, name)
        symbols = sorted({
            key
            for tok in IDENT_RE.findall(statement)
            if (key := semantic_symbol_key(tok)) is not None
        })
        out.append(LeanDeclaration(
            corpus=pin.corpus,
            role=pin.role,
            file=pin.path,
            kind=kind,
            name=name,
            full_name=full_name,
            statement=statement,
            symbols=tuple(symbols),
        ))
    return out


def discover_aliases(declarations: Sequence[LeanDeclaration]) -> list[AliasRule]:
    out: list[AliasRule] = []
    for d in declarations:
        if d.kind != "abbrev" or ":=" not in d.statement:
            continue
        rhs = ALIAS_RHS_RE.search(d.statement)
        if not rhs:
            continue
        target = semantic_symbol_key(rhs.group(1))
        alias = semantic_symbol_key(d.full_name) or semantic_symbol_key(d.name)
        if alias and target and alias != target:
            out.append(AliasRule(
                corpus=d.corpus,
                alias=alias,
                target=target,
                evidence=f"{d.corpus}:{d.file}:{d.full_name}",
            ))
    return out


def canonicalize_symbol(symbol: str, aliases: Mapping[str, str]) -> str:
    seen: set[str] = set()
    cur = symbol
    while cur in aliases and cur not in seen:
        seen.add(cur)
        cur = aliases[cur]
    return cur


def discover_implications(
    declarations: Sequence[LeanDeclaration],
) -> list[ImplicationRule]:
    out: list[ImplicationRule] = []
    for d in declarations:
        if d.kind != "structure":
            continue
        source = semantic_symbol_key(d.full_name) or semantic_symbol_key(d.name)
        ext = EXTENDS_RE.search(d.statement)
        if not source or not ext:
            continue
        target = semantic_symbol_key(ext.group(1))
        if target and source != target:
            out.append(ImplicationRule(
                source=source,
                target=target,
                evidence=f"{d.corpus}:{d.file}:{d.full_name}",
                corpus=d.corpus,
            ))
    return out


def _canonical_symbols(
    declaration: LeanDeclaration, aliases: Mapping[str, str]
) -> set[str]:
    return {canonicalize_symbol(s, aliases) for s in declaration.symbols}


def discover(
    source_texts: Sequence[tuple[SourcePin, str]],
) -> dict[str, object]:
    declarations: list[LeanDeclaration] = []
    for pin, source in source_texts:
        declarations.extend(extract_declarations(pin, source))

    alias_rules = discover_aliases(declarations)
    alias_map = {r.alias: r.target for r in alias_rules}
    implications = discover_implications(declarations)

    by_symbol: dict[str, list[LeanDeclaration]] = {}
    for d in declarations:
        if d.role == "bridge-library":
            continue
        for symbol in _canonical_symbols(d, alias_map):
            by_symbol.setdefault(symbol, []).append(d)

    equivalence_candidates: list[dict[str, object]] = []
    for symbol, rows in sorted(by_symbol.items()):
        corpora = sorted({d.corpus for d in rows})
        if len(corpora) < 2:
            continue
        equivalence_candidates.append({
            "kind": "shared_semantic_head",
            "canonical_symbol": symbol,
            "corpora": corpora,
            "evidence": [
                {
                    "corpus": d.corpus,
                    "file": d.file,
                    "declaration": d.full_name,
                    "kind": d.kind,
                }
                for d in rows[:20]
            ],
            "status": "CANDIDATE_REQUIRES_VERIFIER",
        })

    implication_candidates: list[dict[str, object]] = []
    non_library = [d for d in declarations if d.role != "bridge-library"]
    for rule in implications:
        producers = [
            d for d in non_library
            if d.role == "producer"
            and rule.source in _canonical_symbols(d, alias_map)
        ]
        consumers = [
            d for d in non_library
            if d.role == "consumer"
            and rule.target in _canonical_symbols(d, alias_map)
        ]
        for p in producers:
            for c in consumers:
                if p.corpus == c.corpus:
                    continue
                implication_candidates.append({
                    "kind": "verified_library_implication_candidate",
                    "source_symbol": rule.source,
                    "target_symbol": rule.target,
                    "producer": {
                        "corpus": p.corpus,
                        "file": p.file,
                        "declaration": p.full_name,
                    },
                    "consumer": {
                        "corpus": c.corpus,
                        "file": c.file,
                        "declaration": c.full_name,
                    },
                    "bridge_evidence": rule.evidence,
                    "status": "CANDIDATE_REQUIRES_VERIFIER",
                })

    return {
        "schema": "mathgraph.lean-bridge-discovery.v1",
        "boundary": (
            "Exact source pins and deterministic discovery only. "
            "Candidates do not promote truth; Lean qualification is required."
        ),
        "declaration_count": len(declarations),
        "alias_rules": [x.to_dict() for x in alias_rules],
        "implication_rules": [x.to_dict() for x in implications],
        "equivalence_candidates": equivalence_candidates,
        "implication_candidates": implication_candidates,
        "declarations": [x.to_dict() for x in declarations],
    }


def run_manifest(
    manifest_path: str | Path,
    *,
    out_path: str | Path | None = None,
) -> dict[str, object]:
    pins = load_manifest(manifest_path)
    texts = [(pin, fetch_pin(pin)) for pin in pins]
    result = discover(texts)
    result["source_pins"] = [asdict(pin) for pin in pins]
    if out_path is not None:
        Path(out_path).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return result
