# V67 — Minimal sufficient proof basis

V66 is the fresh causal capability result: three source-law capabilities were
compiled in an earlier external stream; eleven later naturally recurring
proof-candidate targets were all proved warm and all eleven were cold failures;
six had exact individual lemma-lineage deletion/restoration witnesses.

V67 applies the MSI / Lean-kernel minimisation idea to that learned machinery
itself.

For the 11 protected later targets, it:
1. discards source bases with no protected continuation;
2. computes the derivation-closed support of rules actually used by successful
   V66 proofs;
3. re-runs all protected targets with only that support;
4. greedily deletes a retained lemma lineage whenever every protected target
   remains provable;
5. iterates to a local fixed point;
6. demands an explicit later theorem witness for every surviving derived lemma:
   delete its lineage -> proof disappears; restore -> proof returns.

The result is only a local minimality statement relative to the declared V66
protected targets and frozen V63 search. It does not claim a globally minimal
equational basis.
