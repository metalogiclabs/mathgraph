# MathGraph Claim Assurance: independent rover software-contract transfer

Status: source-native research. **No JPL upstream writes/contact, no deployed rover
test, no institutional endorsement.** Draft MathGraph only, no release authority.

## Why this authentic case

The actual [JPL Open Source Rover](https://github.com/nasa-jpl/osr-rover-code)
has ROS-independent pure kinematics in
\`ROS/osr_control/osr_control/kinematics.py\`. Its own
\`RoverKinematics.body_speed_for_radius\` docstring describes a speed clamp so
each drive wheel stays within \`max_vel\`; the repository's actual
\`test_body_speed_keeps_every_wheel_within_max_vel\` and
\`test_body_speed_for_radius_clamps_reverse\` execute this contract. The
test-encoded requirement is **not** an independently accepted flight-system
safety requirement.

- Exact public source: \`nasa-jpl/osr-rover-code@7aaf18512c9e8a997931f0caae28b63c8c6e9a78\`
- Implementation Git blob SHA1: \`38e35e5823111808177d78427a1595d27d0ebe00\`
- Authored test Git blob SHA1: \`5860abcdd690f4c62f912e79ebfdd84d0817b4ae\`
- Native evidence: unmodified upstream pytest module and selected wheel-speed
  tests under Python 3, \`pytest==8.4.2\`.
- MathGraph evidence: separate 70-case wheel-geometry grid (10 signed valid
  nonzero radii × 7 commanded speeds), raw observations and a checker
  using an independently written scalar geometry calculation.
- Adversarial native evidence: one local-only mutation removes the body-speed
  limiting return and makes the **same upstream** speed-bound tests fail.
  No claim of an existing upstream software defect is made.
- Out-of-scope evidence: hardware emergency stop, traction, wheel-actuator
  response, ROS signalling, timing guarantees, physical terrain control,
  Endurance mission software or flight-certified safety.

The external source is not part of the Pinto/Wagner/Havelund/Rouquette
2026 life-cycle assurance paper's actual case-study evidence. This is an
**independent JPL public educational rover** case motivated by that
publication, not a reproduction of its proprietary or nonpublic assurance
case.

## A claim must identify the proposition, its source and its exact test

The valid bounded claim is deliberately narrow:

\`OSR_KINEMATICS_WHEEL_SPEED_BOUND\`

A proof receipt must bind the author \`body_speed_for_radius\` docstring,
the actual \`test_body_speed_keeps_every_wheel_within_max_vel\` source AST,
the selected passed author test execution, the source hash, the raw
finite observation records and their independently checked numerical
limits, and the retained original-test-induced-regression.

The independent checker has **no imports from the source-native runner** and
does not assume that a green pytest exit authorizes any other claim.

| Control | Changed premise from same real retained evidence | Expected |
|---|---|---|
| Positive | Exact revision, authored requirement and original selected test + finite grid pass | \`WARRANTED_BOUNDED\` |
| Wrong target | Another genuinely passing rover test attributed to wheel-speed claim | \`MISMATCH\` |
| Stronger scope | Claims this proves flight-hardware / end-to-end safety | \`UNKNOWN\` |
| Stale source | Exact source revision no longer matches | \`WITHDRAWN\` |
| Wrong scientific function | E-stop requirement claimed from wheel-speed tests | \`UNKNOWN\` |
| Missing evidence | Withhold original native record | \`WITHDRAWN\` |
| Forged native outcome | Alter mutant's recorded failed exit to success | \`REJECTED_EVIDENCE\` |
| Forged geometry | Alter one measured wheel value, preserving source and test identities | \`REJECTED_EVIDENCE\` |
| Wrong source-test bytes | Replace authentic test Git blob identity in record | \`REJECTED_EVIDENCE\` |

The eight adversarial controls above are probe mutations, not eight
distinct rover defects. **No assertion of a theorem for all inputs.**

## Strong conventional baseline

The native \`pytest\` suite is our competent preexisting *software-testing*
baseline. It catches the induced body-speed mutant on the same authored test.
An *unaugmented CI green signal alone* has no binding to a separately asserted
requirement and remains green even if an unrelated test is cited. MathGraph's
additional gate refuses wrong target attribution and scope inflation.
This does **not** establish superiority over a fully informed competent human
reviewer or a conventional provenance-aware test/requirements system.
Claim identity is a predeclared author-sourced contract, not inferred natural
language understanding.

## Reproduction and provenance

The MathGraph-only workflow \`.github/workflows/mathgraph-claim-assurance-rover.yml\`
performs exact detached JPL source checkout (read-only) and native replay,
retains \`native-observation.json\`, the original and induced-fault pytest
logs, 70 numerical source observations, \`CLAIM_ASSURANCE_RESULT.json\`,
all source/evidence hashes and the exact pytest environment. GitHub Actions
archives them on both success and failure. A source-test mismatch or missing
receipt must fail closed. Deliberately mutated code runs from a separate
local \`results/mutant/\` package and is never applied to the authentic repo.
