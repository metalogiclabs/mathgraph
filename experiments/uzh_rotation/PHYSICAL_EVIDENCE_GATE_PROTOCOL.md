# MathGraph Visual Compass — five-revolution Physical Evidence Gate (v1)

**Purpose:** run a five-revolution experiment on a real one-pixel-wide camera column, gyro and physically separate optical encoder. Navigation may use only camera and gyro; the encoder is a referee, not a compass input. The existing C99 first-turn interval capture, 64-bin reference map, finite ambiguity planner, and physical-reference research on \`exp/uzh-rotation-validation-20261021\` remain unchanged. This is a **logging, verification, and scoring harness**, not a replacement estimator or a flight demonstration.

## Current actual result

**UNKNOWN — NO PHYSICAL CAPTURE HAS BEEN SUBMITTED OR SCORED.** The CI self-tests create only intentionally labeled \`FIXTURE\` packets, exercise the code and test failure paths. Scores on fixture packets MUST NOT be represented as physical accuracy or the achievement of any user acceptance criterion.

## Required apparatus and human evidence

- Rigid single-axis spinning rig or secured, nonflying aircraft. Start with bench testing: no motors/rotors exposed to people. Real onboard gyro; single linear optical sensor or one physically captured fixed pixel column; visual surroundings include repeated and nonrepeated landmarks.
- Separate calibrated optical encoder with *unwrapped* cumulative ticks and published/measured counts per revolution. Its electrical/logging path must NOT enter the device running the navigation code, camera input, gyroscope input, motor controller or online confidence policy. Record independent electrical isolation and wiring photographs separately.
- Common monotonic nanosecond capture clock or independent synchronized hardware pulse edges: at least five calibration pulse pairs, source device IDs, measured skew and a conservative uncertainty budget. An observed maximum residual is **not** itself a guaranteed future bound. An external calibration/attestation procedure is still needed to promote the physical bound.
- Independent immutable build identity, hardware serials, column geometry and scene configuration. Log all observations and negatives, including occlusions, dropped columns, requests, actual acquisitions and visual confusion.
- Capture the first revolution as training only, freeze once, then acquire and score revolutions 2–5. Pre-designate experimental conditions: normal reference, imposed bias/drift, masked frames or occlusions, repeated/ambiguous landmarks, and active separation; use multiple physical runs if all conditions cannot coexist. Never pick the clearest run post hoc and call it held-out.
- Freeze method, camera normalization, byte source schema, noise assumptions, bounds, sensor timing, reference identity, conventional comparison policy, and scoring script SHA *before* inspecting reserved physical capture scores.

## Two role-disjoint immutable artifact bundles

\`mgvc-navigation-raw-v1\` must contain only:

\`\`\`
nav_manifest.json
sensors.jsonl
decisions.jsonl
timing.json
\`\`\`

\`nav_manifest.json\`:
\`\`\`json
{
  "schema": "MGVC-PHYSICAL-1",
  "capture_id": "some_unique_capture_id",
  "role": "NAVIGATION",
  "mode": "PHYSICAL",
  "files": {
    "sensors.jsonl": {"sha256": "64_lowercase_hex", "bytes": 123},
    "decisions.jsonl": {"sha256": "64_lowercase_hex", "bytes": 123},
    "timing.json": {"sha256": "64_lowercase_hex", "bytes": 123}
  }
}
\`\`\`

Every JSONL row carries contiguous integer \`seq\`, strictly increasing integer \`t_ns\`, and \`kind\`. Camera/gyro log row types:

- \`GYRO\`: \`{"seq":0,"t_ns":...,"kind":"GYRO","omega_rad_s":...}\` (one declared signed *spin-axis* component; calibrated alignment and orientation are an external qualification).
- \`COLUMN\`: \`{"seq":1,"t_ns":...,"kind":"COLUMN","status":"OK","column_u16":43690}\` or \`"status":"OCCLUDED","column_u16":null\`. Exactly 16 binary pixels in this v1 finite grammar, not an arbitrary RGB column, direct encoder reading or ground-truth-derived image. A real hardware adapter must declare how its physical column is converted into these bits.

The capture \`timing.json\` has **exactly** \`capture_id, source, independent_reference, nominal_skew_ns, error_bound_ns, witness_pairs, calibrated_before_ns, valid_through_ns, max_gyro_rad_s, integration_error_rad\`. \`source\` must be \`independent_reference_pulses\`; witness pairs contain \`camera_ns\` and \`gyro_ns\`. The auditor requires at least five in strictly increasing source order, checks their residuals against the claimed bound, source validity for the entire recording, and confirms that measured gyro rates stay inside the declared speed envelope. It computes a *minimum required 16-bit phase uncertainty radius* from the supplied timing and integrated gyro budget. **These are declared physical premises; no certificate signature or external metrological error-bound verification is present yet.**

Navigation decision rows: \`MAP_CAPTURE\` (camera sequence ID, \`phase_u16\`, \`radius_u16\`, \`disposition\`), \`FREEZE\` (SHA256 of canonical frozen 64-bin/quarantine map), \`REQUEST\` (heading candidate set, target \`step_bins\`, boolean \`witness_predicted\`), \`MATCH\` (causal postfirstturn camera ID, pre/post candidate sets, target step, optional earlier request ID), \`ESTIMATE\` (unwrapped \`fused_heading_rad\`, \`correction_delta_rad\`, \`authority\` \`WARRANTED|UNKNOWN\`, \`support_camera_seq\` or null), \`WITHDRAW\` (reason). All navigation decisions must be generated **by the actual estimator** during replay, not fabricated to agree with the encoder later. This harness recomputes fine-bin interval eligibility, duplicate/quarantine handling, map freeze, a bounded ±1-bin/2-Hamming candidate filter and existence of a prospective separating pair independently of the estimator's claimed result. No future camera image is permitted to enter the map; unsupported or stale visual corrections fail.

\`mgvc-encoder-raw-v1\` must contain only:

\`\`\`
encoder_manifest.json
encoder.jsonl
\`\`\`

\`encoder_manifest.json\` pins the exact SHA256 and byte count of \`encoder.jsonl\`, uses the SAME \`capture_id\`, \`mode\`, and exact navigation manifest SHA256, and additionally provides \`counts_per_revolution\` and \`encoder_to_navigation_clock\` containing \`offset_ns, bound_ns, independent_reference, source, pulse_pairs, max_interpolation_gap_ns\`. \`encoder.jsonl\` rows are \`{"seq":0,"t_ns":...,"ticks_unwrapped":...}\`. A supplied reset, backwards time or ambiguous tick-wrap fails instead of silently crossing revolutions. Interpolation across an unsampled gap larger than the independently declared maximum returns UNKNOWN for that score sample.

**Process boundary:** GitHub Actions has **separate, non-shared jobs**: navigation/audit job downloads ONLY \`mgvc-navigation-raw-v1\`; encoder/referee job downloads ONLY \`mgvc-encoder-raw-v1\` and the navigation-audit result. The navigation job must never download, copy, inspect or import encoder bytes or encoder artifacts. Published artifacts contain source hashes, adjudication and derived scores, but no raw hardware recordings unless intentionally uploaded by the capture owner.

## Encoder-isolated scoring

For each actual navigator \`ESTIMATE\` time, the separate referee independently interpolates *unwrapped encoder ticks* in its own clock domain after applying an independently documented pulse-reference offset. Compare gyro-only ZOH integration and the onboard fused estimate to the same encoder displacement, both referenced to the first estimator output (a gauge choice made only in the referee). Report unwrapped angular RMSE in **degrees** per optical revolution 2, 3, 4 and 5, plus overall RMSE, raw error reduction and source-alignment exclusions. Scoring never feeds truth-derived lag, pose, phase, confidence or rank into the navigator.

The exact policy-replay checks are more restrictive than arbitrary reported confidence: map cannot mutate after freeze; candidate removal requires an actual observed column, bounded slip and source-supported Hamming mismatch; UNKNOWN cannot apply a new correction; an occlusion or unassimilated intervening image prevents a stale source from authorizing a fresh correction; a \`REQUEST\` is a future hypothesis-dependent observation and becomes acquired only when linked to a later real camera sample.

The main physical acceptance gate must remain **RED/UNKNOWN until**: (1) all five turns independently recorded by optical encoder, (2) each held-out turn has genuine estimates, (3) reduced error relative to same-sensor gyro-only, (4) occlusion and ambiguity demonstrably force permission withdrawal, (5) separating observation is actually requested/acquired, (6) calibrated *physical* timing uncertainty is externally attested, (7) camera/fingerprint stationarity and motor-to-sensor alignment assumptions are independently qualified, and (8) the device's encoder isolation and logged binary provenance are attested. Exact numeric error thresholds are not preselected as a capability claim.

## CI and interpretations

\`mathgraph-physical-evidence-gate.yml\` runs adversarial **FIXTURE-only** tests on push. It checks manipulation of hashed logs, impossible sensor clocks, encoder leakage into the navigator, false calibration pulse bounds, phantom camera matches, post-freeze mutation, stale occlusion authority, score recomputation and five-turn coverage. Separate manual \`workflow_dispatch\` takes two existing Actions run IDs and downloads their **named source artifacts in separate jobs**. No upload has happened yet; running just harness CI is **not** a physical capture.

The independent encoder referee intentionally reports \`hardware_and_future_bound_attestation=NOT_IMPLEMENTED\`. Even if the self-declared capture mode says PHYSICAL, the workflow cannot promote that assertion to a green hardware result. The explicit promotion job fails unless future separately trusted hardware attestation is implemented and verified. This is an implementation gap by design, not something to bypass by changing thresholds or flipping an output bit.

**Source method continuity:** C99 \`firstturn_fine_capture.c\` and \`firstturn_source_obligation.c\` remain unchanged. The navigation audit reproduces their finite acceptance concept and must be reconciled with exact on-device traces in real captures. It cannot prove a fabricated \`fused_heading_rad\` was actually produced by the rig solely from JSON; signed/attested firmware and recorder identity are needed. No Joshua Bird upstream repository or motor-control PR is touched.
