# MathGraph × Open Math Model — Reproducible Contribution Brief

## One-line proposition

**Use models to explore unresolved mathematics; once an output earns independent
verification, compile it into persistent capability so later work does not pay
the model to rediscover it.**

## Evidence now available

Using `google/gemma-4-31b-it` through OpenRouter/DeepInfra, MathGraph ran a
sequence of increasingly strict tests.

### Public SAIR sample-200

Gemma generated acquisition artifacts on the first 25 known-FALSE public tasks.
Only independently checked finite countermodels were promoted.

On 75 untouched FALSE tasks:

- model calls: **75 → 27** (-64.0%)
- tokens: **10,829 → 3,888** (-64.1%)
- verified results: **21 → 49**
- restart: exact
- targeted ablation: restores cold exactly

Run:
https://github.com/metalogiclabs/mathgraph/actions/runs/35402264089

### Disjoint public normal replication

After excluding every sample-200 equation pair, Gemma acquired capability on
the first 50 remaining FALSE problems.

On the next 200:

- model calls: **200 → 94** (-53.0%)
- tokens: **28,777 → 13,515** (-53.0%)
- verified results: **66 → 106**
- restart: exact
- targeted ablation: restores cold exactly

Run:
https://github.com/metalogiclabs/mathgraph/actions/runs/35402563917

### Sealed 250-problem reserve

The exact three-capability V5 bank was frozen before this reserve was evaluated.

On the final 250:

- model calls: **250 → 125** (-50.0%)
- tokens: **36,221 → 17,997** (-50.3%)
- verified results: **82 → 125**
- restart: exact
- targeted ablation: restores cold exactly

Run:
https://github.com/metalogiclabs/mathgraph/actions/runs/35402936630

Across the complete 500-FALSE disjoint normal stream, including acquisition,
retained verified capability reduced:

- model calls **531 → 300** (-43.5%)
- tokens **77,514 → 44,028** (-43.2%)
- OpenRouter cost **$0.00887070 → $0.00494998** (-44.2%)
- model latency **443.9 s → 239.7 s** (-46.0%)

## Architecture

```text
model proposal
      ↓
independent verifier
      ↓
verified artifact / counterexample / proof
      ↓
scope + provenance + causal ledger
      ↓
persistent capability
      ↓
check before next model call
      ↓
reuse if licensed; otherwise ask model
```

Verification and usefulness are deliberately separate. Earlier cross-set testing
showed that a verified artifact can be mathematically valid yet economically
unhelpful in a different regime. So promotion needs scope, not a global cache.

## Why this may matter for Open Math Model

The interface is model-agnostic. It can sit around an open-weight model or a
closed model. It targets three questions that become increasingly important in
sustained mathematical use:

1. Which generated results have earned authority?
2. Which verified results remain relevant to the current problem regime?
3. When can the system stop paying inference cost because a verified answer or
   reusable construction already exists?

## Current claim boundary

The experiments above cover public equational-theory FALSE tasks and bounded
finite countermodels. They do not establish private evaluation performance,
TRUE-proof generation, arbitrary mathematics, or weight-level learning.

The contribution is the developmental verification protocol and its
reproducible evidence: **propose → verify → promote → restart → reuse →
ablate**.
