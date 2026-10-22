# Synthetic one-column compass: frozen v1 holdout result

Date: 2026-10-22. Verification boundary: **synthetic procedural scene**, 12 nominal turns,
64-row single-column vectors, gyro-integrated first-turn map. No physical line camera.

## Provenance and qualification

- Implementation, independent trace auditor, unit tests, and preregistered seeds frozen
  at [`ea16bcb264de4acd4e5fc310789d52fe3e88b4c9`](https://github.com/metalogiclabs/mathgraph/commit/ea16bcb264de4acd4e5fc310789d52fe3e88b4c9).
- A separate workflow-only commit
  [`735dd5c2ce20d34fae4b7d7ac7248a958509d34f`](https://github.com/metalogiclabs/mathgraph/commit/735dd5c2ce20d34fae4b7d7ac7248a958509d34f)
  executes four new seeds (`101`, `211`, `307`, `401`) for all 12 declared
  scenarios, and checks the estimator/verifier/protocol have not changed.
- [GitHub Actions run 39756993577](https://github.com/metalogiclabs/mathgraph/actions/runs/39756993577): **PASS**,
  10/10 invariants, 48/48 independent full-trace replays (four estimators per
  case), zero incorrect accepted corrections by robust and evidence-aware
  under the declared external 10-degree target metric. The full trace artifact
  `adversarial-frozen-holdout-traces-v1` has GitHub artifact ID `12416575751`,
  SHA-256 `3f6d39fd40104b047070cc3b63e86a0fcf3a76a688ebb6302eb1d788957dd659`.

## Findings (ranges over all four previously unopened seeds)

| Scenario | Gyro-only RMSE | Matched-filter RMSE | Robust / evidence RMSE | Limitation |
| --- | ---: | ---: | ---: | --- |
| Clean | 20.77–20.84° | 1.61–1.65° | 1.62–1.64° | Favorable synthetic scene |
| Blackout turns | 20.77–20.84° | 3.41–3.43° | 3.07–3.15° | Recovered in three samples |
| Gyro drift | 96.65–96.72° | 1.69–1.71° | 1.79–1.82° | Declared scenario |
| Repeated exact | 20.77–20.84° | 1.73–1.77° | 1.62–1.65° | Reacquired in two samples |
| Partial first map | 20.77–20.84° | 2.47–2.54° | 2.45–2.57° | Only 28.1% map coverage |
| Moving objects | 20.72–20.86° | 1.70–1.82° | 3.28–3.74° | Robust method less accurate |
| Recovery confuser | 137.07–137.12° | 152.81–152.83° | 140.13–140.25° | Neither robust method recovered |
| Combined | 96.45–96.52° | 97.49–101.43° | 96.45–96.52° | Both robust methods abstained throughout |

Results on `parallax_height`, `timing_jitter`, `repeat_near`, and
`speed_changes` are preserved in the complete workflow log and trace artifact.
`recovery_confuser` produced **2414–2419 incorrect accepted corrections**
by the naive matched filter. Stronger baselines abstained but kept gross heading
error; zero incorrect *accepted* corrections is **not** sufficient navigation
reliability. The alias detector correctly withheld under the tested noisy
fourfold patterns, but its threshold is empirical rather than proven sound.

**Warranted within this model:** first-turn causal map, repeat recognition under
the defined stress classes, a conservative shared alias guard, correct
independent arithmetic replay, and explicit failure detection by withholding.

**Not established:** comparative superiority of the MathGraph method; on all
48 heldouts it produced the same heading estimates as the equally informed
strong conventional baseline. Also not established: calibrated availability,
true line sensor support, real repeated rotations, autonomous recovery from
the confuser, or flight readiness.

## Residual and lineage

The initial global-witness scheme was **REJECTED** because a first-turn map
with noisy repeated sectors appeared falsely distinctive; details remain in
`ADVERSARIAL_PROTOCOL.md`. The repaired scheme is a synthetic **WARRANTED,
bounded** result for refusal, not a MathGraph performance advantage. It is
unable to obtain an additional separating landmark when all nearby evidence
is indistinguishable.

Next independent task: a separate finite/noise-bounded acquisition protocol
that emits a minimal set of future observations, and an equally informed
conventional hypothesis tracker. Keep v1 source frozen and do not promote a
new finite-model guarantee into a physical-camera claim.
