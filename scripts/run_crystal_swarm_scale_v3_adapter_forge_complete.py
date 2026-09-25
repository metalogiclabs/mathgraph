#!/usr/bin/env python3
"""Complete Adapter Forge using a second mechanical semantic-anchor grammar."""

from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

from mathgraph.crystal import SemanticObject
from mathgraph.falsifier_semantic_adapter import (
    ReplayableSemanticNegativeAnchor,
    semantic_negative_contract,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "evidence" / "crystal-swarm-scale-v3-adapter-forge-complete" / "result.json"
PARENT = "999c791a894865fc36d0f76480308038650346bf"
MAX_WORKERS = 5
NODE_TIMEOUT = 35

V3_PATH = ROOT / "scripts" / "run_crystal_swarm_scale_v3_adapter_forge.py"

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

v3 = load_module(V3_PATH, "swarm_scale_v3_for_completion")

NAME_MARKERS = (
    "fail", "reject", "block", "invalid", "missing",
    "refut", "countermodel", "false", "obstruction",
)
SEMANTIC_MARKERS = (
    "find_quotient_falsifiers",
    "finite_countermodel",
    "refutation_certificate",
    "verified_false",
    "terminalform.finite_countermodel",
    "finite_verified",
)


def source_sha(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def node_source(source: str, node: ast.AST) -> str:
    return " ".join((ast.get_source_segment(source, node) or "").split())


def candidate_for_family(family):
    path = ROOT / family.path
    source = path.read_text(encoding="utf-8")
    low = source.lower()
    tree = ast.parse(source)
    helpers = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("test_")
    }

    candidates = []
    for top in tree.body:
        functions = []
        if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions = [(top, None)]
        elif isinstance(top, ast.ClassDef):
            functions = [
                (child, top.name)
                for child in top.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
        for fn, cls in functions:
            if not fn.name.startswith("test_"):
                continue
            nid = family.path + (f"::{cls}" if cls else "") + f"::{fn.name}"
            fn_text = node_source(source, fn)
            fn_low = fn_text.lower()
            asserts = sorted(
                (n for n in ast.walk(fn) if isinstance(n, ast.Assert)),
                key=lambda n: getattr(n, "lineno", 0),
            )

            # Rule 1: the test contract itself says fail/reject/block/etc.
            name_marker = next((m for m in NAME_MARKERS if m in fn.name.lower()), None)
            if name_marker and asserts:
                a = asserts[0]
                candidates.append((
                    1, nid, getattr(a, "lineno", fn.lineno),
                    "negative_test_contract", node_source(source, a), f"test-name:{name_marker}"
                ))

            # Rule 2: explicit negative semantic operator/terminal form in the test body.
            semantic_marker = next((m for m in SEMANTIC_MARKERS if m in fn_low), None)
            if semantic_marker:
                candidates.append((
                    0, nid, fn.lineno,
                    "explicit_negative_semantics", fn_text[:1600], semantic_marker
                ))

            # Rule 3: test invokes a local fixture/helper containing explicit negative semantics.
            called = {
                n.func.id
                for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            }
            for helper_name in sorted(called & set(helpers)):
                helper = helpers[helper_name]
                helper_text = node_source(source, helper)
                helper_low = helper_text.lower()
                helper_marker = next((m for m in SEMANTIC_MARKERS if m in helper_low), None)
                if helper_marker:
                    candidates.append((
                        2, nid, helper.lineno,
                        "negative_fixture", helper_text[:1600], f"helper:{helper_name}:{helper_marker}"
                    ))

    if not candidates:
        return None
    candidates.sort(key=lambda row: (row[0], row[1], row[2], row[5]))
    rank, nid, line, kind, text, marker = candidates[0]
    return {
        "path": family.path,
        "domain": family.domain,
        "node_id": nid,
        "line": line,
        "anchor_kind": kind,
        "anchor_text": text,
        "marker": marker,
        "source_sha256": source_sha(source),
    }


def replay(candidate):
    command = [sys.executable, "-m", "pytest", "-q", candidate["node_id"]]
    start = time.perf_counter()
    try:
        p = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=NODE_TIMEOUT)
        return {
            "candidate": candidate,
            "status": "PASS" if p.returncode == 0 else "FAIL",
            "returncode": p.returncode,
            "wall_seconds": time.perf_counter() - start,
            "stdout_tail": p.stdout[-1000:],
            "stderr_tail": p.stderr[-1000:],
        }
    except subprocess.TimeoutExpired:
        return {
            "candidate": candidate,
            "status": "TIMEOUT",
            "returncode": None,
            "wall_seconds": time.perf_counter() - start,
            "stdout_tail": "",
            "stderr_tail": "",
        }


def main():
    start = time.perf_counter()
    families = v3.family_frontier()
    direct_covered = {f.path for f in families if v3.find_anchors(f)}
    unknown_families = [f for f in families if f.path not in direct_covered]
    assert len(direct_covered) == 51
    assert len(unknown_families) == 5

    candidates = []
    no_anchor = []
    for family in unknown_families:
        c = candidate_for_family(family)
        if c is None:
            no_anchor.append({"path": family.path, "domain": family.domain, "reason": "no_semantic_anchor"})
        else:
            candidates.append(c)

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(replay, c) for c in candidates]
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda row: row["candidate"]["path"])

    forged = []
    unresolved = list(no_anchor)
    for row in results:
        c = row["candidate"]
        if row["status"] != "PASS":
            unresolved.append({
                "path": c["path"], "domain": c["domain"],
                "reason": f"replay_{row['status'].lower()}",
                "node_id": c["node_id"],
            })
            continue
        anchor = ReplayableSemanticNegativeAnchor(
            source_path=c["path"],
            source_sha256=c["source_sha256"],
            node_id=c["node_id"],
            line=c["line"],
            anchor_kind=c["anchor_kind"],
            anchor_text=c["anchor_text"],
            marker=c["marker"],
            replay_command=(sys.executable, "-m", "pytest", "-q", c["node_id"]),
        )
        obj = anchor.semantic_object()
        assert SemanticObject.from_bytes(obj.to_bytes()) == obj
        contract = semantic_negative_contract(
            anchor,
            family_space=f"repo-test-family:{c['path']}",
            evidence_refs=(
                f"hosted:crystal-swarm-scale-v3-adapter-forge-complete:{c['path']}",
                f"semantic-anchor:{c['anchor_kind']}:{c['line']}",
            ),
        )
        forged.append({
            **c,
            "semantic_object_id": obj.id,
            "adapter_contract_id": contract.id,
            "replay_wall_seconds": row["wall_seconds"],
        })

    total_coverage = len(direct_covered) + len(forged)
    evidence = {
        "schema": "mathgraph.crystal-swarm-scale-v3-adapter-forge-complete.qualified",
        "status": "QUALIFIED_BOUNDED",
        "parent_head": PARENT,
        "mined_falsifier_families": len(families),
        "direct_v3_adapters": len(direct_covered),
        "semantic_v31_adapters": len(forged),
        "total_forged_adapters": total_coverage,
        "remaining_unknown": len(unresolved),
        "coverage_ratio": total_coverage / len(families),
        "semantic_forged": forged,
        "remaining_unknown_families": sorted(unresolved, key=lambda x: x["path"]),
        "forge_wall_seconds": time.perf_counter() - start,
        "architecture_result": (
            "A two-tier mechanical grammar covers direct negative assertions first and explicit "
            "semantic negative anchors second. Every forged adapter is exact-node replay backed."
        ),
        "epistemic_boundary": (
            "Semantic anchors warrant replayable negative evidence/provenance, not arbitrary "
            "translation of the entire source module. No LLM judgment participates."
        ),
    }
    if unresolved:
        print("V31_REMAINING_UNKNOWN", json.dumps(unresolved, sort_keys=True))
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_SWARM_SCALE_V3_ADAPTER_FORGE_COMPLETE=QUALIFIED_BOUNDED")
    print(json.dumps({
        "mined_falsifier_families": len(families),
        "direct_v3_adapters": len(direct_covered),
        "semantic_v31_adapters": len(forged),
        "total_forged_adapters": total_coverage,
        "remaining_unknown": len(unresolved),
        "coverage_ratio": evidence["coverage_ratio"],
        "forged": [[x["path"], x["anchor_kind"], x["marker"]] for x in forged],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
