# Supplemental visual compass replay — reconciliation (2026-10-24)

## Canonical authority: existing physical-evidence gate, NOT this PR

The [canonical UZH branch](https://github.com/metalogiclabs/mathgraph/tree/exp/uzh-rotation-validation-20261021) already contained `PHYSICAL_EVIDENCE_GATE_PROTOCOL.md`, `physical_evidence_gate.py`, `physical_encoder_score.py` and `.github/workflows/mathgraph-physical-evidence-gate.yml` **before** this integration branch. Its [Actions 40047078690](https://github.com/metalogiclabs/mathgraph/actions/runs/40047078690) exercised 16 adversarial tests and [Actions 40047078699](https://github.com/metalogiclabs/mathgraph/actions/runs/40047078699) qualified separate navigation/referee artifact jobs. Its encoder referee scores **unwrapped** revolutions 2–5 and checks actual optical first-turn freeze. These are the canonical physical evidence and safety boundaries; do not replace them with this branch's weaker CSV manifest gate or a modulo-360 scoreboard.

This draft [PR #200](https://github.com/metalogiclabs/mathgraph/pull/200) is a **supplemental estimator-replay experiment**, not a replacement of the original physical gate. Duplicate manifest and calibration code should be removed or explicitly scoped to synthetic test infrastructure before any merge. No upstream Joshua drone repository has been changed.

## New bounded result: WARRANTED in CI, SYNTHETIC only

[Actions 40058373670](https://github.com/metalogiclabs/mathgraph/actions/runs/40058373670) passed original 16 protected hardware-gate tests **unchanged**, plus 18 supplemental source preflight tests, 13 replay controls, 6 isolation controls, a real Docker encoder-denial test and a real Docker full six-turn synthetic replay. The physically separate firstturn-map and heading-estimator Docker invocations expose only camera, gyro and first-turn map; an encoder is not passed into either. Original-source identities and hardware attestation remain outside this test.

Synthetic generator `physical_column_demo.py` creates six simulated turns, 16-bit columns and gyro bias (no physical recordings). Causal `physical_column_replay.py` builds the first-turn map and then produces a **model-only** heading estimate and an equally informed conventional nearest-column baseline. Independent `physical_encoder_scorer.py` reads synthetic encoder counts **only after** estimator output is frozen. It refuses a first-turn freeze before optical revolution 1 and reports unwrapped heading errors so a 360-degree slip cannot be concealed by circular normalization. Real-container and adversarial tests exercise firstturn map reconstruction, changing future images without changing firstturn contents, scene changes, occlusions, repeated scenes, source timestamp tampering, encoder denial and false physical authority claims.

Deterministic 320 held-out model frames:
- Gyro-only unwrapped heading RMSE: **8.3455507002 degrees**
- MathGraph bounded witness/abstention estimate: **3.0280012441 degrees**
- Equal-information conventional nearest-column baseline: **2.8125000000 degrees**
- MathGraph versus gyro-only: **63.72% error reduction** (synthetic model, not hardware).
- Conventional accuracy advantage: **0.21550 degrees lower RMSE**. A MathGraph heading-accuracy advantage is **REJECTED for this frozen fixture**, not broadly disproved.
- Correction authority: `navigation_correction_authorized=false` for every event; no onboard correction was sent. The planner makes requests but the fixture does NOT establish prospective physical sensor acquisition.

## Epistemic classification

- **WARRANTED (bounded software):** firstturn map and estimator are encoder-blind for these Docker invocations; reproducible causal model replay and independent unwrapped synthetic scoring, with source-integrity, occlusion and ambiguity negative controls. Existing canonical source/role gate protected.
- **REJECTED (specific frozen fixture):** claimed synthetic heading-RMSE superiority over an equally informed conventional nearest-column tracker.
- **CANDIDATE:** single-column finite-witness model implementation and distinguishing-observation requests.
- **UNKNOWN:** encoder/clock physical authenticity and bounded future timing error, real five-turn source capture, genuine heading recovery, request-triggered sensor acquisition, independent physical accuracy, runtime/power on Joshua's hardware.
- **SUPERSEDED as merge scope:** any notion that supplemental CSV manifest gate replaces canonical v1.1 original NAVIGATION/ENCODER role-disjoint contract.

## Next decisive experiment

Use the canonical separate `mgvc-navigation-raw-v1` and `mgvc-encoder-raw-v1` hardware bundles. Capture five uninterrupted secured-rotor revolutions with independently bounded camera/gyro/encoder clocks, freeze first-turn reference from navigation inputs alone, and invoke existing [physical evidence workflow](https://github.com/metalogiclabs/mathgraph/actions/workflows/mathgraph-physical-evidence-gate.yml). Apply the supplemental column estimator and conventional comparison on identical camera/gyro observations, then let the independent optical referee adjudicate. Preserve UNKNOWN if clock/hardware attestation, source identity, turn coverage or separating-observation causality is missing.
