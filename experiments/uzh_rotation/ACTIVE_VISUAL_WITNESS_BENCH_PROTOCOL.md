# MathGraph Visual Compass — active sensing and robust passive landmarks

**Status: WARRANTED in finite synthetic CI only. Physical gyro-correction and autonomous camera scheduling remain UNKNOWN.** This is an additive research deliverable for Joshua Bird's single-propeller drone. No changes were made to his ArduPilot or moteus repositories, and nothing here authorizes flight.

## Which evidence is authoritative?

The original `exp/uzh-rotation-validation-20261021` branch already has the **canonical** role-disjoint physical experiment contract: `PHYSICAL_EVIDENCE_GATE_PROTOCOL.md`, `physical_evidence_gate.py`, `physical_encoder_score.py` and `mathgraph-physical-evidence-gate.yml`, including independent encoder ground truth and unwrapped heading errors. It also **already** has the production-oriented, jitter-aware 146-byte `MGReferenceMap` and minimum-witness C99 selector in `finite_partial_map.c/.h`. That source predates this supplemental PR and is unchanged. The initially drafted duplicate standalone C99 scheduler was deliberately withdrawn from the PR; its exploratory commits remain in history.

Supplemental [PR #200](https://github.com/metalogiclabs/mathgraph/pull/200) supplies independent synthetic experiments, source-faithful NAVIGATION/JSONL conversion, Docker-isolated firstturn replay and independent test harnesses. The existing reference-map guard and physical referee remain authoritative.

## 1. Active sensing with equal-model continuous reference

[Independent CI 40148357936](https://github.com/metalogiclabs/mathgraph/actions/runs/40148357936) and [latest integrated CI 40149309813](https://github.com/metalogiclabs/mathgraph/actions/runs/40149309813) verify a frozen census of **768 synthetic trials**: 32 seeds, four heading candidates, six stress conditions.

- In 128 clean distinctive-landmark trials, MathGraph requested 2 camera observations per trial and identified heading at angular step 13; a conventional continuous set-valued tracker with the same frozen firstturn map, candidate prior and noise model used 13 frames and resolved at the same step. **256 versus 1,664 requested/attempted observations = 84.615% reduction**; no incorrect model-unique decisions.
- Missing landmark at step 7, step 13, or both could be overcome by later separating views in the bounded repeating-scene model. All 128 trials blocking every useful step (7, 13, 23, 29) returned UNKNOWN; all 128 intrinsically unbreakable scenes returned UNKNOWN.
- `audit_physical_active_acquisition.py` independently replays every requested source observation and candidate elimination, exhaustively checks minimum nonadaptive pair-cover basis sizes within the declared grammar, and refuses forged requests, false obstructions, incorrect heading evidence or physical claims.
- The equal-model conventional tracker **receives more observations**. Savings in the model are not evidence of measured battery savings or superiority over an equally informed *optimized active* conventional sensor scheduler. The minimum is for this **finite nonadaptive pair-cover grammar**, not a globally optimal adaptive sensing theorem.

## 2. Existing C99 core under assumed phase uncertainty

The original `finite_partial_map.c` (146-byte map, memory-bounded exact pair-cover DP, map holes/quarantine) is reused through `physical_native_witness_replay.py`. No duplicate C99 implementation survives in the supplemental PR.

[Native run 40149085303](https://github.com/metalogiclabs/mathgraph/actions/runs/40149085303) and latest [40149309813](https://github.com/metalogiclabs/mathgraph/actions/runs/40149309813) pass the existing original C99 regression suite, six new native bridge controls, and the exact 768-trial Python/native parity census for **jitter=0**. Under **assumed ±1 bin uncertainty** the original narrow landmark scene has 0/128 guaranteed identifications and 128/128 UNKNOWN: the planner correctly refuses to infer a robust heading.

These are model phase-error envelopes; the source timing is not independently calibrated or physically warranted.

## 3. Passive landmark width required by a deliberately controlled test scene

The `physical_landmark_width_design.py` experiment constructs a **four-sector synthetic passive fiducial**. Each sector repeats a broad 16-bit vertical-column marker drawn from `0x0000, 0xFFFF, 0x0F0F, 0xF0F0`. Training and later observations independently contain at most one corrupt bit each (assumed total Hamming difference ≤2). The original native C99 planner considers every allowed actual phase shift in ±j angular bins. Each bin is 360°/64 = 5.625°.

For this deliberately isolated-marker geometry, **width ≥ 2j+1 bins** guarantees each heading is separated at the marker center:

| Assumed phase uncertainty | Minimum tested broad marker | Shift-swept model correct | Narrower tested markers |
| --- | --- | --- | --- |
| 0 bins | 1 bin = 5.625° | 64/64 | — |
| ±1 bin | 3 bins = 16.875° | 192/192 | UNKNOWN |
| ±2 bins | 5 bins = 28.125° | 320/320 | UNKNOWN |
| ±3 bins | 7 bins = 39.375° | 448/448 | UNKNOWN |

Across all sixteen width–jitter conditions and 4,096 synthetic source-shift cases, no false unique headings were admitted under the declared noise envelope. [Independent CI 40149309813](https://github.com/metalogiclabs/mathgraph/actions/runs/40149309813), retained [artifact 12581607445](https://github.com/metalogiclabs/mathgraph/actions/runs/40149309813/artifacts/12581607445).

This is a **sufficient construction for this artificial four-sector source**, NOT a universally necessary landmark width for real-world camera observations. Neither real camera contrast, optics, image blur, yaw/body dynamics, sensor throughput nor phase calibration has been measured. Broad visual markers could make an early secured test stand easier, but are not proof of beacon-free natural-scene flight.

## 4. Important negative control

A deliberately changed source observation that exceeds the assumed noise bound can produce a **wrong model-unique heading**. The independent post-hoc grader catches that false correction, but the online estimator cannot generally distinguish a coordinated scene spoof from a real heading change. Accordingly physical stationarity, calibrated timing and genuine source-error bounds remain indispensable. All runtime outputs in these experiments keep `physical_navigation_authorized=false`.

## 5. Reproduce the evidence

```bash
python -m unittest discover -s experiments/uzh_rotation -p 'test_physical_active_acquisition.py' -v
python experiments/uzh_rotation/physical_active_acquisition.py --seeds 32 --output active_acquisition_census.json
python experiments/uzh_rotation/audit_physical_active_acquisition.py active_acquisition_census.json --output active_acquisition_audit.json
python -m unittest discover -s experiments/uzh_rotation -p 'test_physical_native_witness_replay.py' -v
python experiments/uzh_rotation/physical_native_witness_replay.py --seeds 32 --output native_active_acquisition_census.json
python -m unittest discover -s experiments/uzh_rotation -p 'test_physical_landmark_width_design.py' -v
python experiments/uzh_rotation/physical_landmark_width_design.py --seeds 16 --output passive_landmark_width_grid.json
```

The original [canonical physical evidence gate](https://github.com/metalogiclabs/mathgraph/blob/exp/uzh-rotation-validation-20261021/experiments/uzh_rotation/PHYSICAL_EVIDENCE_GATE_PROTOCOL.md) remains separately verified and cannot be bypassed by passing any of these commands.

## Smallest decisive real-world next experiment

Once independent hardware is available, build a *secured, unpowered or guarded rotating* camera/gyro fixture with an isolated optical encoder. Start with a broad 3-bin high-contrast passive marker for a declared ±1-bin phase model, but independently measure and freeze camera/gyro/encoder timing error before interpreting physical results. Record at least five complete revolutions, build/freeze map on the first, then compare MathGraph's active requests with continuous and optimized active conventional baselines on heldout turns; validate per-turn unwrapped heading error through the canonical separated encoder referee.

**Not yet obtained:** real camera observations spanning five turns, a calibrated future-valid source error bound, hardware benchmark, actual triggered sensor-acquisition proof, qualified heading correction, or flight-readiness evidence. The physical conclusion remains UNKNOWN.
