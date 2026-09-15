# V65 — Fresh external verified proof capability compounding

V63 showed that a source identity can generate a replay-verified universal lemma
which then proves an external TRUE implication. V64 showed on opened
train/validation data that retaining source-specific compiled lemma bases
improved later targets: cold source-only proved 1/4, retained bases proved 3/4,
including two warm-only proofs.

V65 freezes that mechanism prospectively.

Fresh Phase A is Wrong Book 3000 rows 2820:2900.
Fresh Phase B is Wrong Book 3500 rows 2820:2900.

Phase A may compile a source-law basis only when the frozen cvc5 route probe
returns PROOF_CANDIDATE. cvc5 UNSAT is advisory and never promoted to TRUE.
The Phase-A archive is serialized, hashed, reloaded, and derivation-replayed
before any Phase-B transfer proof is attempted.

The decisive gate is causal: a Phase-B target must be provable with a retained
Phase-A derived lemma while source-only search fails, and deleting an exact
used lemma lineage must remove at least one such proof; restoring the frozen
archive must restore it.

No proof file or published verdict is read.
