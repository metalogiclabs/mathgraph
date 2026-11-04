# MathGraph Check for Open Math Model — claim bridge V1

**Status:** research integration CANDIDATE. This is not an enabled GitHub App method, a live OMM `/check` or `/fix` command, or a research-intent certificate.

This additive adapter can turn a trusted, exact-source native Lean replay into the shared MathGraph Check/Passport-style neutral report. It distinguishes:

1. **Lean candidate compilation:** the exact candidate was compiled in the pinned environment; compilation alone is not an axiom audit.
2. **Original-target consumer:** an operator-authored, hash-pinned consumer compiled with standard axioms, was rejected by Lean in this replay, or is UNKNOWN. Rejection does not prove semantic inequivalence.
3. **Formal-statement equivalence:** UNKNOWN in this adapter until a separately authenticated, same-context SemantEq result is integrated.
4. **Candidate proof necessity and paper-to-Lean intended meaning:** both UNKNOWN, including on consumer acceptance.
5. **Independent evidence warrant:** UNKNOWN until a trusted GitHub/Actions artifact chain is verified externally.

The bridge expects an `omm.request.v1` formed from authenticated GitHub PR metadata and **actual fetched candidate source bytes**; a separately admitted `omm.claim-contract.v1`; and an `omm.native-receipt.v1`. Contract and receipt exact-byte SHA-256 pins must ultimately be admitted by the trusted Check controller, not the PR, an AI answer, or an arbitrary JSON field. The native output must include both pinned source hashes, the consumer and candidate declaration names, the Mathlib Git revision, tracked toolchain hash, native exit codes and separate candidate/consumer axiom audit. The current qualification CLI creates local contracts, receipts and SHA-256 manifests; this is **not** an independently attested evidence publisher or authenticated live GitHub App pipeline.

The optional workflow `check-omm-artin-native.yml` performs a fixed, first-party native Lean cohort only:

- PR #239: an Artin proof with an added `CommGroup` hypothesis. Candidate Lean compilation can succeed, but an original `Group` target consumer should reject. The result is **NOT_ESTABLISHED_IN_THIS_REPLAY**, not a proof of mathematical inequivalence.
- PR #240: the repaired candidate under the original `Group` assumption. The exact original-target consumer and separate `#print axioms` checks should accept. The result is **CONSUMER_ACCEPTED**, never an intended-claim warrant.

GitHub preflight pins both public PR head/base identities, the exact `ArtinGenerators.lean` bytes and the externally published exercise. A separate job executes only those pre-registered sources with Lean 4.28.0 and a pinned Mathlib revision, without GitHub App or LLM credentials. CI stores source, manifest, trace, assessment, neutral report **and a deterministic GitHub App Check-run preview** for each fixed case. The preview reuses the existing `advisory-publisher-v1` schema, remains `conclusion: neutral`, and never transmits credentials or publishes a Check by itself. Workflow outcome and artifacts, not this README, are the authority for whether the native cohort actually passed.

Untrusted Lean source must not be invoked by the production Worker or a credentialed job: Lean elaboration executes macros. Before introducing community intake, qualify a separate offline, unprivileged native sandbox and an authenticated native receipt-publisher boundary, with no GitHub App/model credentials in the sandbox.

No existing L4YAML checking method, live runtime, `/pilot` page, examples, installation policy, price cap or model route is modified by this change. No automatic OMM repair is enabled. To test locally:

```sh
node --test integrations/mathgraph-check-github/omm-v1/*.test.mjs
```

The next decisive gates are an actual green first-party native Artin run and **separately authorized Check publication on an owned repository**, followed by authenticated artifact admission, budgeted sandbox execution and precise intent/claim-source mapping before community intake. Existing generic Lean work in [MathGraph PR #241](https://github.com/metalogiclabs/mathgraph/pull/241) is operator-only and not already a safe webhook executor; it remains independent until qualified transport is implemented.

