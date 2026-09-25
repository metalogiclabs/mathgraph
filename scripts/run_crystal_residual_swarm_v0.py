#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass, asdict
from itertools import combinations
import json
from pathlib import Path
from mathgraph.crystal import SemanticObject
from mathgraph.graph_invariants import (
    FiniteSimpleGraphPayload, has_isolated_vertex,
    maximum_matching_number, minimum_edge_cover_number,
)

ROOT = Path(__file__).resolve().parents[1]
PARENT = "2b224b30523322bd580f05800ab9a5c2d59fa0cf"
RESULT = ROOT / "evidence" / "crystal-residual-swarm-v0" / "result.json"

@dataclass(frozen=True)
class Vertex:
    name: str
    status: str
    interface: str

@dataclass(frozen=True)
class Action:
    name: str
    closes: tuple[str, ...]
    unlocks: tuple[str, ...]
    decisiveness: int
    cost: int
    def score(self, live: set[str]) -> tuple[int, int]:
        closure = len(set(self.closes) & live)
        return 8 * closure + 3 * self.decisiveness + 2 * len(self.unlocks), self.cost

def better(a: Action, b: Action, live: set[str]) -> bool:
    an, ad = a.score(live); bn, bd = b.score(live)
    return an * bd > bn * ad or (an * bd == bn * ad and a.name < b.name)

def all_graphs(n: int):
    es = tuple(combinations(range(n), 2))
    for mask in range(1 << len(es)):
        yield FiniteSimpleGraphPayload(n, tuple(e for i, e in enumerate(es) if mask & (1 << i)))

def execute_interface():
    total = defined = mismatch = eqfail = roundtrips = 0
    for n in range(1, 7):
        for g in all_graphs(n):
            total += 1
            obj = g.semantic_object()
            assert SemanticObject.from_bytes(obj.to_bytes()) == obj
            roundtrips += 1
            rho = minimum_edge_cover_number(g)
            nu = maximum_matching_number(g)
            iso = has_isolated_vertex(g)
            if (rho is None) != iso:
                mismatch += 1
            if rho is not None:
                defined += 1
                if nu + rho != n:
                    eqfail += 1
    assert mismatch == 0 and eqfail == 0
    return {
        "graphs_checked": total,
        "edge_cover_defined": defined,
        "definedness_mismatches": mismatch,
        "gallai_equality_failures": eqfail,
        "semantic_object_roundtrips": roundtrips,
    }

def main():
    vertices = (
        Vertex("canonical_exact_law", "closed", "claim.equivalence@1"),
        Vertex("research_exact_law", "closed", "claim.equivalence@1"),
        Vertex("vixra_weak_shadow", "closed", "claim.implication@1"),
        Vertex("isolated_vertex_obstruction", "promoted", "graph.isolated-vertices@1"),
        Vertex("formal_edge_cover_interface_gap", "residual", "graph.edge-cover.minimum@1"),
        Vertex("universal_gallai_proof_gap", "residual", "proof.universal@1"),
    )
    live = {v.name for v in vertices if v.status == "residual"}
    actions = (
        Action("extend_graph_edge_cover_interface",
               ("formal_edge_cover_interface_gap",),
               ("formal_cross_source_adapter","future_cover_duality_families"), 3, 2),
        Action("attempt_universal_gallai_proof",
               ("universal_gallai_proof_gap",),
               ("universal_theorem_authority",), 3, 8),
        Action("search_more_gallai_sources",
               (), ("more_candidate_perspectives",), 1, 1),
    )
    selected = actions[0]
    for a in actions[1:]:
        if better(a, selected, live):
            selected = a
    assert selected.name == "extend_graph_edge_cover_interface"
    execution = execute_interface()
    after = live - set(selected.closes)
    probe = FiniteSimpleGraphPayload(2, ((0,1),)).semantic_object()
    assert "graph.edge-cover.minimum@1" in probe.interfaces
    scores = {}
    for a in actions:
        num, den = a.score(live)
        scores[a.name] = {"numerator":num,"denominator":den,"ratio":num/den}
    evidence = {
        "schema":"mathgraph.crystal-residual-swarm-v0.qualified",
        "status":"QUALIFIED_BOUNDED",
        "parent_head":PARENT,
        "crystal_waist_changed":False,
        "claim_dialect_changed":False,
        "initial_vertices":[asdict(v) for v in vertices],
        "initial_live_residuals":sorted(live),
        "candidate_action_scores":scores,
        "selected_action":selected.name,
        "execution":execution,
        "post_action_live_residuals":sorted(after),
        "new_semantic_interface":"graph.edge-cover.minimum@1",
        "architecture_result":"Residual-first scheduling chose a reusable missing interface before an expensive universal proof or more source search.",
        "boundary":"The scheduler weights are a candidate policy, not an optimality theorem; execution is exhaustive only for labelled finite simple graphs on 1..6 vertices."
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    print("CRYSTAL_RESIDUAL_SWARM_V0=QUALIFIED_BOUNDED")
    print(json.dumps(evidence,sort_keys=True))

if __name__ == "__main__":
    main()
