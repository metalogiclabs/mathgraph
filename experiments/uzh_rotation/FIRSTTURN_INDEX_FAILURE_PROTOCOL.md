# V5 limitation: first-revolution gyro-to-column index is unqualified

The 146-byte reference-map recorder is correct **only if** its externally
supplied 64-bin angular index labels the actual camera viewing direction.
V4 accounted for subsequent ±1-bin timing offsets; that bound is **not** a
proof that first-turn camera indexing is correct.

`audit_firstturn_gyro_jitter.py` deliberately violates this assumption while
preserving the source's one-bit image noise and later gyro timing-jitter model.
It constructs the entire first-revolution map from camera columns observed at
`assigned_bin + delta`, but lies to the algorithm by labeling them as
`assigned_bin`. The first-turn disturbance is identical across all later true
heading hypotheses for a given seed and condition. An early exploratory
variant seeded it on later true heading and was rejected as a confounded
generator, although it had already exposed wrong accepted corrections.

## Development stress (4 seeds × 4 headings)

| Index-error scenario | Active correct | Active wrong accepted | Continuous correct | Continuous wrong accepted |
| --- | ---: | ---: | ---: | ---: |
| Exact-index control | 16 | 0 | 16 | 0 |
| Constant +1 bin | 8 | 0 | 0 | 0 |
| Constant -1 bin | 12 | 0 | 0 | 0 |
| Alternating ±1 bin | 8 | 0 | 0 | 0 |
| Independently varying ±1 bin | 10 | **6** | 4 | **12** |
| Jitter near landmark boundaries | 16 | 0 | 16 | 0 |
| Independently varying ±2 bins | 8 | **7** | 3 | **9** |

The remaining cases may yield `CONFLICT` or `UNKNOWN`, not necessarily a
correct abstention; full traces preserve those states separately. These are
**synthetic out-of-bound failures**, not measured real sensor rates. Correct
performance in an easier perturbation does not validate that perturbation
physically, and a correct decision is not independently warranted where the
first-turn index assumption is broken.

This failure has an actionable engineering consequence. A future first-turn
capture should be admitted to a reference bin only when the entire declared
gyro/camera timestamp uncertainty interval lies inside that bin. Otherwise
the map must retain a hole and request an accurately timed observation.
This requires calibrated clock offsets, angular error bounds, and suitable
sampling density. No asserted visual-match confidence can substitute for
those source-acquisition obligations.

The strongest remaining impossibility is source-identity spoofing: even a
perfectly indexed map cannot distinguish two environments that produce the
same camera/gyro trace but require different heading corrections. MathGraph
must keep that as an explicit authority boundary.
