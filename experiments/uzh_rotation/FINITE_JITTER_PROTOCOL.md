# Finite compass acquisition with bounded gyro/camera timing uncertainty (v3)

Date: 2026-10-22. Separate from the original 12-turn grey-level synthetic
compass, and from exact-timing finite model v2. The latter's frozen CI and
holdout evidence remain unchanged.

## New residual

Under v2, the angular displacement between image columns is exactly known.
On the actual drone, camera/gyro synchronization and changing rotation rate
make that assumption particularly fragile. This v3 model adds an unknown,
independently varying integer timing slip `{-1, 0, +1}` angular bin at EVERY
future observation. The estimator never sees the actual slip or true heading.

For candidate heading `h`, planned relative step `s` and image fingerprint
reference `F`, the permissible predicted reading signatures are:

`{ F[(h + s + d) mod 64] : d in {-1,0,+1} }`.

Each first-turn stored 16-bit vertical-column fingerprint differs from the
physical template by at most one bit. Every later measured column differs
from the physical template at its unknown shifted position by at most one
bit. Thus an admissible camera observation has at most two bit errors relative
to **one** member of the correct predicted set.

An observation is *guaranteed* to separate candidate hypotheses `a,b` only
when the Hamming distance between **every combination** of predicted `a`
and `b` signatures is strictly more than four. It covers that pair for the
exact set-cover compiler; a minimum-cardinality set of permitted future
observation times must cover **all** candidate pairs.

The sensor's true angular jitter is checked by an independent auditor **after
the estimate**. There is no oracle ground truth, oracle timing slip, future
reading or source template in the estimator API. This is a conditional
synthetic model, not a calibrated drone timing bound.

## Controls

1. `wide`: a partly repeated four-sector environment with a three-bin-wide
   distinguishing region near step 7 and a different three-bin-wide region
   near step 13. Width makes two observations guaranteed to separate four
   headings even with the allowed timing slips.
2. `wide` with missing step 7: re-plan after discovery of the outage. The
   planner does not know in advance which camera samples will disappear.
3. `narrow`: otherwise identical single-bin landmarks at 7 and 13. Under
   the same jitter bound, **no observation can guarantee separating every
   hypothesis** within the finite horizon. The robust compiler returns
   `BOUNDED_NO_GUARANTEED_SEPARATION` rather than falsely trusting a point
   prediction. Some fortuitous observations could still resolve a hypothesis
   for an opportunistic continuous estimator; this is NOT proof of physical
   non-identifiability.
4. `unbreakable`: genuinely fourfold-repeated visual signatures, no scene
   feature can differentiate the candidate sectors, withhold correction.
5. Out-of-bound camera/gyro slip or source-identity swap: offline fidelity
   audit REJECTS. A source change engineered to mimic another candidate can
   still make both tracking policies falsely confident; this negative result
   explicitly limits a formal finite-model claim.

## Equally informed comparisons

The conventional baseline maintains exactly the same candidate set, map,
noise budget and `{-1,0,+1}` timing set. It updates on every available
column, so can resolve as early as or earlier than the planner. A separate
brute-force enumerator checks minimum observation cardinality and deadline.
The planner can reduce processed camera samples, **but its search costs
more pairwise comparisons**. This does not imply superiority in latency,
total compute, power consumption, reliability or real sensor performance.

### Independent verification

- First-turn training-map fidelity and runtime image fidelity are separately
  audited. Every actual timing slip is verified to lie in the declared bound.
- All candidate-set transitions and permitted observations are replayed using
  an independently written implementation (no estimator/planner imports).
- An independently enumerating set-cover oracle checks the proposed minimum
  plan, including after an unseen occlusion.
- 100 unrelated maps with 0/1-bin uncertainty challenge the compiler.
- An exhaustive finite check of **675,684** allowed two-observation input
  combinations (4 true headings × 3² timing offsets × 137² bit-error
  patterns) verifies authorization only of the true heading under the model.
- Development seeds: `5`, `11`, `19`, `23`, four headings and four conditions
  (`wide`, `wide+missing7`, `narrow`, `unbreakable`).
- Freeze implementation and protocol before any holdout. Reserved unseen
  seeds: `1031`, `2039`, `3049`, `4093`.

## Boundaries and next decisive experiment

Both v2 and v3 are finite **controlled binary synthetic experiments**. They
do not demonstrate a physical 16-pixel camera, validated timing uncertainty,
real multirevolution reacquisition or resolution of unknown integer turn count.
Their conditional soundness does not survive an unbounded source change.

Most important next integration: learn *empirically defensible* image and
timing uncertainty sets from real repeated-revolution sensor recordings,
then feed those into the witness compiler and independently score coverage,
false corrections, abstention and computational cost on held-out scenes.
RobotEvt pure-rotation data are hosted in six Google Drive ZIPs, and an
independent ground-truth yaw qualifier exists, but sequence qualification
has not yet been achieved. ECRot's published motorized sequences document
single 360° excursions, not multiple visits.
