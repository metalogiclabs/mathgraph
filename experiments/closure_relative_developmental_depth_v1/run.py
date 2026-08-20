#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import product
import json
from pathlib import Path

TOKENS = ("LT", "LE", "AND", "OR", "A", "B", "C", "D")


@dataclass(frozen=True)
class Case:
    name: str
    context: str
    broken: tuple[str, ...]
    target: tuple[str, ...]


@dataclass(frozen=True)
class RewriteAt:
    pos: int
    src: str
    dst: str
    grammar: str = "direct"

    def apply(self, xs: tuple[str, ...]) -> tuple[str, ...]:
        if self.pos < len(xs) and xs[self.pos] == self.src:
            ys = list(xs)
            ys[self.pos] = self.dst
            return tuple(ys)
        return xs


@dataclass(frozen=True)
class ConjugatedFixedSlot:
    """Alternate syntax: rewrite slot 0 after transport, then transport back."""

    shift: int
    src: str
    dst: str

    def apply(self, xs: tuple[str, ...]) -> tuple[str, ...] | None:
        y = rotate(xs, self.shift)
        if y[0] != self.src:
            return None
        z = list(y)
        z[0] = self.dst
        return rotate(tuple(z), -self.shift)


@dataclass(frozen=True)
class CapClass:
    src: str
    dst: str


def rotate(xs: tuple[str, ...], k: int) -> tuple[str, ...]:
    k %= len(xs)
    return xs[k:] + xs[:k]


def old_closure(xs: tuple[str, ...]) -> set[tuple[str, ...]]:
    return {rotate(xs, k) for k in range(len(xs))}


def outside_old_closure(case: Case) -> bool:
    return case.target not in old_closure(case.broken)


def multiset_obstruction(case: Case) -> bool:
    return Counter(case.broken) != Counter(case.target)


def canonical_class(op: RewriteAt | ConjugatedFixedSlot) -> CapClass:
    # Literal position/transport term is quotiented by the old cyclic action.
    return CapClass(op.src, op.dst)


def all_literals(xs: tuple[str, ...], grammar: str = "direct") -> list[RewriteAt]:
    out: list[RewriteAt] = []
    for pos, src in enumerate(xs):
        for dst in TOKENS:
            if dst != src:
                out.append(RewriteAt(pos, src, dst, grammar))
    return out


def all_conjugated_literals() -> list[ConjugatedFixedSlot]:
    return [
        ConjugatedFixedSlot(shift, src, dst)
        for shift in range(4)
        for src in TOKENS
        for dst in TOKENS
        if src != dst
    ]


def survivors(case: Case, grammar: str) -> list[RewriteAt]:
    return [op for op in all_literals(case.broken, grammar) if op.apply(case.broken) == case.target]


def class_survivors(case: Case, grammar: str) -> set[CapClass]:
    return {canonical_class(op) for op in survivors(case, grammar)}


def conjugated_class_survivors(case: Case) -> set[CapClass]:
    return {
        canonical_class(op)
        for op in all_conjugated_literals()
        if op.apply(case.broken) == case.target
    }


def transport_apply(cap: CapClass, xs: tuple[str, ...]) -> tuple[str, ...] | None:
    """Apply a retained capability using current state only.

    The constructor/verifier target is intentionally unavailable here. Transport
    is admitted only when the current state contains exactly one occurrence of
    the capability's source token, so the application site is determined without
    target leakage.
    """
    positions = [i for i, value in enumerate(xs) if value == cap.src]
    if len(positions) != 1:
        return None
    return RewriteAt(positions[0], cap.src, cap.dst).apply(xs)


def black_box_discover(
    case: Case,
    grammar: str,
    start: tuple[str, ...] | None = None,
) -> tuple[list[RewriteAt], list[tuple[RewriteAt, bool]]]:
    """Constructor gets candidate syntax; verifier returns only pass/fail."""
    xs = case.broken if start is None else start
    wins: list[RewriteAt] = []
    trace: list[tuple[RewriteAt, bool]] = []
    for op in all_literals(xs, grammar):
        ok = op.apply(xs) == case.target
        trace.append((op, ok))
        if ok:
            wins.append(op)
    return wins, trace


# ---------------------------------------------------------------------------
# Generation 1: literal repairs differ, closure-relative identity agrees.
# ---------------------------------------------------------------------------
S1 = Case("source_pos0", "if", ("LT", "A", "B", "C"), ("LE", "A", "B", "C"))
S2 = Case("source_pos2", "if", ("A", "B", "LT", "C"), ("A", "B", "LE", "C"))
H1 = Case("heldout_pos1", "if", ("A", "LT", "B", "C"), ("A", "LE", "B", "C"))
HARM = Case("protected_harm", "json", ("LT", "A", "B", "C"), ("LT", "A", "B", "C"))

s1_direct = survivors(S1, "direct")
s2_direct = survivors(S2, "direct")
literal_intersection = set(s1_direct) & set(s2_direct)
class_intersection = class_survivors(S1, "direct") & class_survivors(S2, "direct")
class_intersection_alt = conjugated_class_survivors(S1) & conjugated_class_survivors(S2)
O1 = next(iter(class_intersection)) if len(class_intersection) == 1 else None

# Frozen generic scope grammar over the only observable context field.
CONTEXTS = ("if", "json", "loop", "return")
SCOPE_CANDIDATES = {
    f"context=={c}": (lambda ctx, c=c: ctx == c) for c in CONTEXTS
}
SCOPE_CANDIDATES["ANY"] = lambda _ctx: True


def scope_valid(pred) -> bool:
    return pred(S1.context) and pred(S2.context) and not pred(HARM.context)


valid_scopes = [name for name, pred in SCOPE_CANDIDATES.items() if scope_valid(pred)]
scope_sizes = {
    name: sum(int(pred(c)) for c in CONTEXTS)
    for name, pred in SCOPE_CANDIDATES.items()
}
min_scope_size = min(scope_sizes[name] for name in valid_scopes)
minimal_scopes = [name for name in valid_scopes if scope_sizes[name] == min_scope_size]
SCOPE = minimal_scopes[0] if len(minimal_scopes) == 1 else None
scope_fn = SCOPE_CANDIDATES[SCOPE] if SCOPE else (lambda _ctx: False)

heldout_literal_identity_pass = any(
    op.apply(H1.broken) == H1.target for op in literal_intersection
)
heldout_quotient_state = (
    transport_apply(O1, H1.broken)
    if O1 and scope_fn(H1.context)
    else None
)
heldout_quotient_pass = heldout_quotient_state == H1.target
heldout_ablation_pass = H1.broken == H1.target


# ---------------------------------------------------------------------------
# Generation 2: O1 changes the one-new-class verifier-survival horizon.
# ---------------------------------------------------------------------------
D2 = Case(
    "double_broken",
    "if",
    ("A", "LT", "B", "AND"),
    ("A", "LE", "B", "OR"),
)

cold_wins, cold_trace = black_box_discover(D2, "direct")
mid = (
    transport_apply(O1, D2.broken)
    if O1 and scope_fn(D2.context)
    else None
)
mid_ok = mid == D2.target
warm_wins, warm_trace = black_box_discover(D2, "direct", mid) if mid else ([], [])
warm_classes = {canonical_class(op) for op in warm_wins}
O2 = next(iter(warm_classes)) if len(warm_classes) == 1 else None

# Stronger claim audit: raw meta-language constructibility, not verifier survival.
cold_available_classes = {canonical_class(op) for op, _ in cold_trace}
strict_O2_not_constructible_cold = bool(O2 and O2 not in cold_available_classes)


# Exact G1 closure: cyclic transport plus any transported application of O1.
def apply_O1_anywhere(xs: tuple[str, ...]) -> set[tuple[str, ...]]:
    out = {xs}
    if O1:
        for i, value in enumerate(xs):
            if value == O1.src:
                ys = list(xs)
                ys[i] = O1.dst
                out.add(tuple(ys))
    return out


def closure_G1(xs: tuple[str, ...]) -> set[tuple[str, ...]]:
    seen = {xs}
    queue = [xs]
    while queue:
        z = queue.pop()
        nxt = set(old_closure(z))
        for transported in list(nxt):
            nxt |= apply_O1_anywhere(transported)
        for y in nxt:
            if y not in seen:
                seen.add(y)
                queue.append(y)
    return seen


def O2_outside_G1() -> bool:
    return D2.target not in closure_G1(D2.broken)


# Final causal execution and targeted ablations.
state = transport_apply(O1, D2.broken) if O1 else None
if state is not None and O2:
    state = transport_apply(O2, state)
final_pass = state == D2.target
only_O1 = transport_apply(O1, D2.broken) if O1 else None
only_O2 = transport_apply(O2, D2.broken) if O2 else None
ablate_O2_pass = only_O1 == D2.target
ablate_O1_pass = only_O2 == D2.target


# ---------------------------------------------------------------------------
# Presentation / constructor-grammar invariance.
# ---------------------------------------------------------------------------
grammar_same_class = class_intersection == class_intersection_alt == ({O1} if O1 else set())

ROLE = ("LT", "LE", "AND", "OR")
renaming_checks: list[bool] = []
for perm in product(ROLE, repeat=4):
    if len(set(perm)) < 4:
        continue
    enc = dict(zip(ROLE, perm))
    dec = {v: k for k, v in enc.items()}

    def encode(xs: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(enc.get(x, x) for x in xs)

    a = Case("encoded_source1", "if", encode(S1.broken), encode(S1.target))
    b = Case("encoded_source2", "if", encode(S2.broken), encode(S2.target))
    classes = class_survivors(a, "direct") & class_survivors(b, "direct")
    mapped = {
        CapClass(dec.get(c.src, c.src), dec.get(c.dst, c.dst)) for c in classes
    }
    renaming_checks.append(mapped == {CapClass("LT", "LE")})
encoding_invariance = all(renaming_checks) and len(renaming_checks) == 24


# ---------------------------------------------------------------------------
# Search economics: exhaustive cold two-rewrite reconstruction vs warm audit.
# ---------------------------------------------------------------------------
literals0 = all_literals(D2.broken)
cold_two_rewrite_candidates = sum(
    len(all_literals(op1.apply(D2.broken))) for op1 in literals0
)
warm_calls = len(warm_trace)
compression = cold_two_rewrite_candidates / max(1, warm_calls)


# ---------------------------------------------------------------------------
# Lifecycle: later counterevidence invalidates every frozen scope refinement.
# ---------------------------------------------------------------------------
COUNTER = Case(
    "later_counterevidence",
    "if",
    ("LT", "D", "C", "B"),
    ("LT", "D", "C", "B"),
)


def scope_valid_after_counter(pred) -> bool:
    helps = (S1, S2, H1, D2)
    return (
        all(pred(c.context) for c in helps)
        and not pred(HARM.context)
        and not pred(COUNTER.context)
    )


post_counter_scopes = [
    name
    for name, pred in SCOPE_CANDIDATES.items()
    if scope_valid_after_counter(pred)
]
revoked = len(post_counter_scopes) == 0


gates = {
    "G0_old_closure_obstruction_source1": outside_old_closure(S1) and multiset_obstruction(S1),
    "G1_old_closure_obstruction_source2": outside_old_closure(S2) and multiset_obstruction(S2),
    "G2_literal_identity_does_not_transfer_across_source_positions": len(literal_intersection) == 0 and not heldout_literal_identity_pass,
    "G3_quotient_class_unique_across_sources": class_intersection == {CapClass("LT", "LE")},
    "G4_alternate_constructor_grammar_recovers_same_class": grammar_same_class,
    "G5_24_of_24_token_presentations_recover_same_class": encoding_invariance,
    "G6_scope_is_unique_minimal_and_not_global": SCOPE == "context==if" and not scope_fn(HARM.context),
    "G7_source_distinct_quotient_transport_and_ablation": heldout_quotient_pass and not heldout_ablation_pass,
    "G8_generation2_cold_one_new_class_has_zero_survivors": len(cold_wins) == 0,
    "G9_generation2_after_O1_exposes_unique_O2_class": (not mid_ok) and warm_classes == {CapClass("AND", "OR")},
    "G10_O2_is_outside_G1_semantic_closure": O2_outside_G1(),
    "G11_final_requires_both_classes": final_pass and not ablate_O1_pass and not ablate_O2_pass,
    "G12_warm_search_compresses_cold_two_rewrite_reconstruction": compression > 1.0,
    "G13_later_counterevidence_forces_revocation_under_frozen_scope_grammar": revoked,
}

claim_audit = {
    "developmental_discoverability_depends_on_O1": len(cold_wins) == 0 and len(warm_wins) > 0,
    "strict_O2_raw_meta_language_constructibility_depends_on_O1": strict_O2_not_constructible_cold,
}

core_verdict = "PASS_DISCOVERABILITY_DEPTH" if all(gates.values()) else "FAIL_CORE"
if all(gates.values()) and strict_O2_not_constructible_cold:
    verdict = "PASS_STRICT_SECOND_ORDER_CONSTRUCTIBILITY"
elif all(gates.values()):
    verdict = "PARTIAL_STRICT_CONSTRUCTIBILITY_NOT_ESTABLISHED"
else:
    verdict = "FAIL"

report = {
    "protocol": "CLOSURE_RELATIVE_DEVELOPMENTAL_DEPTH_V1",
    "old_language": {
        "generators": ["cyclic_position_transport"],
        "invariant": "token multiset",
    },
    "generation1": {
        "source1_literal_survivors": [op.__dict__ for op in s1_direct],
        "source2_literal_survivors": [op.__dict__ for op in s2_direct],
        "literal_intersection": len(literal_intersection),
        "quotient_class_intersection": [
            c.__dict__ for c in sorted(class_intersection, key=lambda z: (z.src, z.dst))
        ],
        "selected_class": O1.__dict__ if O1 else None,
        "scope": SCOPE,
        "heldout_literal_identity_pass": heldout_literal_identity_pass,
        "heldout_quotient_transport_pass": heldout_quotient_pass,
    },
    "generation2": {
        "cold_one_new_literal_candidates_tested": len(cold_trace),
        "cold_survivors": len(cold_wins),
        "state_after_O1": list(mid) if mid else None,
        "warm_one_new_literal_candidates_tested": len(warm_trace),
        "warm_survivors": [op.__dict__ for op in warm_wins],
        "O2_class": O2.__dict__ if O2 else None,
        "O2_outside_G1_closure": O2_outside_G1(),
        "final_pass": final_pass,
        "O1_ablated_O2_present_pass": ablate_O1_pass,
        "O2_ablated_O1_present_pass": ablate_O2_pass,
    },
    "invariance": {
        "alternate_grammar": grammar_same_class,
        "token_renamings_passed": sum(renaming_checks),
        "token_renamings_total": len(renaming_checks),
    },
    "economics": {
        "cold_exhaustive_two_rewrite_candidates": cold_two_rewrite_candidates,
        "warm_full_one_rewrite_audit_calls": warm_calls,
        "compression_ratio": compression,
    },
    "lifecycle": {
        "post_counterevidence_valid_scopes": post_counter_scopes,
        "revoked": revoked,
    },
    "gates": gates,
    "claim_audit": claim_audit,
    "core_verdict": core_verdict,
    "verdict": verdict,
    "claim_boundary": (
        "Exact finite model. It establishes closure-relative capability identity, "
        "source-distinct transport, two-generation verifier-dependent discoverability, "
        "semantic closure obstruction for O2, causal ablation, grammar/presentation "
        "robustness, search compression, and revocation. It DOES NOT establish that O2 "
        "was syntactically unconstructible in the raw generic meta-language before O1; "
        "the strict constructibility audit is reported separately."
    ),
}

out = Path(__file__).with_name("RESULT.json")
out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps(report, indent=2, sort_keys=True))
if core_verdict == "FAIL_CORE":
    raise SystemExit(1)
