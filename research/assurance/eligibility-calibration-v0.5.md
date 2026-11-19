# MathGraph third-domain eligibility calibration — frozen v0.5
Date: 2026-11-20 NZDT. Status: PROTOCOL FROZEN BEFORE 24-PROJECT REVEAL; no pre-registered superiority claim.
Authority: internal study protocol only; not an external owner/adjudicator grant.
Source: google/oss-fuzz @ cdd107021c20428647db0699c33d6cb1f717474a; projects tree f4005bbe6406d83b414112624b2a3d6cf461aa44 (1,408 entries).

## Discovery-population and sampling, fixed before inspected candidates
Read exactly the pinned Git tree; collect tree entries with type=="tree", path as project ID. Reject malformed/non-ASCII IDs. Sort by ASCII byte order; use the complete sorted ID vector as the reproducible universe. For deterministic pseudo-random ordering, compute SHA256 of UTF-8 bytes:
  "MathGraph-OSSFuzz-eligibility-2026-11-20-v0.5\0" + project_id
and sort ascending by the 64-character lowercase hex digest, breaking impossible hash ties by project ID. Do not substitute local locale sorting.

Disjoint calibration exclusion IDs from the previous 12-project nonrandom metadata screen (pre-declared): aspectj, cpp-httplib, flex, grpc-swift, jaxb, libexif, mariadb-connector-j, openapi-schema-validator, protoc-gen-validate, rust-regex, teleport, wolfboot. Do not exclude other candidates after ranking based on a suspected defect or attractive source. Select first 24 nonexcluded IDs in hash order. Do not replace candidates on failed/unknown gate. Record their ordinal/hash and immutable registry tree membership.

If a selected project is found to have been previously investigated in an earlier MathGraph campaign, preserve its position, mark PRIOR_EXPOSURE and never count it as blind novelty. Record rather than substitute.

## Sequential, evidence-sensitive eligibility gates
G0 SOURCE: public original source resolved to canonical repository and exact commit; note redirect, archived/read-only, language, docs, license and environment. A broken/missing repository is INELIGIBLE_SOURCE with independently recorded reason. Existence of main_repo in OSS-Fuzz is metadata only.
G1 ORACLE: identify one concrete behavioral obligation from a source independent of the transformation (published normative text or documented, accepted domain-owner requirement), pin clause/revision and governing scope, give two independent interpretations. Material disagreement or no independent reviewer -> UNKNOWN_ORACLE_AUTHORITY, not PASS.
G2 TRANSFORM: pin inspectable original O/q and downstream d (or exact native projection under inspection), input-domain contract, source path and version. Missing obligation-to-code bridge -> UNKNOWN_TRANSFORM, not an invented q.
G3 NATIVE: original test/translator/monitor is run at exact SHA with observations and positive/negative controls under declared resources; a README or historical CI badge does not pass. Native unavailable -> UNKNOWN_NATIVE.
G4 FAIRNESS: pre-identify an independent conventional reviewer (skills and domain experience), and match oracle, source, graph representation or graph-construction charge, solver access, permissions, time and test budget. No human comparator -> UNKNOWN_REVIEWER.
G5 DISPOSITION: ELIGIBLE only if G0-G4 satisfy their declared gates. Explicit disqualifiers -> INELIGIBLE(reason). Missing checks -> UNKNOWN(named missing gates). Report all selected IDs as denominator; do not turn UNKNOWN into failure.

Bounded pilot screening: up to 15 minutes source review per project including metadata and public source, stop at first definitively failed/UNKNOWN gate; later gates NOT_ASSESSED. The environment may prevent authentic native tool execution; no staged claim of complete eligibility.

## Diagnostic scoring and comparator (predeclared, not executed by protocol freeze)
P is independent, approved oracle on declared domain X. q:X->T; d:T->V. Sufficiency: ker(q|X) subset ker(P|X). Fidelity: d(q(x))==P(x) on X. If fidelity universal on same X then sufficiency follows; finite PASS only covers checked X. Sufficient representation need not supply a computable/cheap decoder. Approximate numerical relation must be separately specified and never silently treated as equivalence.
Labels: INSUFFICIENT_REP if a,b collapse in q and P differs; INCORRECT_DECODER if sufficiency is established on X and concrete d disagrees with P; BOTH only with separate evidence of incorrect decoder after information is restored; AMBIGUOUS_DEFENSIBLE if different plausible fixes alter the interface/domain; UNKNOWN when premises or completeness lack warrant.
Primary future subgroups: H1 >=3 source-grounded transformation edges, H2 <=1% probability under prior fixed input distribution; require independent definition before scoring. No post-outcome subgroup re-slicing.
A1-C: competent conventional reviewer with same graph/typed metadata/solvers, unrestricted independent adaptive reasoning. A1-G: generic backward slicing. A1-T: typed obligation traversal. A2-C/T: same raw source/P; all graph extraction charged. Trial B: source-only P acquisition, separate from Trial A.
Report per case verified detection and independently adjudicated repair class, false allegations, total human/compute/setup/verification time, timeouts and non-fit cases. Equal-info human review NOT established by self-authored scripts. A human-independent synthetic baseline test is only MECHANICS/TIE, never competitor superiority.
No-defect natural source is legitimate: seeded variants by independent case author may exercise diagnostics, but do not score them as previously unknown original defects.
Novelty outcomes from arm-blind independent public issue/PR/changelog/advisory search capped at 30 minutes per candidate with fixed queries ("<module> <symptom>", "<function> <input>", "<error> <transformation>" and exact witness strings); NO_PRIOR_PUBLIC_MATCH_FOUND is not proof that nobody knew. Prior-public-match checking for a live case requires an independent auditor and documented source snapshots.

## Stop, lineage, and authority
If no project completes G0-G4, report 0 independently qualified, number UNKNOWN/INELIGIBLE and calibrated gate costs; do not claim 0 true eligibles or continue choosing appealing repos.
Retain any false positive, solver timeout, failed native test, source alias, orphaned requirement or disagreement as evidence. Existing MathGraph and conventional baseline ties remain ties. No installation, third-party contact, upstream repair, release approval or operational mission claim is implied. Do not touch protected PRs #261/#279-#282 or production Cloudflare.
Follow-on native artifact admission is an independent isolated experiment; the G0-G5 registry screen and #282->#261 warrant-invalidation test cannot be merged into one alleged trial.
