# Daniel Coordinate-Free Refinement V3

This is the target-independent follow-up to the earlier `Expose(S)` benchmark.

It removes named coordinate-extension candidates entirely. The developmental constructor receives only:

- an opaque finite state set;
- the current parent partition `P0`;
- verifier conflict pairs between currently-indistinguishable states.

It then exhausts all 225 partitions refining `P0` and synthesizes the unique coarsest refinement that separates the conflicts.

Run:

```bash
python reproductions/daniel_coordinate_free_refinement_v3/reproduce.py
```

No dependencies beyond the Python standard library are required.

## Exact result

The complete finite world contains 256 Boolean targets and 65,280 distinct ordered two-episode target pairs.

V3 establishes:

- all 256 targets have a unique coarsest obstruction-repairing quotient;
- 64 distinct quotient regimes are synthesized;
- target counts by quotient size are exactly `4 / 56 / 196` for 2 / 3 / 4 blocks;
- the counts agree with closed-form combinatorics;
- the selector is equivariant under all 1,152 automorphisms of the base partition, for 294,912 exact checks;
- all 65,280 distinct ordered episode pairs are evaluated;
- exactly 2,324 pairs exhibit strict downstream object-language formability growth;
- the 2,324 count agrees with the closed form `168 + 2156`;
- reconstruction of the parent regime restores non-formability for every growth pair;
- complementing verifier labels leaves the obstruction and synthesized regime unchanged in all 256 cases.

## What changed from V2

V2 still supplied:

```text
Expose(S), S subset of {x,y}
```

V3 has no `x`, `y`, `Expose(x)`, or `Expose(y)` operation in the developmental constructor.

The constructor is the generic coordinate-free operation:

```text
RefinePartition(parent_partition, verifier_conflict_relation)
```

and the actual extension instance is synthesized from obstruction structure by exhaustive search over all parent refinements.

## Claim boundary

This is still standard finite quotient / partition-refinement mathematics.

The generic operation `RefinePartition` is supplied by the developmental meta-language. Therefore V3 does **not** show autonomous invention of partition refinement itself or arbitrary new representation kinds.

The stronger thing it does show, compared with V2, is that the successful extension instance is no longer one of a few named target-coordinate schemas selected in advance. It is constructed as an opaque quotient from verifier-certified distinctions.

Read `MATHEMATICAL_NOTE.md` for the exact statement and proof structure.
