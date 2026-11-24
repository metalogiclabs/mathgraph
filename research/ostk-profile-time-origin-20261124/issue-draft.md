# [fix] Tabulated flight profiles use the wrong time origin for unsorted states

**Describe the bug**

`flight::profile::model::Tabulated` sorts the supplied states, but builds interpolation timestamps relative to the first state in the original input. `calculateStateAt` evaluates relative to the chronological interval start. When the first supplied sample is not earliest, these origins disagree and the resulting position can be wrong.

This reproduces in the C++ 18.0.1 runtime and Python 18.0.1 wheel. The affected C++ file is identical at release 18.0.1 and main `ddc1924a0912bfafc89ef3a217ad21cfc2d98b1f`. The constructor documents an array of states without a sorted-input precondition, and the implementation explicitly sorts it.

**Steps to reproduce**

Run this with normal OSTk Python data setup completed:

```python
"""OSTk astrodynamics 18.0.1, with normal OSTk Python data setup completed."""
import numpy as np
from ostk.physics.time import Instant, Duration
from ostk.physics.coordinate import Frame, Position, Velocity
from ostk.mathematics.geometry.d3.transformation.rotation import Quaternion
from ostk.mathematics.curve_fitting import Interpolator
from ostk.astrodynamics.trajectory import State
from ostk.astrodynamics.flight.profile.model import Tabulated

epoch, frame = Instant.J2000(), Frame.GCRF()
states = [State(epoch + Duration.seconds(t),
                Position.meters(np.array([100.0 + 7*t, 0.0, 0.0]), frame),
                Velocity.meters_per_second(np.array([7.0, 0.0, 0.0]), frame),
                Quaternion.unit(), np.zeros(3), frame)
          for t in [0, 10, 20]]
for order in [[0, 1, 2], [1, 0, 2]]:
    model = Tabulated([states[i] for i in order], Interpolator.Type.Linear)
    x = model.calculate_state_at(epoch + Duration.seconds(5)).get_position().get_coordinates()[0]
    print(order, x)
# Expected both: 135.0. Actual released 18.0.1: 135.0, 205.0.
```

**Expected behavior**

Both orders return x = 135 m. The supplied states describe the same affine motion, with distinct timestamps and one common reference frame.

**Additional context**

A standalone C++ experiment covers all 24 permutations of four samples, seven query instants, and five interpolation configurations (Linear and BarycentricRational, uniform and per-subset constructors, plus Default): 594 of 840 queries have incorrect positions. All 210 earliest-sample-first controls are correct.

Moving the interpolation origin after sorting removes all 594 discrepancies; withdrawing that change restores them. The unchanged upstream C++ profile suite passes 10/10 in the released, recompiled original, repaired and withdrawal arms. The raw released/original/withdrawal CSVs are byte-identical. Separately, 35 selected upstream Python tests pass before/after/withdrawal locally.

[Source-pinned native replay and raw evidence](https://github.com/metalogiclabs/mathgraph/actions/runs/45355578637) — Ubuntu 24.04, g++ 13, public versioned native dependencies. This is a focused translation-unit build with an identical build-only Core formatting compatibility shim in every arm; it is not a complete project build. The actual artifact ZIP has been independently downloaded and verified.

**Potential suggestion**

In `processStatesAndGenerateReducedCoordinateArray`, set `const State& firstState = stateArray_.getFirst();` after sorting `stateArray_`. A regression can compare sorted and permuted input for the same affine position history.

Happy to contribute the focused fix and regression tests if useful.
