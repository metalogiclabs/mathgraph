# Finite bounded-noise witness acquisition: protocol v2

Date: 2026-10-22. This is a **new and separate finite model**, not a
replacement for the v1 64-row grey-level visual-compass estimator.

## Question

Can a first-revolution learned one-column reference support an automatically
compiled, minimum-cost set of *future* observations that discriminates competing
heading hypotheses, without consulting ground truth or future camera readings?
Can it refuse when no permitted observation separates them, and withdraw
previous authority after contradictory new evidence?

## Exact declared model

- 64 angular bins, each with a 16-bit binary vertical column; one nominal
  64-sample revolution is the sole training source. Four candidate headings
  `0,16,32,48` are SUPPLIED as a bounded, gyro-compatible post-blackout
  support. The live gyro support generator is **not** implemented here.
- True physical template versus first-turn stored reference differs by at
  most **one flipped bit** per column. Subsequent observed column differs
  from physical by at most **one flipped bit**. By the triangle inequality,
  stored reference versus later reading differs by at most **two bits**.
  This source stationarity/error envelope is an **assumption**, independently
  checked by an offline auditor; it is not estimated from a real sensor.
- Relative angular step between observations is exactly known in integer
  bins; not calibrated or known from a real gyroscope. Only heading MODULO
  64 is distinguished; missing revolution count is not resolved.
- A predicted witness distinguishes a pair only if the *stored* columns at
  that step have Hamming distance **strictly greater than 4**. Under the
  declared error envelope the two reading balls of radius 2 cannot overlap.
- The compiler finds a minimum-cardinality permitted observation set that
  covers **all hypothesis pairs**. Ties break by earliest final observation,
  then lexicographic step order. Exact dynamic programming finds that set;
  an independent combinatorial subset enumerator checks minimality. A
  `BOUNDED_OBSTRUCTION` only concerns the supplied map, support, permission
  sequence, noise envelope and 32-step horizon; it is no global theorem.
- A proposed future observation is **not used until acquired**. An occluded
  planned instant causes re-planning on remaining future steps. Only an
  actually observed singleton candidate support permits a heading correction.
  A sensor contradiction yields `CONFLICT`/UNKNOWN. Later contradictions
  trigger withdrawal of a prior accepted heading.

## Conventional baselines and cost accounting

1. Continuous exact conventional tracker gets the SAME first-turn reference,
   candidate support and conservative two-bit error bound. It processes all
   available columns until one heading remains. It must be at least as fast to
   decide (in wall-clock observation steps) as a sparse planner.
2. Independent exhaustive set-cover enumeration gets the SAME reference and
   alternatives, validates minimal observation count and earliest deadline.
   It can perform the same planning task; no unique MathGraph optimality is
   claimed relative to this equally informed algorithm.

Report accepted heading, false corrections, unknown/obstruction, decision
step, acquired/attempted columns and planning Hamming pair comparisons.
Acquired-column savings are **not equivalent** to processor-cycle savings:
the compiler itself performs many pair checks, and real camera power is not
measured. Do not claim a total compute, safety or latency advantage over the
best conventional implementation.

## Intentionally distinct controls

- `breakable`: four near-repeated environmental sectors; future landmark at
  step 7 partitions candidates one way, and at step 13 the other. Neither
  single observation separates all four; a two-observation set does.
- `unbreakable`: four exact physical sectors. No visual observation within
  the grammar can determine which sector; the only honest result is UNKNOWN.
- `occluded 7`: the first planned witness is missing; re-plan using subsequent
  observation. No advance knowledge of the outage is given to the policy.
- Changed-scene identity-swap **negative control**: replace future physical
  readings by readings consistent with another heading. Both trackers may
  confidently authorize the wrong heading. The independent environmental
  fidelity audit rejects this changed run because the assumed noise bound
  has been violated. The *online estimator cannot infer* that unseen source
  fidelity from a plausible replacement. This limits physical safety claims.
- Subsequent nonmatching sensor reading: previously accepted authority must
  be withdrawn rather than retained indefinitely. A forged but matching
  reading can still go undetected; there is no universal spoofing guarantee.

## Verification, independent holdout and promotion

- Development seed set: `5`, `11`, `19`, `23`, across every one of four true
  heading bins and three standard conditions. Tests also cover 100 unrelated
  16-bin maps against an independent exact subset baseline and **75,076**
  possible two-probe noisy observation tuples for seed `5`.
- **Freeze before opening** holdout seeds `1013`, `2017`, `3019`, `4019`.
  A workflow-only commit must enforce source immutability and audit each case.
- `WARRANTED` will mean correctness **conditional on the finite source and
  noise assumptions**, not a physical or statistical guarantee. Running
  independently in Actions validates reproducibility, not sensor realism.

The next physical-residual test must bring a real multi-revolution sequence
with synchronized single-column camera/IMU observations, bound/estimate noise
empirically, and construct candidate support without a hidden scene oracle.
The RobotEvt ground-truth qualifier is prepared but recordings remain
unqualified as of this protocol.
