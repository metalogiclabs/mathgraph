# V8 precommit — obstruction constrains a version space, not always one regime

Frozen before the n=6 exhaustive result is computed.

## Question

When the verifier returns only a sparse incompatibility graph rather than the complete unequal-output relation used in V3–V7, does the obstruction uniquely determine the coarsest admissible refinement?

## Frozen world

One parent block with 6 opaque states.

Enumerate all `2^(6 choose 2) = 32,768` undirected simple incompatibility graphs `Omega`.

Enumerate all set partitions of the 6 states (`Bell(6)=203`).

A partition is admissible iff no incompatibility edge has both endpoints in the same block.

For each obstruction graph:

1. exhaust all 203 partitions;
2. find the minimum number of blocks among admissible partitions;
3. retain every admissible partition at that minimum;
4. record whether the coarsest/minimum-block repair is unique or ambiguous;
5. independently verify that the minimum block count equals the graph chromatic number by exhaustive color assignment;
6. verify that the retained minimum partitions are exactly the optimal proper colorings modulo color-name permutation.

## PASS condition

This experiment has no desired positive direction. It passes as an audit if all 32,768 obstruction graphs are classified consistently and the partition and coloring computations agree exactly.

The result may show uniqueness, ambiguity, or a mixture. No threshold is precommitted.

## Claim boundary

This is standard finite graph coloring / partition mathematics. Its purpose is to test a Developmental Intelligence assumption: whether verified obstruction can mathematically determine the next representation, or only constrain the admissible extension space. It does not claim novelty of graph coloring or partition theory.
