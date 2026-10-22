# V6 development: source-bound first-turn phase capture (synthetic)

**Objective:** preserve an accurate environmental reference before the visual
compass is allowed to make consequential heading corrections. V5 silently
assumed correct angular indexing on the first revolution; independent ±1-bin
source errors caused 6/16 incorrect authorized headings in its original
development adversary ([Actions #39858130199](https://github.com/metalogiclabs/mathgraph/actions/runs/39858130199)).

The additional freestanding C99 adapter `firstturn_interval_capture.c/.h`
accepts a 16-bit camera column only when the entire **externally declared**
gyro/timestamp angular interval occupies one of 64 frozen-map bins. All
indices use **16 integer subticks per bin** (1024 per turn). An inclusive
closed interval straddling any bin boundary causes `MG_FIRSTTURN_UNCERTAIN`
with **no mutation**, leaving the map hole to be recorded as UNKNOWN. The
original `finite_partial_map.c/.h` planner and map representation are
**unchanged**; the 146-byte map is retained and no new persistent C storage
is added. The adapter neither measures nor proves the supplied error bound.

## Frozen model for this experiment

- First-turn scene: 64 synthetic static 16-bit columns; one-bit camera noise
  per captured sample. A bin's generated physical viewing angle is chosen
  independently before any later heading hypothesis is evaluated.
- First-turn sampling densities: 1, 2, or 4 columns per angular bin, at
  monotonically ordered physical subtick angles within each bin.
- Truthful external gyro/timestamp bounds: **±3, ±7, ±8 subticks**. Samples
  are generated with a bounded difference between physical camera angle and
  reported phase, but no calibration procedure is implemented.
- Negative control: source reports an unjustified ±3 subtick bound while its
  actual error is approximately ±16 subticks (one complete bin). The adapter
  has no privileged access to this lie.
- The frozen later-turn synthetic renderer, four heading hypotheses, ±1 bin
  camera/gyro jitter, and original C active/continuous matchers are reused.
- A conventional continuously observing comparator is given the **identical
  bounded source map** and its original robust ±1-bin filter. A separate
  nearest-bin comparator ignores the source bound to reveal coverage/safety
  tradeoffs; it is **not** an equally protected baseline.
- Both map builders see only reported first-turn phase, declared error radius
  and measured column. True angles, source identifiers, true heading and
  future observations remain solely in the independent grader.

Development seeds: **5, 11, 19, 23**, all four heading hypotheses.
Predesignated untouched holdouts: **431, 457, 479, 503**. No settings,
thresholds, acquisition policy, source code or test code may be changed
after the source-version freeze before first holdout. If any fix is needed,
the holdout becomes exploratory and a different preregistered pool is required.

## Development observations (local before GitHub independent replay)

| Source condition | Map bins, mean | MathGraph active authorized correct | Robust continuous authorized correct | Wrong accepted (both gated) |
| --- | ---: | ---: | ---: | ---: |
| Honest ±3, 1 sample/bin | 40.25 | 4/16 | 7/16 | 0 |
| Honest ±3, 2 samples/bin | 55.5 | 8/16 | 15/16 | 0 |
| Honest ±3, 4 samples/bin | 63 | 16/16 | 16/16 | 0 |
| Honest ±7, 4 samples/bin | 25.75 | 0/16 | 1/16 | 0 |
| Honest ±8, 4 samples/bin | 0 | 0/16 | 0/16 | 0 |
| False ±3, actual about ±16, 4 samples/bin | 22.5 | 1/16 correct, **1/16 wrong** | 3/16 correct, **1/16 wrong** | **1 each** |

An unchanged reference-map C planner now yields conditional correct outcomes
when its premise is honored, but active acquisition has **lower availability**
than the strongest continuously observing baseline under sparse coverage.
In the false-bound control, both make an incorrect correction: claimed error
intervals are *not* source authority. The important result is a replayable
failure boundary and a method to turn actual measured timing uncertainty
into missing-map evidence, not superior reliability or flight readiness.

The finite oracle independently enumerates all 1024 estimated phases and all
allowed actual phase shifts for radius 0,1,2,3,7,8,15,16 (8192 interval
configurations), checking that every C acceptance corresponds to one physical
bin. End-to-end traces preserve heading outcomes, conflicts, UNKNOWNs, map
coverage, skipped captures and measurement work. Passing tests certify only
the finite model and declared assumptions, not actual clock or gyro bounds.

**Next residual:** replace externally supplied angular uncertainty bounds with
measured real camera/gyro synchronization and spinning-camera angular motion,
including rate changes and first-turn capture timestamps. No external visual
lighthouse is assumed. Source identity spoofing remains separately UNKNOWN.
