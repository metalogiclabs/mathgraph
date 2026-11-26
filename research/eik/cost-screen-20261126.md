# Whole-kernel cost screen — 26 November 2026

**No competitive candidate.** Twenty-three further changes pass the local
scored-output checks, but every one has a worse whole score than its matching
control. All fail the declared 0.5% development-gain gate. The held-out draw
remains unused and no exhaustive qualification of these losers is launched.

This continuation tests numerical representation and two observed sources of
compiled overhead, rather than treating a repaired experiment as a competition
advance. It does not establish that a faster kernel is impossible.

## Exact comparison

Published #49 control SHA-256:
`8f8a23345b12abfe41040c6eca20ee06f4a4c50de69fbc6bdf8a9d758f129f37`.
Original attribution and licensing are retained. Evaluator commit:
`5a32428ad4aa23bce737d50a738ace24ddeeed2e`.
RV32IM training seed: 1284956104. Cortex-M0+ training seed: 150897616.
Held-out seed: 318674905. All costs include emitted code and tables.
Within each comparison, source identities, input digests and fingerprints are
retained in the evidence packet. Local fingerprints remain distinct from the
hosted contest environment; no cross-fingerprint contender comparison is made.

| Fixed experiment group | Changes | Control S | Best changed S |
|---|---:|---:|---:|
| RV exponential, two factor tables and residual | 6 | 29.0515378858 | 31.0859264708 |
| ARM shared/direct immediate-return wrappers | 6 | 41.8378096450 | 50.7863022562 |
| ARM immediate returns inside existing cores | 6 | 41.8378096450 | 42.9097437267 |
| ARM profile-derived branch-hint policies | 5 | 41.8378096450 | 41.9916180595 |

The groups were selected sequentially. Each group's variants and gate were
recorded before its measurements; they were not one globally frozen discovery
trial. No selection or coefficient uses the held-out draw.

## What the measurements resolve

The factorization decomposes the exact fixed-point input as
`abs(x) = i/2^a + j/2^b + r/2^28`. Two downward-rounded factor tables and a
quadratic residual replace the old hot negative-exp family. Guards send
uncertain cases through the complete evaluator, avoiding the previous
approximation-phase mistake. The best layout reduces code/table bytes from
19,272 to 17,796, but increases typical exp instructions from 31.036 to 44.875.
The complete score therefore worsens by about 7%. Passing scored outputs and
arithmetic tests is not all-input numerical qualification of these proposals.

The wrapper experiment tests the unconditional stack setup visible in all
three ARM kernel entry profiles. Genuine shared callers avoid unsupported
compiler directives and artificial unreachable calls. Extra dispatch/call work
outweighs immediate-return savings. Moving the conservative returns directly
inside each core also fails the cost gate. These results reject these concrete
source changes, not every possible outlining method.

The final ARM profile instruments 158 original branch sites and independently
matches all 12,900 scored native outputs to the reference. False/true counts
are weighted using the actual four workload-set weights. Five fixed policies
emit only `__builtin_expect` around original conditions; development counters
and mutable state are absent from every candidate. Even correct branch
frequencies produce no score improvement. The result is compiled-cost evidence,
not a semantic change or a theorem about all compilers.

Five unit tests pass: three cover coordinate retention, guarded rounding across
the binade boundary, and product/table ranges; two cover score-model isolation
and native equivalence of nested hinted conditions with side effects. The
latter tests 12,300 calls, including unsigned wrap boundaries, and catches
double evaluation of an original condition. The profile's 12,900 reference
comparisons are separate integration evidence.

## A decisive bound on the frame-only route

Apply the unchanged official score formula to the already qualified hosted
control from [run 45738054604](https://github.com/metalogiclabs/mathgraph/actions/runs/45738054604).
Hold code/table bytes fixed and subtract a constant from every call, including
all functions and input classes. Means and quantiles shift by that constant.

| Hypothetical saving on every ARM call | Counterfactual S |
|---|---:|
| 0 instructions | 41.8378096450 |
| 1 instruction | 40.6228013669 |
| 2 instructions | 39.4021369033 |
| 3 instructions | 38.1750079197 |
| Recorded #53 takeover threshold on this draw | 38.1250263689 |

Even the deliberately generous three-instruction model misses the recorded
threshold. Actual elimination still needs a return instruction and incurs any
new classification/dispatch cost. This is a **conditional scope bound at fixed
bytes**, not a universal impossibility claim or a prediction for a fresh draw.
Combined arithmetic or substantial size improvements remain outside it.

This bound was calculated after the wrapper probes; it was not their
predeclared admission criterion. It should be used to reject insufficient
standalone frame-only proposals before further implementation.

The original hosted provider ZIP has SHA-256
`e4d3a1fb4c6f99f939d4eefa251e6f6c6a896bb8dfb935e61d11b908be837926`.
Its provider digest, CRC and four member hashes were checked again. The bound
is a local deterministic derivation from that retained hosted control, not a
new hosted execution. Its original fingerprints match the published contest
environment. Applying the same calculation to the new local control gives
exactly the same four values.

## Live target and decision

Read-only official snapshots retain RV32IM #52 and ARM #53; the overall board
has advanced to #56. Source #56 is unavailable, and no source from it is used.
An attempted public former-source #50 retrieval returned `target_unreachable`;
availability is UNKNOWN from that response. No new public baseline was acquired.
The old overall #50 target is superseded. These snapshots do not establish what
score a future submission would obtain on its fresh comparison draw.

**NAMED_OBSTRUCTION:** `NO_COST_GAIN_IN_23_TARGETED_VARIANTS`, plus the
conditional `FRAME_ONLY_SCOPE_TOO_SMALL_AT_FIXED_BYTES`. Reject readiness for
these sources. The next consequential proposal must reduce common numerical
work enough to pay for coordinate conversion, table accesses, guards and
fallbacks together. Correctness evidence alone does not discharge this cost
obligation. No registration, payment, signing or submission occurred.

Source generators, five unit tests and the score-bound calculator are in Git.
Generated candidates, raw profiles, reports and live snapshots are in version 2
of `Conjectures-numerical-continuation-20261126.zip`: 5,424,357 bytes,
SHA-256 `fd3d9ade8d2ea0cdee6cb6c835651a6e574d75b91a1862ca948a312445008437`.
ZIP CRC and all 460 payload hashes were checked. Earlier versions remain
lineage for the distinct 276-candidate continuation and its hosted regression.
