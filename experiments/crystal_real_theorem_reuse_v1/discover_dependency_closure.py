#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from collections import deque
from pathlib import Path

DEFAULT_REPO = "anthropics/fermats-last-theorem"
DEFAULT_COMMIT = "6e837e75355538c7f80bab5b956861e86c4eacc2"
INTERNAL_PREFIXES = ("P2M.", "Theorems.")


def request_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "mathgraph-crystal-residual-first"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def parse_imports(text: str) -> list[str]:
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("import "):
            continue
        out.extend(line[len("import "):].split())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root-file", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--commit", default=DEFAULT_COMMIT)
    args = ap.parse_args()

    owner_repo = args.repo
    commit = args.commit
    root_file = Path(args.root_file)
    dest = Path(args.dest)
    report_path = Path(args.report)
    dest.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    tree_url = f"https://api.github.com/repos/{owner_repo}/git/trees/{commit}?recursive=1"
    tree = json.loads(request_bytes(tree_url))["tree"]
    module_map: dict[str, dict] = {}
    for item in tree:
        path = item.get("path", "")
        if item.get("type") == "blob" and path.endswith(".lean"):
            module = path[:-5].replace("/", ".")
            module_map[module] = item

    roots = parse_imports(root_file.read_text(encoding="utf-8"))
    queue: deque[str] = deque(roots)
    visited: set[str] = set()
    external: set[str] = set()
    missing_internal: set[str] = set()
    edges: list[tuple[str, str]] = []
    fetched: list[dict[str, object]] = []

    while queue:
        module = queue.popleft()
        if module in visited:
            continue
        visited.add(module)
        item = module_map.get(module)
        if item is None:
            if module.startswith(INTERNAL_PREFIXES):
                missing_internal.add(module)
            else:
                external.add(module)
            continue

        path = str(item["path"])
        raw_url = f"https://raw.githubusercontent.com/{owner_repo}/{commit}/{path}"
        data = request_bytes(raw_url)
        got = git_blob_sha(data)
        want = str(item["sha"])
        if got != want:
            raise AssertionError((path, got, want))

        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        fetched.append({
            "module": module,
            "path": path,
            "blob_sha": got,
            "bytes": len(data),
        })

        text = data.decode("utf-8")
        for dep in parse_imports(text):
            edges.append((module, dep))
            if dep not in visited:
                queue.append(dep)

    status = "UNKNOWN" if missing_internal else "CLOSED"
    report = {
        "schema": "crystal.residual-first-dependency-closure@1",
        "status": status,
        "repository": owner_repo,
        "commit": commit,
        "root_file": str(root_file),
        "root_modules": roots,
        "root_count": len(roots),
        "internal_modules": sorted(x["module"] for x in fetched),
        "internal_count": len(fetched),
        "external_imports": sorted(external),
        "missing_internal_modules": sorted(missing_internal),
        "edge_count": len(edges),
        "files": sorted(fetched, key=lambda x: str(x["path"])),
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"CLOSURE_STATUS={status}")
    print(f"ROOT_MODULES={len(roots)}")
    print(f"INTERNAL_MODULES={len(fetched)}")
    print(f"EXTERNAL_IMPORTS={','.join(sorted(external))}")
    if missing_internal:
        print(f"MISSING_INTERNAL={','.join(sorted(missing_internal))}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
