# Joint gyro-bias + camera-clock re-jig — independently verified synthetic comparison

## Evidence and scope

- Research source branch: `exp/uzh-physical-gate-integration-20261024`, supplemental [PR #200](https://github.com/metalogiclabs/mathgraph/pull/200).
- Qualified exact source commit: `4bcc1d490f16405004890e25b57fb63afef17318`.
- [GitHub Actions #40244315456](https://github.com/metalogiclabs/mathgraph/actions/runs/40244315456), job `121322554197`, **SUCCESS**, including seven new joint-estimator negative tests; existing canonical 16 physical evidence gate controls and the native C99, source adapter, independent scorer and actual Docker isolation/replay were preserved and passed.
- [Retained Actions artifact #12617384767](https://github.com/metalogiclabs/mathgraph/actions/runs/40244315456/artifacts/12617384767) (`sha256:a4006e12113432bf3a0a6f88bd6660c743a9d94279c68149acaef5b6dff5b5ec`). Contains `joint_bias_clock_32seeds.json` and previous bounded replay/trial manifests.
- Implementation: `physical_joint_bias_clock_model.py`, tests: `test_physical_joint_bias_clock_model.py`.

**THIS IS NOT A RAW CAMERA OR HARDWARE EXPERIMENT.** The front-end supplies an artificially generated, 16-way sub-bin, relative optical-phase observation rather than a value obtained by matching original camera pixels to the physically captured first-turn reference. Real camera geometry, optical repeatability, blur, lighting and natural landmark aliasing are not admitted. No externally authenticated camera/gyro clock bound or physical data is present. Encoder/hidden true heading never enters any estimator and is used only in the separate synthetic grader. All outputs set physical authority FALSE.

## Model under test

Synthetic gyro phase integrates a constant or varying angular velocity with an unknown constant gyroscope bias. Camera reports a phase observation at an unknown clock offset. This deliberately favorable bearing-level study tests:

```
v(t) ≈ G(t + delta) - G(delta) - bias*t  (modulo 2*pi)
```

The gyro-only revolution index unwraps the phase in this model; incorrect unwrapping and aliasing are outside the guaranteed envelope. The bounded algorithm maintains a finite set of (`bias`, `delta`) pairs against all acquired relative-phase observations, with predeclared numerical tolerance, and abstains on no data, excessive bias width or infeasible intersections. Equal-input standard least squares and iterative robust Huber fitting receive the exact same fixed every-eighth-sample optical observations and gyro trace. Bias/clock priors are common. No future observations, physical encoder or hidden synthetic phase are read by any tracker.

Constants: 64 angular bins, 16 subbins per bin (synthetic optical quantization **0.3515625 degrees**), gyro bias grid ±0.030 rad/s with 121 points, clock offset grid ±40 ms with 33 points; tolerance 0.014 rad. The prior and clock grid should NOT be interpreted as calibrated hardware bounds. No adaptive camera trigger/energy measurement is made in this test.

## Frozen 32-seed matched comparator results

Mean **unwrapped** heading RMSE in degrees:

| Condition | MathGraph bounded | Ordinary LS | Robust Huber | Verdict |
| --- | ---: | ---: | ---: | --- |
| Constant speed | 0.13536 | 0.11054 | 0.11054 | LS/Huber better; clock unidentifiable |
| Variable speed | **0.26372** | 0.40899 | 0.40899 | MathGraph 35.5% lower RMSE |
| Variable speed, camera occlusion | **0.26758** | 0.41143 | 0.41143 | MathGraph 34.9% lower RMSE |
| Variable speed, camera-clock shift | **0.24503** | 0.32257 | 0.32257 | MathGraph 24.0% lower RMSE |
| Corrupt visual observations | 6.60190 | 15.53604 | **0.58622** | Robust Huber far better; MathGraph abstains / falls back to gyro |
| Slowly time-varying gyro bias | 5.27458 | **0.95397** | 0.96821 | Fixed-bias MathGraph assumption invalid; its purported bias interval can exclude hidden truth |
| Ambiguous visual frontend drops readings | **0.29305** | 0.42982 | 0.42982 | Optimistic abstraction, not real visual alias detection |

These are scenario means, not independent field trials; the underlying synthetic truths come from a narrow predefined family. **No broad statistical or physical superiority is established.**

## Necessary negative findings

1. **Clock identifiability**: with constant angular velocity, offset cancels from relative angular displacement; the declared clock interval stays the full 80 ms. Do not mark joint bias+clock warranted. Varying angular velocity produces bounded clock intervals only on some model frames, not a universal future-valid physical calibration.
2. **False confidence under wrong dynamics**: when bias changes, a fixed-bias interval can exclude the true *instantaneous initial bias* even in frames labeled model-bounded. This is a rejected physical assurance premise, not an acceptably certified interval. Runtime cannot detect every misspecification.
3. **Outlier cost**: three corrupted readings on the fixed acquisition schedule make the strict bounded set inconsistent, leading MathGraph to fail closed and rely on gyro. Conventional Huber wins badly on accuracy. Optimizing risk of false correction versus availability is the open problem.
4. **Sub-bin sensor gap**: optical phase is directly simulated and quantized to one-sixteenth of a 64-bin cell. The previous source-native `MGVC-PHYSICAL-1` camera-column matcher does not yet generate these inputs with calibrated sub-bin uncertainty.
5. **Equal-information baseline**: a robust estimator with an appropriately tuned bias-drift model may outperform every method here. Do not compare only against the original weak nearest-bin baseline.

## Independent vectorization oracle follow-up

[GitHub Actions run #40244770158](https://github.com/metalogiclabs/mathgraph/actions/runs/40244770158), source commit `c39a04a20cd6bd2c78dd2059a249d782bd520cc8`, completed **SUCCESS**. Both independent scalar tests in `test_physical_joint_bias_clock_oracle.py` passed:
- A separately written nested-loop exact oracle enumerated **all 3,993 finite (bias, camera-clock) candidates** for three source conditions, matching the optimized vectorized feasibility calculation.
- A corrupted acquired optical phase observation caused the strict joint feasible set to be empty in both implementations.

The same Actions run requalified the 32-seed × 7-condition matched conventional benchmark and the previously protected canonical physical gate, source adapter, native C99 and actual Docker isolation/replay. [Retained artifact #12618805061](https://github.com/metalogiclabs/mathgraph/actions/runs/40244770158/artifacts/12618805061) (SHA256 `f97214a063963c419fda71389721c008a1dee38a08aa2bec8525b59fa3657863`).

No independent **physical** sensor calibration, sub-bin image correspondence or gyro-clock hardware correctness is claimed by this software oracle.

## Recommended next *software* experiment (no hardware needed)

Integrate the bounded joint hypothesis set with **a source-native visual phase extraction path** that is learned from the FIRST camera revolution only, and evaluate it against an equally informed robust bias-plus-clock baseline (including changing bias, outlier handling and ambiguous landmarks). Gate any physical NAVIGATION output through the existing canonical `physical_evidence_gate.py`, never through a new permissive scoreboard. Require a prospective, genuine five-turn hardware source with isolated encoder to promote any physical claim.

**Current classification:** WARRANTED as bounded synthetic estimator/benchmark execution; some LS comparisons improve, robust Huber negative retained, physical beacon-free correction UNKNOWN.
