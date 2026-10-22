# Beacon-free single-column compass: adversarial protocol v1

Date: 2026-10-22. Branch: `exp/uzh-rotation-validation-20261021`.

## Objective and verification boundary

Evaluate whether a first-revolution, gyro-indexed, **frozen** 64-row column map
supports subsequent heading corrections under repeated textures, appearance
changes, camera/gyro timing error, variable speed, drift, missing revolutions,
and incomplete first-turn coverage. This is synthetic only. This protocol does
not establish a flight-ready compass, certified safety, or a formal theorem.

The simulator generates the scene and ground truth; **the estimator signature
accepts only columns, an observed/not-observed mask, and gyro increments**.
No solver receives actual heading, scene-generating parameters, scenario name,
ground-truth mask of an incorrect answer, or future sensor measurements.
The independent replay auditor receives the truth *only after estimation*.

## Frozen comparison and parameters

Four estimators on identical inputs:

1. **Gyro-only:** integrate incremental gyro samples, no visual corrections.
2. **Matched filter:** weak local ±10-bin best-template matcher, 0.30 gain.
3. **Strong conventional:** 5-frame, age-limited normalized temporal correlation
   across all 256 map bins; distinct peaks spaced at least 7 bins; score ≥0.52,
   runner-up gap ≥0.09. Map-only alias detection and conservative local reacquisition.
4. **Evidence-aware:** exactly the strong baseline's temporal scores, thresholds,
   alias detector and gyro uncertainty bound; additionally represents ambiguous
   alternatives and requests a future reference-map observation if it predicts
   a pairwise separation. A requested witness must be actually observed before
   it can license a correction. A planning result is **not** a certificate of
   physical distinguishability; map noise can cause false certificates.

See the constants in `adversarial_compass.py` for the executable specification:
256 angular bins, 64 detector rows, 360 samples/nominal revolution, 12 turns,
10 ms sampling, visual correction gain 0.30, alias warning threshold mean
cross-correlation >0.48 over ≥32 independent occupied bin pairs, gyro
uncertainty budget 0.06 rad + 0.10 rad/s since the most recent accepted anchor,
and an allowed alias-local correction only below half the suspected sector
separation (with a 5° margin). Witness horizon 180 samples.

### Adversarial scenes

`clean`, `repeat_exact`, `repeat_near`, `parallax_height`, `moving_objects`,
`timing_jitter`, `gyro_drift`, `speed_changes`, `blackout_turns`, `partial_map`,
`recovery_confuser`, `combined`. Some are intentionally out of the assumed
gyro-bias bound; that must not be silently treated as a recovered heading.

**Development seeds:** `5`, `11`. Algorithms/thresholds may be debugged against
these development cases only, with changed versions recorded.

**New frozen holdout seeds:** `101`, `211`, `307`, `401`. Do not inspect or tune
on these until the development implementation is committed and its initial CI
run is examined. Once opened, report every result, including failures; do not
silently discard seeds or change thresholds and keep calling them holdout.

## Metrics and audit

- Circular heading RMSE and maximum error, plus **unwrapped** RMSE (to expose
  missed revolution count). Every error is graded after map construction.
- **Incorrect accepted target**: visual target differs from actual heading by
  more than 10° circularly, regardless of whether the partial-gain update
  happens to have a small final error.
- **Harmful accepted correction**: partial update increases circular error by
  more than 5° over uncorrected gyro propagation.
- Heading availability: fraction with an accepted visual anchor no older than
  90 samples, masked off when camera data are absent. It is **not** airworthiness
  authorization or a calibrated probability of correct heading.
- Recovery: samples after the longest observation blackout to the first
  30-sample run of ≤5° circular error with an available visual anchor;
  otherwise `null`. This is graded externally.
- First-turn map coverage, accepted/deferred corrections, named ambiguity
  counts, feature pixel multiplies and bounded witness-search pair checks.
  Pixel multiply count is a hardware-neutral proxy, **not** device latency.

`audit_adversarial_compass.py` is separately written and does not import the
estimator. From the full JSON trace it reconstructs every per-timestep gyro
propagation and accepted update, checks absent cameras cannot cause an accept,
and independently regrades the above errors, recovery and acceptance safety.
This verifies recorded numerical summaries, not real-world fidelity or
the soundness of learned-map identifiability assumptions.

## Preserved negative result, before the alias guard

Development seed `5`: first witness-policy candidate had 49.9° RMSE on
`repeat_exact` and 116.2° on `repeat_near`, versus 38.4° and 75.3° for the
ungarded strong conventional estimator and 1.7° for the local matcher. With
`repeat_exact` the first incorrect strong-baseline global correction targeted
an alias 90.5° away; the first incorrect witness target was 178.5° away.
The candidate was **REJECTED**. Cause: the first-revolution reference contains
noise and quantization, which can make physically equivalent sectors appear
distinct to a finite single-sample witness selector. This must remain visible
in future comparisons, not be retroactively erased.

The alias guard is ordinary statistical engineering, not a formal MathGraph
breakthrough. An equally informed conventional baseline gets the same guard.
If the evidence-aware mode ties it, the result is a tie. A genuine advantage
still needs future independent, ambiguity-breakable scenes and real recordings.

## Epistemic status / next residual

- First-revolution synthetic causal map: **REUSABLE only within the declared
  procedural scene and test boundary**.
- Adversarial development suite: **CANDIDATE** until frozen CI and independent
  replay succeed; even then only bounded synthetic qualification.
- Perfectly periodic absolute heading without external/active distinguishing
  evidence: **UNKNOWN / conditional bounded obstruction**, not warranted full
  relocalization.
- Camera timing and line-scan hardware realism: **UNKNOWN**.
- Cheapest next experiment: independently re-run frozen holdout seeds, then
  test a partial-alias scene with genuinely distinguishable future landmarks.
