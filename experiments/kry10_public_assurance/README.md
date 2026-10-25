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
