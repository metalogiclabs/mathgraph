#!/usr/bin/env python3
"""
Daniel Coordinate-Free Refinement V3

Finite exact benchmark moving one level below the supplied Expose(S) schema.

Scientific setup
----------------
* World W has 8 opaque states. The developmental constructor is NOT told x/y
  coordinate names or an Expose-coordinate operation.
* The base regime is only a partition P0 of those states (two 4-state blocks).
* The verifier emits conflict pairs: currently-indistinguishable states that
  require different Boolean outputs.
* The developmental meta-language contains one generic operation:
      RefinePartition(parent_partition, conflict_relation)
  implemented by exhaustive search over every partition refining P0 and
  selecting the unique coarsest partition that separates all conflicts.
* Every one of the 256 Boolean targets and all 65,280 distinct ordered
  two-episode target pairs are tested.

Claim boundary
--------------
This establishes synthesis of the *extension instance* (a quotient/partition)
from verifier obstruction data without named coordinate-extension candidates.
It remains finite partition refinement under a supplied generic refinement
constructor. It does NOT establish autonomous invention of partition refinement
itself or novelty over standard quotient/partition-refinement mathematics.
"""
from __future__ import annotations

from collections import Counter
from functools import lru_cache
from itertools import permutations, product
import json

# Coordinates are used only to define a readable finite world and the initial
# base partition. The refinement synthesizer below receives only opaque indices,
# P0, and conflict pairs. It never receives coordinate names or values.
W = tuple(product((0, 1), (0, 1), (0, 1)))
N = len(W)
P0 = (
    tuple(i for i, state in enumerate(W) if state[2] == 0),
    tuple(i for i, state in enumerate(W) if state[2] == 1),
)
ALL_TARGETS = tuple(product((False, True), repeat=N))


def canon_partition(partition):
    return tuple(sorted((tuple(sorted(block)) for block in partition), key=lambda b: b))


def set_partitions(items):
    """All set partitions of a small tuple, canonicalized."""
    items = tuple(items)
    if not items:
        return ((),)
    first = items[0]
    out = set()
    for rest in set_partitions(items[1:]):
        out.add(canon_partition(((first,),) + rest))
        for idx in range(len(rest)):
            blocks = [tuple(block) for block in rest]
            blocks[idx] = tuple(sorted((first,) + blocks[idx]))
            out.add(canon_partition(tuple(blocks)))
    return tuple(sorted(out))


# Exhaustive constructor space: every partition that refines P0.
BLOCK_REFINEMENTS = tuple(set_partitions(block) for block in P0)
ALL_REFINEMENTS = tuple(
    sorted(
        {
            canon_partition(left + right)
            for left in BLOCK_REFINEMENTS[0]
            for right in BLOCK_REFINEMENTS[1]
        }
    )
)
assert len(BLOCK_REFINEMENTS[0]) == len(BLOCK_REFINEMENTS[1]) == 15
assert len(ALL_REFINEMENTS) == 225


def block_index(partition):
    idx = {}
    for block_id, block in enumerate(partition):
        for state in block:
            idx[state] = block_id
    assert len(idx) == N
    return idx


def factors_through(target, partition):
    """Target is formable iff constant on each quotient block."""
    return all(len({target[i] for i in block}) <= 1 for block in partition)


def conflict_relation(target, parent=P0):
    """Verifier obstruction: opposite labels inside one current parent block."""
    edges = []
    for block in parent:
        for pos, i in enumerate(block):
            for j in block[pos + 1 :]:
                if target[i] != target[j]:
                    edges.append((i, j))
    return tuple(edges)


def separates_conflicts(partition, conflicts):
    idx = block_index(partition)
    return all(idx[i] != idx[j] for i, j in conflicts)


@lru_cache(maxsize=None)
def synthesize_refinement(conflicts):
    """
    Generic coordinate-free developmental constructor.

    It sees only conflict pairs and the frozen universe of P0-refinements.
    Return the unique coarsest satisfying refinement. Coarseness is measured by
    number of quotient blocks; uniqueness is then verified, not assumed.
    """
    survivors = [p for p in ALL_REFINEMENTS if separates_conflicts(p, conflicts)]
    minimum_blocks = min(len(p) for p in survivors)
    minima = tuple(p for p in survivors if len(p) == minimum_blocks)
    if len(minima) != 1:
        raise AssertionError(f"expected unique coarsest refinement, got {len(minima)}")
    return minima[0]


def synthesize_table(target, partition):
    """Canonical object-language term: a Boolean table on quotient blocks."""
    if not factors_through(target, partition):
        return None
    return tuple((tuple(block), target[block[0]]) for block in partition)


def proper_coarsenings_within_P0(partition):
    """Every strictly coarser P0-refinement from the exhaustive 225-partition universe."""
    fine = block_index(partition)
    out = []
    for candidate in ALL_REFINEMENTS:
        if len(candidate) >= len(partition):
            continue
        coarse = block_index(candidate)
        # partition refines candidate iff states together in partition never cross candidate blocks
        if all(coarse[i] == coarse[j] for block in partition for i in block for j in block):
            out.append(candidate)
    return tuple(out)


# ---------------------------------------------------------------------------
# One-episode exhaustive theorem over all 256 targets.
# ---------------------------------------------------------------------------
SYNTHESIZED = []
BLOCK_COUNT_CLASSIFICATION = Counter()
DISTINCT_PARTITIONS = Counter()
for target in ALL_TARGETS:
    conflicts = conflict_relation(target)
    refinement = synthesize_refinement(conflicts)
    SYNTHESIZED.append(refinement)
    BLOCK_COUNT_CLASSIFICATION[len(refinement)] += 1
    DISTINCT_PARTITIONS[refinement] += 1

    assert factors_through(target, refinement)
    # Strong minimality: no strictly coarser admissible P0-refinement can form target.
    for coarser in proper_coarsenings_within_P0(refinement):
        assert not factors_through(target, coarser)

assert BLOCK_COUNT_CLASSIFICATION == {2: 4, 3: 56, 4: 196}
assert len(DISTINCT_PARTITIONS) == 64
assert set(DISTINCT_PARTITIONS.values()) == {4}

# Closed-form count by number of quotient cells. Each A-fiber independently
# either remains unsplit (2 constant labelings) or is split into two nonempty
# target fibers (14 nonconstant labelings). Across two base fibers:
# 2 blocks: 2*2 = 4
# 3 blocks: 2*(14*2) = 56
# 4 blocks: 14*14 = 196
CLOSED_BLOCK_COUNTS = {2: 4, 3: 56, 4: 196}
assert dict(BLOCK_COUNT_CLASSIFICATION) == CLOSED_BLOCK_COUNTS

# ---------------------------------------------------------------------------
# Coordinate-free equivariance: all 1152 automorphisms of the base partition.
# No x/y names are privileged by the developmental constructor.
# ---------------------------------------------------------------------------
def base_automorphisms():
    b0, b1 = P0
    autos = []
    for swap_blocks in (False, True):
        destinations = (b1, b0) if swap_blocks else (b0, b1)
        for image0 in permutations(destinations[0]):
            for image1 in permutations(destinations[1]):
                mapping = [None] * N
                for source, image in ((b0, image0), (b1, image1)):
                    for s, d in zip(source, image):
                        mapping[s] = d
                autos.append(tuple(mapping))
    assert len(autos) == len(set(autos)) == 1152
    return tuple(autos)


def transport_target(target, automorphism):
    """g.target defined by (g.target)(g(i)) = target(i)."""
    out = [None] * N
    for i, image in enumerate(automorphism):
        out[image] = target[i]
    return tuple(out)


def transport_partition(partition, automorphism):
    return canon_partition(tuple(tuple(automorphism[i] for i in block) for block in partition))


AUTOMORPHISMS = base_automorphisms()
EQUIVARIANCE_CHECKS = 0
for target, refinement in zip(ALL_TARGETS, SYNTHESIZED):
    for g in AUTOMORPHISMS:
        transformed_target = transport_target(target, g)
        transformed_refinement = synthesize_refinement(conflict_relation(transformed_target))
        assert transformed_refinement == transport_partition(refinement, g)
        EQUIVARIANCE_CHECKS += 1
assert EQUIVARIANCE_CHECKS == 256 * 1152 == 294912

# ---------------------------------------------------------------------------
# Two-episode exhaustive audit over every distinct ordered pair.
# ---------------------------------------------------------------------------
pair_total = 0
strict_growth_pairs = 0
strict_growth_by_parent_blocks = Counter()
parent_replay_checks = 0
for i, p1 in enumerate(ALL_TARGETS):
    developed = SYNTHESIZED[i]
    for j, p2 in enumerate(ALL_TARGETS):
        if i == j:
            continue
        pair_total += 1
        cold = synthesize_table(p2, P0)
        warm = synthesize_table(p2, developed)
        if cold is None and warm is not None:
            strict_growth_pairs += 1
            strict_growth_by_parent_blocks[len(developed)] += 1

            # Counterfactual parent-regime reconstruction/replay.
            reconstructed_parent = canon_partition(P0)
            assert synthesize_table(p2, reconstructed_parent) is None
            parent_replay_checks += 1

assert pair_total == 256 * 255 == 65280

# Closed form. For an episode-1 refinement with k quotient blocks, 2^k target
# functions are warm-formable. Four are already base-formable and p1 itself is
# excluded by the distinct-pair protocol. Thus each non-base p1 contributes
# 2^k - 4 - 1 strict downstream targets.
CLOSED_PAIR_COUNTS = {
    3: 56 * ((2**3) - 4 - 1),
    4: 196 * ((2**4) - 4 - 1),
}
assert CLOSED_PAIR_COUNTS == {3: 168, 4: 2156}
assert dict(strict_growth_by_parent_blocks) == CLOSED_PAIR_COUNTS
assert strict_growth_pairs == sum(CLOSED_PAIR_COUNTS.values()) == 2324
assert parent_replay_checks == strict_growth_pairs

# Negative control: exact complement has identical verifier conflict relation,
# therefore must synthesize exactly the same regime. The representation depends
# on obstruction structure, not which Boolean label is called true.
COMPLEMENT_CHECKS = 0
for target, refinement in zip(ALL_TARGETS, SYNTHESIZED):
    complement = tuple(not b for b in target)
    assert conflict_relation(complement) == conflict_relation(target)
    assert synthesize_refinement(conflict_relation(complement)) == refinement
    COMPLEMENT_CHECKS += 1
assert COMPLEMENT_CHECKS == 256

result = {
    "protocol": "DANIEL_COORDINATE_FREE_REFINEMENT_V3",
    "verdict": "PASS_COORDINATE_FREE_OBSTRUCTION_DRIVEN_REGIME_SYNTHESIS",
    "world": {
        "opaque_states": N,
        "base_blocks": len(P0),
        "all_boolean_targets": len(ALL_TARGETS),
        "all_distinct_ordered_pairs": pair_total,
    },
    "constructor": {
        "named_coordinate_extensions_available": False,
        "generic_meta_operation": "RefinePartition(parent_partition, verifier_conflict_relation)",
        "all_P0_refinements_exhausted": len(ALL_REFINEMENTS),
        "generic_refinement_schema_supplied": True,
        "schema_autonomously_invented": False,
    },
    "one_episode": {
        "all_targets_tested": 256,
        "block_count_classification": dict(BLOCK_COUNT_CLASSIFICATION),
        "closed_form_block_counts": CLOSED_BLOCK_COUNTS,
        "distinct_synthesized_regimes": len(DISTINCT_PARTITIONS),
        "each_regime_induced_by_targets": sorted(set(DISTINCT_PARTITIONS.values())),
        "unique_coarsest_refinement_for_all_targets": True,
        "base_partition_automorphisms": len(AUTOMORPHISMS),
        "equivariance_checks": EQUIVARIANCE_CHECKS,
        "complement_obstruction_invariance_checks": COMPLEMENT_CHECKS,
    },
    "two_episode": {
        "all_distinct_pairs_tested": pair_total,
        "strict_downstream_formability_growth_pairs": strict_growth_pairs,
        "strict_growth_by_episode1_regime_block_count": dict(strict_growth_by_parent_blocks),
        "closed_form_pair_counts": CLOSED_PAIR_COUNTS,
        "counterfactual_parent_replay_checks": parent_replay_checks,
    },
    "claim": (
        "Across the complete finite target universe, verifier conflict relations synthesize 64 distinct "
        "coordinate-free quotient regimes by exhaustive selection of the unique coarsest P0-refinement. "
        "The selector is equivariant under all 1,152 automorphisms of the base partition. Across all 65,280 "
        "distinct ordered episode pairs, 2,324 exhibit strict downstream formability growth; reconstruction "
        "of the parent regime restores non-formability. Enumeration agrees with closed-form combinatorics."
    ),
    "boundary": (
        "V3 removes named Expose-coordinate candidates and synthesizes the extension instance itself from "
        "verified obstruction structure. The generic operation of partition refinement remains supplied. "
        "This is standard finite quotient/partition refinement, not evidence that the system invented the "
        "refinement schema or a novel mathematical formalism."
    ),
}

print(json.dumps(result, indent=2, sort_keys=True))
