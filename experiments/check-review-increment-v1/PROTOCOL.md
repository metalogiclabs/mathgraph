# Incremental assurance evaluation v1

Status: REGISTERED_NOT_RUN. This protocol is an experiment definition, not a product accuracy result.

## Question

What independently warranted evidence does MathGraph Check add after Devin Review and the repository's existing CI? Compare arm A (Devin Review + existing CI) with arm B (the identical completed review/CI record + MathGraph Check). This does not assume either product is a complete correctness oracle.

## Selection and freeze

Select the newest-created open PR in nasa-jpl/L4YAML using metadata only, before reading its diff. Record exact repository, PR number, base/head SHA and controller release in `selection.json`. Commit this protocol and selection before acquiring changed source. Do not silently switch PRs because the selected scope is unsupported or produces no finding. A changed upstream head is a different subject; retain the original freeze and record the change.

The current Check capability supports only the reviewed owned-fork ledger module. A selected theorem or unreviewed module is a capability UNKNOWN, not a native-reviewed PR. Importing a snapshot into an owned fork does not authorize a new execution profile.

## Required packet and access

Both arms receive identical pinned base/head source, repository rules, relevant owner-approved requirements, intended production consumers and existing CI evidence. Keep requirement identity distinct from implementation and reviewer/model interpretation. Record which versions each reviewer actually saw, review completion, relevant settings and withheld findings when available. A public-comment search alone is not evidence of full reviewer exposure or complete private output.

Actual Devin access/output is required for arm A. Do not substitute another model, infer private findings or count an absent comment as a confirmed miss. Lack of credentials or access remains UNKNOWN. No upstream comments, reviews, PRs or installation are part of this protocol.

## Budget and order

Freeze the source packet, requirements and scoring rubric first. Finish and retain arm A before arm B sees the completed review, so the measured quantity is incremental value. Both arms may use the same public documentation and CI packet; record any additional information. Bound each review to 15 minutes wall time. Check uses its existing bounded call limits, conservative per-installation reservation and no automatic paid HTTP retries. Record actual tokens, model/tool revisions, elapsed time and charges if available; reservation is not actual cost. Devin's product settings and cost must be recorded, not assumed identical to token pricing.

For a separate *independent reviewer* comparison, preregister a new arm that cannot see A's findings. Do not retrospectively call this incremental design a blind head-to-head experiment.

## Evidence and adjudication

Each candidate records: requirement and its authority; alleged violation; source/consumer identities; smallest reproducer; native toolchain and run/artifact hashes; base/head outcomes; assumptions; semantic adjudication; review exposure; time/cost. Deduplicate by obligation and counterexample mechanism, not wording.

Promotion requires independent replay on the frozen source and an accepted interpretation of the requirement. Passing a model-generated test does not establish that the test states the intended contract. A verifier/kernel accepting a declaration does not establish that its type is the owner's target. Missing/failed/skipped gates cannot be counted as passing.

Report these separately:

- Reproduced introduced discrepancy (qualified base passes, head fails).
- Reproduced inherited discrepancy (qualified base and head fail).
- Resolved discrepancy (base fails, head passes).
- Invalid finding (independent evidence contradicts the alleged violation under the approved contract).
- UNKNOWN (missing access, unsupported capability, ambiguous requirement, incomplete native execution or insufficient evidence).

Do not treat unresolved candidates as proven defects or false alarms. Precision uses adjudicated findings only, with UNKNOWN counts visible. Single-PR observations do not support product-wide recall, comparative superiority or general correctness.

## Controlled assurance cases

Run a separately labeled, owner-designed calibration cohort: (1) a valid alternative proof of the same proposition, (2) a weakened conclusion P ∨ True, (3) an orphaned proof with no required consumer, (4) a skipped/failing verification gate, (5) an introduced implementation defect, (6) an inherited defect, and (7) a finite clean case. Freeze expectations before execution. Preserve native failure and withdrawal controls. These are designed controls, not unseen discoveries or evidence of general proof-review support. Unimplemented capabilities return UNKNOWN.

## Publication

The final comparison must include the same-source exposure table, adjudicated/UNKNOWN counts, native evidence links, inherited-versus-introduced classification, time/cost and remaining scope. Publish no private correspondence or unreleased material. A report may say a finding is absent from inspected public comments; a confirmed reviewer miss needs the stronger exposure evidence above.
