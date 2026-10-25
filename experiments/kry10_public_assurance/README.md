# Kry10 public-source safety-case probe (2026-10-25)

## Objective
Reproduce a bounded observation/assurance test using an immutable **real Kry10 public source**, while refusing to promote a safety claim beyond its evidence.

## Grounded inputs
- Kry10, Ihor Kuz, *Kry10 OS Software Safety Manual* presentation, seL4 Summit 2026: https://sel4.systems/Summit/2026/slides/kry10-os.pdf (slides 5, 7, 9, 17, 21).
- Kry10 public AM335x GPIO/PWM manifest at immutable commit: https://github.com/Kry10-NZ/kos_am335x_starterware/blob/f6758778682a1c9f998feab6e2e976920dec81ee/lib/manifest.ex
- Exact source Git blob: `a61cd6b21996b4dc4af818c3d378c3c283104c7b`, read independently through GitHub and reacquired by GitHub Actions.

**The AM335x manifest is NOT represented as the source of the cart shown in the presentation.** It supplies an independent, checkable exemplar of KOS hardware-resource configuration, not a cart deployment or verified safety property. The slides are accessible through the original seL4 event website, but no PDF content digest is claimed.

## Experiment
A synthetic five-world stop-command model distinguishes nominal from stale sensor, lost command, stuck motor cutoff and excessive coasting. Given equal baseline control signals, exhaustive enumeration of 16 sensor subsets and independent bit-mask dynamic programming agree that sensor freshness + wheel-motion feedback is the least-cost separating pair (4 invented cost units). The cost numbers and fault states are hypothetical, not measured at Kry10.

A sixth synthetic world ('already had contact, now stopped') is exactly observationally equivalent to nominal under **all four snapshot sensors**. It requires historical, source-authenticated stopping / distance / trajectory evidence to distinguish; no historical safety finding is warranted by present snapshot checks.

Power disabled does not logically guarantee no contact: finite toy physics can still allow coasting into a person before stopping.

## Results and limits
- Local standalone Python artifact: 21/21 tests PASS; separate exhaustive verifier reproduces minimum costs and counts.
- GitHub Actions workflow `.github/workflows/kry10-public-assurance-probe.yml` re-fetches real Kry10 source, checks immutable Git blob, checks a few manifest structural tokens without executing copyrighted code, and produces a source-specific JSON receipt. **Do not claim the workflow passed until actual run verified**.
- The public presentation is not Kry10's full safety manual. No real KOS device, deployment manifest, signed update evidence, proof-to-device attestation or actual safety-case acceptance was obtained.
- Kry10's own presentation already covers input/output/hardware faults and common-cause failures. The proposed value is traceable requalification, not discovering that these faults exist.
- No vulnerability or missing feature is alleged. This is candidate evidence-composition capability, not a certified safety analysis.

## Decisive residual
Acquire from an authorized engineer one redacted actual cart/safety case: requirement and assumptions, signed deployed config, evidence identity, motor-stop timing/collision-distance bound, physical actuator feedback/history and a changed revision. Compare the before/after claim requalification against Kry10's existing process on the **same evidence**. If they already handle it equivalently, reject the differentiating claim.

## Action boundaries
Read-only analysis; no changes to Kry10 repos, no robot movement, no enforced release gate, no unsolicited outreach or safety certification assertions.


## External transfer, not Kry10 production testing (2026-10-25)

A second, source-distinct public example, [EdgeCaseResearch/oasc at immutable commit abf48ef](https://github.com/EdgeCaseResearch/oasc/blob/abf48ef74d07ff485ef759c5f6f5390953ca45c6/open-autonomy-safety-case.sacm.xml), provides a genuine SACM 2.2 XML argument template, not a Kry10 artifact or an audited deployed safety case.

`sacm_transfer.py` independently checks exact downloaded Git blob, XML identifiers, artifact references, evidence edges, inference endpoints, reasoning references, and absence of dependency cycles. It then computes the documentary downstream reach of each evidence reference with (a) BFS and (b) a separately coded fixed-point oracle. The native workflow runs 16 adversarial parser tests. The pinned template declares **38 claims, 26 artifact references, 23 evidence links and 23 asserted inference relationships (37 inference source edges)**. Both traversal algorithms agree for all 23 evidence references.

**Hypothetical change**: treating `EV_63` (an ISO 26262 assessment *reference*) as withdrawn yields affected documentary claim IDs `G55, G39, G4, G1`; 34 other claims have no path from `EV_63`. This is not a real withdrawn assessment, proof of safety, completeness, or a warranted claim. The published XML contains no authenticated underlying assessments, so **root safety claim UNKNOWN**, and evidence provenance is unqualified. A competent baseline graph traversal can produce the same structural result; comparative method advantage remains UNKNOWN.

To replay: `python3 -m unittest discover -v -s experiments/kry10_public_assurance -p 'test_sacm_transfer.py'`; then download the pinned upstream XML and run `python3 experiments/kry10_public_assurance/sacm_transfer.py OASC.xml`. The pinned SHA-1 is a Git blob identification check; it does not independently authenticate original author identity or assess certification validity.

**Status:** two separate primary sources were acquired in CI, Kry10's AM335x resource manifest and Edge Case Research's assurance template. They must not be linked as a single deployed system. Inference: no Kry10 deficiency, commercial advantage, independent physical validation or safety approval has been established.

## Minimal evidence request to Kry10 engineering (not sent)

Would Kry10 be willing to share a **redacted, non-operational** example of: (1) one real system-level safety claim and its assumptions; (2) one exact deployed configuration/source identity; (3) linked formal assurance and physical verification receipts (with dates and source IDs); and (4) one version change together with Kry10's current requalification verdict? No raw credentials, personal or export-restricted information, proprietary internals or production control interface are required. We would compare MathGraph's selective warrant/UNKNOWN classification against Kry10's existing assurance process under equal inputs, read-only and privately, and report no differentiated benefit if Kry10 already does this. The public template is available to demonstrate the format without asking for their data first.
