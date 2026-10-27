# NFM 2027 — independent claim-to-warrant assurance addendum (private co-author candidate)

**Prepared 27 October 2026 for Metalogic Labs internal review. NOT sent to Nicolas Rouquette or Xiaolan Xu. NOT inserted into shared Overleaf or any JPL repository.** This note adds source-pinned evidence to the NFM candidate already sent on **11 October**; that original coauthor PDF/LaTeX/diff handoff is already delivered and should not be represented as still owed.

## Candidate contribution: the boundary above a correct proof

A kernel-checked Lean declaration proves **its formal type** under its stated assumptions. A model author, document, imported annotation, optimization or release report may attribute a **different** scientific or engineering claim to that result. The additional independent assurance obligation is:

> Given a claim \(C\), authoritative interpretation \(I\), source and program revision \(S\), and evidence family \(E\), decide only whether the cited, independently checked evidence actually supports **the exact scoped conclusion** \(C\); withdraw that permission when the identity or evidence changes.

MathGraph's bounded method binds explicit author-provided claim/test IDs and exact source revisions to native interpreter/verifier logs, independent observations, negative controls and selective withdrawal. It deliberately returns *MISMATCH*, *UNKNOWN*, *WITHDRAWN*, or *REJECTED_EVIDENCE* rather than stretching a correct proof/test into a stronger scientific assertion. This is **not** a general semantic parser for arbitrary natural language; authorship and intent are separately authoritative inputs.

### Claim → source → verifier → evidence → permitted conclusion

| Real source case | Authentic underlying evidence | Independent challenge | Warranted, bounded conclusion | Does not establish |
|---|---|---|---|---|
| **PKC/OpenSysML \`@Checked\`** | Untouched \`nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824\`, real OpenSysML **v0.9.1** SysML conversion, source-native PKC importer, Lean generated module and actual checks. Six claim-control classes (13 API-JSON native and 5 full-text lane observations), plus five withdrawal/forgery probes. | Genuine proof citation \`PropertyKindCalculus.Iso80000.Part3.Edge.width_length\` is accompanied by separately authored \`@Checked.statement = "False"\`. Original importer and Lean accept the citation while emitting \`False\` as a comment; experimental local strict policy rejects unchecked text, and withdrawing it restores original behaviour. | Citation's exact typed theorem is valid; optional free text is **not** thereby proved. Restrict interpretation of \`statement\` until Nicolas confirms whether field is authoritative proposition or commentary. | A proof of \`False\`, Lean kernel unsoundness, general SysML/PKC failure, or intended upstream contract. |
| **Open Source Rover kinematics** | Unmodified *educational JPL Open Source Rover* \`nasa-jpl/osr-rover-code@7aaf18512c9e8a997931f0caae28b63c8c6e9a78\`, authored \`RoverKinematics.body_speed_for_radius\` docstring and test \`test_body_speed_keeps_every_wheel_within_max_vel\`. All **16/16** authored tests pass. **70/70** finite geometry cases independently recomputed. Removing limiter in an isolated copy makes **7/7** speed-bound tests fail. Eight independent altered claim/evidence controls reject or abstain. | Green tests cited for a **different** requirement, stronger flight safety, old source, missing records, fake native outcomes or tampered wheel measurements. | At exact source and test scope, wheel-speed limiter has the specified selected software-test and finite-grid evidence. A green CI result alone does not establish an unrelated requirement. | NASA flight certification, Endurance mission verification, physical motor/ROS safety, all-input mathematical proof, or measured superiority to an equally informed conventional reviewer. |
| **PKC HCP L4–L6 tutorial** | Current \`nasa-jpl/PropertyKindCalculus@023ff7e730e86260871c1adb7411dee12848d006\` Lean 4.35.0, original source/worksheet/blueprint copies and HCP checker, plus independent auditor; exact Actions qualification must be consulted before promoting. | R3's empirical gate is explicitly *P-only*, with two true spot checks. In the generic P/Q module the same P-scoped R3 leaves **Q UNGOVERNED**. Other controls challenge citing R1 for R3, scope inflation and altered source excerpts. | Conditional source/claim fidelity for named author lesson and P's declared requirement coverage, **if native Lean and independent controls are green**. | That R3 holds for *every* state of P, that Q is governed, that a manufacturer referent was independently validated, or that educational worksheets' \`sorry\` placeholders are certified results. |

## Direct, independently accessible receipts

**PKC SysML source-native V1** — [MathGraph draft PR #207](https://github.com/metalogiclabs/mathgraph/pull/207), [full GREEN Actions #40445570801](https://github.com/metalogiclabs/mathgraph/actions/runs/40445570801), [retained artifact #12707883439](https://github.com/metalogiclabs/mathgraph/actions/runs/40445570801/artifacts/12707883439), artifact SHA-256 \`0e81f5e88121d536df4e33f4ac826d36cd5103495f5b4282211cbcccd8320134\`. Previous REDs preserved as an unavailable historical TorchLean tree and one test-mutator selecting the wrong \`False\` occurrence.

**Autonomous engineering source-to-claim V1** — [MathGraph draft PR #208](https://github.com/metalogiclabs/mathgraph/pull/208), [full GREEN Actions #40447749268](https://github.com/metalogiclabs/mathgraph/actions/runs/40447749268), [artifact #12709146303](https://github.com/metalogiclabs/mathgraph/actions/runs/40447749268/artifacts/12709146303), artifact SHA-256 \`eb0634c41538bfbcc9de1a39b433a437674f1d857198d2da59772e2e43dd6f4d\`. Previous RED was test-harness import selection, not an external rover defect.

**Independent tutorial check (candidate until final receipt)** — [MathGraph draft PR #209](https://github.com/metalogiclabs/mathgraph/pull/209), public pinned PKC [current HCP blueprint](https://github.com/nasa-jpl/PropertyKindCalculus/blob/023ff7e730e86260871c1adb7411dee12848d006/blueprint/PropertyKindCalculusBlueprint/Chapters/HCP/L6_Requirements.lean). Historical Nicolas request cited “chapters 6–8”, whereas **current HCP inventory is L0–L6**; our audit covers the three directly relevant published L4–L6 lessons and must not be described as reviewing nonexistent L7/L8.

## Comparison protocol: FGM and MathGraph (NOT YET RUN)

If/when Nicolas approves sharing FGM outcomes (no private source needed), freeze **one exact named theorem/proof dependency slice** and align:

1. Formal source property and scope; accepted reference \`Match\` and theorem axioms.
2. FGM proof-to-call structural graph and its actual classifications.
3. MathGraph's independent claim, code/requirement authority, upstream SHA, machine logs and required hypotheses.
4. Controlled mutations: undeclared source, same-value/different-source CSE, removed proof edge, valid-but-irrelevant theorem replacing the intended requirement, equivalent harmless reordered match, and missing source or withdrawn receipt.
5. For each mutation, compare FGM and MathGraph's actual verdicts, false positives/negatives, exact reason and whether an equally informed conventional reviewer would detect the same error.

The combined test is a **proposal**, not FGM corroboration. The private FGM code and classifications must not be inferred from public prose. Claim identity may remain an independent human/domain-expert premise even after both verifiers pass.

## Suggested tightly bounded claim for the paper

> We independently replayed two source-pinned claim-assurance cases above existing verification mechanisms. In PKC's public SysML interchange, a valid Lean declaration citation could be accompanied by a separately authored \`statement = "False"\`; the importer emitted that text as a comment while Lean checked a different proposition. In a distinct public rover software case, selected passing original unit tests and an independently recomputed finite wheel-speed grid warranted the named software-contract evidence but not unrelated or stronger safety claims. Controlled misattribution, withdrawn evidence and forged observations were refused. These results motivate a separable claim-to-evidence permission layer; neither case proves general scientific correctness, universal formal statement alignment, hardware safety or superiority to an informed conventional reviewer.

**Manuscript placement:** small source-pinned experiment in §8, with scope note in §3/§4. Do not claim NASA endorsement, change co-authorship, overwrite manuscript, or treat above as already incorporated. The original NFM **11 October** delivery is complete; Nicolas acknowledged the contribution and said he would review/incorporate. The **18 October** SysML contract question was already sent and awaits an authoritative reply. No repeat email is justified.

## Outstanding author-relationship obligations (not hidden by experiment success)

The remaining explicitly invited task is the **tutorial boundary/requirements review**. The current independent HCP L4–L6 replay is its closest available source-native mapped slice, not a literal audited 6–8 paper chapter set. A production-real FGM joint comparison requires Nicolas's approval or release. CPU/GPU floating-point behavioural equivalence is separate JCP research; neither independent case authorizes it. Unrequested institutional/product deployment or PRs on upstream JPL are out of scope.
