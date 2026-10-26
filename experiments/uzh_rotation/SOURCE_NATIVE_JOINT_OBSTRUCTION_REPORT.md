# Source-native 16-bit visual compass: joint bias/clock obstruction and safe abstention

**Scope:** independently executed *synthetic* gyro/camera joint model, with actual 16-bit per-column signatures as the NAVIGATION interface, not an invented high-precision optical phase sensor. [MathGraph draft PR #200](https://github.com/metalogiclabs/mathgraph/pull/200). No original UAV five-turn recording, image photometry, physical source certification, or flight authorization.

## Why this experiment was necessary

The preceding `physical_joint_bias_clock_model.py` supplied a **synthetic sub-bin visual-phase sensor**, thereby bypassing the actual 16-bit camera-column descriptor bottleneck. Its favorable 0.264-degree variable-speed result is not evidence that raw camera pixels deliver such phase measurements. This study instead synthesizes a stationary 64-position 16-bit angular panorama. Each camera sample provides only a timestamp, one 16-bit column, and a usable/missing flag. The first 360-degree gyro-estimated turn constructs a frozen 64-bin reference; disagreeing duplicates are quarantined. Later 16-bit columns eliminate joint bias/clock/drift candidates only if they are incompatible with every allowed ±1 angular-bin shift and with the frozen reference. Missing first-turn cells never count as contrary evidence.

The candidate grammar has **17 clock offsets × 41 initial gyro biases × 5 bias-drifts = 3,485** finite states, with an assumed visual Hamming budget of 2 and one possible matching exception. Independent synthetic truth remains in a separate grader, never passed to map-building, estimation, source column selection, or the equal-source conventional capped-Hamming grid comparator.

Clock offsets ±40 ms, sensor noise and angular-grid uncertainty are **declarations** for the finite model, not calibrated hardware bounds. The source generator creates one-bit corrupted original and later columns, actual scene aliases, source-visible occlusions and selected random outliers; no artificially precise bearing stream.

## Source and causality gates

- `physical_source_native_joint.py` uses only camera/gyro source arrays for the map and estimator. Source-native `MGVC-PHYSICAL-1` NAVIGATION-adapter CSV can also enter its offline CLI, but only with the separately produced `adapter_evidence.json` retaining original NAVIGATION manifest/source hashes and checking converted file hashes.
- A source packet must have a strictly increasing timestamp; the gyro is integrated from samples **available in its past only**, and extrapolation beyond 20 ms is rejected rather than retrospectively interpolating from future packets.
- Because unknown camera–gyro offset extends to +40 ms, an offline record explicitly labels its earliest permissible gyro-informed decision time **40 ms after the camera timestamp**. This is *not* an onboard real-time algorithm or a claim that real hardware can meet that delay.
- Canonical `physical_evidence_gate.py`, `physical_encoder_score.py`, C99 sparse map and separated original NAVIGATION/ENCODER gate remain unchanged.

## Frozen 32-seed model results (mean unwrapped RMSE in degrees)

| Synthetic condition | Gyro only | MathGraph feasible-set midpoint **diagnostic** | Same-source conventional capped-Hamming grid |
| --- | ---: | ---: | ---: |
| Steady rate | 5.0348 | 1.6447 | 4.5607 |
| Varying rate | 4.9173 | 2.8122 | 2.9810 |
| Camera-clock shift | 4.9173 | 2.1847 | 3.7453 |
| Linear gyro bias drift | 4.9494 | 2.1079 | 4.1627 |
| Missing camera period | 4.9173 | 2.3992 | 3.4966 |
| Four identical visual sectors | 4.9173 | 2.7609 | 2.9810 |
| Three corrupted columns | 4.9173 | 3.7445 | 3.9516 |

**The decisive result is NOT those point estimates.** Under the frozen, relatively demanding maximum heading-interval width **0.07 rad (~4.0 degrees)**, the model admitted **zero narrow intervals in every tested condition**. It therefore cannot justify a corresponding heading correction. Its midpoint is an untrusted diagnostic. The robust conventional comparator is a reproducible capped-Hamming *heuristic*, not a tuned best-available visual-inertial filter; apparent RMSE advantage over it does not establish algorithmic superiority.

## An adversarial source exposes false confidence

With three genuinely corrupted, actually acquired camera columns, a version checking only the strict one-outlier feasible set produced misleadingly **narrow intervals excluding the true simulated heading**. A separate synthetic grader demonstrated this while never supplying truth to the estimator.

We added a sensitivity check that also tests the **three-outlier feasible set** before labeling an interval model-narrow. It withdraws all such narrow claims in the frozen 32-seed experiment rather than promoting a bad correction.

Post-hoc risk/coverage inspection makes the design tradeoff explicit (32 seeds, ~18,880 post-firstturn frames per condition):

| Maximum projected heading-set width | Varying-speed scenario eligible frames / false intervals | Corrupted-image scenario eligible frames / false intervals |
| --- | ---: | ---: |
| 0.07 rad (4.0°) | 0 / 0 | 0 / 0 |
| 0.10 rad (5.7°) | 96 / 0 | 96 / 0 |
| 0.20 rad (11.5°) | 2,432 / 0 | 2,432 / 0 |
| 0.30 rad (17.2°) | 8,226 / 0 | **12,420 / 3,184** |
| 0.50 rad (28.6°) | 18,741 / 0 | **18,561 / 3,184** |

**These are retrospective diagnostics, not a valid method of choosing a safety threshold from held-out truth.** The sharp corrupted-source failure shows why looser numeric gates cannot be used to create an apparent positive demonstration.

## Evidence and residuals

- [Original source-native 32-seed CI #40250618292](https://github.com/metalogiclabs/mathgraph/actions/runs/40250618292) passed nine raw-source controls, the independent scalar candidate checks and all original protection/isolated Docker controls.
- [Causal source-version CI #40250956622](https://github.com/metalogiclabs/mathgraph/actions/runs/40250956622) passed original gates plus past-only gyro support, bounded age and clock-delay controls.
- [Risk–coverage CI #40251196356](https://github.com/metalogiclabs/mathgraph/actions/runs/40251196356) passed the 32-seed frontier and retained its false-confidence counterexample.
- The `MGVC-PHYSICAL-1` NAVIGATION source-receipt roundtrip additionally prevents a mismatching CSV from being silently used as qualified original source.
- No actual optical encoder was provided to the navigator. Grading uses separate known **synthetic** hidden truth. No five physical revolutions, flight, power draw, inertial source calibration or future-valid timing bound has been measured.

**Next scientifically decisive change:** preserve richer raw grey-level camera-column intensities, or collect more genuinely distinctive temporal views, so the joint bias/clock/heading set can narrow on fresh observations rather than by choosing an unsafe tolerance. Compare with an equally informed tuned conventional robust estimator, not only the capped-Hamming baseline. An encoder-only independent physical referee remains mandatory for any eventual heading correction claim.

**Verdict:** source-native software qualification and model counterexample WARRANTED; beacon-free physical heading accuracy, robust conditional correction and energy advantage **UNKNOWN**.
