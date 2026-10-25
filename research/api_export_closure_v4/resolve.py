#!/usr/bin/env python3
"""V4 bounded static public-export closure (Python stdlib only).

Source independent. Reads only package API files reachable by explicit relative
star imports, plus top-level AST declarations, import bindings and literal __all__.
Does not execute/import target modules, inspect function bodies, or read tests.
Unsupported/dynamic exports are UNKNOWN, never guessed.
"""
import ast
import hashlib
import json
from pathlib import Path

EXCLUDED = {"tests", "test", "docs", "examples", "benchmarks", "build", "dist", "vendor"}
MAX_DEPTH = 5
MAX_FILES = 20


class UnknownExport(Exception):
    pass


def _literal_all(tree):
    found = False
    names = None
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
            continue
        if found:
            raise UnknownExport("REASSIGNED_ALL")
        found = True
        value = node.value
        if not isinstance(value, (ast.List, ast.Tuple)) or not all(
            isinstance(x, ast.Constant) and isinstance(x.value, str) for x in value.elts
        ):
            raise UnknownExport("DYNAMIC_ALL")
        names = [x.value for x in value.elts]
        if len(set(names)) != len(names):
            raise UnknownExport("DUPLICATE_ALL")
    return names


def _relative_target(current, level, module, package_root):
    if level < 1 or not module:
        raise UnknownExport("UNSUPPORTED_STAR_IMPORT")
    directory = current.parent
    for _ in range(level - 1):
        directory = directory.parent
    raw = directory.joinpath(*module.split("."))
    candidates = [raw.with_suffix(".py"), raw / "__init__.py"]
    valid = [p for p in candidates if p.is_file() and p.resolve().is_relative_to(package_root.resolve())]
    if len(valid) != 1:
        raise UnknownExport("MISSING_OR_AMBIGUOUS_LOCAL_MODULE")
    return valid[0]


def _declared_bindings(tree):
    bindings = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bindings.add(node.name)
        if isinstance(node, ast.Import):
            bindings.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            bindings.update(alias.asname or alias.name for alias in node.names if alias.name != "*")
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    bindings.add(t.id)
    return {name for name in bindings if not name.startswith("_")}


def inspect_package(entrypoint, package_root):
    entrypoint = Path(entrypoint)
    package_root = Path(package_root)
    files = {}
    edges = []
    cache = {}
    active = set()

    def resolve(path, depth):
        path = path.resolve()
        if not path.is_relative_to(package_root.resolve()):
            raise UnknownExport("IMPORT_ESCAPED_PACKAGE")
        if depth > MAX_DEPTH or len(files) >= MAX_FILES:
            raise UnknownExport("STATIC_BUDGET")
        if path in cache:
            return cache[path]
        if path in active:
            raise UnknownExport("CYCLIC_STAR_IMPORT")
        active.add(path)
        try:
            data = path.read_bytes()
            tree = ast.parse(data, filename=str(path))
            rel = str(path.relative_to(package_root.resolve()))
            files[rel] = hashlib.sha256(data).hexdigest()
            declared = _declared_bindings(tree)
            inferred = set(declared)
            for node in tree.body:
                if not isinstance(node, ast.ImportFrom):
                    continue
                if not any(alias.name == "*" for alias in node.names):
                    continue
                target = _relative_target(path, node.level, node.module, package_root)
                tgt_rel = str(target.resolve().relative_to(package_root.resolve()))
                edges.append({"from": rel, "to": tgt_rel, "kind": "relative-star"})
                inferred.update(resolve(target, depth + 1))
            all_names = _literal_all(tree)
            if all_names is not None:
                missing = set(all_names) - inferred
                if missing:
                    raise UnknownExport("ALL_NOT_STATICALLY_BOUND:" + ",".join(sorted(missing)))
                result = set(all_names)
            else:
                result = {s for s in inferred if not s.startswith("_")}
            if "*" in result:
                raise UnknownExport("UNRESOLVED_STAR_BINDING")
            cache[path] = result
            return result
        finally:
            active.remove(path)

    exports = resolve(entrypoint, 0)
    manifest = {"files": dict(sorted(files.items())),
                "edges": sorted(edges, key=lambda x: (x["from"], x["to"]))}
    return {
        "exports": sorted(exports),
        "api_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "api_manifest": manifest,
        "status": "STATIC_EXPORT_CLOSURE_BOUNDED",
    }


def scan(root):
    root = Path(root)
    paths = sorted(set(root.glob("src/*/__init__.py")) | set(root.glob("*/__init__.py")))
    paths = [p for p in paths if p.parent.name not in EXCLUDED and not p.parent.name.startswith(".")]
    if not paths:
        return {"status": "UNKNOWN_NO_API_ENTRYPOINT", "exports": []}
    candidate = []
    for path in paths:
        try:
            result = inspect_package(path, path.parent)
        except (UnknownExport, SyntaxError, OSError) as exc:
            result = {"status": "UNKNOWN_STATIC_EXPORT:" + str(exc), "exports": []}
        symbols = result["exports"]
        priority = (0 if any("slug" in s.lower() for s in symbols) else
                    1 if any(any(t in s.lower() for t in ("normaliz", "normalis", "canonical", "standardiz", "standardis")) for s in symbols) else 2)
        candidate.append((priority, str(path.relative_to(root)), path, result))
    _, relative, path, result = sorted(candidate, key=lambda item: (item[0], item[1]))[0]
    return {**result, "relative_api_path": relative, "module": path.parent.name}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    data = scan(a.source)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
    print("STATIC_PUBLIC_API_EXPORT_CLOSURE", data["status"], data["exports"])


if __name__ == "__main__":
    main()
