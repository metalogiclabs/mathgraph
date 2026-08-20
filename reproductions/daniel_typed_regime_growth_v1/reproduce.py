#!/usr/bin/env python3
"""
Typed Regime Growth V1

Exact finite witness of strict object-level constructor-language growth under a
supplied developmental extension family.

Scientific boundary:
  * M0/M1 are the frozen object-level languages available to the controller.
  * ExposeDependency is supplied by the developmental meta-language; this
    experiment does NOT claim autonomous invention of that schema.
  * P2 is committed before episode-1 selection and is not read by the selector;
    this establishes online target blindness, not independent authorship.

Standard library only. Deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import product
import json

X = (0, 1)
A = (0, 1, 2)
XA = tuple(product(X, A))
U = "U"  # A -> Bool
D = "D"  # X x A -> Bool

# Fixed before episode-1 selection. select_episode1_extension() never reads it.
P2_BITS = tuple((x == 0) == (a == 0) for x, a in XA)
P2_COMMITMENT = sha256(bytes(int(b) for b in P2_BITS)).hexdigest()


@dataclass(frozen=True)
class Term:
    sort: str
    op: str
    args: tuple["Term", ...] = ()

    def size(self) -> int:
        return 1 + sum(a.size() for a in self.args)

    def pretty(self) -> str:
        if self.op in {"⊥", "⊤", "a=0", "a=1", "a=2", "x=0"}:
            return self.op
        if self.op == "lift":
            return f"lift({self.args[0].pretty()})"
        if self.op == "¬":
            return f"¬({self.args[0].pretty()})"
        return f"({self.args[0].pretty()} {self.op} {self.args[1].pretty()})"


@dataclass(frozen=True)
class Regime:
    name: str
    dep_sort: bool
    unary_primitives: tuple[str, ...] = ("a=0",)


def eval_u(t: Term, a: int) -> bool:
    if t.op == "⊥": return False
    if t.op == "⊤": return True
    if t.op == "a=0": return a == 0
    if t.op == "a=1": return a == 1
    if t.op == "a=2": return a == 2
    if t.op == "¬": return not eval_u(t.args[0], a)
    if t.op == "∧": return eval_u(t.args[0], a) and eval_u(t.args[1], a)
    if t.op == "∨": return eval_u(t.args[0], a) or eval_u(t.args[1], a)
    raise ValueError(t)


def eval_d(t: Term, x: int, a: int) -> bool:
    if t.op == "x=0": return x == 0
    if t.op == "lift": return eval_u(t.args[0], a)
    if t.op == "¬": return not eval_d(t.args[0], x, a)
    if t.op == "∧": return eval_d(t.args[0], x, a) and eval_d(t.args[1], x, a)
    if t.op == "∨": return eval_d(t.args[0], x, a) or eval_d(t.args[1], x, a)
    raise ValueError(t)


def sem_u(t: Term) -> tuple[bool, ...]:
    return tuple(eval_u(t, a) for a in A)


def sem_d(t: Term) -> tuple[bool, ...]:
    return tuple(eval_d(t, x, a) for x, a in XA)


def enumerate_unary(regime: Regime, max_size: int = 7) -> dict[tuple[bool, ...], Term]:
    bases = [Term(U, "⊥"), Term(U, "⊤")] + [Term(U, p) for p in regime.unary_primitives]
    by_size: dict[int, list[Term]] = {1: bases}
    seen: dict[tuple[bool, ...], Term] = {}
    for size in range(1, max_size + 1):
        candidates = list(by_size.get(size, []))
        if size >= 2:
            for t in by_size.get(size - 1, []):
                candidates.append(Term(U, "¬", (t,)))
            for left_size in range(1, size - 1):
                right_size = size - 1 - left_size
                for l in by_size.get(left_size, []):
                    for r in by_size.get(right_size, []):
                        candidates.append(Term(U, "∧", (l, r)))
                        candidates.append(Term(U, "∨", (l, r)))
        keep = []
        for t in candidates:
            s = sem_u(t)
            if s not in seen:
                seen[s] = t
                keep.append(t)
        by_size[size] = keep
    return seen


def enumerate_dep(regime: Regime, max_size: int = 12) -> dict[tuple[bool, ...], Term]:
    if not regime.dep_sort:
        return {}
    unary = enumerate_unary(regime)
    by_size: dict[int, list[Term]] = {1: [Term(D, "x=0")]}
    for u in unary.values():
        by_size.setdefault(1 + u.size(), []).append(Term(D, "lift", (u,)))
    seen: dict[tuple[bool, ...], Term] = {}
    for size in range(1, max_size + 1):
        candidates = list(by_size.get(size, []))
        if size >= 2:
            for t in by_size.get(size - 1, []):
                candidates.append(Term(D, "¬", (t,)))
            for left_size in range(1, size - 1):
                right_size = size - 1 - left_size
                for l in by_size.get(left_size, []):
                    for r in by_size.get(right_size, []):
                        candidates.append(Term(D, "∧", (l, r)))
                        candidates.append(Term(D, "∨", (l, r)))
        keep = []
        for t in candidates:
            s = sem_d(t)
            if s not in seen:
                seen[s] = t
                keep.append(t)
        by_size[size] = keep
    return seen


def synthesize_dep(regime: Regime, target: tuple[bool, ...]) -> Term | None:
    return enumerate_dep(regime).get(target)


def obstruction_pairs(target: tuple[bool, ...]):
    """Pairs merged by projection (x,a)->a but requiring different outputs."""
    pairs = []
    for i, p in enumerate(XA):
        for j, q in enumerate(XA):
            if i < j and p[1] == q[1] and target[i] != target[j]:
                pairs.append((p, q))
    return pairs


M0 = Regime("M0", dep_sort=False, unary_primitives=("a=0",))
M1 = Regime("M1=M0+ExposeDependency", dep_sort=True, unary_primitives=("a=0",))
ALL_UNARY_BITS = tuple(product((False, True), repeat=len(A)))
P1 = tuple((x == 0) or (a == 0) for x, a in XA)


def select_episode1_extension() -> str:
    """Select within the supplied extension family using P1 only."""
    if not obstruction_pairs(P1):
        raise AssertionError("P1 must expose a projection obstruction")
    # Exhaust the complete unary-only subfamily. None can distinguish x.
    for bits in ALL_UNARY_BITS:
        lifted = tuple(bits[A.index(a)] for x, a in XA)
        if lifted == P1:
            raise AssertionError("A unary-only extension unexpectedly represented P1")
    # ExposeDependency is a supplied meta-language candidate, not synthesized here.
    if synthesize_dep(M1, P1) is None:
        raise AssertionError("Supplied ExposeDependency candidate failed to represent P1")
    return "ExposeDependency"


O1 = select_episode1_extension()

# Only now use the already-committed second target.
assert sha256(bytes(int(b) for b in P2_BITS)).hexdigest() == P2_COMMITMENT
O2 = synthesize_dep(M1, P2_BITS)

m0_u = enumerate_unary(M0)
m1_u = enumerate_unary(M1)
m1_d = enumerate_dep(M1)
all_unary_shams_fail_p2 = all(
    tuple(bits[A.index(a)] for x, a in XA) != P2_BITS
    for bits in ALL_UNARY_BITS
)

gates = {
    "G1_P1_has_projection_obstruction": len(obstruction_pairs(P1)) > 0,
    "G2_complete_unary_only_subfamily_preserves_P1_impossibility":
        all(tuple(bits[A.index(a)] for x, a in XA) != P1 for bits in ALL_UNARY_BITS),
    "G3_supplied_ExposeDependency_admitted_using_P1_only": O1 == "ExposeDependency",
    "G4_M0_has_no_D_terms": enumerate_dep(M0) == {},
    "G5_P2_outside_complete_unary_only_subfamily": all_unary_shams_fail_p2,
    "G6_M1_strictly_adds_D_formability": len(m1_d) > 0,
    "G7_O2_constructed_in_M1": O2 is not None and sem_d(O2) == P2_BITS,
    "G8_ancestor_ablation_restores_nonformability": synthesize_dep(M0, P2_BITS) is None,
    "G9_unary_shams_preserve_nonformability": all_unary_shams_fail_p2,
    "G10_old_U_semantic_fragment_preserved": set(m0_u) == set(m1_u),
    "G11_O2_is_composed_not_primitive": O2 is not None and O2.op not in {"x=0", "lift"},
    "G12_identical_second_generation_synthesizer_cold_vs_warm":
        synthesize_dep(M0, P2_BITS) is None and synthesize_dep(M1, P2_BITS) == O2,
}
assert all(gates.values()), {k: v for k, v in gates.items() if not v}

result = {
    "verdict": "PASS_STRICT_TYPED_REGIME_GROWTH_V1",
    "domains": {"X": list(X), "A": list(A), "XA_points": len(XA)},
    "episode1": {
        "target_bits": list(P1),
        "projection_obstruction_pairs": [[list(p), list(q)] for p, q in obstruction_pairs(P1)],
        "extension_family_boundary": "all 8 unary truth-table primitives plus supplied ExposeDependency schema",
        "selected_extension": O1,
        "M0_U_semantic_classes": len(m0_u),
        "all_possible_unary_shams_tested": len(ALL_UNARY_BITS),
    },
    "episode2": {
        "target_commitment_sha256": P2_COMMITMENT,
        "target_bits": list(P2_BITS),
        "online_target_blindness_only": True,
        "independent_authorship_claimed": False,
        "cold_D_form_count": 0,
        "warm_D_semantic_classes": len(m1_d),
        "O2": O2.pretty() if O2 else None,
        "O2_size": O2.size() if O2 else None,
        "cold_constructible": synthesize_dep(M0, P2_BITS) is not None,
        "warm_constructible": O2 is not None,
        "ablated_constructible": synthesize_dep(M0, P2_BITS) is not None,
        "all_unary_shams_constructible": not all_unary_shams_fail_p2,
    },
    "old_fragment": {
        "meaning_of_conservative": "equality of denotable U-semantics in this finite model",
        "M0_U_classes": len(m0_u),
        "M1_U_classes": len(m1_u),
        "same_old_fragment": set(m0_u) == set(m1_u),
        "general_proof_theoretic_conservativity_claimed": False,
    },
    "gates": gates,
    "claim": (
        "Within the frozen finite object-level calculus, Form_D(M0) is empty; after admission of the "
        "supplied ExposeDependency extension schema, M1 has D-typed terms and the unchanged episode-2 "
        "synthesizer constructs O2. Removing that extension restores non-formability; the complete "
        "unary-only sham family fails; and the old U semantic fragment is preserved."
    ),
    "boundary": (
        "This is strict object-language formability growth under a supplied developmental extension family. "
        "ExposeDependency is not autonomously invented, P2 commitment establishes online target blindness "
        "rather than independent authorship, and no host-language or general proof-theoretic growth is claimed."
    ),
}
print(json.dumps(result, indent=2, sort_keys=True))
