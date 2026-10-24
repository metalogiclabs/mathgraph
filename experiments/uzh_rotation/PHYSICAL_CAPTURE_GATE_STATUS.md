# UZH physical capture gate — evidence snapshot (2026-10-24)

Lineage: `exp/uzh-rotation-validation-20261021` → `exp/uzh-physical-gate-integration-20261024` → draft [PR #200](https://github.com/metalogiclabs/mathgraph/pull/200).

## WARRANTED within the declared CI boundary

[GitHub Actions run #40056737614](https://github.com/metalogiclabs/mathgraph/actions/runs/40056737614), job `120761252877`, on PR #200 after head commit `e4ad7087b63207cf9612e8db1722511c2b9b2c82`:
- 18/18 unit controls passed for structural sensor admission.
- 6/6 tests passed in the dedicated real-Docker isolation job, including an actual positive run and attempted forbidden encoder file access.
- All job steps concluded successfully. The workflow prints `PHYSICAL_HEADING_RECOVERY=UNKNOWN`.

The capture preflight now recomputes SHA-256 on camera, gyro, encoder and frozen-map files; reads and verifies native CSV timestamps for each stream, detects collisions and source/manifests disagreements; derives at least five turns from contiguous encoder source counters and a declared pulses-per-revolution; verifies independent calibration/holdout trace hashes, disjoint time windows, and numeric residuals against a declared frozen time offset and envelope. Negative tests reject relevant source forgery and corruption.

`physical_estimator_isolation.py` launches a separate Docker process with only estimator, camera, gyro and frozen map mounted as files. The run uses `--network none`, read-only filesystem, non-root uid, dropped capabilities and no host-workspace mount. The real-container test proves that the forbidden `/encoder.csv` is unreadable **in this test configuration**. This is process-level isolation for executions through that runner, not proof about arbitrary alternate estimator invocations.

## UNKNOWN / remaining physical obligations

- The inputs used by these gate tests are **synthetic fixtures**; no independently authenticated five-turn camera/gyro/encoder physical capture has been acquired.
- Encoder resolution and physical pulse integrity, index, mounting, gyro/camera clock reference and instrument authentication remain external assumptions.
- The calibrated numeric envelope is checked against supplied independent-reference CSVs, but those references are not cryptographically or physically authenticated, and a finite held-out pass is not a universal clock-error guarantee.
- Real onboard first-turn map construction through the new isolation runner, actual MathGraph heading-correction execution, benchmark baseline fairness, and encoder-only independent scoring remain untested.
- Map hash integrity does not establish that map construction was encoder-blind.
- The Docker image uses a mutable `python:3.11-slim` tag; freeze its digest before release qualification.
- Existing DARK-GS recordings do not supply two uninterrupted, gyro-measured rotations, much less this gate's five, and remain insufficient for corrected-heading claims.

## Current objective → residual → next experiment

Objective: demonstrate correction of drift over five camera-observed complete physical revolutions.

Residual: no five-turn independent ground-truth capture or corresponding estimator-vs-baseline scoring.

Cheapest decisive next experiment: collect camera-column, gyro and encoder data with independently checked timing; retain encoder exclusively for an independent scorer; freeze map after turn one; run a real MathGraph estimator and conventional baseline on identical allowed inputs inside the tested isolation boundary; publish paired angular errors and abstention/witness traces. Physical heading-correction status remains UNKNOWN.
