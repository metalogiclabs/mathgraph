# 2026-11-20 — Exact-source RFC native and relational-oracle calibration

PRIVATE RESEARCH — source-grounded bounded result, not a scored competition. The selected OSS-Fuzz rank-24 uriparser case was picked after source metadata inspection; NOT a blind holdout. Upstream was untouched.

## Authorities and source pins
- Original uriparser source: https://github.com/uriparser/uriparser/commit/abb9f328ae836ff5bf8f211e0ba82f7b6de01ebe
- Independently published examples: https://www.rfc-editor.org/rfc/rfc3986.html#section-5.4.1 and section 5.4.2. Expected outcomes were manually transcribed; independent two-person oracle adjudication NOT RUN.
- Hosted exact-source qualification: https://github.com/metalogiclabs/mathgraph/actions/runs/44627758550 at tested head 4db62d1e6f8fc93608c7bdd99d5e20aef14b350f. Two successful jobs: compile original source from a pinned checkout, then a separate job rehashes the received binary, independently rebuilds the original source and replays the reference checks.
- Artifact 14580286542 ZIP independently rehashed SHA256 ccd584d07bd48caa1ca72e765f34dfa57ec40b52eb2a024f7d52a843d96d2f64; artifact 14579977158 ZIP SHA256 04568e4aa966caaf2e6dc155a0c97b56d8a0da6b6d09fce133b03c151f4e418a; both match GitHub-reported digests.

## Executed findings
- 41/41 published unambiguous RFC3986 §5.4.1/5.4.2 examples matched for the declared base URI, including non-obvious query/fragment and path cases.
- The RFC permits TWO outputs for its backward-compatibility example http:g: the strict http:g or compatibility expansion http://a/b/c/g. Pinned native uriparser returned the permitted strict form. An oracle that insists on the alternative expansion alone would manufacture a false defect.
- Deliberately seeded observation loss strips query and fragment and creates 39 consequential conflicting pairs over the checked 41 examples. These are not upstream uriparser errors or 39 independent discoveries. A separately injected wrong decoder fails at g?y despite a sufficient unmodified observation.
- Equal-information conventional exhaustive pairwise script TIED; no human reviewer comparison or cost advantage has been established.
- Five tampered records were refused in the second CI job: stale source identity, forged native output, forged owner approval, changed diagnosis and changed allowed-output result.

## Mathematical refinement (STANDARD FACT, not novelty)
For deterministic protected property P:S→V, the original sufficient-representation criterion ker(q)⊆ker(P), and actual fidelity d(q(x))=P(x), remain correct on the declared domain.

For a requirement allowing multiple valid values A(x)⊆V, actual fidelity is d(q(x)) ∈ A(x). A compliant deterministic decoder on finite q(S) exists if and only if the intersection of permitted output sets in every q-fibre is nonempty. Equal allowed sets in every fibre is sufficient but unnecessarily restrictive.

Finite exhaustive control: research/assurance/relational-factorization-finite.py. Enumerated 216/216 configurations of three source states, two observation labels and two output values: 156 admit a decoder, 60 do not, and 96 of the 156 feasible cases have unequal permitted sets in a fibre. This is 96 false rejections by an overstrict *test*, not 96 software defects. Computability, efficiency, external requirement authority, action permission and infinite-domain generalization remain separate.

## Negative lineage and limits
- First CI #44626516597 failed in an isolation allowlist, which omitted two earlier rocket-integration research files; no native test ran. Corrected explicit allowlist only.
- Expanded first CI #44627679741 failed because the new test stripped literal backslash-r/n rather than the actual trailing newline from the permitted-output result. Corrected that exact test error; final run #44627758550 passed.
- Earlier system-installed liburiparser 12/12 test is NOT this source-pinned run. Native results above warrant only these actual pinned bytes and finite cases; no full RFC compliance, new upstream defect, independent owner acceptance or tool superiority.
- The normative permitted-output treatment can be a candidate method-specific profile of the EXISTING six-part Boundary Warrant. Do not create a new platform, new requirements standard, or extra ontology. Existing Check PRs #261, #279–#282 remain distinct; this experiment neither merges nor replaces them.

## Current residual and next experiment
An independently adjudicated, source-authorized real P or allowed-outcome A for an unfamiliar transformation; a blind, competent conventional reviewer with equal information/tool access; reproducible source-native witness; correct repair/diagnosis classification; complete human+compute and failure costs. The 24-project registry calibration was source screened; 24/24 remain UNKNOWN for full G0–G5 eligibility, not failed. Retain an out-of-model denominator and negative findings. No upstream source, deployment, external permissions or production infrastructure was changed.
