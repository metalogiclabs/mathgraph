# Numerical speed continuation — 26 November 2026

**No winning candidate.** Six complete-family arithmetic variants are rejected
for performance on the declared input draw. Their mathematical output checks
passed within the stated interval. A separate score-budget calculation explains
why this small-family route cannot reach either board by itself at fixed size.

## Exact experiment

Published baseline #49 SHA-256:
`8f8a23345b12abfe41040c6eca20ee06f4a4c50de69fbc6bdf8a9d758f129f37`.
Its original attribution and licensing are retained. Evaluator:
`conjectures-io/exact-integer-kernels-miner` at
`5a32428ad4aa23bce737d50a738ace24ddeeed2e`.

For the ARM tanh family with magnitudes in `[1/128, 1/8)`, the original quadratic
uses three products; the fused form uses two. With offset D in 0..65535 and row
coefficients R and P, the original nonconstant term is

```
A = floor(R D / 2^12) + floor(P floor(D^2 / 2^16) / 2^17)
B = floor((R + floor(P D / 2^21)) D / 2^12)
```

Both approximate `R D / 2^12 + P D^2 / 2^33`. Their floor-error bounds imply
`-2 <= A-B <= 16`. Every fused unsigned product fits 32 bits; the maximum
source-bounded product is 4,185,130,635. A low-byte guard in 21..239 preserves
the quotient and the original settled guard. Ambiguous values and special
low-input cases retain the original calculation. One variant prebiases the
table by 16 and compensates the original fallback, giving a one-sided interval
`-18..0` and the simpler low-byte guard 37..255.

## Executed evidence

Four guard/range tests pass, including wrap boundaries and deliberate failing
controls. Every variant was natively compared with the original ARM function
on both signs of all words in `[0x3c000000, 0x3e000000)`: **67,108,864 per
variant, 402,653,184 total, zero mismatches**. The native adapter calls the ARM
function directly and uses `-ftrivial-auto-var-init=zero`. These are source-relative
numerical comparisons, not independent reference or full-target qualification.

Each variant passes official scored-output checks on RV32IM and Thumb-M0+.
Extra target samples were disabled in these development measurements. Seed:
1284956104. Actual local measurement and verifier fingerprints and input hashes
match the local control. No claim of matching the hosted Python environment is
made for these local reports.

| Variant | ARM S, lower is better | Decision |
|---|---:|---|
| Published baseline | 41.4988452337 | Retained control |
| Plain fused path | 42.6843184444 | Rejected |
| Likely fused path | 42.7282138968 | Rejected |
| Fused helper | 42.9907089925 | Rejected |
| Likely fused helper | 42.9773319588 | Rejected |
| Recomputed fallback address | 41.7669817536 | Rejected |
| Positive-bias guard | 41.6880546250 | Rejected |

The initial variants introduce stack adjustment on every ARM tanh call. At
input 1.0 the original takes 36 instructions and the plain variant 38; at zero,
10 becomes 12. Recomputing the fallback address recovers much of this cost,
but no variant improves the whole score. The RV32IM score is unchanged.

## Conditional score budget

The original published source was checked and measured on each champion's
published seed: 1284956104 for RV32IM #52 and 150897616 for ARM #53. The score
model's unmodified result is independently reconstructed from individual
instruction counts and asserted equal to the official kit's report.

For the experiment below, all instruction counts outside the named family and
all code/table bytes remain fixed. A zero-cost family is a counterfactual lower
bound, not an implemented kernel or prediction for a future draw.

| Board | Baseline S | Small tanh family at zero cost | Takeover S |
|---|---:|---:|---:|
| RV32IM | 29.0515378858 | 27.6555645035 | 27.3380091766 |
| ARM M0+ | 41.8378096450 | 40.091018 | 38.1250263689 |

Thus this small family alone cannot clear either recorded bar under those
fixed-size assumptions. The differing ARM baseline above is a different input
draw, not a conflicting result.

For RV32IM, reducing all instruction counts in the central sigmoid region
`1/4 <= abs(x) < 4` by about **33.01%**, or in negative exp with
`1/4 <= abs(x) < 8` by **34.08%**, would reach the recorded threshold if the
other counts and bytes stayed fixed. These are conditional workload budgets;
neither optimization has been implemented. The next consequential experiment
must address one of these larger families or establish a comparable combined
cost reduction.

## Replay and lineage

`fused_quadratic.py` generates exact pinned candidates;
`test_fused_quadratic.py` tests the arithmetic guards and range rejection;
`fused_quadratic_diff.c` enumerates the complete changed magnitude interval on
both signs through direct ARM-function adapters. `region_budget.py` reproduces
the score-budget calculation with source/evaluator checks and official output
verification. Generated source files, reports and diagnostics are retained in
the numerical-speed evidence archive, whose identity is recorded in the small
receipt alongside this report.

The fully qualified earlier joint source remains a distinct result. This trial
does not promote a speed candidate, qualify all 2^32 target inputs, or establish
a live competition takeover. Registration and entry submission remain undone.
