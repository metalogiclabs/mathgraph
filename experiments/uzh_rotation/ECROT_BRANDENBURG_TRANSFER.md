# ECRot Brandenburg transfer: original source diagnosis and V2 repair (2026-10-23)

**Epistemic status: REJECTED as evidence of a completed first revolution and later relocalization.**

## Evidence lineage

- V1 development code and frozen retrieval rule: \`62ddc79389f2f39c7a8782d8b378d9d95ca5a068\`.
- V1 success is only for Charlottenburg Palace, with a 1.0155-turn gyro proxy and one ambiguous short revisit. It remains immutable.
- Brandenburg Gate was identified as a different-scene holdout *before downloading*, in \`ecrot_sources.json\`, but is now **EXPOSED** and is not eligible for fresh prospective tuning.
- Independent diagnostic after exposure: [GitHub Actions #39870666780](https://github.com/metalogiclabs/mathgraph/actions/runs/39870666780), original ROS1 bag SHA256
  \`3d8e3284670c94b52919228c2a133586e8e592c07f3a6e1e127fee6acd747455\`.
- The source contains 6,295 IMU messages and five repeated IMU header/receipt times. The pre-existing strictly increasing timestamp integrator correctly refuses those repeated timestamps; this does not license silently shifting clocks.
- Positive-interval diagnostic y gyro integration gave **0.9934958 turns**, slightly under one full turn, with no external heading reference.

## Retrospective correction

\`audit_ecrot_brandenburg_v2.py\` compares original serialized IMU bytes as well as exact integer nanosecond header and bag receipt timestamps. It collapses only **byte-identical retransmissions**. Different messages sharing a timestamp, reversed times, malformed rates or an unverified source hash cause explicit UNKNOWN. It never sorts source observations or makes up a missing angular sector. If the cleaned gyro proxy is below 2π, it returns **INSUFFICIENT_FIRST_REVOLUTION** without building an artificial first-turn map or matching a “later” visual scene.

These rules are independently tested with explicit collisions, retransmissions, backward time, NaN rates and incomplete/complete synthetic turns. A nominal complete gyro turn is only \`ELIGIBLE_FOR_SEPARATE_VISUAL_REPLAY_ONLY\`, not heading permission.

## What this does and does not claim

Source authentic replay qualifies or disqualifies the inputs. It is **not** a visual-compass performance win, a proof of true angular coverage without independently bounded gyro error, a physically tested single-column camera, or a navigation-control authorization. The v1 cosine/ambiguity thresholds remain frozen; no test-derived improvement is claimed from Brandenburg. If duplicate records are not byte-identical, the truthful status is \`AMBIGUOUS_IMU_TIMESTAMP\` rather than “repaired source”.

**Residual:** Obtain an actual multi-revolution, timestamp-aligned real single-column camera/IMU recording; then test a forecasted separating observation against an equally informed robust conventional tracker on genuinely subsequent revolutions.
