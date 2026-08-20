#!/usr/bin/env python3
"""
Daniel Target-Independent Regime Growth V2.1

Repairs two audit findings from V2:
  * sham controls are tested by explicit observation-partition equality and synthesis;
  * "ancestor ablation" is replaced by explicit parent-regime reconstruction and replay.

The result remains an exact finite theorem/certificate, not an empirical causal trial.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import product
import json

X = Y = A = (0, 1)
W = tuple(product(X, Y, A))
MASKS = (frozenset(), frozenset({"x"}), frozenset({"y"}), frozenset({"x", "y"}))
ALL_TARGETS = tuple(product((False, True), repeat=len(W)))
ALL_A_PREDICATES = tuple(product((False, True), repeat=len(A)))


@dataclass(frozen=True)
class Regime:
    exposed: frozenset[str]
    sham_a_predicate: tuple[bool, ...] | None = None

    def observe(self, state: tuple[int, int, int]) -> tuple[int | bool, ...]:
        x, y, a = state
        out: list[int | bool] = []
        if "x" in self.exposed:
            out.append(x)
        if "y" in self.exposed:
            out.append(y)
        out.append(a)
        if self.sham_a_predicate is not None:
            out.append(self.sham_a_predicate[a])
        return tuple(out)


def base_regime() -> Regime:
    return Regime(frozenset())


def extend(parent: Regime, coords: frozenset[str]) -> Regime:
    assert parent.sham_a_predicate is None
    return Regime(parent.exposed | coords)


def reconstruct_parent(_: Regime) -> Regime:
    """Counterfactual removal of episode-1 extension: reconstruct frozen M0."""
    return base_regime()


def sham_regime(bits: tuple[bool, ...]) -> Regime:
    return Regime(frozenset(), sham_a_predicate=bits)


def same_observation_partition(r1: Regime, r2: Regime) -> bool:
    for p in W:
        for q in W:
            if (r1.observe(p) == r1.observe(q)) != (r2.observe(p) == r2.observe(q)):
                return False
    return True


def factors_through(target: tuple[bool, ...], regime: Regime) -> bool:
    seen: dict[tuple[int | bool, ...], bool] = {}
    for state, value in zip(W, target):
        key = regime.observe(state)
        if key in seen and seen[key] != value:
            return False
        seen[key] = value
    return True


def synthesize_table(target: tuple[bool, ...], regime: Regime):
    if not factors_through(target, regime):
        return None
    table: dict[tuple[int | bool, ...], bool] = {}
    for state, value in zip(W, target):
        table[regime.observe(state)] = value
    return tuple(sorted(table.items()))


def fiber_conflicts(target: tuple[bool, ...], regime: Regime):
    out = []
    for i, p in enumerate(W):
        for j in range(i + 1, len(W)):
            q = W[j]
            if regime.observe(p) == regime.observe(q) and target[i] != target[j]:
                out.append((p, q))
    return tuple(out)


def essential_hidden_coordinates(target: tuple[bool, ...]) -> frozenset[str]:
    required = set()
    index = {s: i for i, s in enumerate(W)}
    for coord, idx in (("x", 0), ("y", 1)):
        for p in W:
            q = list(p)
            q[idx] = 1 - q[idx]
            q = tuple(q)
            if target[index[p]] != target[index[q]]:
                required.add(coord)
                break
    return frozenset(required)


def select_extension_from_obstruction(target: tuple[bool, ...]) -> frozenset[str]:
    required = essential_hidden_coordinates(target)
    selected = extend(base_regime(), required)
    assert factors_through(target, selected)
    for c in required:
        smaller = extend(base_regime(), frozenset(required - {c}))
        assert not factors_through(target, smaller)
        assert fiber_conflicts(target, smaller)
    return required


def mask_name(mask: frozenset[str]) -> str:
    return "BASE" if not mask else "Expose(" + ",".join(sorted(mask)) + ")"


def swap_xy_target(target: tuple[bool, ...]) -> tuple[bool, ...]:
    index = {s: i for i, s in enumerate(W)}
    return tuple(target[index[(y, x, a)]] for x, y, a in W)


def swap_mask(mask: frozenset[str]) -> frozenset[str]:
    return frozenset("y" if c == "x" else "x" for c in mask)


M0 = base_regime()

# Real sham controls: each q(A) is installed as an extra observable feature.
# Since q(A) is determined by A, the induced observation partition must equal M0's.
SHAM_REGIMES = tuple(sham_regime(bits) for bits in ALL_A_PREDICATES)
assert len(SHAM_REGIMES) == 4
assert all(same_observation_partition(M0, sham) for sham in SHAM_REGIMES)
for target in ALL_TARGETS:
    cold = synthesize_table(target, M0)
    for sham in SHAM_REGIMES:
        assert (synthesize_table(target, sham) is not None) == (cold is not None)

# Exhaustive one-episode classification.
classification = Counter()
for target in ALL_TARGETS:
    ext = select_extension_from_obstruction(target)
    classification[mask_name(ext)] += 1
    selected = extend(M0, ext)
    assert factors_through(target, selected)
    for candidate in MASKS:
        if candidate < ext:
            assert not factors_through(target, extend(M0, candidate))
    swapped = swap_xy_target(target)
    assert select_extension_from_obstruction(swapped) == swap_mask(ext)

closed_base = 2 ** len(A)
closed_x = 2 ** (len(X) * len(A)) - closed_base
closed_y = 2 ** (len(Y) * len(A)) - closed_base
closed_xy = 2 ** len(W) - 2 ** (len(Y) * len(A)) - 2 ** (len(X) * len(A)) + closed_base
CLOSED_CLASSIFICATION = {
    "BASE": closed_base,
    "Expose(x)": closed_x,
    "Expose(y)": closed_y,
    "Expose(x,y)": closed_xy,
}
assert dict(classification) == CLOSED_CLASSIFICATION == {
    "BASE": 4, "Expose(x)": 12, "Expose(y)": 12, "Expose(x,y)": 228
}

# Exhaustive two-episode audit.
pair_total = 0
strict_growth_pairs = 0
strict_growth_by_extension = Counter()
parent_replay_checks = 0
sham_replay_checks = 0

for i, p1 in enumerate(ALL_TARGETS):
    ext_mask = select_extension_from_obstruction(p1)
    developed = extend(M0, ext_mask)
    reconstructed_parent = reconstruct_parent(developed)
    assert reconstructed_parent == M0

    for j, p2 in enumerate(ALL_TARGETS):
        if i == j:
            continue
        pair_total += 1
        cold = synthesize_table(p2, M0)
        warm = synthesize_table(p2, developed)

        if cold is None and warm is not None:
            strict_growth_pairs += 1
            strict_growth_by_extension[mask_name(ext_mask)] += 1

            # Counterfactual parent-regime replay: remove episode-1 extension,
            # reconstruct M0 as a distinct regime value, rerun unchanged synthesizer.
            parent_replay_checks += 1
            assert synthesize_table(p2, reconstructed_parent) is None

            # Explicit sham-regime replay, not a partition predicate shortcut.
            for sham in SHAM_REGIMES:
                sham_replay_checks += 1
                assert synthesize_table(p2, sham) is None

            needed2 = essential_hidden_coordinates(p2)
            assert needed2 and needed2.issubset(ext_mask)

assert pair_total == 256 * 255 == 65280
closed_pair_x = closed_x * (closed_x - 1)
closed_pair_y = closed_y * (closed_y - 1)
closed_pair_xy = closed_xy * ((256 - closed_base) - 1)
CLOSED_PAIR_COUNTS = {
    "Expose(x)": closed_pair_x,
    "Expose(y)": closed_pair_y,
    "Expose(x,y)": closed_pair_xy,
}
assert {k: strict_growth_by_extension[k] for k in CLOSED_PAIR_COUNTS} == CLOSED_PAIR_COUNTS
assert CLOSED_PAIR_COUNTS == {"Expose(x)": 132, "Expose(y)": 132, "Expose(x,y)": 57228}
assert strict_growth_pairs == 57492
assert parent_replay_checks == strict_growth_pairs
assert sham_replay_checks == strict_growth_pairs * len(SHAM_REGIMES)

result = {
    "protocol": "DANIEL_TARGET_INDEPENDENT_REGIME_GROWTH_V2_1",
    "verdict": "PASS_EXHAUSTIVE_TARGET_INDEPENDENT_REGIME_SELECTION_REPAIRED_CONTROLS",
    "one_episode": {
        "classification": dict(classification),
        "closed_form_classification": CLOSED_CLASSIFICATION,
        "x_y_equivariance": "256/256",
    },
    "two_episode": {
        "all_distinct_pairs_tested": pair_total,
        "strict_formability_growth_pairs": strict_growth_pairs,
        "strict_growth_by_episode1_extension": dict(strict_growth_by_extension),
        "closed_form_pair_counts": CLOSED_PAIR_COUNTS,
        "parent_regime_replay_checks": parent_replay_checks,
        "explicit_sham_regime_replay_checks": sham_replay_checks,
    },
    "controls": {
        "A_only_sham_regimes": len(SHAM_REGIMES),
        "all_sham_partitions_equal_base": all(same_observation_partition(M0, s) for s in SHAM_REGIMES),
        "ablation_wording": "counterfactual parent-regime reconstruction/replay; not an empirical intervention",
    },
    "boundary": (
        "Exact finite dependency/partition-refinement theorem under supplied generic Expose(S). "
        "Repairs V2's vacuous sham implementation and clarifies parent replay as a mathematical "
        "counterfactual, not empirical ablation. Does not establish autonomous schema invention."
    ),
}
print(json.dumps(result, indent=2, sort_keys=True))
