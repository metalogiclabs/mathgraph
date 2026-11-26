# Activation cost residual — 26 November 2026

**No competitive construction found.** Nine cold-arithmetic sharing candidates
and 112 isolated ARM branch-hint candidates fail the 0.5% training-gain gate.
All pass their declared scored-output checks. The held-out draw remains unused;
no new exhaustive qualification is performed.

Control: published #49, SHA-256
`8f8a23345b12abfe41040c6eca20ee06f4a4c50de69fbc6bdf8a9d758f129f37`.
Evaluator: `5a32428ad4aa23bce737d50a738ace24ddeeed2e`.
Attribution and licensing are retained. The experiments use the same local
fingerprints and exact input digests as their respective controls; no
cross-fingerprint competitive admission is claimed.

## Actual experiments

Cold sharing preserves the original polynomial arithmetic. It tests ordinary
non-inline declarations, eight-register tail interfaces for the tangent
comparison, sharing exponential/sigmoid residual calculations, and a unified
seven-argument terminal. The unified interface distinguishes aligned tangent
offsets from odd exponential reduction indices using their existing parity.
The tangent comparison ignores all but five code bits; callers clear the
remaining bits before packing sigmoid's final inversion.

Four producer-contract tests pass: original shift-count equivalence, clean
inversion packing and its deliberate failing control, forward/reverse table
offset identities, and anchor-tail/request-parity preservation. These tests
and scored cases do not establish a new full-domain numerical qualification.

On RV seed 1284956104, the control is S=29.0515378858 at 19,272 bytes.
Removing the inline hint or introducing the comparison tail interface yields
the same score and bytes. Residual sharing increases S to 29.1204308941 and
bytes to 19,332. The unified terminal reduces bytes to 19,124 but worsens S to
30.2026988447. Combining these changes with the earlier guard hints creates
no consequential gain. This rejects these implementations, not all possible
cold sharing or compiler configurations.

The ARM marginal search freezes one direction for each of 112 previously
profiled, visited branch conditions. Each source changes one condition only;
no arithmetic or persistent state is introduced. Four disjoint workers write
separate reports; all 112 finish without apparatus errors. Each generated
source is independently reconstructed and hash-checked against its measured
file. Each report matches the control's measurement/verifier identities and
input digest.

On ARM seed 150897616, the best single hint, `tanh-18-1`, scores
41.8272751375 versus control 41.8378096450 at the same 20,119 bytes: a
**0.025179%** training gain. This is below the predeclared 0.5% gate, not a
promoted contender. Held-out seed 318674905 is not consumed. The grouped
profile policies from the preceding continuation remain separate negative
results; isolated marginal effects do not imply their composition improves.

## Price the larger construction before implementing it

`common_cost_budget.py` counts the unmodified control on the recorded RV draw,
asserts exact reconstruction of its original S, then changes only counts in
the complete magnitude regions:

- sigmoid: `[1/4, 4)`;
- tanh: `[1/8, 2)`.

All other input counts remain fixed. Table/code savings are explicit separate
parameters. These are local planning counterfactuals, not executable kernels,
new hosted qualifications or future-draw takeover verdicts.

| Uniform saving in both regions | Emitted byte saving | Counterfactual S |
|---|---:|---:|
| None | 0 | 29.0515378858 |
| 3 instructions per affected call | 0 | 28.1555548582 |
| 3 instructions per affected call | 2,048 | 27.8135177700 |
| 5 instructions per affected call | 1,024 | 27.3741252856 |
| 5 instructions per affected call | 2,048 | 27.2063290472 |
| 6 instructions per affected call | 0 | 27.2279001514 |
| Recorded target, for planning orientation | — | 27.3380091766 |

Thus merely removing one multiply, its coefficient load and an addition in
both central evaluators is insufficient in this fixed-other-work model.
Additional tables worsen that budget unless they deliver more instruction
savings. A new quadratic numerical family was not implemented on the premise
that those three removed operations alone could win. A construction could
also alter other costs; the model does not rule those changes out.

The remaining objective is a cheaper common numerical evaluator that also
pays for addressing, normalization, rounding guards and fallback frequency.
No such construction is claimed here. The conditional models define useful
design targets, not proof that the targets are achievable or impossible.

## Evidence and status

Terminal form for the bounded search result:
`NAMED_OBSTRUCTION: NO_GATE_CLEAR_IN_COLD_SHARING_AND_ARM_MARGINALS`.
The earlier exhaustive joint-source qualification is unchanged and does not
transfer to these candidates. No registration, payment or submission occurred.

Source, four tests and reconstruction/calculation scripts are retained in Git.
Generated cold candidates, all raw measurements, branch protocols, logs and
planning outputs are in version 3 of
`Conjectures-numerical-continuation-20261126.zip`: 6,316,620 bytes;
SHA-256 `acb6ced524e41527009517e2e8f462f16c69ff0abd1b45da5ef9edc2ca1f076b`.
CRC and all 601 payload hashes were verified. The 112 reproducible single-hint
source files are omitted from the archive; their reconstruction identities,
full baseline and original profile are included. Prior archive versions retain
their distinct experiments and qualification boundaries.
