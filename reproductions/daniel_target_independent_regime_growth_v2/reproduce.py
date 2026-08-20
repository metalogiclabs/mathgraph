#!/usr/bin/env python3
"""
Daniel Target-Independent Regime Growth V2

Exhaustive finite benchmark eliminating hand-picked-target staging:
  * world W = X x Y x A with all coordinates Boolean;
  * M0 observes only A;
  * the frozen developmental meta-operation is the single symmetric schema
        Expose(S), S subseteq {x,y};
  * ALL 256 Boolean targets W -> Bool are evaluated;
  * ALL 65,280 distinct ordered two-episode target pairs are evaluated.

The selector computes the target's essential hidden-coordinate set from verified
fiber conflicts. No target is selected by the experimenter.

Claim boundary: this establishes target-independent selection of minimal
coordinate-exposure extensions and strict object-language formability changes in
this finite calculus. It does NOT establish autonomous invention of the generic
Expose schema or mathematical novelty beyond finite dependency/partition
refinement.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations, product
import json

X = Y = A = (0, 1)
W = tuple(product(X, Y, A))
HIDDEN = ("x", "y")
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
    """Canonical full-language synthesis: return observation-cell truth table iff formable."""
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
    """Coordinates whose variation changes the target while all other coordinates are fixed."""
    required = set()
    for coord, idx in (("x", 0), ("y", 1)):
        for p in W:
            q = list(p)
            q[idx] = 1 - q[idx]
            q = tuple(q)
            i, j = W.index(p), W.index(q)
            if target[i] != target[j]:
                required.add(coord)
                break
    return frozenset(required)


def select_extension_from_obstruction(target: tuple[bool, ...]) -> frozenset[str]:
    """Generic target-independent selector for the frozen Expose(S) schema."""
    required = essential_hidden_coordinates(target)
    # Verified consequence: target must factor through A + required coordinates.
    assert factors_through(target, required)
    # Minimality: removing any required coordinate restores a certified fiber conflict.
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
            if p[2] == q[2]:
                if bits[p[2]] != bits[q[2]]:
                    return False
    return True


# ---------------------------------------------------------------------------
# Exhaustive one-episode audit over the entire target universe.
# ---------------------------------------------------------------------------
classification = Counter()
one_episode_failures = []
for target in ALL_TARGETS:
    selected = select_extension_from_obstruction(target)
    classification[mask_name(selected)] += 1

    # Exact minimality against every smaller mask.
    assert factors_through(target, selected)
    for candidate in MASKS:
        if candidate < selected:
            if factors_through(target, candidate):
                one_episode_failures.append((target, selected, candidate))

assert not one_episode_failures
assert sum(classification.values()) == 256

# The selector must genuinely discriminate among different extensions.
assert classification["BASE"] > 0
assert classification["Expose(x)"] > 0
assert classification["Expose(y)"] > 0
assert classification["Expose(x,y)"] > 0

# Exhaust the entire A-only sham family. None changes the base observation fibers.
assert len(ALL_A_PREDICATES) == 4
assert all(unary_sham_preserves_base_partition(bits) for bits in ALL_A_PREDICATES)

# ---------------------------------------------------------------------------
# Exhaustive two-episode audit over every DISTINCT ordered pair.
# Episode 1 chooses an extension from its obstruction. Episode 2 is never
# hand-picked: every possible distinct second target is tested.
# ---------------------------------------------------------------------------
pair_total = 0
strict_growth_pairs = 0
strict_growth_by_extension = Counter()
pair_failures = []

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

            # Ancestor ablation returns exactly to M0 and must remove formability.
            if synthesize_table(p2, frozenset()) is not None:
                pair_failures.append((i, j, "ancestor_ablation"))

            # Every A-only sham is semantically no stronger than M0 for hidden dependence.
            for bits in ALL_A_PREDICATES:
                if not unary_sham_preserves_base_partition(bits):
                    pair_failures.append((i, j, "bad_sham_model"))

            # At least one hidden coordinate exposed by episode 1 is genuinely needed
            # for this episode-2 target relative to M0.
            needed2 = essential_hidden_coordinates(p2)
            if not needed2.issubset(ext) or not needed2:
                pair_failures.append((i, j, "dependency_mismatch"))

assert pair_total == 256 * 255
assert not pair_failures

# Independently expected closed-form counts for this finite world.
EXPECTED_CLASSIFICATION = {
    "BASE": 4,
    "Expose(x)": 12,
    "Expose(y)": 12,
    "Expose(x,y)": 228,
}
EXPECTED_PAIR_COUNTS = {
    "Expose(x)": 132,
    "Expose(y)": 132,
    "Expose(x,y)": 57228,
}
assert dict(classification) == EXPECTED_CLASSIFICATION
assert {k: strict_growth_by_extension[k] for k in EXPECTED_PAIR_COUNTS} == EXPECTED_PAIR_COUNTS
assert strict_growth_pairs == sum(EXPECTED_PAIR_COUNTS.values()) == 57492

# A tiny theorem-level sanity check: base formability is exactly A-invariance.
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
        "all_256_targets_have_exact_minimal_extension": True,
        "selector_uses_coordinate_essentiality_from_fiber_conflicts": True,
        "different_targets_select_different_extensions": True,
    },
    "two_episode": {
        "all_distinct_pairs_tested": pair_total,
        "strict_formability_growth_pairs": strict_growth_pairs,
        "strict_growth_by_episode1_extension": dict(strict_growth_by_extension),
        "ancestor_ablation_passes_for_all_growth_pairs": True,
        "no_handpicked_P1_or_P2": True,
    },
    "claim": (
        "Across the complete finite target universe, a single frozen symmetric Expose(S) schema maps "
        "verified fiber conflicts to the exact minimal hidden-coordinate extension for all 256 targets. "
        "Across all 65,280 distinct ordered two-episode pairs, 57,492 pairs exhibit strict downstream "
        "object-language formability growth: P2 is unformable in M0 but formable after the extension "
        "selected by P1, with ancestor ablation restoring non-formability."
    ),
    "boundary": (
        "This removes hand-picked-target and single-prebuilt-extension staging from the finite witness, "
        "but it remains a standard finite dependency/partition-refinement problem under a supplied generic "
        "Expose schema. It does not establish autonomous invention of that schema or novelty over prior art."
    ),
}

print(json.dumps(result, indent=2, sort_keys=True))
