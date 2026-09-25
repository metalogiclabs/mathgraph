#!/usr/bin/env python3
"""Execute the compiler selected by Swarm Scale V1: finite falsifier witnesses."""
from __future__ import annotations

from itertools import combinations, product
import json
from pathlib import Path
import time

from mathgraph.crystal import AdapterContract, Hyperedge, SemanticObject, greatest_viability_kernel
from mathgraph.finite_falsifier import find_first_falsifier
from mathgraph.graph_invariants import (
    FiniteSimpleGraphPayload,
    maximum_matching_number,
    minimum_edge_cover_number,
)

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "evidence" / "crystal-swarm-scale-v2-falsifier" / "result.json"
PARENT = "44f3e9c7da2074d532e6312740e6bbb7f20201d0"
PROJECTED_FRONTIER_FANOUT = 56


def graph_cases(max_n: int = 3):
    for n in range(1, max_n + 1):
        edges = tuple(combinations(range(n), 2))
        for mask in range(1 << len(edges)):
            yield FiniteSimpleGraphPayload(
                n,
                tuple(edge for i, edge in enumerate(edges) if mask & (1 << i)),
            )


def run_family(
    name,
    cases,
    prop,
    encode,
    *,
    claim_ref,
    boundary_ref,
    verifier_ref,
):
    start = time.perf_counter()
    result = find_first_falsifier(
        cases,
        prop,
        encode_case=encode,
        family_id=name,
        claim_ref=claim_ref,
        boundary_ref=boundary_ref,
        verifier_ref=verifier_ref,
        evidence_refs=(f"hosted:crystal-swarm-scale-v2-falsifier:{name}",),
    )
    elapsed = time.perf_counter() - start
    if result.witness is None:
        raise AssertionError(f"{name}: expected a falsifier but search exhausted")
    obj = result.witness.semantic_object()
    assert SemanticObject.from_bytes(obj.to_bytes()) == obj
    return {
        "family": name,
        "checked_cases": result.checked_cases,
        "case_id": result.witness.case_id,
        "witness_object_id": obj.id,
        "wall_seconds": elapsed,
    }


def main() -> None:
    rows = []

    # 1. Mathematical claim: p does not imply p∧q∧¬r.
    vals = tuple(product((False, True), repeat=3))
    rows.append(run_family(
        "math-claim.strict-strengthening",
        vals,
        lambda t: (not t[0]) or (t[0] and t[1] and (not t[2])),
        lambda t: (
            "".join("1" if x else "0" for x in t),
            json.dumps({"p": t[0], "q": t[1], "r": t[2]}, sort_keys=True).encode(),
        ),
        claim_ref="claim:p_implies_p_and_q_and_not_r",
        boundary_ref="Bool^3",
        verifier_ref="python:truth-enumeration",
    ))

    # 2. Gallai/domain: not every finite simple graph has an edge cover.
    rows.append(run_family(
        "gallai.edge-cover-definedness",
        graph_cases(),
        lambda g: minimum_edge_cover_number(g) is not None,
        lambda g: (
            f"n{g.vertex_count}:{g.edges}",
            json.dumps({"n": g.vertex_count, "edges": list(g.edges)}).encode(),
        ),
        claim_ref="claim:all_finite_simple_graphs_have_edge_cover",
        boundary_ref="finite-simple-graphs:n<=3",
        verifier_ref="mathgraph.graph_invariants:minimum_edge_cover_number",
    ))

    # 3. ARC: one coarse action class is not sufficient for protected channel.
    actions = ("A", "B", "C", "D", "E")
    channel = {"A": "MARK", "B": "SOURCE_TRANSFORM", "C": "MARK", "D": "SOURCE_TRANSFORM", "E": "MARK"}
    rows.append(run_family(
        "arc.coarse-action-quotient",
        tuple(combinations(actions, 2)),
        lambda pair: channel[pair[0]] == channel[pair[1]],
        lambda pair: (
            f"{pair[0]}~{pair[1]}",
            json.dumps({"left": pair[0], "right": pair[1], "channels": [channel[pair[0]], channel[pair[1]]]}).encode(),
        ),
        claim_ref="claim:all_generator_actions_same_protected_effect",
        boundary_ref="ARC-generator:A-E",
        verifier_ref="qualified:arc-generator-effect-quotient",
    ))

    # 4. CLC: Unit certificate identity does not determine live warrant.
    clc_cases = (("p0", "Unit", "0"), ("p3", "Unit", "3"))
    rows.append(run_family(
        "clc.certificate-provenance",
        tuple(combinations(clc_cases, 2)),
        lambda pair: (pair[0][1] != pair[1][1]) or (pair[0][2] == pair[1][2]),
        lambda pair: (
            f"{pair[0][0]}~{pair[1][0]}",
            json.dumps({"certificate": "Unit", "warrants": [pair[0][2], pair[1][2]]}).encode(),
        ),
        claim_ref="claim:certificate_identity_determines_warrant",
        boundary_ref="CLC-Unit-provenance",
        verifier_ref="qualified:clc-certificate-provenance",
    ))

    # 5. Metatron: one-shot and replenished dynamics do not have same viability.
    states = ("ready", "depleted", "unauthorized_ready", "unauthorized_depleted")
    failures = ("0", "1")
    one_shot = [
        Hyperedge("ready", "depleted", "0", frozenset({"0"})),
        Hyperedge("ready", "depleted", "1", frozenset({"0"})),
    ]
    replenished = [
        Hyperedge("ready", "ready", "0", frozenset({"0"})),
        Hyperedge("ready", "ready", "1", frozenset({"0"})),
    ]
    one_kernel = greatest_viability_kernel(states, failures, one_shot, {"0"})
    rep_kernel = greatest_viability_kernel(states, failures, replenished, {"0"})
    rows.append(run_family(
        "metatron.viability-dynamics",
        states,
        lambda state: (state in one_kernel) == (state in rep_kernel),
        lambda state: (
            state,
            json.dumps({"state": state, "one_shot": state in one_kernel, "replenished": state in rep_kernel}).encode(),
        ),
        claim_ref="claim:one_shot_and_replenished_same_viability",
        boundary_ref="Metatron-V7-four-state",
        verifier_ref="mathgraph.crystal:greatest_viability_kernel",
    ))

    # 6. MSI: coarse representation does not preserve protected target.
    k1 = (4, 0, 4, 0)
    k2 = (4, 4, 0, 0)
    chi = (1, -1, 1, -1)
    def coarse(k):
        return (tuple(k.count(i) for i in range(5)), sum(2 * c - 4 for c in k))
    def target(k):
        return sum(sign * (2 * c - 4) for sign, c in zip(chi, k))
    rows.append(run_family(
        "msi.quotient-sufficiency",
        ((k1, k2),),
        lambda pair: coarse(pair[0]) != coarse(pair[1]) or target(pair[0]) == target(pair[1]),
        lambda pair: (
            "k1~k2",
            json.dumps({"left": pair[0], "right": pair[1], "coarse": coarse(pair[0]), "targets": [target(pair[0]), target(pair[1])]}).encode(),
        ),
        claim_ref="claim:coarse_signature_is_sufficient",
        boundary_ref="MSI-finite-quotient-counterexample",
        verifier_ref="qualified:msi-quotient-falsifier",
    ))

    # 7. PRISM quotient: safe and over-quotient protected futures differ.
    prism_cases = (("safe", ("0.4", "0.6")), ("over", ("1", "1")))
    rows.append(run_family(
        "prism.overquotient",
        tuple(combinations(prism_cases, 2)),
        lambda pair: pair[0][1] == pair[1][1],
        lambda pair: (
            f"{pair[0][0]}~{pair[1][0]}",
            json.dumps({"left": pair[0], "right": pair[1]}).encode(),
        ),
        claim_ref="claim:safe_and_overquotient_same_reachability",
        boundary_ref="PRISM-goal1-reachability",
        verifier_ref="qualified:prism-quotient-separator",
    ))

    # 8. Finite magma: left-projection magma is not commutative.
    magma_cases = tuple(product((0, 1), repeat=2))
    op = lambda x, y: x
    rows.append(run_family(
        "finite-magma.commutativity",
        magma_cases,
        lambda pair: op(*pair) == op(pair[1], pair[0]),
        lambda pair: (
            f"{pair[0]},{pair[1]}",
            json.dumps({"x": pair[0], "y": pair[1], "xy": op(*pair), "yx": op(pair[1], pair[0])}).encode(),
        ),
        claim_ref="claim:left_projection_magma_commutative",
        boundary_ref="magma-order-2",
        verifier_ref="python:finite-magma-enumeration",
    ))

    # 9. Adapter preservation: a reachability-only adapter does not preserve state identity.
    contract = AdapterContract(
        adapter_id="falsifier-adapter",
        contract_version=1,
        source_space="source",
        target_space="target",
        preserves_interfaces=("probability.reachability.interval@1",),
    )
    requested = ("probability.reachability.interval@1", "state.identity@1")
    rows.append(run_family(
        "adapter.preservation-boundary",
        requested,
        lambda interface: interface in contract.preserves_interfaces,
        lambda interface: (
            interface,
            json.dumps({"requested": interface, "preserved": list(contract.preserves_interfaces)}).encode(),
        ),
        claim_ref="claim:adapter_preserves_all_requested_interfaces",
        boundary_ref="AdapterContract:falsifier-adapter",
        verifier_ref="mathgraph.crystal:AdapterContract",
    ))

    total_wall = sum(row["wall_seconds"] for row in rows)
    total_checks = sum(row["checked_cases"] for row in rows)

    evidence = {
        "schema": "mathgraph.crystal-swarm-scale-v2-falsifier.qualified",
        "status": "QUALIFIED_BOUNDED",
        "parent_head": PARENT,
        "crystal_waist_changed": False,
        "claim_dialect_changed": False,
        "graph_dialect_changed": False,
        "relation_dialect_changed": False,
        "selected_compiler": "falsifier.finite.witness@1",
        "representative_families_executed": len(rows),
        "projected_frontier_fanout_from_v1": PROJECTED_FRONTIER_FANOUT,
        "actual_representative_residuals_closed": len(rows),
        "total_cases_checked_until_first_witness": total_checks,
        "measured_search_wall_seconds": total_wall,
        "families": rows,
        "new_interfaces": [
            "falsifier.finite.witness@1",
            "claim.refutation@1",
            "evidence.provenance@1",
        ],
        "architecture_result": (
            "One generic deterministic finite falsifier search and witness envelope "
            "replayed nine heterogeneous bounded families with stable content-addressed "
            "counterexample objects and no Crystal-waist change."
        ),
        "boundary": (
            "Actual execution covers nine representative families, not all 56 repository-mined "
            "candidate families. The 56-family number is projected fanout from V1 refinement. "
            "V3 should auto-generate thin adapters for the mined frontier and measure true closure."
        ),
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_SWARM_SCALE_V2_FALSIFIER=QUALIFIED_BOUNDED")
    print(json.dumps({
        "representative_families_executed": len(rows),
        "projected_frontier_fanout_from_v1": PROJECTED_FRONTIER_FANOUT,
        "actual_representative_residuals_closed": len(rows),
        "total_cases_checked_until_first_witness": total_checks,
        "measured_search_wall_seconds": total_wall,
        "families": [[r["family"], r["case_id"], r["checked_cases"]] for r in rows],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
