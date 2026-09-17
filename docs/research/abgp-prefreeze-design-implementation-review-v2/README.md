# A/B/G/P Pre-Freeze Design & Implementation Review v2

**Metalogic Labs — provisional design review for text–implementation consistency before any scientific freeze.**

**Status:** `REVIEW_PENDING`  
**Harness:** statistical/synthetic-fixture checks passed  
**End-to-end implementation qualification:** `PENDING`  
**Confirmatory namespace:** untouched

## Scope correction

The earlier v1 review used `QUALIFIED` too broadly. The verified 200-test / 21-fixture result established that the statistical analyzers, frozen synthetic challenge fixtures, exact-reference checks, replay, and namespace firewall behaved as specified. It did **not** establish that every experimental arm was implemented end to end.

This v2 package preserves the agreed science and makes the remaining implementation and methodological blockers explicit.

## Agreed scientific criteria — unchanged

| Arm | Agreed target | Key freeze condition |
|---|---|---|
| **A** | Non-identifying verifier information beyond matched ordinary updating | Exact constructor-visible information budget; Bayesian-optimal control sees the same permitted observations/messages; ≥5 pp floor plus arm significance and hard gates. |
| **B** | Capability/action-order recovery across genuinely different grammars | 12 ordered directions; independent grammar machinery; held-out structural interventions; >90% protected-order agreement and ≥15 pp advantage over required controls. |
| **G** | Dose response specific to action-relevant distinctions | Preclassified relevance; matched corruption; world-level blocked randomization; ≥15 pp max-dose gap plus corrected significance. |
| **P** | Persistence without verifier or reconstruction | Retained object only across hard restart; label-free invocation; zero verifier/search/reconstruction; ≥5 pp over strongest baseline; deletion within 2 pp of cold and preregistered reacquisition. |

## What the existing harness evidence supports

Existing DEV/QUAL evidence supports analysis mechanics: exact paired tests and Holm handling, B IUT plumbing, world-blocked G DP/reference agreement, frozen positive/ordinary-explanation/INVALID fixtures, deterministic replay, and confirmatory-namespace isolation.

These are **harness checks only**. They are not A/B/G/P scientific results and they are not yet an end-to-end implementation qualification.

## Requirement-to-evidence status

| Requirement | Current evidence | Status before freeze |
|---|---|---|
| A/P earliest shared stochastic ancestor | Episode/future seed separation and P restart mechanics exist. A complete ancestry audit covering upstream sampled worlds, grammars, pools, and constructor state has not yet been established. | **OPEN — audit required** |
| A exact information-matched Bayesian baseline | Analysis/fixture path exists; end-to-end oracle and full PASS-event implementation still require verification. | **OPEN — implementation/evidence** |
| B 36-component IUT | IUT analysis path is implemented. Current DEV B generator still assigns recovered order from target order; posterior/bisimulation control remains mechanics-only. | **OPEN — real recovery/control paths** |
| B alpha provenance | `α=.0125` is the conservative four-arm Holm component floor, not a multiplicity correction across B's 36 IUT components. | **CLARIFIED** |
| G world-blocked statistic | One world-level sign exchange across doses and exact DP/brute-force numerical agreement are implemented. | **MECHANICS CHECKED** |
| G exchangeability | Need a design-level argument that the entire within-world vector is invariant under joint label exchange under H0, including generation, selection, and stopping. | **OPEN — justification required** |
| P restart/deletion boundary | Independent acquisition episodes and restart/deletion mechanics exist in DEV/QUAL; earliest-ancestor independence and end-to-end ordinary-control paths still need audit. | **OPEN — audit/implementation** |
| Power for complete PASS event | Current B power includes the 36-component IUT aggregation. A/P figures are paired-test calculations and do not yet establish power of the complete multi-control plus hard-gate PASS rules. | **OPEN — recompute after final implementation** |

## Bill Bao review points — 17 September

1. **A/P independence:** establish independence at the earliest shared stochastic ancestor, not from distinct future seeds or hard restarts alone.
2. **B IUT:** the 36-component intersection–union construction is defensible if PASS genuinely requires all 36 component alternatives. State explicitly that `α=.0125` comes from the four-arm familywise procedure, not from multiplicity across those 36 components. Recompute power for the complete PASS event after the real recovery and posterior/bisimulation controls are implemented.
3. **G exchangeability:** DP/brute-force agreement validates the calculation, not the exchangeability assumption. Freeze requires a design-level argument that the full within-world outcome vector is invariant to the joint label exchange under H0, including any generation, selection, or stopping steps.

## Current power numbers — corrected interpretation

| Arm | Candidate N | Reported calculation | Correct interpretation |
|---|---:|---:|---|
| A | 4,096 episodes | 0.825254 | Paired-test power at 5 pp over the declared discordance envelope; **not** complete-arm PASS power. |
| B | 1,015/direction = 12,180 | 0.800598 | Dependence-agnostic lower bound for simultaneous rejection across 36 IUT components; revisit with real controls and all gates. |
| G | 421 worlds | 0.801242 | Conservative max-dose-only power under the world-blocked paired model; exchangeability justification remains pending. |
| P | 4,096 episodes | 0.825254 | Paired-test power at 5 pp over the declared discordance envelope; **not** complete-arm PASS power. |

These numbers remain review-candidate calculations, not a frozen sample-size decision.

## Freeze rule

Do **not** mark the study `FROZEN` until every agreed requirement maps to a concrete implementation path and auditable evidence, the remaining methodological assumptions are justified, and power is recomputed for the actual complete PASS rules.

Any change to hypotheses, effect floors, source-distinctness, inferential units, or PASS criteria must return to joint scientific review rather than being relabeled as an implementation clarification.

**No confirmatory result is represented here. The confirmatory namespace remains outside this review package.**
