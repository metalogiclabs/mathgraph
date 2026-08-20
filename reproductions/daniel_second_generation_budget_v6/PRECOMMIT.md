# V6 precommit — resource-indexed second-generation constructibility

Frozen before held-out implementation and execution.

## Question

Does retaining the learned V4/V5 repair law change what a later law is constructible within a fixed program-size budget, while leaving unbounded semantic expressivity unchanged?

This is deliberately a `CapReach_H` question, not a claim of absolute language growth.

## Cold DSL

Terminals: `E,O1,O2,I,U`.
Operations: converse, complement relative to `U`, intersection, union.
No set-difference primitive and no learned repair macro.

## Warm DSL

Same cold DSL plus one installed binary capability `K(R,S)`, with semantics equal to the previously learned repair law `R \ S`.

The installed capability is frozen before V6 acquisition search. `K` is not a new unbounded semantic primitive: every `K` occurrence can be macro-expanded to the old relation language.

## Acquisition family

Parent blocks `(2,2)`. Episode-1 labels binary, episode-2 labels binary. Use all `2^4 * 2^4 = 256` ordered label pairs.

For each case:

- `E` is the parent equivalence;
- `O1` is the complete unequal-label relation for episode 1 inside `E`;
- `E1 = E \ O1`;
- `O2` is the complete unequal-label relation for episode 2 inside `E1`;
- target is `E2 = E1 \ O2`.

Search both DSLs independently by syntax size with semantic quotienting over the complete acquisition family.

## Frozen held-out families

Not used during program selection:

1. parent `(1,3)`, episode-1 ternary, episode-2 binary: `3^4 * 2^4 = 1296` cases;
2. parent `(2,3)`, episode-1 binary, episode-2 ternary: `2^5 * 3^5 = 7776` cases.

Total held-out cases: **9,072**.

## Frozen resource budget

`H = 5` AST nodes.

## PASS gates

V6 passes only if:

1. no cold acquisition-perfect program exists at size <= 5;
2. the cold unique shortest acquisition-perfect program exists at size 6;
3. a warm unique shortest acquisition-perfect program exists at size <= 5;
4. the warm winner is frozen before held-out evaluation;
5. the warm winner matches the verifier target on all 9,072 held-out cases;
6. every cold program of size <= 5 fails to match the verifier target on at least one held-out case;
7. replacing `K` by matched-arity sham macros `intersection` or `union` does not produce an acquisition-perfect program within budget 5;
8. macro-expanding `K(R,S)` to `R \ S` yields an old-language expression extensionally identical to the warm program, proving no claim of unbounded semantic growth;
9. deterministic, standard-library-only execution.

## Claim boundary

A PASS establishes second-generation **resource-indexed constructibility**: a previously learned reusable law changes `CapReach_H` for a later law under a frozen size budget. It explicitly does not establish absolute second-generation expressivity or a new semantic closure.
