# MathGraph eligibility calibration v0.5 — prospective protocol (PRIVATE RESEARCH WORK; PUBLIC SOURCE ONLY)
Date: 2026-11-20 (Pacific/Auckland). Status: FROZEN SELECTION DESIGN, NOT AN EXECUTED COMPARATIVE STUDY.
This is a read-only eligibility calibration and method/denominator test, not a finding of upstream defects or an owner authorization. Do not deploy or contact maintainers from this protocol.

## Objective and stopping rule
Establish whether an OSS-Fuzz source-side sample contains independently source-authoritative, inspectable, and source-native testable transformation obligations suitable for a fair MathGraph versus conventional-review comparison.
This is a 24-item *calibration*, NOT the third-domain holdout or the predeclared 48-case superiority trial.
Record EVERY sampled item even if no qualifying case is found; no replacement, no post-result revisions, no selected-project cherry-picking. A failure to recruit qualifies as a negative result for THIS source registry.

## Immutable sampling authority
OSS-Fuzz: google/oss-fuzz@cdd107021c20428647db0699c33d6cb1f717474a.
Projects Git tree f4005bbe6406d83b414112624b2a3d6cf461aa44: exactly 1408 project directories.
Full source-side identifier list: oss_fuzz_ids_20261120.txt, ASCII sorted by strict bytewise order.
Prior 12-project systematic calibration exclusions: aspectj, cpp-httplib, flex, grpc-swift, jaxb, libexif, mariadb-connector-j, openapi-schema-validator, protoc-gen-validate, rust-regex, teleport, wolfboot.
These 12 are NEVER eligible for this disjoint 24-sample, nor for a subsequent truly unseen holdout.

Selection algorithm (implemented exactly in select_calibration.py): remove exclusions; seed unsigned 32-bit state from the first eight hexadecimal digits of the pinned commit XOR 0x4d475635 (label MGV5); run xorshift32 with shifts 13,17,5 and 32-bit masking, using descending Fisher–Yates j = state mod (i+1); take first 24 resulting identifiers. This is deterministic pseudo-random selection (modulo bias negligible, NOT cryptographically unpredictable); audit every result. No filtering by suspected bug type. Freeze THIS protocol and code on GitHub before revealing the selected IDs or reading any selected project's upstream documents. Any subsequent expansion must be a new version.

## Immutable screening disposition
G0 IDENTITY: resolve OSS-Fuzz main_repo against the pinned metadata; record redirects, canonical upstream URL, default branch, archive status, and source revision. A rename is NOT automatically ineligible.
G1 EXTERNAL OBLIGATION: identify a specific, independent, version-pinned normative/documented behavioral requirement with exact clause and admitted domain. Source existence alone is not enough. Required two independent interpretations must agree; unresolved disagreement = UNKNOWN_ORACLE_AUTHORITY. A project's README is not necessarily an external standard.
G2 TRANSFORMATION: identify executable or inspectable q and downstream d with exact source paths, admitted input, and observer semantics; do not infer this from project category.
G3 NATIVE REPLAY: execute genuine original upstream test or an independent source-derived witness under a fixed, reported environment/budget; preserve logs and reason for inability. A repository with tests but no executed native test = NOT_RUN/UNKNOWN, not PASS.
G4 FAIR COMPARATOR: source/obligation/graph/solvers/tools exposed symmetrically to baseline and MathGraph; independent qualified reviewer selected before outcome, independent oracle and arm-blinded adjudication. If missing = UNKNOWN/NOT_ADMITTED.
G5 FINAL: ELIGIBLE only if G0–G4 PASS; INELIGIBLE for a definitively failed intrinsic admissibility criterion, or UNKNOWN with exact missing gate otherwise. All cases remain in the recruitment denominator; missing results are never counted as failures or wins.

Screen pass order G0->G1->G2->G3->G4, stop on decisive intrinsic failure but retain all G0 metadata. For the current read-only connector calibration, explicitly mark unavailable native execution or independent owner/reviewer as NOT_RUN; do not invent human approvals or imply full G0–G5 completion.

## Independent evaluators and constraints
Oracle authority must be outside the detector and case constructor. Pre-appoint two independent P reviewers; material disagreement disqualifies from scored trial and is reported. Independently chosen competent conventional reviewer: relevant implementation language/transform domain, substantial production review/testing experience, demonstrable source/requirement-reading competence, no MathGraph-author involvement. Record identity/qualifications/conflicts before revealing cases; if unavailable, comparison is NOT_RUN.
No arm sees the other's outputs; blind final defect/repair/novelty scorer to arm labels. Both may use solvers, source inspection, scripts, adaptive testing and indexed ledgers. Graph preconstruction cost either available to ALL A1 arms or fully charged in A2.

## Diagnostic ground truth
For exact deterministic q,P,d on declared finite X:
- q(a)=q(b), P(a)!=P(b) -> REPRESENTATION_INSUFFICIENT (verified pair);
- complete sufficiency on X plus d(q(x))!=P(x) -> DECODER_WRONG;
- BOTH only if separately witnessed; sound alternative repairs accepted as DEFENSIBLE_ALTERNATIVE, not incorrectly forced into one category.
- A repair adding additional source information changes q; existence of some decoder says nothing about computability, cost, or owner approval.
- UNKNOWN when P, X, q, d, completeness or authoritative interpretation is missing.
For numeric approximate comparisons freeze a separate exact relation; do not assume non-transitive tolerance is an equivalence.
Score correct repair class and defensible alternatives separately from detection.

## Trial structure after eligibility
Trial A1: same independently prepared graph and P to conventional C, generic backward-slice G, MathGraph typed traversal T. Baseline C can use typed relations and same solvers. T-vs-G tests mechanism ablation; T-vs-C tests actual differentiation.
Trial A2: same raw source and P to conventional C and T; all graph-generation/preparation time billed.
Trial B: independently authored source-only P extraction, sealed reference P, separate outcome; NOT merged with detection score.
Preregister primary composed (>=3 independently source-derived edges) and rare-class (<=1% under justified frozen input distribution) subgroups, report overlap. Full cohort including OUT_OF_MODEL and no-finding is context.

## Coverage, cost, novelty and stop
Report all-case correct findings/UNKNOWN/no-finding and false-decisions; paired determinate-case cost is supplementary and can be selection-biased; include timeouts via censored time-to-finding. Record human time, compute, setup, graph extraction, native oracles, failed probes, adjudication, review, requalification and correction.
Novelty search for any natural candidate: exact upstream issue and PR trackers, release changelog and relevant advisory records at frozen revision; search 3 distinctive identifiers/literals, 2 conceptual paraphrases, up to 20 min independent adjudicator, blind to arm; report PREVIOUSLY_DOCUMENTED, NO_PRIOR_PUBLIC_MATCH_FOUND, UNKNOWN_NOVELTY. A seeded defect is never a novel upstream finding.
When no real-world defect exists, independent seeded variants can test diagnosis; count no-finding and actual cost for unmodified system, never infer no bugs globally.
No independent owner approval / current source / qualified oracle / equal tooling / fully measured costs => no public comparative score or permission to repair. Permission to investigate is not permission to modify, deploy, certify or claim an institution endorses MathGraph.

## State and next gate
Already recorded: YAML/FRET two-domain finite diagnostic transfer, existing Boundary Warrant v0 and rocket native PR #282, strong equal-information baseline ties, corrected stale-source fingerprint. Those are historical observations, NOT newly executed by this calibration.
Immediate action: run select_calibration.py on pinned complete roster; then screen all 24 in generated order, keeping G0–G5 result and missing authorities. If eligibility poor, retain failure and compare a newly preregistered registry, not post-hoc relax requirements.
