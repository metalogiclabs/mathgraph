# Physical capture gate: qualification boundary

Branch lineage: exp/uzh-rotation-validation-20261021 -> exp/uzh-physical-gate-integration-20261024.

## Implemented (candidate; CI result not yet independently confirmed)
- Source-file SHA-256 verification and monotonic declared timestamp checks.
- Encoder edge CSV requires timestamp_ns and unwrapped_count.
- Count increments must equal +1 with strictly increasing source timestamps.
- Minimum five turns derived as floor((last_count - first_count)/pulses_per_revolution), not taken from a manifest claim.
- Adversarial tests reject incomplete turns, count gaps, clock omissions, tampering, and encoder source/manifest timestamp disagreement.

## Unresolved and deliberately not warranted
- Encoder resolution, direction, absolute zero, index pulse and physical attachment are still asserted metadata, not independently authenticated.
- A source CSV can be internally consistent but fabricated; no capture-device signature or raw hardware provenance is checked.
- Camera/gyro timestamp lists are manifest declarations rather than parsed original source records.
- Timing calibration is currently a manifest SHA plus a Boolean, not independent numerical residual validation.
- Encoder isolation is an attestation, not a process-level sandbox preventing estimator access.
- No scorer computes gyro-only versus corrected heading errors against independent encoder truth.
- No five-revolution physical capture has been acquired.
- Existing DARK-GS 360 and 360_2 data remain rejected for complete repeated-turn physical validation.

## Next cheapest decisive work
Replace manifest-declared camera/gyro timestamps and timing-calibration Boolean with independently parsed source logs and a frozen numerical calibration envelope. Enforce estimator input isolation by construction. Then replay real five-turn data through existing first-turn map and matched conventional tracker. Until that occurs: physical heading correction UNKNOWN.
