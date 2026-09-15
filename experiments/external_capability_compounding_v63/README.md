# V63 — Verified lemma genesis + target-guided narrowing

V61 established that target-only rewriting is the wrong proof graph.
V62 adds verified critical-pair lemma genesis. V63 adds the missing execution
semantics for non-regular equational lemmas: explicit target-guided
instantiation of variables not bound by the matched side.

Every narrowing step records:
- verified lemma id,
- direction,
- exact subterm position,
- a complete substitution for every lemma variable.

A separate replay routine checks the instantiated left side against the chosen
subterm and reconstructs the exact successor term. Proposal search remains
heuristic; proof acceptance is exact.

This workflow uses only TRUE cases opened before V62. Rows 2820+ remain sealed.
