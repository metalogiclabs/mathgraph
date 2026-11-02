# Brahe endpoint-direction retrospective (V1)

This is a **first-party, source-pinned retrospective**, not a deployment of MathGraph Check in the Brahe repository. It concerns [Brahe issue #607](https://github.com/duncaneddy/brahe/issues/607) and [Heath Sanchez's merged fix #608](https://github.com/duncaneddy/brahe/pull/608). The maintainer confirmed the underlying issue and accepted the fix; no maintainer has been asked to install or use Check as part of this experiment.

## Bounded question

Can an event detector configured for one crossing direction incorrectly report an **opposite-direction** event when a propagation endpoint lands at or very near the target value?

The original production code contained two affected paths in `src/events/detection.rs`. The fix added a direction-sensitive condition for endpoint tolerance. This experiment only tests that defined behavior; it does not assess all event-detection, orbital, or release-safety properties.

## Exact source and method

| Input | Identity |
| --- | --- |
| Upstream | [`duncaneddy/brahe`](https://github.com/duncaneddy/brahe) (MIT) |
| Before fix | `323c4542ad915aa1b6a1dbf65f1f6a8040609294` |
| After fix | `f40f97da4094fddbd3745158f0123f9bcd0f3bd3` |
| Source file | `src/events/detection.rs` |
| Before-fix Git blob | `e161f52140cbcff04d0d7cbf0500b1c7cbd7dccf` |
| After-fix Git blob | `eb4172629778a63f874871629ddebc8fe0701858` |
| Native test command | `cargo test --locked -p brahe --lib events::detection::tests:: -- --nocapture` |

1. Fetch and check out the exact commits, verify both Git blob identities, and refuse to proceed if either source pattern differs from the expected buggy/fixed guards.
2. Copy **only** the fixed head's `#[cfg(test)] mod tests` block into the unchanged base implementation. Verify the generated patch contains no production-code edits.
3. Generate a Rust dependency lockfile from the fixed revision, copy the **identical** lockfile to the base, and execute the same 17 native tests on both.
4. Preserve complete stdout/stderr, command exit codes, the test-only patch, the lockfile, source identities, and a machine-readable bounded verdict in the GitHub Actions artifact.
5. Independently re-parse the archived raw test output and lockfile against the recorded receipt and check the GitHub workflow run identity before describing the result as verified within this narrow scope.

The four negative tests specifically exercise wrong-direction near-endpoint detection in the static and dynamic detector variants. The expected regression is **four failures on the unchanged base**; the corrected head should pass all 17 tests. Any missing, extra, or unexpectedly failed test; setup/compile error; pin mismatch; or incomplete artifact keeps the result `UNKNOWN`.

## Executable entry points

- [GitHub Actions workflow](../../.github/workflows/mathgraph-check-brahe-endpoint-v1.yml) runs the exact Rust replay.
- [`brahe-endpoint-v1.mjs`](./brahe-endpoint-v1.mjs) enforces the test-only transplant boundary.
- [`run-brahe-endpoint-v1.mjs`](./run-brahe-endpoint-v1.mjs) parses native outcomes and builds the bounded receipt.
- [`brahe-artifact-readback-v1.mjs`](./brahe-artifact-readback-v1.mjs) checks a downloaded artifact's internal consistency. The caller must obtain trusted workflow metadata separately.
- [`brahe-evidence-presentation-v1.mjs`](./brahe-evidence-presentation-v1.mjs) produces an **advisory, neutral preview**; it does not post a GitHub Check or change upstream PR state.

The artifact's `CANDIDATE_BOUNDED` label means the internal parser found the expected observation. It is **not** an authenticated result by itself. A separate artifact and run readback is necessary before reporting the bounded native result as verified.

## Limits that must accompany any public use

- Heath identified and patched the bug. MathGraph Check did **not** independently discover it.
- The added tests reflect the author's stated regression, rather than a prospectively frozen third-party oracle.
- This does not establish performance against CI plus an equally informed human reviewer.
- The maintainer's acceptance of the **Brahe fix** is not adoption, validation, endorsement, purchase interest, or evaluation of the **MathGraph Check product**.
- The first replay of this harness had a receipt-parser false negative: Cargo's normal `error: test failed` footer was incorrectly interpreted as a build error. Raw Rust outcomes were preserved; the parser was repaired with positive and negative regression tests before a new CI run.
- A native Rust result here does not yet demonstrate a generalized Rust adapter, live Check install, or prospective approval decision.

## Qualification runs

- [First replay #41414043619](https://github.com/metalogiclabs/mathgraph/actions/runs/41414043619): preserved native outputs, but failed qualification because of the parser bug; no verified label from that run.
- [Corrected replay #41415446440](https://github.com/metalogiclabs/mathgraph/actions/runs/41415446440): **completed successfully** on 2026-11-02. The downloaded [workflow artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/41415446440#artifacts) has SHA-256 `87c105ef5ab2c8880dbed6cbae78cfdb4c7bd680f23419cdb5776685b3cc914e`, matching the digest returned by GitHub's artifact API. Its archived native results are:
  - **Base:** 17 tests executed, 13 passed, the four named wrong-direction endpoint tests failed (`EXPECTED_REGRESSION`; native exit 101).
  - **Fixed head:** all 17 tests passed (`PASSED`; native exit 0).
  - **Shared generated dependency lockfile:** SHA-256 `e2f93032f5c581a3858771f3b44afe15015bf23982863f985dc152acdd4c7a0f`; `rustc 1.99.1`.
  - **Readback:** `READBACK_CONSISTENT`, zero errors. The independent readback recomputed test classifications and log hashes from the archived stdout/stderr, checked the lockfile, and compared the receipt to the separately retrieved successful GitHub run metadata. Public GitHub blob retrieval also confirmed the original base has two buggy guards, the fixed head has two corrected guards, and the copied test boundary is unique. The archived patch has only `mod tests` hunks.

**Interpretation: verified within the narrow historical native-test boundary.** The workflow's own machine verdict remains `CANDIDATE_BOUNDED` and `ADVISORY_ONLY`; the external archive/run readback above supports the bounded observation but does not automatically change the programmatic verdict or remove the listed unknowns. GitHub's workflow artifacts expire; the source-pinned method is replayable afterward, but the generated dependency lockfile may then resolve differently.

The practical next experiment is a consented, read-only evaluation of Check on an independent maintainer's live PR or repository, with explicit expectations, code-access permissions, and outcomes recorded separately from this retrospective.
