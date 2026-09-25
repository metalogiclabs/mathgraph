#!/usr/bin/env python3
"""Cross-family residual market over five independently qualified families."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from itertools import product
import json
from pathlib import Path

from mathgraph.crystal import Hyperedge, SemanticObject, greatest_viability_kernel
from mathgraph.finite_relation import (
    FiniteObservationProfile,
    FinitePredicateProfile,
    predicate_equivalent,
    predicate_implies,
    predicate_separator,
    quotient_falsifiers,
)
from mathgraph.graph_invariants import (
    has_isolated_vertex,
    maximum_matching_number,
    minimum_edge_cover_number,
)
from scripts.run_crystal_residual_swarm_v0 import all_graphs

ROOT = Path(__file__).resolve().parents[1]
PARENT = "36ef1100abc6f989f6d19e42775319259dbb54d1"
RESULT = ROOT / "evidence" / "crystal-cross-family-swarm-v0" / "result.json"


@dataclass(frozen=True)
class Residual:
    name: str
    family: str
    kind: str


@dataclass(frozen=True)
class Action:
    name: str
    closes: tuple[str, ...]
    unlocks: tuple[str, ...]
    decisiveness: int
    cost: int

    def score(self, live: set[str]) -> tuple[int, int]:
        closure = len(set(self.closes) & live)
        numerator = 8 * closure + 3 * self.decisiveness + 2 * len(self.unlocks)
        return numerator, self.cost


def better(a: Action, b: Action, live: set[str]) -> bool:
    an, ad = a.score(live)
    bn, bd = b.score(live)
    lhs, rhs = an * bd, bn * ad
    return lhs > rhs or (lhs == rhs and a.name < b.name)


def roundtrip(*profiles) -> int:
    count = 0
    for profile in profiles:
        obj = profile.semantic_object()
        assert SemanticObject.from_bytes(obj.to_bytes()) == obj
        count += 1
    return count


def family_claims() -> dict:
    cases = tuple("".join("1" if x else "0" for x in vals)
                  for vals in product((False, True), repeat=3))
    vals = tuple(product((False, True), repeat=3))
    base = FinitePredicateProfile(
        "claim.base", cases, tuple(p for p, q, r in vals)
    )
    equiv = FinitePredicateProfile(
        "claim.equiv", cases, tuple(p and (q or (not q)) for p, q, r in vals)
    )
    stronger = FinitePredicateProfile(
        "claim.stronger", cases, tuple(p and q and (not r) for p, q, r in vals)
    )
    assert predicate_equivalent(base, equiv)
    assert predicate_implies(stronger, base)
    sep = predicate_separator(base, stronger)
    assert sep is not None
    return {
        "profiles": roundtrip(base, equiv, stronger),
        "equivalent": True,
        "strict_implication": True,
        "separator": sep[0],
    }


def family_gallai() -> dict:
    cases = []
    exact_truth = []
    weak_truth = []
    defined_truth = []
    nonisolated_truth = []
    for n in range(1, 7):
        for idx, graph in enumerate(all_graphs(n)):
            case = f"n{n}:g{idx}"
            cases.append(case)
            rho = minimum_edge_cover_number(graph)
            nu = maximum_matching_number(graph)
            exact_truth.append(rho is not None and nu + rho == n)
            weak_truth.append(rho is not None and nu + rho <= n)
            defined_truth.append(rho is not None)
            nonisolated_truth.append(not has_isolated_vertex(graph))
    c = tuple(cases)
    exact = FinitePredicateProfile("gallai.exact", c, tuple(exact_truth))
    weak = FinitePredicateProfile("gallai.weak", c, tuple(weak_truth))
    defined = FinitePredicateProfile("gallai.defined", c, tuple(defined_truth))
    noniso = FinitePredicateProfile("gallai.nonisolated", c, tuple(nonisolated_truth))
    # Exact and weak are equivalent as partial claims once definedness is included.
    assert predicate_equivalent(exact, weak)
    assert predicate_equivalent(defined, noniso)
    return {
        "profiles": roundtrip(exact, weak, defined, noniso),
        "cases": len(c),
        "exact_equals_weak": True,
        "defined_equals_nonisolated": True,
    }


def family_arc() -> dict:
    actions = ("A", "B", "C", "D", "E")
    protected = FiniteObservationProfile(
        "arc.generator.channel",
        actions,
        (("MARK",), ("SOURCE_TRANSFORM",), ("MARK",), ("SOURCE_TRANSFORM",), ("MARK",)),
    )
    classes = set(protected.partition().values())
    assert classes == {("A", "C", "E"), ("B", "D")}
    coarse = FiniteObservationProfile(
        "arc.coarse.all-actions",
        actions,
        tuple(("ACTION",) for _ in actions),
    )
    falsifiers = quotient_falsifiers(coarse, protected)
    assert falsifiers
    return {
        "profiles": roundtrip(protected, coarse),
        "classes": sorted([list(group) for group in classes]),
        "coarse_falsifiers": len(falsifiers),
    }


def family_clc() -> dict:
    cases = ("p0", "p3")
    certificate = FiniteObservationProfile(
        "clc.certificate-id", cases, (("Unit",), ("Unit",))
    )
    warrant = FiniteObservationProfile(
        "clc.live-warrant", cases, (("live-warrant", "0"), ("live-warrant", "3"))
    )
    falsifiers = quotient_falsifiers(certificate, warrant)
    assert falsifiers == (("p0", "p3"),)
    return {
        "profiles": roundtrip(certificate, warrant),
        "falsifiers": [list(x) for x in falsifiers],
    }


def family_metatron() -> dict:
    states = ("ready", "depleted", "unauthorized_ready", "unauthorized_depleted")
    failures = ("0", "1")
    one_shot_edges = [
        Hyperedge("ready", "depleted", "0", frozenset({"0"})),
        Hyperedge("ready", "depleted", "1", frozenset({"0"})),
    ]
    replenished_edges = [
        Hyperedge("ready", "ready", "0", frozenset({"0"})),
        Hyperedge("ready", "ready", "1", frozenset({"0"})),
    ]
    one = greatest_viability_kernel(states, failures, one_shot_edges, {"0"})
    rep = greatest_viability_kernel(states, failures, replenished_edges, {"0"})
    p_one = FinitePredicateProfile(
        "metatron.one-shot-viable", states, tuple(s in one for s in states)
    )
    p_rep = FinitePredicateProfile(
        "metatron.replenished-viable", states, tuple(s in rep for s in states)
    )
    sep = predicate_separator(p_one, p_rep)
    assert sep == ("ready", False, True)
    return {
        "profiles": roundtrip(p_one, p_rep),
        "one_shot_kernel": sorted(one),
        "replenished_kernel": sorted(rep),
        "separator": sep[0],
    }


def main() -> None:
    residuals = (
        Residual("claim_relation_compiler_gap", "math-claims", "shared-relation"),
        Residual("gallai_relation_compiler_gap", "graph-theory", "shared-relation"),
        Residual("arc_relation_compiler_gap", "ARC", "shared-relation"),
        Residual("clc_relation_compiler_gap", "CLC", "shared-relation"),
        Residual("metatron_relation_compiler_gap", "Metatron", "shared-relation"),
        Residual("universal_gallai_proof_gap", "graph-theory", "domain-specific"),
        Residual("arc_target_projection_gap", "ARC", "domain-specific"),
        Residual("clc_general_transport_gap", "CLC", "domain-specific"),
        Residual("metatron_unbounded_viability_gap", "Metatron", "domain-specific"),
    )
    live = {r.name for r in residuals}
    shared = tuple(r.name for r in residuals if r.kind == "shared-relation")
    actions = (
        Action(
            "compile_generic_finite_relation_interface",
            shared,
            (
                "literature-perspective-batching",
                "cross-domain-quotient-cache",
                "separator-deduplication",
            ),
            3, 4,
        ),
        Action(
            "attempt_universal_gallai_proof",
            ("universal_gallai_proof_gap",),
            ("universal-theorem-authority",),
            3, 8,
        ),
        Action(
            "solve_arc_target_projection",
            ("arc_target_projection_gap",),
            ("arc-next-task",),
            3, 5,
        ),
        Action(
            "prove_clc_general_transport",
            ("clc_general_transport_gap",),
            ("transport-reuse",),
            3, 6,
        ),
        Action(
            "solve_metatron_unbounded_viability",
            ("metatron_unbounded_viability_gap",),
            ("unbounded-control-reuse",),
            3, 7,
        ),
        Action(
            "search_more_sources",
            (),
            ("more-candidate-perspectives", "more-residuals"),
            1, 1,
        ),
    )

    selected = actions[0]
    for action in actions[1:]:
        if better(action, selected, live):
            selected = action
    assert selected.name == "compile_generic_finite_relation_interface"

    families = {
        "math_claims": family_claims(),
        "gallai": family_gallai(),
        "arc": family_arc(),
        "clc": family_clc(),
        "metatron": family_metatron(),
    }
    after = live - set(selected.closes)
    scores = {}
    for action in actions:
        num, den = action.score(live)
        scores[action.name] = {
            "numerator": num,
            "denominator": den,
            "ratio": num / den,
        }

    evidence = {
        "schema": "mathgraph.crystal-cross-family-swarm-v0.qualified",
        "status": "QUALIFIED_BOUNDED",
        "parent_head": PARENT,
        "crystal_waist_changed": False,
        "claim_dialect_changed": False,
        "graph_dialect_changed": False,
        "families": families,
        "live_residuals_before": sorted(live),
        "candidate_action_scores": scores,
        "selected_action": selected.name,
        "closed_residuals": sorted(set(selected.closes)),
        "live_residuals_after": sorted(after),
        "residual_count_delta": [len(live), len(after)],
        "new_interfaces": [
            "relation.equivalence@1",
            "relation.implication@1",
            "relation.separator@1",
            "relation.partition@1",
            "relation.quotient-falsifier@1",
        ],
        "architecture_result": (
            "One generic finite-relation dialect reproduced five previously "
            "domain-specific equivalence/separator/quotient patterns and closed "
            "five live compiler gaps in one action."
        ),
        "boundary": (
            "The five families are bounded replays of already-qualified finite "
            "structures. Scheduler weights remain candidate policy, not optimality proof."
        ),
    }
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print("CRYSTAL_CROSS_FAMILY_SWARM_V0=QUALIFIED_BOUNDED")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
