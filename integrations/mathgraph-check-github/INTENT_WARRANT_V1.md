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

The consumer also reports whether the collision refutes decoding the
**protected verdict** from the proposed observation (`target_decidability`),
or only loses provenance (`source_traceability`). These are different failure
modes. A later verdict collision takes precedence over an earlier provenance
collision; both witnesses are preserved when present. A verdict collision
refutes factorization on any domain containing the pair. A `FINITE_PRESERVED`
result does **not** establish a universal factorization.

The source-pinned L4YAML case in
`experiments/check-l4-observation-ceiling-v1/` uses a previously qualified Lean
raw-comment witness to demonstrate this no-go for the frozen parser-success
bit versus a necessary normative character requirement. It can form an
advisory-only Check Run preview, but it neither reruns Lean nor publishes a
Check Run. Complete YAML-language correctness remains UNKNOWN.

## Authenticated Check → Resolve → Monitor projection adapter

The read-only GitHub PR adapter `authenticated-cycle-v1.mjs` additionally
accepts optional `projectionClaim` and **separately trusted**
`projectionAuthority`. It reads the current PR head from GitHub first. The
pure `projection-claim-v1.mjs` then binds that head, an exact reviewed claim
digest and an independently qualified finite-universe SHA; a pair whose
observed result is identical but whose **qualified opposite verdicts** are
`OBSERVED` and `BLOCKED` becomes an advisory `NAMED_OBSTRUCTION` and a
`BLOCKED` Check claim. An `UNKNOWN` verdict cannot impersonate the opposite
truth value. Provenance-only changes, a finite no-collision, mismatched source
or missing trust remain UNKNOWN.

The existing `resolve()` only selects a non-executing suggestion from the
host's explicitly permitted, source-authoritative plans; no generated fix is
entitled to run. The existing `compareSnapshots()` and `monitor()` withdraw
the claim when a changed head has no newly qualified witness. The native
Check API still excludes MathGraph's own Check Runs as independent evidence.

**Operational boundary:** This is a wired, tested optional argument to the
authenticated readback used by the first-party workflow, not a new public
webhook payload or a deployed generic witness-discovery engine. The current
default first-party runner does not inject an independently qualified
projection contract/policy, so ordinary runs behave exactly as before. The
frozen L4YAML witness may be supplied only for an authenticated matching
head, never copied onto a newer PR. Qualifying arbitrary user requirements,
discovering genuine separating witnesses, protected policy distribution,
and deployment remain distinct UNKNOWN work.

## Signed independent reviewer admission (research path)

`signed-projection-review-v1.mjs` adds an optional cryptographic reviewer
boundary before the same finite projection checker. An Ed25519 signature covers
the canonical claim, exact authenticated PR subject, reviewer's key identity,
and a named evidence receipt with its artifact digest. Only an out-of-band
trusted public-key allowlist can qualify the signature; a public key embedded
in a PR or claim packet is rejected. The authenticated `githubSnapshot` accepts
an optional `signedProjectionReview` with `trustedReviewerKeys`, mutually
exclusive with the earlier raw trusted-host `projectionClaim` inputs. A forged,
stale, unsigned, or incomplete review remains UNKNOWN even with green CI.

**Not a proof replay:** The signature authenticates *who reviewed and approved
these exact bytes*, not whether the reviewer was correct or whether the
referenced Lean proof artifact itself is valid. Proof-byte verification and
the protected runner supplying independent trust keys are still required for
stronger assurance. The existing default first-party runner, GitHub workflow,
and deployed hosted pilot do not pass a signed packet or new trust keys.

## Historical Lean artifact-byte corroboration (opt-in research path)

`proof-artifact-corroboration-v1.mjs` computes SHA-256 over the **downloaded
ZIP bytes** and compares it with a separately pinned receipt. It then checks
the exact historical Lean source commit and build, reported theorem type,
reported allowed axioms, source witness, successful proof qualifications, and
an intentionally failed negative control. Missing, duplicate or altered
evidence returns `UNKNOWN`. It never executes ZIP member paths or declares a
new Lean kernel check. A local replay command using the pinned 8 November
L4YAML record is under
`experiments/check-l4-observation-ceiling-v1/corroborate-artifact.mjs`.

`admitCorroboratedSignedProjectionReview` adds a stricter signed-review mode:
the review's receipt reference and artifact digest must match that separate
trusted policy, and the artifact bytes must corroborate. `githubSnapshot`
exposes this only when the host explicitly supplies `proofArtifactPath` and
`trustedProofReceipt`. If the host requests this mode without both valid
inputs, the projection is `UNKNOWN` even if the signature and ordinary CI are
green. No automatic upgrade occurs from a self-selected in-PR policy.

**Boundary:** `CORROBORATED` means the named historical archive and its logs
match the policy, **not** that the Lean proof was freshly rerun, the reviewer
is independent, YAML is fully formalized, or downstream callers exercise the
intended contract. The default runner still supplies neither protected
reviewer keys nor a signed review. A protected, independently administered
production runner and actual outside reviewer approval remain `UNKNOWN`.

## Protected-host operator admission — executable, not activated

`protected-review-runner-v1.mjs` composes the authenticated GitHub PR-head
readback, exact signed-review and ZIP-byte gates, and separately authenticated
GitHub artifact/job metadata. It requires a default-branch
`workflow_dispatch` context, verifies the source-run SHA and successful
`directive-proofs` job, and rereads the PR head before any advisory
`NAMED_OBSTRUCTION` is admitted. A replacement artifact, changed PR head,
missing reviewer key, failed job, incomplete API response or wrong context
remains `UNKNOWN`. No check is published, no repair is run and no merge is
authorized. The ZIP decoder uses fixed `/usr/bin/unzip` with a scrubbed child
environment; an attacker-supplied `unzip` on `PATH` cannot execute.

The companion read-only `run-protected-review-v1.mjs` entrypoint consumes
environment-controlled values:

- `GITHUB_REPOSITORY`, `GITHUB_EVENT_NAME`, `GITHUB_REF`,
  `MATHGRAPH_DEFAULT_BRANCH`, `MATHGRAPH_PR_NUMBER`, `GITHUB_TOKEN`
- `MATHGRAPH_EVIDENCE_TOKEN` (scoped cross-repository Actions read)
- `MATHGRAPH_SIGNED_REVIEW_FILE`, `MATHGRAPH_TRUSTED_REVIEWER_KEYS_FILE`,
  `MATHGRAPH_TRUSTED_PROOF_RECEIPT_FILE`, `MATHGRAPH_PROOF_ARTIFACT_PATH`,
  `MATHGRAPH_PROOF_ARTIFACT_ID`

It prints neutral JSON and uses exit 3 for UNKNOWN; it never prints secrets.
The files and two tokens **must be provisioned out of band** by a trusted
operator. Values provided by PR source, workflow inputs or an AI suggestion
are not an independent policy. A supplied `GITHUB_REF` string cannot itself
prove the code is protected. A suitably protected default-branch environment,
an actual independent reviewer key/approval, and real credentialed end-to-end
qualification are still required. This branch does not create/activate the
environment, access admin secrets, or deploy a new workflow.

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
