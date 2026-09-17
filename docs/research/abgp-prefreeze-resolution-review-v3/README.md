# A/B/G/P Pre-Freeze Resolution Review V3

**Metalogic Labs - review candidate only**

**Status:** `REVIEW_PENDING`  
**Confirmatory execution:** disabled  
**Confirmatory namespace used:** no  
**Implementation snapshot:** `f9764a3696f880e2ec09e8eb7b60054f92b8ac53`

This supersedes the power/implementation interpretation in the earlier v1 qualification sheet. It is not a confirmatory result and it is not yet a freeze-ready package.

## What has been resolved since v2

### 1. A/P inferential units now trace to the earliest sampled ancestor

The audit no longer treats a hard restart or a fresh future seed as sufficient proof of independence.

- **A:** every episode has its own acquisition seed plus separately derived sealed-future seed. Fixed constructor code, old-language definition, verifier-message alphabet and analysis rule are protocol constants, not sampled ancestors.
- **P:** every episode has its own acquisition seed; its retained object is a within-episode descendant and the only state crossing that restart; its four future probes are nested and do not increase `n`.

The current finite generator audit finds **zero sampled stochastic ancestors reused across scored episodes** in either A or P.

### 2. B placeholders have been removed

The treatment now executes a real source-to-target path:

`source grammar encode -> source grammar infer -> retain capability-order -> predict intervention -> target grammar encode/infer -> protected evaluator comparison`

The extensional, compositional, graph/reachability and constraint/order grammars use different surface carriers, serialization schemas, primitive inventories/arity patterns and inference routes. No cross-grammar translation table is supplied.

The three primary controls are now executable:

- matched wrong capability class;
- shuffled source/target coupling via an independently seeded source world;
- target-bisimulation/Bayesian control whose coarse observation merges two candidate protected orders, with a registered intervention that separates those observationally equivalent candidates.

All four interventions remain nested inside the ordered-direction world unit.

### 3. B alpha provenance is explicit

`0.0125` is the worst-case component alpha used for **four-arm Holm power planning** (`0.05 / 4`). It is **not** a 36-way Bonferroni correction inside B.

B remains an intersection-union arm: PASS requires all registered direction-by-control component requirements; the B arm p-value is the maximum of the 36 component p-values, and that one p-value enters the four-arm Holm procedure.

### 4. G now has a design-level exchangeability contract

DP/brute-force agreement only verifies the arithmetic. The proposed generator resolution now also fixes the selection/generation/stopping conditions needed by the randomization argument.

Relevant and irrelevant cells are selected as pre-outcome matched pairs. Pair ranking uses an **unordered pair identity**, so a relevant/irrelevant label exchange cannot change which pairs are selected. Count and magnitude are identical within each pair. All doses are fixed before outcomes and there is no adaptive stopping.

The registered sharp null is:

> conditional on the fixed matched-pair construction and all non-label inputs, the complete within-world outcome vector is unchanged by one joint exchange of relevant/irrelevant labels across every nonzero dose.

A label-blind null path checks the complete vector after that joint exchange. The audit fails closed when matching, schedule or stopping invariance is broken.

This is a finite-generator design contract, not a claim that arbitrary natural-domain relevance classes are exchangeable. The matched-pair generation procedure therefore remains subject to joint text-implementation review before freeze.

## Power correction: one real issue remains

The previous `0.80-0.83` figures were significance-component power diagnostics, **not complete-arm PASS power**.

The exact audit now includes the frozen rule that the **observed** treatment-control difference must itself meet the effect floor. The earlier planning calculation simultaneously assumed a **true** effect exactly equal to that same floor.

At that planning alternative, the observed difference is centered on the PASS threshold, so the probability of satisfying `significance AND observed effect >= floor` stays close to one half; increasing `n` alone does not make it an 80% event.

Current exact minimum component probabilities across the registered discordance envelopes are:

| Arm | Candidate n used in historical diagnostic | Observed PASS floor | Min `significance + observed floor` probability when true effect = floor |
|---|---:|---:|---:|
| A | 4,096 | 5 pp | **0.498856** |
| B | 1,015 / direction | 15 pp | **0.487144** |
| P | 4,096 | 5 pp | **0.498856** |
| G max-dose diagnostic | 421 worlds | 15 pp | **0.474616** |

For A/B/P, the dependence-agnostic union-bound lower bound for simultaneous success of all registered primary components at those exact-floor planning alternatives is therefore **0**, before adding B's `>=90%` pooled agreement gate or P's deletion/reacquisition gates.

### Why this cannot be fixed by just making N bigger

The issue is the planning alternative, not merely sample size. If the true effect is exactly the threshold the observed estimate must exceed, the estimate remains centered on the threshold as `n` grows.

A complete-PASS power calculation therefore needs a **jointly frozen planning alternative strictly above the observed PASS floor**. B also needs a planning value above its `0.90` agreement gate, and P needs an explicit planning model for the deletion/reacquisition gate and dependence among its seven primary comparisons.

This does **not** require changing the scientific PASS floors. It requires distinguishing the minimum effect required to call a result meaningful from the larger effect assumed when choosing a sample size for 80% power.

## Requirement-to-evidence map

| Bill review item | Current state |
|---|---|
| A/P earliest stochastic ancestor | **Implemented and audited** - zero reused sampled ancestors in current finite generator |
| B recovered structure | **Executable** - direct target injection placeholder removed |
| B posterior/bisimulation control | **Executable** - coarse merged states plus separating intervention witness |
| B 36-component IUT | **Retained** - one arm p-value = max of 36; no second within-B multiplicity correction |
| `alpha=.0125` provenance | **Explicit** - four-arm Holm planning floor, not 36-way B correction |
| G joint world exchangeability | **Proposed executable design contract** - matched-pair label-swap-invariant selection, label-blind sharp null, fixed schedule/no stopping |
| Complete-PASS power | **Still requires joint planning choice** - the earlier exact-floor power rule cannot deliver 80% complete-PASS power |

## Proposed disposition before freeze

Do **not** mark the study `FROZEN` yet.

The implementation issues that caused the v1 qualification overstatement are now materially reduced. The remaining substantive choice is statistical: jointly specify the planning alternatives used for complete-PASS power while leaving the scientific PASS thresholds unchanged. The proposed G matched-pair generation procedure should be reviewed at the same time for text-implementation consistency.

After those are agreed, the final manifest can bind the exact generator/analysis hashes and the confirmatory namespace can remain untouched until the one-shot run.
