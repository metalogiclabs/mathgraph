# Visual Compass: minimum-witness camera scheduling (synthetic qualification)

**Purpose for Joshua Bird's single-propeller drone:** a small, source-bounded selector that can determine which future body-angle view would resolve competing headings, request that camera observation, and refuse an unjustified correction. This research must not touch motor control, flight authorization or the IR-beacon fallback.

## The smallest reusable contribution

- `finite_witness_embedded.c/.h`: standalone C99, no heap, no sensor or encoder access, exact minimum-cardinality nonadaptive future-observation basis within the declared **64-bin / four-heading / 16-bit / Hamming-error<=2 / horizon<=32** grammar. The 64-state DP uses 640 bytes of temporary arrays plus caller-owned 128-byte signatures and 64-byte presence flags. `mgw_plan` returns a future step or bounded obstruction; `mgw_filter` eliminates candidates only **after** an observation arrives.
- `physical_active_acquisition.py`: executable, callback-only camera-source model. It never provides future columns to the policy before the recorded request. Continuous set-valued conventional comparator uses the same firstturn map, gyro-derived candidate prior and noise assumptions, but elects to read every frame.
- `audit_physical_active_acquisition.py`: independent exhaustive subset cover oracle, causal acquisition trace replay, contradiction/refusal checks and hidden-truth referee. It reads source/hidden truth **only after** policies have finished; unlike the planner it does not call the planner's implementation.
- `test_finite_witness_embedded.py`: native cc `-std=c99 -Wall -Wextra -Werror -pedantic` and Python-vs-C99 equivalence across generated heading priors, missed witnesses, map holes, obstructions and 100 randomly generated frozen scenes.

## Independent source-linked result

[Qualified Actions run #40148622260](https://github.com/metalogiclabs/mathgraph/actions/runs/40148622260) (before the small follow-up singleton test) passed all previously protected canonical physical-gate tests, 8 C99 equivalence tests, 14 independent active-acquisition adversaries, 13 isolated-replay controls, 5 role-disjoint source-adapter tests and real Docker map/estimator isolation. The C99 implementation is source-compatible with the existing Python finite witness compiler on the tested grammar; it is **not** yet built into ArduPilot/moteus.

The frozen 32-seed x 4-heading x 6-stress-condition model census **768/768** is independently audited:
- 128 clean breakable synthetic source trials: both active and continuous identify the true heading by angular **step 13**. Active camera requests 256 total exposures (2 per trial) versus 1,664 for continuous (13 per trial) = **84.615% fewer camera attempts**. There are zero false unique decisions under the assumed total Hamming noise bound.
- Occlusion of one planned witness sometimes permits recovery at a later angular step. Complete blockade of all separating witness steps (7,13,23,29) yields UNKNOWN (128/128); intrinsically unbreakable repeated scenes also yield UNKNOWN (128/128).
- An adversarial changed-scene column that violates the assumed noise bound can induce a wrong unique heading; a dedicated test **demonstrates** that the bound/source-stationarity premise is indispensable. The independent referee catches this false conclusion after the fact; the runtime policy cannot detect every spoof.
- Exact minimum means minimum **static pair-cover basis in the finite grammar**, not globally optimal adaptive sensing or a unique algorithmic advantage over any equally informed optimized conventional scheduler.
- The continuous comparator receives **more observations** by design; it has the same model, prior and timeline. The result concerns observation cost for equal clean-case identification time, **not improved heading accuracy, battery power or sensing advantage over an optimized active baseline**.

## Correct authority boundary

The actual hardware contract is already on the original `exp/uzh-rotation-validation-20261021` branch: `PHYSICAL_EVIDENCE_GATE_PROTOCOL.md`, `physical_evidence_gate.py`, `physical_encoder_score.py`, `mathgraph-physical-evidence-gate.yml`. It enforces independent NAVIGATION/ENCODER artifact roles and unwrapped per-turn optical scoring. This supplemental C99 scheduler adds NO physical authorization and MUST NOT replace the canonical gate.

Model inputs require: frozen first-turn 16-bit signatures and admitted map bins, an independently valid gyro-derived candidate heading set containing truth, an actual gyro phase-to-future-step clock authority, a total camera reference/observation error bound, a stationary scene and a permitted temporal horizon. Failure of ANY physical assumption means UNKNOWN. `MGW_ALREADY_UNIQUE` means only a singleton assumed candidate prior; it is never a camera warrant by itself. No physical clock instrument, encoder, dynamic sensor scheduling, GPU/CPU energy, flight, or five physical revolutions were tested.

## Reproduce (research checkout)

```bash
python -m unittest discover -s experiments/uzh_rotation -p 'test_finite_witness_embedded.py' -v
python -m unittest discover -s experiments/uzh_rotation -p 'test_physical_active_acquisition.py' -v
python experiments/uzh_rotation/physical_active_acquisition.py --seeds 32 --output active_acquisition_census.json
python experiments/uzh_rotation/audit_physical_active_acquisition.py active_acquisition_census.json --output active_acquisition_audit.json
```

## Next independent physical test (requires genuine data)

Keep the rotor safely secured. Have the camera/gyro module make its own first-turn map, schedule/record actual column exposures and retain UNKNOWN when evidence is insufficient. Independently log encoder and calibration reference, freeze timing bounds before holdout, then score revolutions 2–5 through the canonical role-disjoint gate. Match both the always-on and an equally informed optimized active-tracker baseline. Use encoder only in the independent referee, never in navigation or sensor selection.

**Status:** WARRANTED bounded finite C99 and synthetic acquisition pipeline; physical compass UNKNOWN.
