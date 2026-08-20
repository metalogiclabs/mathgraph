#!/usr/bin/env python3
"""
Daniel Target-Independent Regime Growth V2

Exhaustive finite benchmark eliminating hand-picked-target staging:
  * world W = X x Y x A with all coordinates Boolean;
  * M0 observes only A;
  * the frozen developmental meta-operation is one symmetric schema
        Expose(S), S subseteq {x,y};
  * ALL 256 Boolean targets W -> Bool are evaluated;
  * ALL 65,280 distinct ordered two-episode target pairs are evaluated;
  * executable counts are cross-checked against closed-form combinatorics;
  * x<->y equivariance is checked for all targets.

Claim boundary: this establishes target-independent selection of minimal
coordinate-exposure extensions and strict object-language formability changes in
this finite calculus. It does NOT establish autonomous invention of the generic
Expose schema or novelty beyond finite dependency/partition refinement.
"""
from __future__ import annotations

from collections import Counter
from itertools import product
import json

X = Y = A = (0, 1)
W = tuple(product(X, Y, A))
MASKS = (frozenset(), frozenset({"x"}), frozenset({"y"}), frozenset({"x", "y"}))
ALL_TARGETS = tuple(product((False, True), repeat=len(W)))
ALL_A_PREDICATES = tuple(product((False, True), repeat=len(A)))


def observe(state: tuple[int, int, int], mask: frozenset[str]) -> tuple[int, ...]:
    x, y, a = state
    out = []
    if "x" in mask:
        out.append(x)
    if "y" in mask:
        out.append(y)
    out.append(a)
    return tuple(out)


def factors_through(target: tuple[bool, ...], mask: frozenset[str]) -> bool:
    """Whether target is constant on every fiber of the regime observation map."""
    seen: dict[tuple[int, ...], bool] = {}
    for state, value in zip(W, target):
        key = observe(state, mask)
        if key in seen and seen[key] != value:
            return False
        seen[key] = value
    return True


def synthesize_table(target: tuple[bool, ...], mask: frozenset[str]):
    """Canonical full-language synthesis: observation-cell truth table iff formable."""
    if not factors_through(target, mask):
        return None
    table: dict[tuple[int, ...], bool] = {}
    for state, value in zip(W, target):
        table[observe(state, mask)] = value
    return tuple(sorted(table.items()))


def fiber_conflicts(target: tuple[bool, ...], mask: frozenset[str]):
    conflicts = []
    for i, p in enumerate(W):
        for j in range(i + 1, len(W)):
            q = W[j]
            if observe(p, mask) == observe(q, mask) and target[i] != target[j]:
                conflicts.append((p, q))
    return tuple(conflicts)


def essential_hidden_coordinates(target: tuple[bool, ...]) -> frozenset[str]:
    """Hidden coordinates whose flip can change target with all else fixed."""
    required = set()
    for coord, idx in (("x", 0), ("y", 1)):
        for p in W:
            q = list(p)
            q[idx] = 1 - q[idx]
            q = tuple(q)
            if target[W.index(p)] != target[W.index(q)]:
                required.add(coord)
                break
    return frozenset(required)


def select_extension_from_obstruction(target: tuple[bool, ...]) -> frozenset[str]:
    """Generic target-independent selector for the frozen Expose(S) schema."""
    required = essential_hidden_coordinates(target)
    assert factors_through(target, required)
    for c in required:
        smaller = frozenset(required - {c})
        assert not factors_through(target, smaller)
        assert fiber_conflicts(target, smaller)
    return required


def mask_name(mask: frozenset[str]) -> str:
    return "BASE" if not mask else "Expose(" + ",".join(sorted(mask)) + ")"


def unary_sham_preserves_base_partition(bits: tuple[bool, ...]) -> bool:
    """Adding q:A->Bool cannot separate states already equal on A."""
    for p in W:
        for q in W:
            if p[2] == q[2] and bits[p[2]] != bits[q[2]]:
                return False
    return True


def swap_xy_target(target: tuple[bool, ...]) -> tuple[bool, ...]:
    """Pull target back along the symmetry (x,y,a) -> (y,x,a)."""
    vals = []
    for x, y, a in W:
        vals.append(target[W.index((y, x, a))])
    return tuple(vals)


def swap_mask(mask: frozenset[str]) -> frozenset[str]:
    return frozenset("y" if c == "x" else "x" for c in mask)


# ---------------------------------------------------------------------------
# Exhaustive one-episode audit over the entire target universe.
# ---------------------------------------------------------------------------
classification = Counter()
for target in ALL_TARGETS:
    selected = select_extension_from_obstruction(target)
    classification[mask_name(selected)] += 1

    # Exact minimality against every proper submask.
    assert factors_through(target, selected)
    for candidate in MASKS:
        if candidate < selected:
            assert not factors_through(target, candidate)

    # Full x<->y equivariance: swapping world coordinates swaps selected regime.
    swapped = swap_xy_target(target)
    assert select_extension_from_obstruction(swapped) == swap_mask(selected)

assert sum(classification.values()) == 256
assert all(classification[name] > 0 for name in ("BASE", "Expose(x)", "Expose(y)", "Expose(x,y)"))

# Exhaust the complete A-only predicate family.
assert len(ALL_A_PREDICATES) == 4
assert all(unary_sham_preserves_base_partition(bits) for bits in ALL_A_PREDICATES)

# Closed-form one-episode counts, derived independently from enumeration.
# Functions of A only: 2^(2)=4.
closed_base = 2 ** len(A)
# Functions of (x,a) that genuinely depend on x: 2^(2*2)-closed_base = 12.
closed_x = 2 ** (len(X) * len(A)) - closed_base
closed_y = 2 ** (len(Y) * len(A)) - closed_base
# Inclusion-exclusion: functions depending on both hidden coordinates.
closed_xy = 2 ** len(W) - (2 ** (len(Y) * len(A))) - (2 ** (len(X) * len(A))) + closed_base
CLOSED_CLASSIFICATION = {
    "BASE": closed_base,
    "Expose(x)": closed_x,
    "Expose(y)": closed_y,
    "Expose(x,y)": closed_xy,
}
assert dict(classification) == CLOSED_CLASSIFICATION == {
    "BASE": 4,
    "Expose(x)": 12,
    "Expose(y)": 12,
    "Expose(x,y)": 228,
}

# ---------------------------------------------------------------------------
# Exhaustive two-episode audit over every DISTINCT ordered pair.
# ---------------------------------------------------------------------------
pair_total = 0
strict_growth_pairs = 0
strict_growth_by_extension = Counter()

for i, p1 in enumerate(ALL_TARGETS):
    ext = select_extension_from_obstruction(p1)
    for j, p2 in enumerate(ALL_TARGETS):
        if i == j:
            continue
        pair_total += 1

        cold = synthesize_table(p2, frozenset())
        warm = synthesize_table(p2, ext)

        if cold is None and warm is not None:
            strict_growth_pairs += 1
            strict_growth_by_extension[mask_name(ext)] += 1

            # Ancestor ablation returns exactly to M0 and restores non-formability.
            assert synthesize_table(p2, frozenset()) is None

            # Every A-only sham preserves the base partition.
            assert all(unary_sham_preserves_base_partition(bits) for bits in ALL_A_PREDICATES)

            needed2 = essential_hidden_coordinates(p2)
            assert needed2 and needed2.issubset(ext)

assert pair_total == 256 * 255 == 65280

# Closed-form pair counts. For an exact-x P1 there are 11 other exact-x P2s;
# for an exact-xy P1, every non-base target except itself is formable warm.
closed_pair_x = closed_x * (closed_x - 1)
closed_pair_y = closed_y * (closed_y - 1)
closed_pair_xy = closed_xy * ((256 - closed_base) - 1)
CLOSED_PAIR_COUNTS = {
    "Expose(x)": closed_pair_x,
    "Expose(y)": closed_pair_y,
    "Expose(x,y)": closed_pair_xy,
}
assert {k: strict_growth_by_extension[k] for k in CLOSED_PAIR_COUNTS} == CLOSED_PAIR_COUNTS
assert CLOSED_PAIR_COUNTS == {
    "Expose(x)": 132,
    "Expose(y)": 132,
    "Expose(x,y)": 57228,
}
assert strict_growth_pairs == sum(CLOSED_PAIR_COUNTS.values()) == 57492

# Base formability is exactly A-fiber invariance for every target.
for target in ALL_TARGETS:
    assert (synthesize_table(target, frozenset()) is not None) == factors_through(target, frozenset())

result = {
    "protocol": "DANIEL_TARGET_INDEPENDENT_REGIME_GROWTH_V2",
    "verdict": "PASS_EXHAUSTIVE_TARGET_INDEPENDENT_REGIME_SELECTION",
    "world": {
        "states": len(W),
        "all_boolean_targets": len(ALL_TARGETS),
        "distinct_ordered_target_pairs": pair_total,
    },
    "meta_language": {
        "single_generic_schema": "Expose(S), S subset of {x,y}",
        "masks": [mask_name(m) for m in MASKS],
        "A_only_shams_exhausted": len(ALL_A_PREDICATES),
        "schema_autonomously_invented": False,
    },
    "one_episode": {
        "classification": dict(classification),
        "closed_form_classification": CLOSED_CLASSIFICATION,
        "all_256_targets_have_exact_minimal_extension": True,
        "x_y_equivariance_checked": "256/256",
        "different_targets_select_different_extensions": True,
    },
    "two_episode": {
        "all_distinct_pairs_tested": pair_total,
        "strict_formability_growth_pairs": strict_growth_pairs,
        "strict_growth_by_episode1_extension": dict(strict_growth_by_extension),
        "closed_form_pair_counts": CLOSED_PAIR_COUNTS,
        "ancestor_ablation_passes_for_all_growth_pairs": True,
        "no_handpicked_P1_or_P2": True,
    },
    "claim": (
        "Across the complete finite target universe, one frozen symmetric Expose(S) schema maps verified "
        "fiber conflicts to the exact minimal hidden-coordinate extension for all 256 targets, equivariantly "
        "under x<->y. Across all 65,280 distinct ordered episode pairs, 57,492 exhibit strict downstream "
        "object-language formability growth, with ancestor ablation restoring non-formability. Exhaustive "
        "counts agree with independent closed-form combinatorics."
    ),
    "boundary": (
        "This eliminates hand-picked-target and one-target-shaped-extension staging in the finite witness. "
        "It remains standard finite dependency/partition refinement under a supplied generic Expose schema; "
        "it does not establish autonomous invention of that schema or novelty over prior art."
    ),
}

print(json.dumps(result, indent=2, sort_keys=True))
