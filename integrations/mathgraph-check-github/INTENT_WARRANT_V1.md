# MathGraph Check — Bounded Intent Gap V1

This is the first **advisory, source-bound** intent/probe adapter for the existing Check → Resolve → Monitor product, on an isolated development branch. It has **no webhook or deployment changes**, no PR comments, and no action or merge permission.

## Product question

> The coding agent says DONE. CI is green. Does the software actually do what the user asked?

Green CI and source declarations are **not** proof of that implication. This module asks an independently authenticated verifier for *specific, user-defined, machine-checkable probes* of the requested behavior and refuses to carry results across changed sources or contracts.

## Input and trust boundary

Call auditIntent(contract, receipts, authority).

- Contract schema: mathgraph.intent-probes.v1. Subject binds repository, PR, exact base and head Git SHA. Claims name behavior and list required probe IDs. Every probe pins **input SHA-256, oracle SHA-256 and verifier Git SHA**. The contract digest is canonical sorted-key JSON SHA-256.
- Receipt binds contract SHA-256, subject SHA, probe ID, input, oracle and verifier pins; its result is PASS, COUNTEREXAMPLE, INCONCLUSIVE or ERROR, and its exit code and log SHA-256 are preserved. Counterexamples need an evidence witness SHA-256.
- **authority is not user or agent input.** The host adapter must independently select allowed repositories and exact source/contract hashes, authenticate receipt IDs, and qualify the oracle and verifier implementation hashes. A body field labeled verified/authenticated never grants authority. The pure module cannot itself authenticate GitHub, execute the probe or replay the witness.
- No hidden test coverage claim: finite pins only. If a probe is absent, ambiguous, changed, untrusted, crashed or timed out, its status is UNKNOWN.

Outputs use existing OBSERVED, BLOCKED and UNKNOWN. OBSERVED means these *particular* probes passed. BLOCKED means an independently admitted bounded witness was reported by an approved oracle; it is not a theorem or universal countermodel. Every report says intent_verification=NOT_ESTABLISHED, permission=ADVISORY_ONLY, current_applicability=UNKNOWN, with no proof badge. Source/head changes require requalification.

A trust policy **must** qualify test content, not just a green CI job. E.g. for a refund service, the independent oracle must encode the user requirement that an unavailable purchase **must not** return a successful refund. The agent's own convenient tests do not establish that oracle.

## Existing product integration

- Check: auditIntent returns results and claim_dependencies compatible with check-resolve-monitor-v1.mjs.
- Resolve: the existing resolve() may choose an explicitly permitted low-cost *proposal*, but does not execute or authorize it.
- Monitor: the existing monitor() downgrades carried-over OBSERVED state to UNKNOWN on source changes unless trusted independent requalification occurs.
- Report: renderIntentReport produces a readable *advisory* HTML report without a verified badge.

## Qualification

From the existing live-app source branch, the scoped CI runs Node 22 tests:

    node --test integrations/mathgraph-check-github/intent-contract-v1.test.mjs integrations/mathgraph-check-github/evidence-contract-v1.test.mjs integrations/mathgraph-check-github/check-resolve-monitor-v1.test.mjs

No permissions or cloud deployment required. Future work: a separately qualified GitHub App adapter must fetch exact-head evidence and independently execute selected oracles, retain artifacts and witness bytes in external storage, enforce a customer-authored intent contract, and add gated publishing. The present adapter **does not implement** that live integration.

## Warrant-preserving reuse: finite quotient collision gate

The companion pure consumer finite-warrant-quotient-v1.mjs checks the finite restriction of:

    ker(alpha) restricted to U  subseteq  ker(Phi_protected) restricted to U

Here alpha is a proposed compressed/merged representation, and the protected
observation Phi consists of the **exact source SHA and warrant status**.
A source swap or a change from OBSERVED to BLOCKED cannot be hidden behind the
same green-CI summary. When two explicitly enumerated rows have the same
alpha_key but different protected observations, the consumer returns
FINITE_COUNTEREXAMPLE with the two concrete rows. When there is no collision it
returns FINITE_PRESERVED **only for the supplied authenticated finite universe**.
No table self-hash authorizes a universal claim; an independently admitted
expectedUniverseSha256 and source allowlist are required.

Use this finite contract to audit proposed caches, provenance compression and
monitoring state merges before using them to decide which evidence can carry
forward. Do not infer that every possible run was checked.

## Reproducible synthetic product demo

The demo under demo/ has two independent programs. The deliberately buggy
agent's happy-path refund test passes. The separately written customer intent
oracle checks already-refunded orders and finds a concrete double-refund
counterexample. The demo runner executes both, binds the input and witness
bytes, and emits report.html and report.json with status BLOCKED.

The example is **SYNTHETIC**, with synthetic PR identity and a simulated
out-of-band authority. It establishes no live customer finding or actual GitHub
authentication. The CI retains an inspectable ZIP named
mathgraph-check-intent-gap-synthetic-demo. No comments or deploy actions run.

Full isolated tests:

    node --test integrations/mathgraph-check-github/intent-contract-v1.test.mjs \
      integrations/mathgraph-check-github/finite-warrant-quotient-v1.test.mjs \
      integrations/mathgraph-check-github/demo/intent-green-ci-demo.test.mjs \
      integrations/mathgraph-check-github/evidence-contract-v1.test.mjs \
      integrations/mathgraph-check-github/check-resolve-monitor-v1.test.mjs
