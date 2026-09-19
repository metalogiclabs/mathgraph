# QCKN Maintained Revocable Consequential Equilibration V3

## Objective

V2 proved that one exact consequence-kernel operator can move representations in both directions:

- refine when the present is too coarse;
- coarsen when the present is too fine.

Its coarsening authority was deliberately expensive: for 101 arithmetic histories the V2 gate checked all 5,050 unordered state pairs.

V3 asks the next operational question:

> Can a previously verified sufficient basis be reused incrementally so the active present stays small, while raw distinctions remain recoverable and a later protected obligation can revoke an earlier merge without reacquiring the past?

## Frozen source

Pinned source:

`heathsanchez/Minimal-Sufficient-Interface@5d448c0ecc82ff3945d009963064ebbb67d2f308`

Load-bearing source:

`tests/test_arithmetic_base_invariance.py`

Git blob:

`5d23b9b5b2d16e94e2c15c2ed7439fba1335c6a3`

For decimal two-addend local addition:

- carrier: empty history + every one-position digit-pair history;
- raw carrier size: **101**;
- complete old protected family: next output digit under all **100** possible next digit pairs;
- qualified sufficient basis: the single context **(0,0)**;
- exact protected future-behaviour quotient: **2 classes**.

CI re-runs the complete source qualification. V3 runtime metrics do not pretend that basis discovery was free: the source certificate is an already-earned artifact whose proof is requalified separately.

## Maintained state

The active representation stores only the currently consequential quotient.

The reserve stores raw identity/provenance required for recovery.

A maintained representation serializes:

- active partition;
- raw reserve IDs;
- per-state sufficient-basis values;
- scope ID;
- scope-certificate ID;
- representation ID;
- explicit revocation records.

Serialization is canonical and restart must reproduce exact text and digest.

## Initial live Flash

The arithmetic target first materializes **20 raw histories**.

Then the previously qualified one-context certificate arrives.

Runtime authority evaluates only the certified basis context on every raw state:

**101 consequence evaluations**.

The active representation contracts to **2 classes**.

As the remaining histories arrive, they are routed into the active two-class quotient while their raw identities are retained in reserve.

After the stream:

- ACTIVE classes: **2**
- RESERVE raw identities: **101**

## Scope expansion and revocation

A genuinely new protected obligation then arrives:

`audit-last-pair-is-9-1-v1`

It asks whether the most recent digit pair was exactly `(9,1)`.

This obligation is deliberately outside the old addition-next-digit scope.

The old two-class carry quotient is not sufficient for it: `(9,1)` and other carry-producing histories were previously merged.

Therefore V3 must:

1. record an explicit revocation of the old representation;
2. reopen all **101 raw distinctions** from reserve;
3. perform **zero raw-data reacquisition**;
4. evaluate the new protected consequence once on each history: **101 evaluations**;
5. combine the old sufficient-basis value with the new obligation value;
6. compile the expanded scope to its exact **3-class** present.

The three classes are:

- old no-carry class;
- carry class excluding `(9,1)`;
- singleton `(9,1)`.

## Controls

### NO_RESERVE

The system coarsens correctly but discards raw recovery state.

When the new obligation arrives, revocation must fail with `RecoveryUnavailable`.

### NO_REVOCATION

The system keeps using the old two-class representation under the expanded scope.

The authority must produce an explicit unsoundness witness: two histories merged by the old quotient but separated by the new obligation.

### RESTART

The maintained active+reserve state is serialized and restarted before scope expansion.

Restart must preserve exact text and digest, and the later revocation must again reach the same 3-class result.

## Economics

V2 pairwise authority:

- 5,050 checks per representation update;
- 10,100 checks if repeated for two updates.

V3 maintained runtime authority:

- 101 evaluations for the old certified basis;
- 101 evaluations for the new obligation;
- **202 runtime evaluations total**.

That is a **98% reduction in repeated runtime authority checks** relative to rerunning the V2 pairwise authority twice.

This is an amortized result. The sufficient-basis certificate was paid for previously and is requalified by CI; V3 demonstrates that the system does not pay that discovery cost again on every live representation update.

## QCKN alignment

RealityGraph QCKN already has:

- compiled active state;
- explicit revocations;
- ACTIVE vs RESERVE retention;
- recovery requirements;
- exact restart.

V3 applies that same design pattern to representations. It does not alter frozen QCK/MSI semantics.

## Claim boundary

A pass earns:

> In this bounded finite arithmetic setting, a previously qualified sufficient-basis certificate can maintain a small active representation at 101 runtime consequence evaluations rather than repeated exhaustive pairwise checks; raw distinctions can be retained in reserve; a new out-of-scope protected consequence can revoke the old coarsening, reopen all raw distinctions with zero reacquisition, and recompile a new minimum present. Removing reserve prevents recovery, while suppressing revocation leaves a detectably unsound quotient.

It does not establish cheap basis discovery, safe coarsening without a scope certificate, universal open-world revocation, or universal representation optimality.
