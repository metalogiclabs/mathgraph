#!/usr/bin/env python3
"""V4 — synthesize a quotient-repair law from a weak generic relation DSL.

Protocol frozen in PRECOMMIT.md at commit 71b9ba081c69d5908d79b5005d0e40943c49737b.
Standard library only; deterministic.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import product
from collections import Counter
import json

Relation = frozenset[tuple[int, int]]


def universal(n: int) -> Relation:
    return frozenset((i, j) for i in range(n) for j in range(n))


def identity(n: int) -> Relation:
    return frozenset((i, i) for i in range(n))


def parent_equivalence(block_sizes: tuple[int, ...]) -> Relation:
    blocks = []
    start = 0
    for size in block_sizes:
        blocks.append(tuple(range(start, start + size)))
        start += size
    return frozenset((i, j) for block in blocks for i in block for j in block)


def obstruction(E: Relation, labels: tuple[int, ...]) -> Relation:
    return frozenset((i, j) for (i, j) in E if labels[i] != labels[j])


def verifier_repair(E: Relation, labels: tuple[int, ...]) -> Relation:
    return frozenset((i, j) for (i, j) in E if labels[i] == labels[j])


@dataclass(frozen=True)
class Case:
    blocks: tuple[int, ...]
    arity: int
    labels: tuple[int, ...]

    @property
    def n(self) -> int:
        return sum(self.blocks)

    @property
    def E(self) -> Relation:
        return parent_equivalence(self.blocks)

    @property
    def O(self) -> Relation:
        return obstruction(self.E, self.labels)

    @property
    def target(self) -> Relation:
        return verifier_repair(self.E, self.labels)

    @property
    def signature(self):
        return (self.blocks, self.arity, self.labels)


@dataclass(frozen=True)
class Expr:
    op: str
    left: "Expr | None" = None
    right: "Expr | None" = None
    size: int = 1

    def pretty(self) -> str:
        if self.op in {"E", "O", "I", "U"}:
            return self.op
        if self.op == "conv":
            return f"converse({self.left.pretty()})"
        symbol = {"inter": "∩", "union": "∪", "diff": "\\"}[self.op]
        return f"({self.left.pretty()} {symbol} {self.right.pretty()})"


def eval_expr(expr: Expr, case: Case, override_O: Relation | None = None) -> Relation:
    if expr.op == "E": return case.E
    if expr.op == "O": return case.O if override_O is None else override_O
    if expr.op == "I": return identity(case.n)
    if expr.op == "U": return universal(case.n)
    if expr.op == "conv":
        r = eval_expr(expr.left, case, override_O)
        return frozenset((j, i) for i, j in r)
    a = eval_expr(expr.left, case, override_O)
    b = eval_expr(expr.right, case, override_O)
    if expr.op == "inter": return a & b
    if expr.op == "union": return a | b
    if expr.op == "diff": return a - b
    raise ValueError(expr.op)


def all_cases(blocks: tuple[int, ...], arity: int, limit: int | None = None):
    n = sum(blocks)
    for idx, labels in enumerate(product(range(arity), repeat=n)):
        if limit is not None and idx >= limit:
            break
        yield Case(blocks, arity, labels)


ACQUISITION = tuple(all_cases((2, 2), 2)) + tuple(all_cases((3, 2), 2)) + tuple(all_cases((2, 2), 3))
assert len(ACQUISITION) == 129
HELDOUT = tuple(all_cases((4, 4), 2)) + tuple(all_cases((3, 3, 2), 3)) + tuple(all_cases((2, 3, 2), 4, 7000))
assert len(HELDOUT) == 13817


def semantic_signature(expr: Expr, cases=ACQUISITION):
    return tuple(eval_expr(expr, c) for c in cases)


TERMINALS = tuple(Expr(x) for x in ("E", "O", "I", "U"))
canonical_by_signature = {semantic_signature(t): t for t in TERMINALS}
canonical_by_size = {1: list(TERMINALS)}
raw_by_size = {1: list(TERMINALS)}
perfect_raw_by_size = Counter()
TARGET_SIGNATURE = tuple(c.target for c in ACQUISITION)

winner = None
winner_size = None
for size in range(1, 8):
    if size > 1:
        raw = []
        for child_size, children in canonical_by_size.items():
            if child_size + 1 == size:
                raw.extend(Expr("conv", c, size=size) for c in children)
        for ls, lefts in canonical_by_size.items():
            for rs, rights in canonical_by_size.items():
                if 1 + ls + rs != size:
                    continue
                for l in lefts:
                    for r in rights:
                        raw.append(Expr("inter", l, r, size=size))
                        raw.append(Expr("union", l, r, size=size))
                        raw.append(Expr("diff", l, r, size=size))
        raw_by_size[size] = raw
        new_canonical = []
        for expr in raw:
            sig = semantic_signature(expr)
            if sig not in canonical_by_signature:
                canonical_by_signature[sig] = expr
                new_canonical.append(expr)
        canonical_by_size[size] = new_canonical

    perfect = [e for e in raw_by_size[size] if semantic_signature(e) == TARGET_SIGNATURE]
    perfect_raw_by_size[size] = len(perfect)
    if perfect:
        assert len(perfect) == 1, (size, [e.pretty() for e in perfect])
        winner = perfect[0]
        winner_size = size
        break

assert winner is not None
assert winner_size == 3
assert winner.pretty() == "(E \\ O)"
assert perfect_raw_by_size[1] == 0 and perfect_raw_by_size[2] == 0 and perfect_raw_by_size[3] == 1
LEARNED_PROGRAM = winner

heldout_pass = sum(eval_expr(LEARNED_PROGRAM, c) == c.target for c in HELDOUT)
assert heldout_pass == len(HELDOUT)

acq_signatures = {c.signature for c in ACQUISITION}
literal_memory_hits = sum(c.signature in acq_signatures for c in HELDOUT)
assert literal_memory_hits == 0

strict_heldout = [c for c in HELDOUT if c.target != c.E]
no_obstruction_failures = sum(
    eval_expr(LEARNED_PROGRAM, c, override_O=frozenset()) != c.target
    for c in strict_heldout
)
assert no_obstruction_failures == len(strict_heldout)


def next_case(c: Case) -> Case:
    digits = list(c.labels)
    carry = 1
    for i in range(len(digits) - 1, -1, -1):
        if not carry: break
        digits[i] += 1
        if digits[i] == c.arity:
            digits[i] = 0
        else:
            carry = 0
    return Case(c.blocks, c.arity, tuple(digits))

wrong_matches = 0
wrong_failures = 0
for c in HELDOUT:
    wrong_O = next_case(c).O
    if eval_expr(LEARNED_PROGRAM, c, override_O=wrong_O) == c.target:
        wrong_matches += 1
    else:
        wrong_failures += 1
assert wrong_matches + wrong_failures == len(HELDOUT)
# PRECOMMIT explicitly froze this as a descriptive control: adjacent labelings
# can induce the same quotient, so accidental matches are reported, not gated.

instance_relation_pairs = sum(len(c.target) for c in ACQUISITION)

result = {
    "protocol": "DANIEL_RELATIONAL_LAW_SYNTHESIS_V4",
    "verdict": "PASS_GENERIC_RELATIONAL_LAW_SYNTHESIS_AND_TRANSFER",
    "precommit_commit": "71b9ba081c69d5908d79b5005d0e40943c49737b",
    "dsl": {
        "terminals": ["E", "O", "I", "U"],
        "operations": ["converse", "intersection", "union", "difference"],
        "named_refinement_primitive_present": False,
        "search_max_size": 7,
    },
    "acquisition": {
        "cases": len(ACQUISITION),
        "perfect_raw_programs_by_size": dict(perfect_raw_by_size),
        "unique_smallest_program": LEARNED_PROGRAM.pretty(),
        "program_size": winner_size,
        "stored_instance_relation_pairs_if_memorized": instance_relation_pairs,
    },
    "heldout": {
        "cases": len(HELDOUT),
        "world_families": ["(4,4)/binary", "(3,3,2)/ternary", "(2,3,2)/quaternary:first7000"],
        "program_exact_matches": heldout_pass,
        "literal_instance_memory_hits": literal_memory_hits,
    },
    "controls": {
        "strict_refinement_heldout_cases": len(strict_heldout),
        "no_obstruction_control_failures": no_obstruction_failures,
        "wrong_obstruction_failures": wrong_failures,
        "wrong_obstruction_accidental_matches": wrong_matches,
        "wrong_obstruction_is_descriptive_not_pass_gate": True,
    },
    "claim": (
        "A unique smallest program was synthesized from a generic relation DSL on 129 acquisition cases: E\\O. "
        "Frozen before held-out evaluation, it exactly produced the verifier-required quotient repair on all "
        "13,817 held-out cases spanning new world sizes, parent geometries, and output arities."
    ),
    "boundary": (
        "The experiment does not invent relational algebra, set difference, finite program search, or minimization. "
        "It moves below a supplied RefinePartition primitive by synthesizing the reusable repair law itself from "
        "generic relation operations. The wrong-obstruction control is non-decisive because neighboring labelings "
        "often induce the same quotient; its exact counts are reported rather than post-hoc thresholded."
    ),
}
print(json.dumps(result, indent=2, sort_keys=True))
