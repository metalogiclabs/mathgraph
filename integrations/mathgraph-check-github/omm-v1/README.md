# MathGraph Check for Open Math Model — claim bridge V1

**Status:** research integration CANDIDATE. This is not an enabled GitHub App method, a live OMM `/check` or `/fix` command, or a research-intent certificate.

This additive adapter can turn a trusted, exact-source native Lean replay into the shared MathGraph Check/Passport-style neutral report. It distinguishes:

1. **Lean candidate compilation:** the exact candidate was compiled in the pinned environment; compilation alone is not an axiom audit.
2. **Original-target consumer:** an operator-authored, hash-pinned consumer compiled with standard axioms, was rejected by Lean in this replay, or is UNKNOWN. Rejection does not prove semantic inequivalence.
3. **Formal-statement equivalence:** UNKNOWN in this adapter until a separately authenticated, same-context SemantEq result is integrated.
4. **Candidate proof necessity and paper-to-Lean intended meaning:** both UNKNOWN, including on consumer acceptance.
5. **Independent evidence warrant:** UNKNOWN until a trusted GitHub/Actions artifact chain is verified externally.

The bridge expects an `omm.request.v1` formed from authenticated GitHub PR metadata and **actual fetched candidate source bytes**; a separately admitted `omm.claim-contract.v1`; and an `omm.native-receipt.v1` wrapping the existing operator-only `generic-lean-consumer-run-v1` output. Contract and receipt exact-byte SHA-256 pins must come from the trusted Check controller, not the PR, an AI answer, or an arbitrary JSON field. The native output must include both pinned source hashes, the consumer and candidate declaration names, the Mathlib Git revision, tracked toolchain hash, native exit codes and separate candidate/consumer axiom audit.

Untrusted Lean source must not be invoked by the production Worker or a credentialed job: Lean elaboration executes macros. Before introducing community intake, qualify a separate offline, unprivileged native sandbox and an authenticated native receipt-publisher boundary, with no GitHub App/model credentials in the sandbox.

No existing L4YAML checking method, live runtime, `/pilot` page, examples, installation policy, price cap or model route is modified by this change. No automatic OMM repair is enabled. To test locally:

```sh
node --test integrations/mathgraph-check-github/omm-v1/*.test.mjs
```

The next decisive gate is a **first-party native Artin positive/weakened/UNKNOWN cohort** using a separately approved original claim and same-source context, then actual Check publication on an owned repository. Existing generic Lean work in [MathGraph PR #241](https://github.com/metalogiclabs/mathgraph/pull/241) is operator-only and not already a safe webhook executor; it remains independent until qualified transport is implemented.

