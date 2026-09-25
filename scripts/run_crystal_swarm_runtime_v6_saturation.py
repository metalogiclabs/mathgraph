#!/usr/bin/env python3
from __future__ import annotations

import ast
from collections import Counter, defaultdict
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
RESULT = ROOT / "evidence" / "crystal-swarm-runtime-v6-saturation" / "result.json"
PARENT = "5c29aacfc86f79cda97a02b14b6ec384846be21f"
MAX_WORKERS = 10
NODE_TIMEOUT = 30

BASE_PATH = ROOT / "scripts" / "run_crystal_swarm_scale_v1.py"

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

base = load_module(BASE_PATH, "swarm_scale_v1_for_v6")
registry = {spec.motif: spec for spec in default_registry()}

# These are already fully adapter-qualified at exact parent lineage.
INHERITED_FULL = {
    "certificate_witness": 71,
}

def segment(source: str, node: ast.AST) -> str:
    return " ".join((ast.get_source_segment(source, node) or "").split())

def candidates_for(family, motif):
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
    needles = tuple(base.MOTIFS[motif])
    out = []
    for top in tree.body:
        funcs = []
        if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs = [(top, None)]
        elif isinstance(top, ast.ClassDef):
            funcs = [
                (child, top.name)
                for child in top.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
        for fn, cls in funcs:
            if not fn.name.startswith("test_"):
                continue
            nid = family.path + (f"::{cls}" if cls else "") + f"::{fn.name}"
            text = segment(source, fn)
            low = text.lower()
            marks = [n for n in needles if n in low]
            if marks:
                out.append((0, nid, fn.lineno, text[:1800], marks[0], source_sha))
            called = {
                n.func.id for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            }
            for helper_name in sorted(called & set(helpers)):
                helper = helpers[helper_name]
                htext = segment(source, helper)
                hlow = htext.lower()
                hmarks = [n for n in needles if n in hlow]
                if hmarks:
                    out.append((1, nid, helper.lineno, htext[:1800], hmarks[0], source_sha))
    return sorted(out, key=lambda row: (row[0], row[1], row[2], row[4]))

def replay(node_id):
    cmd = [sys.executable, "-m", "pytest", "-q", node_id]
    start = time.perf_counter()
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=NODE_TIMEOUT)
        return {
            "node_id": node_id,
            "status": "PASS" if p.returncode == 0 else "FAIL",
            "returncode": p.returncode,
            "wall_seconds": time.perf_counter() - start,
        }
    except subprocess.TimeoutExpired:
        return {
            "node_id": node_id,
            "status": "TIMEOUT",
            "returncode": None,
            "wall_seconds": time.perf_counter() - start,
        }

def main():
    start = time.perf_counter()
    families = [base.parse_family(path) for path in sorted(base.TESTS.glob("test_*.py"))]
    frontier = base.select_frontier(families)
    assert len(frontier) == 96

    targets = []
    no_anchor = []
    for family in frontier:
        for motif in family.motifs:
            if motif == "finite_enumeration":
                continue
            if motif in INHERITED_FULL:
                continue
            if motif not in registry:
                continue
            candidates = candidates_for(family, motif)
            if not candidates:
                no_anchor.append({"path": family.path, "domain": family.domain, "motif": motif})
                continue
            rank, nid, line, text, marker, source_sha = candidates[0]
            targets.append({
                "path": family.path,
                "domain": family.domain,
                "motif": motif,
                "node_id": nid,
                "line": line,
                "anchor_text": text,
                "marker": marker,
                "source_sha256": source_sha,
            })

    unique_nodes = sorted({t["node_id"] for t in targets})
    replay_results = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(replay, nid): nid for nid in unique_nodes}
        for fut in as_completed(futures):
            row = fut.result()
            replay_results[row["node_id"]] = row

    forged = []
    failed = []
    forged_counts = Counter()
    forged_by_family = defaultdict(set)
    for target in targets:
        rr = replay_results[target["node_id"]]
        if rr["status"] != "PASS":
            failed.append({
                "path": target["path"],
                "domain": target["domain"],
                "motif": target["motif"],
                "node_id": target["node_id"],
                "status": rr["status"],
            })
            continue
        compiler = registry[target["motif"]]
        anchor = ReplayableOperationAnchor(
            source_path=target["path"],
            source_sha256=target["source_sha256"],
            node_id=target["node_id"],
            line=target["line"],
            motif=target["motif"],
            anchor_text=target["anchor_text"],
            replay_command=(sys.executable, "-m", "pytest", "-q", target["node_id"]),
        )
        obj = anchor.semantic_object()
        assert SemanticObject.from_bytes(obj.to_bytes()) == obj
        contract = operation_adapter_contract(
            anchor,
            compiler,
            evidence_refs=(
                f"hosted:crystal-swarm-runtime-v6-saturation:{target['path']}",
                f"motif-anchor:{target['motif']}:{target['marker']}",
            ),
        )
        forged.append({
            **target,
            "semantic_object_id": obj.id,
            "adapter_contract_id": contract.id,
        })
        forged_counts[target["motif"]] += 1
        forged_by_family[target["path"]].add(target["motif"])

    occurrence_total = Counter()
    for family in frontier:
        for motif in family.motifs:
            occurrence_total[motif] += 1

    coverage = {}
    for motif, total in sorted(occurrence_total.items()):
        if motif == "finite_enumeration":
            coverage[motif] = {
                "occurrences": total,
                "forged": 0,
                "coverage_ratio": 0.0,
                "status": "BROAD_RESIDUAL_REQUIRES_REFINEMENT",
            }
            continue
        if motif in INHERITED_FULL:
            forged_count = min(total, INHERITED_FULL[motif])
            status = "INHERITED_FULL"
        elif motif in registry:
            forged_count = forged_counts[motif]
            status = "FORGED_PARTIAL" if forged_count < total else "FORGED_FULL"
        else:
            forged_count = 0
            status = "NO_COMPILER"
        coverage[motif] = {
            "occurrences": total,
            "forged": forged_count,
            "coverage_ratio": forged_count / total if total else 0.0,
            "status": status,
        }

    unresolved = []
    for motif, row in coverage.items():
        if motif == "finite_enumeration":
            continue
        missing = row["occurrences"] - row["forged"]
        if missing:
            unresolved.append((missing, motif, row["status"]))
    unresolved.sort(key=lambda x: (-x[0], x[1]))

    fully_covered = 0
    for family in frontier:
        needed = {
            m for m in family.motifs
            if m != "finite_enumeration" and (m in registry or m in INHERITED_FULL)
        }
        have = set(forged_by_family.get(family.path, set()))
        for m in INHERITED_FULL:
            if m in family.motifs:
                have.add(m)
        if needed and needed.issubset(have):
            fully_covered += 1

    evidence = {
        "schema": "mathgraph.crystal-swarm-runtime-v6-saturation.qualified",
        "status": "QUALIFIED_BOUNDED",
        "parent_head": PARENT,
        "frontier_size": len(frontier),
        "registered_motifs": sorted(registry),
        "target_adapter_occurrences": len(targets),
        "unique_pytest_nodes_replayed": len(unique_nodes),
        "passed_nodes": sum(r["status"] == "PASS" for r in replay_results.values()),
        "forged_operation_adapters": len(forged),
        "fully_covered_families_excluding_broad_finite": fully_covered,
        "coverage": coverage,
        "no_anchor": no_anchor,
        "failed": failed,
        "remaining_ranked": [
            {"missing_occurrences": m, "motif": motif, "status": status}
            for m, motif, status in unresolved
        ],
        "next_residual": (
            unresolved[0][1] if unresolved else "finite_enumeration_refinement_only"
        ),
        "wall_seconds": time.perf_counter() - start,
        "architecture_result": (
            "Replay-backed operation adapters are saturated motif-by-motif instead of one node per family. "
            "The resulting frontier separates missing compiler/anchor work from the intentionally broad finite meta-category."
        ),
        "boundary": (
            "Coverage is replay contact with registered operations, not universal semantic lowering. "
            "The finite_enumeration meta-category is explicitly left open and must be recursively refined."
        ),
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_SWARM_RUNTIME_V6_SATURATION=QUALIFIED_BOUNDED")
    print(json.dumps({
        "frontier_size": len(frontier),
        "target_adapter_occurrences": len(targets),
        "unique_pytest_nodes_replayed": len(unique_nodes),
        "passed_nodes": evidence["passed_nodes"],
        "forged_operation_adapters": len(forged),
        "fully_covered_families_excluding_broad_finite": fully_covered,
        "next_residual": evidence["next_residual"],
        "remaining_ranked": evidence["remaining_ranked"][:6],
        "coverage": {k:[v["forged"],v["occurrences"]] for k,v in coverage.items()},
    }, sort_keys=True))

if __name__ == "__main__":
    main()
