#!/usr/bin/env python3
"""Frozen V2 public-API-only semantic-obligation proposal with alias recognition.

No import, invocation, implementation-body reading, target-specific hints, or network.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

FORMATS = {
    "toml": {"oracle": "tomllib.loads"},
    "json": {"oracle": "json.loads"},
}
WRITERS = ("dumps", "serialize", "encode")
READERS = ("loads", "parse", "decode")


def classify(metadata: dict) -> str | None:
    txt = (metadata["repository"] + " " + (metadata.get("description") or "")).lower()
    words = set(re.findall(r"[a-z0-9]+", txt))
    hits = [k for k in FORMATS if k in words or k in metadata["repository"].lower().split("/")[-1]]
    return hits[0] if len(hits) == 1 else None


def module_alias_root(value: ast.AST) -> tuple[str, int] | None:
    depth = 0
    while isinstance(value, ast.Attribute):
        depth += 1
        value = value.value
    if isinstance(value, ast.Name) and 1 <= depth <= 2:
        return value.id, depth
    return None


def public_exports(source: bytes) -> tuple[list[str], dict[str, str]]:
    tree = ast.parse(source.decode("utf-8"))
    callable_names: dict[str, str] = {}
    module_bindings = set()
    explicit = None
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not stmt.name.startswith("_"):
                callable_names[stmt.name] = "direct_function"
        elif isinstance(stmt, ast.Import):
            for imported in stmt.names:
                module_bindings.add(imported.asname or imported.name.split(".")[0])
        elif isinstance(stmt, ast.ImportFrom):
            for imported in stmt.names:
                if imported.name == "*":
                    continue
                bound = imported.asname or imported.name
                module_bindings.add(bound)
                if not bound.startswith("_"):
                    callable_names[bound] = "imported_export"
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            value = stmt.value
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id == "__all__":
                    if isinstance(value, (ast.List, ast.Tuple)):
                        vals = [v.value for v in value.elts
                                if isinstance(v, ast.Constant) and isinstance(v.value, str)]
                        if len(vals) == len(value.elts):
                            explicit = set(vals)
                    continue
                if target.id.startswith("_"):
                    continue
                chain = module_alias_root(value)
                if chain and chain[0] in module_bindings:
                    callable_names[target.id] = "static_imported_attribute_alias"
    if explicit is not None:
        callable_names = {k: v for k, v in callable_names.items() if k in explicit}
    return sorted(callable_names), callable_names


def propose(metadata: dict, api_path: Path) -> dict:
    raw = api_path.read_bytes()
    fmt = classify(metadata)
    names, origins = public_exports(raw)
    result = {
        "arm": "candidate", "repository": metadata["repository"],
        "source_sha": metadata["source_sha"],
        "api_sha256": hashlib.sha256(raw).hexdigest(),
        "public_symbols": names,
        "symbol_provenance": {k: origins[k] for k in names},
        "format": fmt,
        "status": "UNKNOWN_NO_SUPPORTED_RELATION",
        "obligations": [],
        "authority": "public root initializer AST plus repository description, before source runtime execution",
    }
    if fmt is None:
        return result
    writer = next((s for s in WRITERS if s in origins), None)
    reader = next((s for s in READERS if s in origins), None)
    if writer is None:
        return result
    result["status"] = "CANDIDATE_PENDING_INDEPENDENT_NATIVE_VERIFICATION"
    result["obligations"] = [{
        "id": "external-semantics", "writer": writer, "reader": None,
        "relation": "independent_parse(writer(mapping)) == mapping",
        "oracle": FORMATS[fmt]["oracle"],
        "domain": "predeclared JSON/TOML-compatible mappings",
    }]
    if reader is not None:
        result["obligations"].append({
            "id": "native-roundtrip", "writer": writer, "reader": reader,
            "relation": "reader(writer(mapping)) == mapping",
            "oracle": "original public reader, not independent",
            "domain": "predeclared JSON/TOML-compatible mappings",
        })
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata", type=Path, required=True)
    ap.add_argument("--api", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    md = json.loads(a.metadata.read_text())
    assert re.fullmatch(r"[a-f0-9]{40}", md["source_sha"])
    receipt = propose(md, a.api)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print("V2_CANDIDATE_API_PROPOSAL", receipt["status"],
          [x["id"] for x in receipt["obligations"]])


if __name__ == "__main__":
    main()
