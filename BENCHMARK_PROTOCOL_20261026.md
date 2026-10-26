# Frozen comparative protocol — 26 October 2026

**Freeze before results.** Comparison of evidence selection on real, Git-pinned `pallets/itsdangerous@672971d66a2ef9f85151e53283113f33d642dabd` URL-safe Base64 encoding. Three *constructed* and previously documented mutations (`standard_alphabet`, `unstripped_padding`, `trailing_zero_loss`); no natural defect discovered.

## Target claim

Does a chosen test set distinguish the exact original behavior from **each of these three predeclared mutations**? The model-backed agent itself is not being benchmarked here; this evaluates the evidence-acquisition selector, not end-to-end LLM success.

## Frozen source and domain

- Verify Git source and test blob hashes using `pinned_source()`.
- Native execution of untouched reference and each predeclared mutation across all **1,026 frozen byte inputs** from `domain()`.
- Oracle: Python standard-library `base64.urlsafe_b64encode(value).rstrip(b'=')`, independently compared to pinned native reference.
- Cost per test: **1 + input byte length**. Synthetic, not wall-clock or model-token cost.
- Reuse existing original native tests as the fixed-suite comparator. A baseline passing its own declared tests does **not** assert global correctness.

## Competitors (same finite input and hypothesis information where stated)

1. **MathGraph exact separator:** existing subset dynamic program, exact minimum-total-cost basis within the frozen hypothesis grammar.
2. **Optimized conventional mutation testing:** source-distinct, adaptive greedy weighted mutation-coverage maximization using **the same mutation-vs-oracle truth table** as MathGraph. This is a strong informed baseline, not an uninformed strawman. Count total tests, covered rivals, and synthetic cost.
3. **Conventional edge-case author:** fixed tests on inputs `00` and `ff` at two-test budget (hex). Also evaluate its three-probe supplement `000000`.
4. **Deterministic random property testing:** seeded uniform sampling *without replacement* from the same 1,026-input domain, **1,000 seeds (0 through 999)**. Frozen budgets: 2, 4, 8, and 16 tests; report full-three-mutant separating success count and mean mutants detected. Seeded reproducible, not random claim of natural input distributions.
5. **Exhaustive/reference oracle:** full 1,026 cases, to validate the finite table but not presented as competitive cost baseline.
6. **Known obstruction control:** a length-four-only defect outside the finite domain is not guaranteed detectable by the selected basis; report this counterexample, not an unwarranted universal claim.

## Required audit

- Native execution (not a simulated backend) and original test receipts for source and mutations.
- Independent brute-force one/two-test minimum check agrees with exact selector.
- Optimized greedy may **tie or beat** MathGraph; report faithfully.
- No inference credits or unrelated secrets used.
- Treat constructed mutation family and synthetic cost as caveats; no claim of superiority over Hypothesis, general property-based testing, arbitrary repo repair, or optimized mutation tools.

**Disposition:** A positive result relative to naive/random selectors is *bounded*, and an optimized conventional tie is expected and must be shown. The differentiating system capability is acquisition of a separating witness with source-bound authority withdrawal and proof of finite optimality, not invention of set cover.
