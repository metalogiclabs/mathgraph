#!/usr/bin/env python3
"""Source-independent, abstention-capable public-API semantic obligation proposer.
Frozen before inspecting held-out implementation or tests. Standard library only.
"""
import argparse, ast, hashlib, json, re
from pathlib import Path

# Not a claim to learn arbitrary intent. This is a fixed finite relation grammar.
FAMILIES = {
    "toml": {"writer": ("dumps", "serialize", "encode"), "reader": ("loads", "parse", "decode"), "oracle": "tomllib.loads"},
    "json": {"writer": ("dumps", "serialize", "encode"), "reader": ("loads", "parse", "decode"), "oracle": "json.loads"},
}
# A separately frozen, expert-authored conventional cookbook with identical access.
EXPERT_WRITERS = ("dumps", "encode", "serialize")
EXPERT_READERS = ("loads", "decode", "parse")


def classify(repository, description):
    tokens = set(re.findall(r"[a-z0-9]+", repository.lower() + " " + description.lower()))
    formats = sorted(set(FAMILIES).intersection(tokens))
    # The repository identifier suffix counts as public metadata, never source.
    formats += [x for x in FAMILIES if x in repository.lower().split("/")[-1] and x not in formats]
    return formats[0] if len(formats) == 1 else None


def public_api(init_file):
    tree = ast.parse(init_file.read_text(encoding="utf-8"), filename=str(init_file))
    seen = set()
    declared = set()
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not stmt.name.startswith("_"):
                seen.add(stmt.name)
        elif isinstance(stmt, (ast.ImportFrom, ast.Import)):
            for name in stmt.names:
                label = name.asname or name.name.split(".")[0]
                if not label.startswith("_"):
                    seen.add(label)
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
                value = stmt.value
                if isinstance(value, (ast.List, ast.Tuple)):
                    declared |= {v.value for v in value.elts if isinstance(v, ast.Constant) and isinstance(v.value, str)}
    return sorted(seen.intersection(declared) if declared else seen)


def propose(metadata, init_file, arm):
    fmt = classify(metadata["repository"], metadata.get("description") or "")
    names = public_api(init_file)
    result = {
        "arm": arm, "repository": metadata["repository"], "source_sha": metadata["source_sha"],
        "api_sha256": hashlib.sha256(init_file.read_bytes()).hexdigest(),
        "public_symbols": names, "format": fmt, "status": "UNKNOWN_NO_SUPPORTED_RELATION",
        "obligations": [], "authority": "public API AST and repository metadata only",
    }
    if fmt is None:
        return result
    grammar = FAMILIES[fmt]
    if arm == "candidate":
        writers, readers = grammar["writer"], grammar["reader"]
    else:
        writers, readers = EXPERT_WRITERS, EXPERT_READERS
    writer = next((name for name in writers if name in names), None)
    reader = next((name for name in readers if name in names), None)
    if writer is None:
        return result
    result["status"] = "CANDIDATE_PENDING_INDEPENDENT_NATIVE_VERIFICATION"
    result["obligations"].append({
        "id": "external-semantics", "writer": writer, "reader": None,
        "relation": "independent_parse(writer(mapping)) == mapping",
        "oracle": grammar["oracle"], "domain": "predeclared JSON/TOML-compatible mappings",
    })
    if reader:
        result["obligations"].append({
            "id": "native-roundtrip", "writer": writer, "reader": reader,
            "relation": "reader(writer(mapping)) == mapping",
            "oracle": "actual source-native public reader; NOT independent reference",
            "domain": "predeclared JSON/TOML-compatible mappings",
        })
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata", type=Path, required=True)
    ap.add_argument("--api", type=Path, required=True)
    ap.add_argument("--arm", choices=("candidate", "expert"), required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    metadata = json.loads(args.metadata.read_text())
    assert re.fullmatch(r"[0-9a-f]{40}", metadata["source_sha"])
    obj = propose(metadata, args.api, args.arm)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n")
    print("PRE_EXECUTION_PROPOSAL", args.arm, obj["status"], [v["id"] for v in obj["obligations"]])


if __name__ == "__main__":
    main()
