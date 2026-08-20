# V5 precommit — closure-relative law identity across DSL presentations

Frozen before implementation and held-out execution.

## Question

Does the reusable repair law from V4 survive a material change in the generic relation DSL, so that the retained capability is better identified by verified behavior than by literal syntax?

## DSL A

Terminals: `E,O,I,U`.
Operations: converse, intersection, union, set difference.

## DSL B

Terminals: `E,O,I,U`.
Operations: converse, complement relative to `U`, intersection, union.

DSL B has no set-difference primitive. Neither DSL has partition/refinement/split/repair primitives.

## Acquisition families

Use all labelings in both frozen families:

1. parent blocks `(2,3)`, binary outputs: `2^5 = 32` cases;
2. parent blocks `(1,2,2)`, ternary outputs: `3^5 = 243` cases.

Total acquisition cases: **275**.

Each DSL is searched independently by syntax size with semantic quotienting over acquisition. Each must produce a unique smallest acquisition-perfect program.

## Held-out families

Not used during either program search:

1. parent blocks `(2,2,2)`, quaternary outputs: all `4^6 = 4096` cases;
2. parent blocks `(1,3,3)`, binary outputs: all `2^7 = 128` cases.

Total held-out evaluations: **4,224**.

## PASS gates

V5 passes only if:

1. DSL A has a unique smallest acquisition-perfect program;
2. DSL B has a unique smallest acquisition-perfect program;
3. the two literal programs are syntactically different;
4. both are frozen before held-out evaluation;
5. both match the verifier-required repaired equivalence on all 4,224 held-out cases;
6. their held-out outputs are extensionally identical on all 4,224 cases;
7. literal program identity therefore fails while behavioral capability identity transfers;
8. removing `O` makes both programs fail on every held-out case requiring strict refinement;
9. all code is deterministic and standard-library-only.

## Claim boundary

A PASS would show representation-independent identity only relative to these two supplied generic relational DSLs and the verifier-defined behavior. It would not prove a universal quotient notion of capability identity, nor invention of relational algebra.
