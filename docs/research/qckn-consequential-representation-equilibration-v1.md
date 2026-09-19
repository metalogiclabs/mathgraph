# QCKN Consequential Representation Equilibration V1

**Status:** executable bounded bidirectional qualification  
**Host:** `metalogiclabs/mathgraph`  
**Branch:** `qckn-consequential-representation-equilibration-v1`

## Question

Can one consequence-governed representation operator move in either direction—refining a state space that is too coarse and coarsening one that is too fine—based only on a complete frozen protected-consequence map, and can the change be injected by Flash after work has already begun?

## Candidate operator

For a finite carrier `X` and a complete frozen protected consequence map `c : X -> Y`, define

[
E_c(x,y) iff c(x)=c(y).
]

The V1 equilibration operator replaces the current representation by exactly `E_c`.

This automatically selects a direction relative to the current representation:

- **REFINE** when the current quotient merges states with different protected consequences;
- **COARSEN** when the current representation distinguishes states with identical protected consequences;
- **EQUAL** when already at the exact consequence kernel;
- **REPARTITION** when neither representation contains the other.

V1 qualifies only the comparable REFINE and COARSEN cases.

This is **not** a modification of frozen QCK/MSI conservative refinement semantics. It is a QCKN-level candidate operator with a stronger snapshot contract. Coarsening is permitted only because the protected consequence set is complete and frozen for the declared finite world.

## World A — finite circuit complexity: too coarse

Pinned source:

- `heathsanchez/test@4df88a272926126b895c2fb6220c56012949df05`
- P-vs-NP finite signal evidence blob `b5781dd62f53fdaaeb32a703bbc7c13977f0e19e`

The old representation is the existing 12-scalar structural signature.

It merges `0x8f` and `0xea`, although their exact NAND sizes are 2 and 3. It also merges two projection functions with exact size 0.

The complete protected consequence map is exact NAND size on the four retained functions.

Therefore the exact consequence kernel strictly **refines** the old representation.

Flash arm:

1. the circuit target tests six scalar diagnostics;
2. all six fail to distinguish the colliding pair;
3. the equilibration operator arrives;
4. exact finite authority computes the consequence kernel;
5. the target refines immediately.

Controls: cold, raw history, discrete over-fine sham, and ablation.

## World B — Lean LocalDef cache identity: too fine

Pinned source:

- `heathsanchez/lean-kernel-arena@919937fb4a58becfb31ad7cbcce9351b601d8e11`
- `experiments/localdef-semantic-context-cache.mjs` Git blob `b4ad942b7a12772044f9edeba8f86051e0ba8eca`

The pinned experiment states the relevant representational defect directly: LocalDef wrapper objects are freshly allocated, so wrapper object identity can distinguish contexts even when the exact LocalDef type and exact value term are unchanged.

Its candidate semantic key replaces only that transient wrapper identity:

[
	ext{LocalDef wrapper id}
quad	oquad
(	ext{exact type object id}, 	ext{exact value object id}).
]

The V1 finite target model instantiates eight fresh wrappers belonging to two exact `(type,value)` consequence classes.

Current wrapper-identity representation: **8 classes**.

Exact consequence kernel: **2 classes**.

Therefore the same equilibration operator strictly **coarsens** this world.

Matched cache schedule:

- COLD: 8 misses / 0 hits;
- WARM: 2 misses / 6 hits;
- FLASH after three queries: 3 misses / 5 later hits;
- RAW_HISTORY: 8 misses;
- SHAM_ALL_MERGED: rejected because it merges the two distinct exact consequence classes;
- ABLATION: 8 misses.

CI separately checks the pinned Lean source and executes the retained LocalDef semantic-context experiment. The finite cache model is a qualification of the exact key semantics, not a claim that these eight wrappers reproduce every Lean workload.

## Scientific pass

V1 passes only if:

1. one and the same exact consequence-kernel operator chooses REFINE for the circuit world and COARSEN for the Lean world;
2. the exact P-vs-NP collision reproduces;
3. circuit Flash resolves after six failed scalar checks;
4. circuit cold remains unresolved after all twelve checks;
5. the circuit over-fine sham is rejected;
6. the Lean old representation has eight wrapper-identity classes;
7. its exact consequence kernel has two semantic classes;
8. Lean WARM reduces misses 8 -> 2;
9. Lean FLASH after three old-key misses avoids all five remaining misses;
10. raw history does not reproduce either effect;
11. the Lean over-coarsened one-class sham is rejected;
12. exact ablation restores cold behavior.

## Claim boundary

A pass establishes a bounded bidirectional result under complete finite consequence maps:

> The same consequence-kernel construction can correct opposite representational errors in two source-distinct finite worlds: it refines an insufficient circuit-complexity quotient and coarsens an over-fine LocalDef cache-key model, including after both targets have begun work.

It does not establish safe coarsening under unknown future obligations, universal representation optimality, P != NP, arbitrary Lean acceleration, or unrestricted open-world equilibration.
