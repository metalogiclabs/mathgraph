#!/usr/bin/env python3
from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

from mathgraph.compiler_registry import (
    ReplayableOperationAnchor,
    default_registry,
    operation_adapter_contract,
)
from mathgraph.crystal import SemanticObject

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "evidence" / "crystal-swarm-runtime-v5-certificates" / "result.json"
PARENT = "bf23d4ae3023e46e35e71cc35cae9aed86eca5a8"
MAX_WORKERS = 8
NODE_TIMEOUT = 30

BASE_PATH = ROOT / "scripts" / "run_crystal_swarm_scale_v1.py"

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

base = load_module(BASE_PATH, "swarm_scale_v1_for_v5_certificates")
registry = {spec.motif: spec for spec in default_registry()}
compiler = registry["certificate_witness"]
NEEDLES = tuple(base.MOTIFS["certificate_witness"])

def frontier_families():
    families = [base.parse_family(path) for path in sorted(base.TESTS.glob("test_*.py"))]
    frontier = base.select_frontier(families)
    selected = [f for f in frontier if "certificate_witness" in f.motifs]
    assert len(frontier) == 96
    assert len(selected) == 71
    return frontier, selected

def source_segment(source: str, node: ast.AST) -> str:
    return " ".join((ast.get_source_segment(source, node) or "").split())

def anchor_for_family(family):
    path = ROOT / family.path
    source = path.read_text(encoding="utf-8")
    source_sha = hashlib.sha256(source.encode()).hexdigest()
    tree = ast.parse(source)
    helpers = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("test_")
    }
    candidates = []
    for top in tree.body:
        funcs = []
        if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs = [(top, None)]
        elif isinstance(top, ast.ClassDef):
            funcs = [
                (child, top.name) for child in top.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
        for fn, cls in funcs:
            if not fn.name.startswith("test_"):
                continue
            nid = family.path + (f"::{cls}" if cls else "") + f"::{fn.name}"
            text = source_segment(source, fn)
            low = text.lower()
            direct = [n for n in NEEDLES if n in low]
            if direct:
                candidates.append((0, nid, fn.lineno, text[:1800], direct[0], "direct"))
            called = {
                n.func.id
                for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            }
            for helper_name in sorted(called & set(helpers)):
                helper = helpers[helper_name]
                htext = source_segment(source, helper)
                hlow = htext.lower()
                marks = [n for n in NEEDLES if n in hlow]
                if marks:
                    candidates.append((1, nid, helper.lineno, htext[:1800], marks[0], f"helper:{helper_name}"))
    if not candidates:
        return None
    candidates.sort(key=lambda row: (row[0], row[1], row[2], row[4]))
    _, nid, line, text, marker, kind = candidates[0]
    return {
        "path": family.path,
        "domain": family.domain,
        "node_id": nid,
        "line": line,
        "anchor_text": text,
        "marker": marker,
        "anchor_kind": kind,
        "source_sha256": source_sha,
    }

def replay(c):
    cmd = [sys.executable, "-m", "pytest", "-q", c["node_id"]]
    start = time.perf_counter()
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=NODE_TIMEOUT)
        return {
            "candidate": c,
            "status": "PASS" if p.returncode == 0 else "FAIL",
            "returncode": p.returncode,
            "wall_seconds": time.perf_counter() - start,
        }
    except subprocess.TimeoutExpired:
        return {
            "candidate": c,
            "status": "TIMEOUT",
            "returncode": None,
            "wall_seconds": time.perf_counter() - start,
        }

def main():
    start = time.perf_counter()
    frontier, families = frontier_families()
    candidates = []
    unknown = []
    for f in families:
        c = anchor_for_family(f)
        if c is None:
            unknown.append({"path": f.path, "domain": f.domain, "reason": "no_certificate_anchor"})
        else:
            candidates.append(c)

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(replay, c) for c in candidates]
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda row: row["candidate"]["path"])

    forged = []
    replay_wall_sum = 0.0
    for row in results:
        c = row["candidate"]
        replay_wall_sum += row["wall_seconds"]
        if row["status"] != "PASS":
            unknown.append({
                "path": c["path"], "domain": c["domain"],
                "reason": f"replay_{row['status'].lower()}",
                "node_id": c["node_id"],
            })
            continue
        anchor = ReplayableOperationAnchor(
            source_path=c["path"],
            source_sha256=c["source_sha256"],
            node_id=c["node_id"],
            line=c["line"],
            motif="certificate_witness",
            anchor_text=c["anchor_text"],
            replay_command=(sys.executable, "-m", "pytest", "-q", c["node_id"]),
        )
        obj = anchor.semantic_object()
        assert SemanticObject.from_bytes(obj.to_bytes()) == obj
        contract = operation_adapter_contract(
            anchor, compiler,
            evidence_refs=(
                f"hosted:crystal-swarm-runtime-v5-certificates:{c['path']}",
                f"certificate-anchor:{c['anchor_kind']}:{c['marker']}",
            ),
        )
        forged.append({
            **c,
            "semantic_object_id": obj.id,
            "adapter_contract_id": contract.id,
            "replay_wall_seconds": row["wall_seconds"],
        })

    domains = sorted({x["domain"] for x in forged})
    evidence = {
        "schema": "mathgraph.crystal-swarm-runtime-v5-certificates.qualified",
        "status": "QUALIFIED_BOUNDED",
        "parent_head": PARENT,
        "frontier_size": len(frontier),
        "certificate_witness_families": len(families),
        "compiler_id": compiler.compiler_id,
        "compiler_interfaces": list(compiler.interfaces),
        "families_with_anchor": len(candidates),
        "forged_certificate_adapters": len(forged),
        "unknown_families": len(unknown),
        "coverage_ratio": len(forged) / len(families),
        "forged_domain_count": len(domains),
        "forged_domains": domains,
        "replay_wall_seconds_sum": replay_wall_sum,
        "wall_seconds": time.perf_counter() - start,
        "forged": forged,
        "unknown": sorted(unknown, key=lambda x: x["path"]),
        "architecture_result": (
            "Existing Certificate/EvidenceManifest machinery is now registered as a reusable "
            "certificate/witness compiler and contacted through replay-backed family adapters."
        ),
        "boundary": (
            "A certificate adapter warrants replayable contact with certificate/witness machinery. "
            "It does not imply that every certificate object in the family is independently valid."
        ),
    }
    if not forged:
        raise AssertionError("zero certificate adapters forged")
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_SWARM_RUNTIME_V5_CERTIFICATES=QUALIFIED_BOUNDED")
    print(json.dumps({
        "certificate_witness_families": len(families),
        "families_with_anchor": len(candidates),
        "forged_certificate_adapters": len(forged),
        "unknown_families": len(unknown),
        "coverage_ratio": evidence["coverage_ratio"],
        "forged_domain_count": len(domains),
        "reason_counts": dict(__import__("collections").Counter(x["reason"] for x in unknown)),
    }, sort_keys=True))

if __name__ == "__main__":
    main()
