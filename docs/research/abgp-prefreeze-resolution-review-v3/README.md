# A/B/G/P Pre-Freeze Review V3

*Metalogic Labs | Publication revision 1 | 18 September 2026*

> **REVIEW_PENDING | IMPLEMENTATION QUALIFICATION PENDING | NOT FROZEN**

This publication replaces the stronger readiness interpretation in the V3 draft. It records implementation progress and remaining acceptance requirements. It is neither a confirmatory result nor a final-lock candidate. No scientific threshold or confirmatory execution is authorized by this document.

## 1. What is implemented, and what it establishes

A/P ancestry: the new review functions list protocol constants and count shared acquisition/future seed fields. The saved DEV records report zero duplicates among those listed fields. This is useful trace information, but it does not independently discover every upstream sampled object or prove the full sampling model. Earliest-shared-stochastic-ancestor acceptance remains pending. [S1]

B recovery: the direct recovered_order = target_order assignment is gone. Grammar-specific encode/infer paths and predictions now execute. However, represent() still starts from the protected ordering; supplied slot-token mappings recover common canonical slots. The control called bisimulation/Bayes uses a two-candidate parity grouping. These mechanisms do not yet establish independent grammar acquisition or the required acquisition-posterior/greatest-bisimulation control. [S2]

G blocking: matched-pair selection and a fixed dose schedule are implemented. The additional null check duplicates the same label-blind output in both positions before swapping them. It checks that constructed example, not exchangeability of the actual outcome process. The scored DEV flips are still planted outputs. A design-level justification covering actual generation, selection and stopping remains open. [S3]

P restart/deletion: the inspected episode path serializes and deserializes in the same process and assigns deletion success from cold success. That exercises record construction, not the enforced hard-restart and causal-deletion boundary agreed in the thread. Those mechanisms still need end-to-end acceptance evidence. [S4]

## 2. B multiplicity: the distinction to preserve

The candidate B analysis takes the maximum of 36 direction-by-control p-values as its single arm p-value. This matches an intersection-union requirement only when all required component alternatives must hold. The 0.0125 diagnostic threshold comes from 0.05/4 for conservative four-arm Holm planning, not an extra 36-way correction within B. Full PASS additionally includes effect floors, agreement and validity gates. [S5]

> **Publication status is settled; scientific acceptance is not. Passing the existing tests is not evidence that the remaining requirements above are satisfied.**

# Power: a reproduced diagnostic, not a guarantee

*V3 publication revision 1 | Same scientific PASS floors; no new counts adopted*

The previous 0.80-0.83 figures concern significance components under particular models, not the probability that an entire arm satisfies every PASS condition. An independent calculation now reproduces the effect-floor diagnostic without generating any study tasks. [D1]

## 3. Exactly what was calculated

For n independent paired binary outcomes, let q be the probability of disagreement and delta the true treatment-minus-control difference. Then M, the number of discordant pairs, is Binomial(n,q), and wins W given M=m are Binomial(m,(q+delta)/(2q)). The component event requires BOTH the one-sided null binomial tail to be at most 0.0125 and (2W-M)/n to reach the observed PASS floor.

The calculation sets delta equal to that observed floor and sums the finite distribution. The table gives the minimum only over the listed q grid. It is a hypothetical paired-data calculation, not proof that the actual generator supplies independent episodes and not a guarantee over an unexamined continuous nuisance range.

| Diagnostic | Candidate n | Floor | Minimum probability |
| --- | --- | --- | --- |
| A | 4,096 | 5 pp | 0.498856 |
| B component | 1,015 / direction | 15 pp | 0.487144 |
| P | 4,096 | 5 pp | 0.498856 |
| G max-dose only | 421 worlds | 15 pp | 0.474616 |

A/P q grid: .05, .10, .25, .50, .75, 1.00. B/G grid: .15, .30, .50, .75, 1.00. G is a max-dose-only special-case diagnostic; it is not the complete dose-weighted world-blocked test.

When the true effect equals the threshold imposed on its estimate, these component probabilities are near one half at the candidate sizes. Increasing n alone does not supply the claimed 80% guarantee across these exact-floor planning cases. For A/B/P the corresponding dependence-agnostic union-bound lower bound is zero. A zero lower bound is uninformative; it does NOT mean actual simultaneous PASS probability is zero.

## 4. What must precede a complete-PASS power claim

Keep the scientific floors separate from a scientifically justified planning alternative. Specify the full joint outcome model, or defensible worst-case bounds, including multi-control dependence, B's 90% agreement gate, P's deletion/reacquisition conditions, and G's full dose vector. Any selected planning alternative and final count require joint review. No alternative has been fitted to confirmatory outcomes or adopted in this release.

> **Independent numerical verification: 24 small cases agree with exhaustive rational-probability enumeration; maximum absolute discrepancy is 1.12e-16. The script and all grid values are included in the package. This validates this diagnostic only.**

# Acceptance map and release record

*V3 publication revision 1 | Requirements retained; unresolved items remain open*

| Requirement | Evidence now | Acceptance status |
| --- | --- | --- |
| A/P earliest sampled ancestor | Listed-seed audit and fixed-object inventory | PENDING: complete ancestry/model |
| B grammar recovery and controls | Executable finite encode/infer demonstrator | PENDING: independence and full control |
| B IUT and alpha provenance | 36-component maximum; four-arm planning alpha | DOCUMENTED; validity still conditional |
| G exchangeability | Matched pairs; constructed symmetric null example | PENDING: actual design argument |
| P restart and causal deletion | In-process round trip; assigned deletion score | PENDING: enforced execution |
| Complete-PASS power | Independent component + floor calculation | NOT QUALIFIED |
| Confirmatory execution | Review status; existing disabled manifest | NOT AUTHORIZED |

## 5. Preserve the agreed scientific criteria

This publication changes no hypotheses, margins, sample counts, source-distinctness rules, tests or PASS conditions in the normative files. Existing values remain review candidates, not newly approved choices. B's four interventions stay nested; the proposed four P probes do not inflate n. A retains its exact-information-matching obligation.

The thread requires P deletion to return performance within two percentage points of cold, followed by tracked reacquisition. The candidate analysis-plan wording instead refers to an ordinary-control envelope. That text-implementation discrepancy remains explicitly unresolved; this publication does not silently select either interpretation. [S5]

## 6. Evidence and limits

Code evidence: f9764a3696f880e2ec09e8eb7b60054f92b8ac53. Reviewed source snapshot, including its later documentation commit: 0e37943e3364e8dda671b4fc47ded812c437a56d.

Historical run 35251639106 completed successfully. Its downloaded artifact ZIP was verified against the reported SHA-256. The legacy QUALIFIED output concerns its synthetic-fixture/statistical harness; it is not promoted to end-to-end qualification here. This publication did not rerun the full source regression, execute confirmation, or contact the collaborator. [S6]

The separate readiness record sets implementation_qualified=false, complete_pass_power_qualified=false and freeze_authorized=false. Outstanding acceptance work belongs to the implementation; it is not delegated to the collaborator merely by publishing this review.

Evidence keys S1-S6 refer to evidence-and-limits.md; D1 is power-floor-diagnostic.json and its reproducible script. Prior versions remain in Git history. V1 is superseded; V2 remains a provisional design summary. The V3 draft's stronger "addressed" labels are superseded by this publication revision.

[PDF](ABGP_PreFreeze_Resolution_Review_v3.pdf) | [Evidence and limitations](evidence-and-limits.md) | [Power diagnostic](power-floor-diagnostic.json) | [Reproduce it](power_floor_diagnostic.py) | [Readiness record](readiness.json)
