#!/usr/bin/env python3
"""Adapter Forge V3 over the 56 repository-mined falsifier families."""

from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

from mathgraph.crystal import SemanticObject
from mathgraph.falsifier_adapter import (
    ReplayableFalsifierAnchor,
    replayable_falsifier_contract,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "evidence" / "crystal-swarm-scale-v3-adapter-forge" / "result.json"
PARENT = "4c439f8b68d81d833add8718071549e6435e5411"
MAX_WORKERS = 6
NODE_TIMEOUT = 25

BASE_PATH = ROOT / "scripts" / "run_crystal_swarm_scale_v1.py"
REFINE_PATH = ROOT / "scripts" / "run_crystal_swarm_scale_v1_finite_refinement.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


base = load_module(BASE_PATH, "swarm_scale_v1_for_adapter_forge")
refine = load_module(REFINE_PATH, "swarm_scale_refine_for_adapter_forge")

NEGATIVE_MARKERS = (
    "finite_countermodel",
    "countermodel",
    "refuted",
    "rejected",
    "violated",
    "violation",
    "unsafe",
    "falsif",
    "unknown",
    "not_verified",
    "no_countermodel",
    "cannot_promote",
    "can_promote_truth",
    "advisory_only",
    "outside_preservation_contract",
    "named_obstruction",
)


@dataclass(frozen=True)
class CandidateAnchor:
    path: str
    domain: str
    node_id: str
    line: int
    assertion_text: str
    marker: str
    source_sha256: str


def family_frontier():
    families = [base.parse_family(path) for path in sorted(base.TESTS.glob("test_*.py"))]
    frontier = base.select_frontier(families)
    finite = [f for f in frontier if "finite_enumeration" in f.motifs]
    assert len(finite) == 76
    selected = []
    for family in finite:
        submotifs = refine.classify(family.path)
        if "countermodel_falsifier" in submotifs:
            selected.append(family)
    assert len(selected) == 56
    return selected


def find_anchors(family) -> list[CandidateAnchor]:
    path = ROOT / family.path
    source = path.read_text(encoding="utf-8")
    source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    anchors = []
    for node in tree.body:
        class_prefix = None
        functions = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions = [(node, None)]
        elif isinstance(node, ast.ClassDef):
            functions = [
                (child, node.name)
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
        for fn, cls in functions:
            if not fn.name.startswith("test_"):
                continue
            node_id = family.path
            if cls:
                node_id += f"::{cls}"
            node_id += f"::{fn.name}"
            for sub in ast.walk(fn):
                if not isinstance(sub, ast.Assert):
                    continue
                segment = ast.get_source_segment(source, sub) or ""
                low = segment.lower()
                marker = next((m for m in NEGATIVE_MARKERS if m in low), None)
                if marker is None:
                    continue
                anchors.append(
                    CandidateAnchor(
                        path=family.path,
                        domain=family.domain,
                        node_id=node_id,
                        line=getattr(sub, "lineno", 0),
                        assertion_text=" ".join(segment.split())[:1200],
                        marker=marker,
                        source_sha256=source_sha,
                    )
                )
    return sorted(anchors, key=lambda a: (a.node_id, a.line, a.marker))


def replay(candidate: CandidateAnchor) -> dict:
    command = [sys.executable, "-m", "pytest", "-q", candidate.node_id]
    start = time.perf_counter()
    try:
        p = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=NODE_TIMEOUT,
            check=False,
        )
        status = "PASS" if p.returncode == 0 else "FAIL"
        return {
            "candidate": candidate,
            "status": status,
            "returncode": p.returncode,
            "wall_seconds": time.perf_counter() - start,
            "stdout_tail": p.stdout[-1200:],
            "stderr_tail": p.stderr[-1200:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "candidate": candidate,
            "status": "TIMEOUT",
            "returncode": None,
            "wall_seconds": time.perf_counter() - start,
            "stdout_tail": (exc.stdout or "")[-1200:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-1200:] if isinstance(exc.stderr, str) else "",
        }


def main() -> None:
    start_total = time.perf_counter()
    families = family_frontier()

    family_candidates = {}
    for family in families:
        family_candidates[family.path] = find_anchors(family)

    # Forge only the first deterministic anchored negative node per family.
    replay_candidates = [
        anchors[0] for path, anchors in sorted(family_candidates.items()) if anchors
    ]

    replay_results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(replay, cand): cand for cand in replay_candidates}
        for fut in as_completed(futures):
            replay_results.append(fut.result())

    replay_results.sort(key=lambda row: row["candidate"].path)

    forged = []
    unknown = []
    replay_wall_sum = 0.0
    for row in replay_results:
        replay_wall_sum += row["wall_seconds"]
        c = row["candidate"]
        if row["status"] != "PASS":
            unknown.append({
                "path": c.path,
                "domain": c.domain,
                "reason": f"replay_{row['status'].lower()}",
                "node_id": c.node_id,
                "wall_seconds": row["wall_seconds"],
            })
            continue

        anchor = ReplayableFalsifierAnchor(
            source_path=c.path,
            source_sha256=c.source_sha256,
            node_id=c.node_id,
            line=c.line,
            assertion_text=c.assertion_text,
            marker=c.marker,
            replay_command=(sys.executable, "-m", "pytest", "-q", c.node_id),
        )
        obj = anchor.semantic_object()
        assert SemanticObject.from_bytes(obj.to_bytes()) == obj
        contract = replayable_falsifier_contract(
            anchor,
            family_space=f"repo-test-family:{c.path}",
            evidence_refs=(
                f"hosted:crystal-swarm-scale-v3-adapter-forge:{c.path}",
                f"assert-line:{c.line}",
            ),
        )
        forged.append({
            "path": c.path,
            "domain": c.domain,
            "node_id": c.node_id,
            "line": c.line,
            "marker": c.marker,
            "anchor_id": anchor.id,
            "semantic_object_id": obj.id,
            "adapter_contract_id": contract.id,
            "preserves_interfaces": list(contract.preserves_interfaces),
            "replay_wall_seconds": row["wall_seconds"],
        })

    paths_with_no_anchor = [
        family.path for family in families if not family_candidates[family.path]
    ]
    for path in paths_with_no_anchor:
        family = next(f for f in families if f.path == path)
        unknown.append({
            "path": path,
            "domain": family.domain,
            "reason": "no_mechanically_anchored_negative_assertion",
        })

    forged_domains = sorted({row["domain"] for row in forged})
    total_elapsed = time.perf_counter() - start_total

    evidence = {
        "schema": "mathgraph.crystal-swarm-scale-v3-adapter-forge.qualified",
        "status": "QUALIFIED_BOUNDED",
        "parent_head": PARENT,
        "mined_falsifier_families": len(families),
        "families_with_mechanical_anchor": len(replay_candidates),
        "forged_adapters": len(forged),
        "unknown_families": len(unknown),
        "forged_domain_count": len(forged_domains),
        "forged_domains": forged_domains,
        "adapter_coverage_ratio": len(forged) / len(families),
        "replay_wall_seconds_sum": replay_wall_sum,
        "adapter_forge_wall_seconds": total_elapsed,
        "parallel_workers": MAX_WORKERS,
        "node_timeout_seconds": NODE_TIMEOUT,
        "forged": forged,
        "unknown": sorted(unknown, key=lambda row: row["path"]),
        "architecture_result": (
            "The forge mechanically anchors explicit negative assertions, replays the exact "
            "pytest node, and emits a content-addressed falsifier adapter contract only on PASS. "
            "Unsupported or non-replaying families remain UNKNOWN."
        ),
        "epistemic_boundary": (
            "A forged adapter warrants replayable negative-test evidence and provenance. It does "
            "not automatically claim that the test file's entire mathematical semantics has been "
            "translated into the generic finite falsifier case/property API."
        ),
        "next_action": (
            "For forged adapters, add extractor plugins only where the negative assertion exposes "
            "a concrete witness payload; route those into falsifier.finite.witness@1. Keep anchor-only "
            "families at replayable-test authority and UNKNOWN for stronger semantics."
        ),
    }

    if not forged:
        raise AssertionError("adapter forge produced zero qualified adapters")

    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_SWARM_SCALE_V3_ADAPTER_FORGE=QUALIFIED_BOUNDED")
    print(json.dumps({
        "mined_falsifier_families": len(families),
        "families_with_mechanical_anchor": len(replay_candidates),
        "forged_adapters": len(forged),
        "unknown_families": len(unknown),
        "forged_domain_count": len(forged_domains),
        "adapter_coverage_ratio": evidence["adapter_coverage_ratio"],
        "replay_wall_seconds_sum": replay_wall_sum,
        "adapter_forge_wall_seconds": total_elapsed,
        "reason_counts": dict(__import__("collections").Counter(x["reason"] for x in unknown)),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
