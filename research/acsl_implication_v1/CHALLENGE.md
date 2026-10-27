# Retained synthetic challenge controls

Only copies of authentic Qwen/C native output records are modified.
Eight negative/positive controls test whether the independent baseline
and source normalizer catch or accept deliberately constructed variants:
- MAX result below all elements: reject.
- False all-even result: reject.
- All-even result asserted for odd array: reject.
- Even-index zero guarantee violated: reject.
- Index-initialized doubling guarantee violated: reject.
- Changing an **odd-index** value when the original ACSL postcondition
  only constrains even positions and lacks an assigns constraint: ACCEPT.
  This critical positive control avoids inventing preservation rights.
- Missing original record: reject.
- Forged target blob identity: reject.
- Forged source packet that elevates unknown \old/pointer case: reject.

Nine mutations total: eight negative controls and one positive control.
A mutated receipt's observation digest is recomputed in every attempt,
so these tests are not merely old-hash consistency checks. These are
synthetic mutations, NOT authentic migration defects, no superiority
over a conventional independent comparator is claimed.
