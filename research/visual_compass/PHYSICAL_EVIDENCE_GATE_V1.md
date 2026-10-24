# Visual compass: physical evidence gate v1

Status: CANDIDATE protocol. No physical heading-recovery claim is warranted by this document.

## Capture contract
Record at least five uninterrupted gyro-measured revolutions on a rotating rig with a camera column, gyro and independent optical encoder. Preserve raw immutable recordings and SHA-256 digests. Each sample must have a monotonic hardware-clock timestamp, clock identity, sequence number, and units. Record camera exposure start/end (not just frame arrival), gyro sample timing and encoder edge timing. Record sensor mounting orientation, lens geometry, encoder resolution, rotational direction, calibration version, and dropped-sample counters.

Encoder data is forbidden from estimator inputs, map construction, observation selection, timing adjustment during evaluation, and recovery logic. It is available only to an independent scorer after the estimator outputs are frozen.

## Timing qualification
Use an independent synchronization stimulus/reference instrument to estimate camera–gyro clock offset, drift and jitter. Partition calibration revolutions from held-out test revolutions. Freeze a conservative time-error envelope before testing; if held-out timing residuals exceed it, invalidate correction authority. A fitted nominal offset alone is not an error bound.

## Evaluation
Revolution 1 constructs the environment map. Hash and freeze that map before revolutions 2–5. Score gyro-only, a conventional tracker, and MathGraph using identical camera/gyro data and the same allowed timing envelope. Introduce controlled drift, dropped gyro/camera samples, occlusions, and scene changes. Preserve trial identities and perturbation schedules.

For each proposed correction, retain candidate headings, visual observations, predicted observations, timing uncertainty, hypothesis-separation certificate or UNKNOWN, requested separating observation, and eventual result. No correction on UNKNOWN.

The independent scorer computes circular heading error versus encoder, per-revolution RMSE, median, p95, correction counts, false-authorized corrections, recovery latency, and abstention rate. Report paired per-trial comparisons and confidence intervals; do not tune thresholds on held-out trials.

## Fail-closed acceptance
- Reject missing, duplicate, non-monotonic, or incompatible-clock timestamps.
- Reject fewer than five complete revolutions independently established by encoder ground truth.
- Reject missing or altered map hash and non-frozen map updates after revolution 1.
- Reject estimator/scorer data leakage from encoder.
- Reject missing calibration, unbounded timing uncertainty, or held-out calibration violations.
- Reject corrections lacking an auditable separation witness.
- Keep incomplete capture and all unavailable physical evidence UNKNOWN, never PASS.
- CI success qualifies the harness only; physical claims require separately archived raw data, manifests, and independent scoring artifacts.

## Current residual
No independently verified five-revolution synchronized camera/gyro/encoder dataset has been attached. Hardware heading-recovery performance is UNKNOWN.

## Cheapest decisive next experiment
Collect one five-revolution capture with an independently timed encoder, then run the frozen-map estimator and baseline on exactly the same held-out sequence.
