# V4 precommit — generic relational law synthesis

Frozen before implementation/result inspection.

## Question

Can the V3 quotient-repair operation itself be synthesized as a reusable program from a weak generic relation DSL, rather than supplied as `RefinePartition`?

## Scientific boundary

The DSL contains only four relation-valued terminals and four generic operations:

- terminals: `E` (current observational equivalence), `O` (verifier obstruction relation), `I` (identity), `U` (universal relation)
- unary: `converse(R)`
- binary: `R ∩ S`, `R ∪ S`, `R \ S`

There is no `partition`, `quotient`, `refine`, `split`, `separate`, `conflict repair`, or target-coordinate primitive.

The verifier supplies, for each case, the required repaired equivalence relation as the semantic acceptance criterion. Program synthesis enumerates DSL terms by size, quotients candidates extensionally over the acquisition suite, and returns the unique smallest program if one exists.

## Acquisition suite

All labelings are used for each frozen world:

1. parent block sizes `(2,2)`, binary outputs: `2^4 = 16` cases;
2. parent block sizes `(3,2)`, binary outputs: `2^5 = 32` cases;
3. parent block sizes `(2,2)`, ternary outputs: `3^4 = 81` cases.

Total acquisition cases: **129**.

For a parent equivalence `E` and output labels `y`, the obstruction relation is all pairs `(i,j) ∈ E` with `y_i != y_j`. The verifier accepts exactly the equivalence relation induced by equal labels inside the old `E`-classes.

## Frozen held-out suites

These are not used during program selection:

1. `(4,4)` parent blocks, binary outputs: all `2^8 = 256` cases;
2. `(3,3,2)` parent blocks, ternary outputs: all `3^8 = 6561` cases;
3. `(2,3,2)` parent blocks, quaternary outputs: the first 7000 lexicographically enumerated labelings from the `4^7` possible cases.

Total held-out evaluations: **13,817**.

Held-outs change world size, parent geometry, and output arity relative to acquisition.

## Controls

- **Literal instance memory:** acquisition output relations are not transferable by exact instance identity to held-out world signatures; this baseline must solve 0 held-out cases by exact lookup.
- **No-obstruction control:** replacing `O` with the empty relation must fail on every held-out case requiring a strict refinement.
- **Wrong-obstruction control:** use the obstruction relation from the lexicographically next labeling in the same held-out world; the learned program must not be credited when it happens to match accidentally. Report exact match/failure counts rather than requiring zero accidental matches.
- **Ablation:** removing the learned program returns the constructor to the frozen old DSL state; held-out repair must then be unavailable unless another acquisition-equivalent DSL term exists.

## PASS gates

V4 passes only if all are true:

1. a unique smallest acquisition-perfect DSL program exists;
2. it is not a primitive terminal;
3. the program is frozen before held-out evaluation;
4. it matches the verifier repair relation on all 13,817 held-out cases;
5. exact literal-instance memory solves 0 held-out cases;
6. the no-obstruction control fails on every strict-refinement held-out case;
7. no distinct acquisition-equivalent program of the same or smaller size survives semantic quotienting;
8. the result and all controls are deterministic and standard-library-only.

## Claim boundary

A PASS would establish synthesis and cross-world reuse of a representation-changing **law program** from generic relation operations. It would not establish invention of set difference, relational algebra, search/minimization, or arbitrary representation-changing mathematics.

If no unique transferring law exists, record `NULL`; do not add DSL primitives after inspecting the result.
