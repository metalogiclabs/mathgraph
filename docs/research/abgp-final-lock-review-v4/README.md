# A/B/G/P Final-Lock Review V4

**Metalogic Labs | 18 September 2026**

**Status:** `REVIEW_PENDING` | `IMPLEMENTATION_QUALIFIED` | `NOT_FROZEN`  
**Confirmation:** `ABGP-CONFIRM-v1` untouched

This is the final pre-freeze review package for the A/B/G/P study. It supersedes V3 **only for current readiness**. V3 remains unchanged as the historical record of the earlier implementation and power objections.

No confirmatory result is reported here. `ABGP-CONFIRM-v1` has not been used. This document does not itself authorize freezing or confirmation.

## 1. Exact candidate identity

- **RealityGraph branch:** `abgp-preregistration-freeze-v1`
- **Implementation head:** `bed8a4e5d35e211e7bdebca42f39d923f264fb70`
- **Candidate digest:** `771793f52cc8228c 54bf2ac8ab46ebbc b0c7a99284d94e30 42951a7976921e04`
- **Implementation qualification digest:** `a7a9e40a...f866cfd3`
- **Planning proposal digest:** `a38c94cf...1df9f34`
- **Status:** `REVIEW_PENDING`
- **Implementation qualified:** `true`
- **Complete-PASS power qualified:** `false`, pending joint planning approval
- **Freeze authorized:** `false`
- **Confirmatory namespace used:** `false`

The exact unspaced digests are recorded in the machine-readable readiness record and the CI final-candidate artifact.

The final candidate binds the design and analysis plans, executed A/B/G/P generators, registered analysis and validity logic, exchangeability code, P acquisition/invocation/posterior workers, implementation qualification, planning review, and the final-candidate builder itself by SHA-256.

The current exact-head CI runs are green:

- DEV preregistration / full regression: `35285093632`
- Executed boundaries / final-lock candidate: `35285093739`
- Full regression in the boundary workflow: **280 tests, all OK**

The machine-readable final candidate is retained in the executed-boundaries CI review artifact from run `35285093739`.

## 2. Resolution of the three remaining methodological review points

### A/P - inferential unit and earliest generated ancestry

The current executed matrix makes the inferential unit explicit for every arm and audits generated roots at that unit.

- **A:** acquisition-to-sealed-future episode. Acquisition and future roots are separately generated; no generated root is reused across scored episodes.
- **P:** acquisition -> hard restart -> four nested source-distinct future probes, collapsed to one episode outcome. Source and future roots are separately generated; probes do not inflate `n`.
- **B:** ordered-direction latent-world pair. Every scored unit now has a fresh latent world plus independently generated source and target grammar roots.
- **G:** world. Doses are repeated measurements nested within the world and are not treated as independent units.

The ancestry audit establishes the declared generated dependency graph and reports no shared generated ancestor across scored units. Fixed protocol objects are shared by design. It deliberately does **not** claim that this audit alone proves statistical independence against arbitrary untracked global state; that scope remains explicit in the artifact.

### B - IUT, grammar independence and ordinary-explanation control

B now executes all 12 ordered directions across four independently parameterized grammar families: extensional, compositional, reachability and constraint/order.

Source and target grammars use disjoint surface symbols and primitives, different primitive counts/arity patterns, different serialization schemas, different inference routes and independent grammar seeds. No deterministic cross-grammar translation or one-to-one primitive dictionary is supplied.

Acquisition learns a behavioral equality-pattern capability from the source representation and protected source order, then applies that capability to the target grammar under all four preregistered structural interventions. Wrong-class, shuffled-coupling and old-information/bisimulation controls are executed from their permitted information.

The statistical construction is unchanged: 12 directions x 3 primary controls = 36 required components. The B arm p-value is the **maximum** of those 36 p-values because PASS requires all 36 alternatives. The `0.0125` planning alpha is the conservative first Holm threshold across the four arm-level p-values; it is not an additional 36-way Bonferroni correction inside B.

### G - world-level exchangeability

G now uses an executed paired-cell structural world and a cell-dependent protected evaluator. Relevance is computed before corruption by intervention against that evaluator. Corruption count and magnitude are matched within each pair and the full dose schedule is fixed with no adaptive stopping.

For each world the generator has one fair binary role assignment: left-side relevant or right-side relevant. The exact two-assignment potential-outcome law is enumerated under the registered sharp null and the complete within-world paired outcome vector is required to be invariant under the joint relevance-label exchange. The randomization block is the **world**, not individual cells or doses.

The implementation explicitly scopes this argument to the frozen finite paired-cell generator; it is not presented as a theorem about arbitrary observational relevance labels.

## 3. P persistence boundary now executed

P is no longer a same-process serialization demonstration. Invocation runs in a fresh restricted Python worker image with the retained structural object as the only experimental state supplied to the invocation path. The invocation image contains no acquisition/search routine. A kernel seccomp filter is installed before experiment input is read and the implementation probes forbidden file, network, process and inherited-descriptor access.

The executed P gates require:

- source-distinct future carrier and serialization;
- label-free applicability;
- zero verifier calls after restart;
- zero pre-action reconstruction/search;
- targeted lineage deletion;
- explicit reacquisition through the frozen acquisition procedure; and
- restored performance after reacquisition.

The current final-lock implementation gate for P is true. This is implementation/mechanism qualification only, not a confirmatory P result.

## 4. Power issue identified in V3 and proposed resolution

V3 correctly showed that using a true planning effect equal to the observed PASS floor leaves the significance-plus-observed-floor event near 0.5. The scientific PASS floors are therefore kept unchanged while the planning alternatives are proposed strictly above them.

The proposed counts are unchanged from the reviewed candidate counts.

| Arm | Proposed count | Observed scientific PASS floor | Proposed planning alternative | Conservative complete-PASS planning lower bound |
|---|---:|---:|---:|---:|
| **A** | 4,096 episodes | 5 pp | 10 pp | 0.998000 |
| **B** | 1,015 worlds/direction = 12,180 worlds | 15 pp | 25 pp | 0.980978 |
| **G** | 421 worlds | 15 pp | 25 pp | 0.980495 |
| **P** | 4,096 episodes | 5 pp | 10 pp | 0.995334 |

These are conservative planning calculations, not predicted confirmatory outcomes.

For B, the proposal additionally assumes a **0.95 true all-four-intervention world agreement rate** when planning power for the observed `>=0.90` pooled agreement gate. At 12,180 independent world units, the resulting conservative agreement-gate power rounds to 1.0 in the candidate calculation.

For P, deletion-to-cold closeness is proposed as an **enforced mechanism condition rather than a separate stochastic advantage**. The deletion operation removes the retained lineage; both the deleted and cold invocation paths then receive the same null retained state. Reacquisition must separately re-enter the frozen acquisition procedure and restore the pre-deletion capability.

## 5. What is being requested for joint approval

No new scientific hypothesis, observed PASS floor, Holm/IUT rule, source-distinctness requirement, inferential-unit definition or confirmatory result is being introduced here.

Joint approval is requested for exactly the following final-lock choices:

1. **Planning alternatives:** A = 0.10, B = 0.25, G = 0.25, P = 0.10.
2. **Counts:** A = 4,096; B = 1,015 per ordered direction; G = 421; P = 4,096.
3. **B planning agreement:** 0.95 all-four-intervention world agreement for planning the observed `>=0.90` gate.
4. **P deletion condition:** deletion-to-cold equality is treated as a mechanically enforced gate rather than a separately powered effect.
5. **Text-implementation consistency:** the implementation summarized above matches the jointly specified A/B/G/P study closely enough to freeze the exact normative package.

If all five are accepted, the intended approval text is simply:

> **APPROVED AS WRITTEN**

Any revision should identify the item and replacement value or wording before freeze.

## 6. Freeze rule after approval

Approval of this review does **not** itself execute confirmation.

After explicit joint approval, and only then:

1. update the normative planning text to the exact agreed wording;
2. hash the resulting exact repository tree and required implementation/environment artifacts;
3. mark the lock `FROZEN`;
4. verify the confirmatory namespace remains unused at the frozen tree; and
5. enable `ABGP-CONFIRM-v1` for one confirmatory execution.

Any post-freeze scientific change requires a new preregistration/version and a fresh confirmatory namespace.

## 7. Interpretation boundary

`implementation_qualified=true` means the current DEV execution paths satisfy the registered implementation/validity gates and are bound into the registered analysis. It is **not** evidence that A, B, G or P is scientifically true. The developmental scientific verdicts are not confirmatory evidence and the confirmatory namespace remains untouched.

The strongest interpretation available before joint approval is therefore:

**Implementation qualification complete; final planning and text-implementation approval pending; study not frozen; no confirmatory evidence observed.**
