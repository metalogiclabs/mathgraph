# V67 — Cross-source developmental transfer

V66 established causal reuse of a verified lemma basis when the *same* source
law recurred. V67 tests a different object: whether prior verified development
episodes can train a source-ID-agnostic developer that builds better verified
lemma bases for source laws it has never seen.

## Frozen transferred object

Training uses only previously opened YanbiaoLab Wrong Book rows below 2980.
For recurring source laws, V67 recompiles a replay-verified critical-pair basis,
runs exact target proofs, and marks every lemma on the ancestry of an actually
used derived rule as developmentally useful.

From those old episodes it learns a deterministic linear retention policy over
source/critical-pair/obstruction features. The policy never contains source IDs,
target IDs, truth labels, proof text, or stored source-specific lemmas.

The policy is serialized and SHA-256 hashed **before** either evaluation stream
is parsed.

## Prospective evaluation

1. A pinned Stage-2 public problem stream is opened only after the developmental
   operator is frozen. The first 100 distinct source IDs absent from the entire
   training window form the source census. No source-ID recurrence from training
   is permitted.
2. Wrong Book 3000 rows 2980:3000 are also opened only after the freeze as the
   final untouched tail left by V66.

For each proof-candidate whose source-only proof fails:

- **COLD** gets the source law and the same verified critical-pair generation
  budget, retaining candidates by the generic complexity ordering.
- **META** gets the same source, same target obstruction, same generation
  mechanism, same lemma budget, and the frozen learned retention policy.
- Every retained lemma is independently replay-verified.
- Every terminal TRUE is exact step-by-step replay.
- A decisive event requires META to prove where COLD cannot, using at least one
  META-exclusive newly generated lemma.
- That exact lemma lineage is deleted and restored.
- Deleting the transferred developer is the COLD condition; restoring it is the
  META condition.

A PASS is therefore bounded evidence for **capability-generation transfer**:
old verified development changes how the system develops a new source law, and
that transferred developmental policy causally creates a new verified
capability needed by a later proof. It is not a claim of unrestricted theorem
proving, universal learning, or open-ended intelligence.
