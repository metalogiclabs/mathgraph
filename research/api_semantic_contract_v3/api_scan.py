#!/usr/bin/env python3
"""Source-independent public API export scanner, before any implementation/native outcomes."""
import ast
import hashlib
from pathlib import Path

EXCLUDED = {"tests", "test", "docs", "examples", "benchmarks", "build", "dist", "vendor"}


def exported_symbols(path):
    raw = path.read_bytes()
    tree = ast.parse(raw, filename=str(path))
    inferred = set()
    declared = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not node.name.startswith("_"):
                inferred.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                name = alias.asname or (alias.name.split(".")[0] if isinstance(node, ast.Import) else alias.name)
                if not name.startswith("_"):
                    inferred.add(name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
                if isinstance(node.value, (ast.Tuple, ast.List)):
                    declared = {x.value for x in node.value.elts if isinstance(x, ast.Constant) and isinstance(x.value, str)}
    return {
        "exports": sorted(inferred if declared is None else declared),
        "api_sha256": hashlib.sha256(raw).hexdigest(),
    }


def identify_public_entrypoint(root):
    root = Path(root)
    paths = sorted(set(root.glob("src/*/__init__.py")) | set(root.glob("*/__init__.py")))
    paths = [p for p in paths if p.parent.name not in EXCLUDED and not p.parent.name.startswith(".")]
    if not paths:
        return None
    # This chooses from top-level API export files only, not implementation bodies.
    candidates = []
    for path in paths:
        info = exported_symbols(path)
        symbols = info["exports"]
        rank = (0 if any("slug" in s.lower() for s in symbols) else
                1 if any(any(q in s.lower() for q in ("normaliz", "normalis", "canonical", "standardiz", "standardis")) for s in symbols) else 2)
        candidates.append((rank, str(path.relative_to(root)), path, info))
    _, rel, path, info = sorted(candidates, key=lambda item: (item[0], item[1]))[0]
    return {"relative_api_path": rel, "module": path.parent.name, **info}
