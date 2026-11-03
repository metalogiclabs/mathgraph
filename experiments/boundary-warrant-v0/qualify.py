"""Read-only qualification report over the original MathGraph warrant graph.

The JSON output is a projection of typed BoundaryWarrants, not a second graph,
verifier, or independent source of truth. Historical evidence is pinned exactly.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from brahe_export import export_brahe_boundary
from mathgraph_check.boundary_warrant import admitted_route, resolve_boundaries, scope_identity
from mathgraph_check.warrant_resolution import compare_snapshots


def _l4_adapter():
    adapter = HERE.parent / "check-l4-claim-consumer-v1" / "boundary_export.py"
    spec = importlib.util.spec_from_file_location("l4_qualified_boundary_for_report", adapter)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qualification_report(items, assessments) -> dict:
    """Project *already admitted* exact artifacts; simulate identity changes.

    Rechecking real bytes is the job of the method import adapters, which must be
    called before constructing this report. Inputs must never come from JSON.
    """
    if len(items) not in (2, 3) or len(assessments) != len(items):
        raise ValueError("EXPECTED_TWO_OR_THREE_BOUNDARIES")
    if {w.verification.method for w, _ in items} != {"formal", "native"}:
        raise ValueError("METHOD_DIVERSITY_NOT_QUALIFIED")
    current = {}
    for warrant, receipt in items:
        admitted_route(warrant, receipt)
        for dep in warrant.dependencies:
            if dep.key in current and current[dep.key] != dep.sha256:
                raise ValueError("CONFLICTING_CURRENT_DEPENDENCY")
            current[dep.key] = dep.sha256

    before = resolve_boundaries(items, current)
    ids = [admitted_route(w, r)[0].id for w, r in items]
    simulated = []
    for index, (warrant, _) in enumerate(items):
        for dep in warrant.dependencies:
            changed = dict(current)
            changed[dep.key] = "f" * 64 if dep.sha256 != "f" * 64 else "e" * 64
            after = resolve_boundaries(items, changed)
            delta = compare_snapshots(before.states, after.states)
            others_preserved = all(not delta[other]["changed"]
                                   for other in ids if other != ids[index])
            if not (delta[ids[index]]["after"] == "STALE" and others_preserved):
                raise ValueError("SELECTIVE_WITHDRAWAL_FAILED")
            simulated.append({
                "method": warrant.verification.method,
                "dependency_role": dep.role,
                "dependency_key": dep.key,
                "affected": delta[ids[index]],
                "unaffected_still_admitted": others_preserved,
                "scenario": "SIMULATED_DEPENDENCY_CHANGE_NOT_OBSERVED_UPSTREAM",
            })

    return {
        "format": ("mathgraph.boundary-qualification.v0" if len(items) == 2
                   else "mathgraph.boundary-qualification.v1"),
        "basis": "RECHECKED_HISTORICAL_ACTIONS_ARTIFACTS_AND_PINNED_SOURCE",
        "current_upstream_applicability": "UNKNOWN",
        "independent_customer_obligation_authority": "UNKNOWN",
        "scope": "RETROSPECTIVE_BOUNDED_ONLY",
        "pinned_states": dict(before.states),
        "warrants": [
            {**json.loads(json.dumps(asdict(w))), "scope_sha256": scope_identity(w),
             "graph_claim_id": ids[i]}
            for i, (w, _) in enumerate(items)
        ],
        "replay_evidence": {
            "l4yaml": {
                "weak_offering": assessments[0]["weak_offering"],
                "axiom_free_claim": assessments[0]["axiom_free_claim"],
                "whole_generator_correctness": assessments[0]["whole_generator_correctness"],
            },
            "brahe": assessments[1],
            **({"nyx": assessments[2]} if len(items) == 3 else {}),
        },
        "simulated_withdrawals": simulated,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--l4-archive", required=True, type=Path)
    parser.add_argument("--brahe-archive", required=True, type=Path)
    parser.add_argument("--brahe-base", required=True, type=Path)
    parser.add_argument("--brahe-head", required=True, type=Path)
    parser.add_argument("--nyx-archive", type=Path)
    parser.add_argument("--nyx-base-event", type=Path)
    parser.add_argument("--nyx-head-event", type=Path)
    parser.add_argument("--nyx-base-test", type=Path)
    parser.add_argument("--nyx-head-test", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    l4, l4_receipt, l4_assessment = _l4_adapter().export_l4_boundary(args.l4_archive)
    brahe, brahe_receipt, brahe_assessment = export_brahe_boundary(
        args.brahe_archive, args.brahe_base, args.brahe_head,
    )
    items = [(l4, l4_receipt), (brahe, brahe_receipt)]
    assessments = [l4_assessment, brahe_assessment]
    nyx_paths = (args.nyx_archive, args.nyx_base_event, args.nyx_head_event,
                 args.nyx_base_test, args.nyx_head_test)
    if any(nyx_paths):
        if not all(nyx_paths):
            parser.error("All Nyx archive and exact source paths are required together")
        from nyx_export import export_nyx_boundary
        nyx, nyx_receipt, nyx_assessment = export_nyx_boundary(
            args.nyx_archive.read_bytes(),
            base_event=args.nyx_base_event.read_bytes(),
            head_event=args.nyx_head_event.read_bytes(),
            base_test=args.nyx_base_test.read_bytes(),
            head_test=args.nyx_head_test.read_bytes(),
        )
        items.append((nyx, nyx_receipt))
        assessments.append(nyx_assessment)
    report = qualification_report(items, assessments)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("BOUNDARY_WARRANTS=" + json.dumps(report["pinned_states"], sort_keys=True))
    print("SELECTIVE_WITHDRAWAL_CASES=" + str(len(report["simulated_withdrawals"])))
    print("CURRENT_UPSTREAM_APPLICABILITY=UNKNOWN")


if __name__ == "__main__":
    main()
