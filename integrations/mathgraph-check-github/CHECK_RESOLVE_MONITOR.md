# MathGraph Check — Check · Resolve · Monitor

**Product promise:** Verify what's justified. Resolve what's unknown. Monitor what changes.

This is a proposed **product-facing interface**, not a claim of independently qualified end-to-end production operation. GitHub App installation, webhooks and native Check Runs remain separate, pre-existing components.

## Check
Consumes a source-pinned evidence contract *after the caller authenticates the evidence*. Emits OBSERVED, BLOCKED or UNKNOWN for scoped claims. `OBSERVED` means successful cited checks, **not** a theorem, proof of semantic equivalence or permission to merge.

## Resolve
Given UNKNOWN/BLOCKED obligations and a caller-supplied, explicitly permitted, source-authoritative candidate-experiment set, selects a lowest-recorded-cost proposal (lexical tie-break). **Does not invent, run or independently verify the experiment.** No qualified plan means an explicit null recommendation.

## Monitor
Compares source-bound claim snapshots; computes changed/retained/withdrawn statuses with dependency-aware impact. A new head, missing dependency scope or changed evidence cannot be silently requalified from apparent CI success. `independent_requalification` is an explicit **trusted-host assertion** and must be set only after fresh independent checks. The monitor cannot authenticate that assertion itself.

### Separation of powers
- Evidence authenticity: external authenticated GitHub/native-verifier adapter.
- Decision semantics: pure functions in `check-resolve-monitor-v1.mjs`.
- Action permission: independent policy layer; this module returns ADVISORY_ONLY.
- GitHub publication: existing authenticated MathGraph Check App only, once separately qualified.

### Test
`node --test integrations/mathgraph-check-github/evidence-contract-v1.test.mjs integrations/mathgraph-check-github/check-resolve-monitor-v1.test.mjs`

No external repository comments, installations, app deployment or automated posting are performed.
