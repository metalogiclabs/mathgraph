# MathGraph Check for Open Math Model — claim bridge V1

**Status:** the frozen first-party Artin native replay and registered-App transport are **WARRANTED_BOUNDED** within their declared source and environment; general OMM community intake is **UNKNOWN**. There is no enabled community OMM `/check` or `/fix` command, arbitrary Lean evaluation, or research-intent certificate.

This additive adapter can turn a trusted, exact-source native Lean replay into the shared MathGraph Check/Passport-style neutral report. It distinguishes:

1. **Lean candidate compilation:** the exact candidate was compiled in the pinned environment; compilation alone is not an axiom audit.
2. **Original-target consumer:** an operator-authored, hash-pinned consumer compiled with standard axioms, was rejected by Lean in this replay, or is UNKNOWN. Rejection does not prove semantic inequivalence.
3. **Formal-statement equivalence:** UNKNOWN in this adapter until a separately authenticated, same-context SemantEq result is integrated.
4. **Candidate proof necessity and paper-to-Lean intended meaning:** both UNKNOWN, including on consumer acceptance.
5. **Independent evidence warrant:** UNKNOWN until a trusted GitHub/Actions artifact chain is verified externally.

The bridge expects an `omm.request.v1` formed from authenticated GitHub PR metadata and **actual fetched candidate source bytes**; a separately admitted `omm.claim-contract.v1`; and an `omm.native-receipt.v1`. Contract and receipt exact-byte SHA-256 pins must be admitted by the trusted Check controller, not the PR, an AI answer, or an arbitrary JSON field. The native output includes both pinned source hashes, the consumer and candidate declaration names, the Mathlib Git revision, tracked toolchain hash, native exit codes and separate candidate/consumer axiom audit. The controlled release stage independently re-derives the qualified source identities and artifacts before App publication; this does not confer authority over a paper's intended meaning.

The optional workflow `check-omm-artin-native.yml` performs a fixed, first-party native Lean cohort only:

- PR #239: an Artin proof with an added `CommGroup` hypothesis. Candidate Lean compilation can succeed, but an original `Group` target consumer should reject. The result is **NOT_ESTABLISHED_IN_THIS_REPLAY**, not a proof of mathematical inequivalence.
- PR #240: the repaired candidate under the original `Group` assumption. The exact original-target consumer and separate `#print axioms` checks should accept. The result is **CONSUMER_ACCEPTED**, never an intended-claim warrant.

GitHub preflight pins both public PR head/base identities, the exact `ArtinGenerators.lean` bytes and the externally published exercise. A separate job executes only those pre-registered sources with Lean 4.28.0 and a pinned Mathlib revision, without GitHub App or LLM credentials. CI stores source, manifest, trace, assessment, neutral report **and a deterministic GitHub App Check-run preview** for each fixed case. The preview reuses the existing `advisory-publisher-v1` schema, remains `conclusion: neutral`, and never transmits credentials or publishes a Check by itself. Workflow outcome and artifacts, not this README, are the authority for whether the native cohort actually passed.

An additional, strictly first-party publisher stage runs **only after both native jobs pass**. It downloads artifacts from that same workflow run, independently recomputes all manifest hashes, exact Artin source identities and OMM assessment, verifies the GitHub App Check payload against the native receipt, and rechecks each exact owned PR head immediately before and after Check publication. It uses the existing registered MathGraph App's private key in a **separate job**, mints a narrowly scoped token with Checks write/Pull Requests read, and independently reads the posted neutral Check back from GitHub. Duplicate same-App checks are reconciled instead of repeatedly created. This does not enable community webhook intake. A missing installation, permission or secret must leave App publication **UNKNOWN**, even while the native research controls remain qualified.

The [registered-App qualification run](https://github.com/metalogiclabs/mathgraph/actions/runs/41916425178) passed and independently updated the original neutral Check IDs on [PR239](https://github.com/metalogiclabs/mathgraph/runs/126876654761) and [PR240](https://github.com/metalogiclabs/mathgraph/runs/126876680794), rather than creating duplicates. This proves bounded transport for the frozen source cohort, not universal proof review.

For an *independent* stale-source control, `check-omm-intake-lifecycle.yml` operates only on the owned draft PR270 and publishes a distinct **OMM intake (advisory)** App Check. It reports UNKNOWN for every proof/intent axis; no theorem is examined. On successive owned pushes, it checks exact live head and App identity and explicitly supersedes the immediately preceding Check, with independent readback. The workflow's actual runs and Check bodies, not its existence, determine whether revocation has passed in production.

`optin-admission.mjs` is a **non-publishing, operator-only source gate** for the exact future `@MathGraph -claim` comment. It re-reads comment identity, admits only the two registered, unchanged Artin PRs via independent published-source preflight, and checks source identity again. Its maximum result is `SOURCE_ADMITTED_ONLY`; native receipt, original target, mathematical intent and independent warrant remain UNKNOWN, and repairs/publication are denied. There is **no live issue-comment route for this command** yet. It deliberately does not compete with the existing separate `@MathGraph -check` demo.

Untrusted Lean source must not be invoked by the production Worker or a credentialed job: Lean elaboration executes macros. Before introducing community intake, qualify a separate offline, unprivileged native sandbox and an authenticated native receipt-publisher boundary, with no GitHub App/model credentials in the sandbox.

The separate experimental `check-omm-native-sandbox-smoke.yml` exercises **two fixed, first-party Lean fixtures only** in a distinct Docker image built from the existing Lean 4.28.0 Dockerfile with verified Lean distribution bytes. The native process receives a single read-only source file, `--network none`, read-only root filesystem, a small no-execute tmpfs, non-root UID 65534, no Linux capabilities, no-new-privileges, and CPU/memory/PID/time/output limits. Each invocation has a unique generated container name and independently forces removal of that exact container even after a client timeout; failed cleanup returns UNKNOWN. A separate container probe tests read-only mount/root, non-root UID and absent default network route. Positive compilation and negative rejection are kept distinct; failure or resource exhaustion remains UNKNOWN. The smoke receipt carries first-party source digests, runtime image identity in the Action artifact, observed constraints and explicit denial of community execution. Passing this smoke **does not** qualify arbitrary adversarial Lean source or a secure multi-tenant execution service; the base container image is not yet digest-pinned, and the trust boundary needs independent adversarial and deployment review.

No existing L4YAML checking method, live runtime, `/pilot` page, examples, installation policy, price cap or model route is modified by this change. No automatic OMM repair is enabled. To test locally:

```sh
node --test integrations/mathgraph-check-github/omm-v1/*.test.mjs
```

The remaining decisive gates are independently read-back **live stale-head withdrawal on the owned PR270**, followed by a trusted default-branch comment trigger, immutable claim-owner contract, authenticated community artifact admission, budgeted unprivileged sandbox execution and precise intent/claim-source mapping. Existing generic Lean work in [MathGraph PR #241](https://github.com/metalogiclabs/mathgraph/pull/241) is operator-only and not already a safe webhook executor; it remains independent until qualified transport is implemented.

