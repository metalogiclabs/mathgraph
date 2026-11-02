# Native proof-relevance advisory — operator-only design

## Intent and boundary

The generic MathGraph operator CLI can compile an original-target consumer even when that consumer proves the target independently of the candidate. The existing `NATIVE_CONSUMER_ACCEPTED` accurately reports Lean acceptance but must never be read as essential candidate dependence or proof-to-paper warrant.

Add an optional exact-byte-pinned, native SemantEq ProofChecker receipt as an **independent, unbound diagnostic**. Do not claim its assumed theorem is the current candidate or its goal is the current reference unless a future verifier actually matches elaborated declarations against both trusted source files.

## Approaches

- **Implemented: native unbound advisory** — run a trusted local proof fixture through pinned SemantEq `--raw --strict --proof`, retain a PASS/FAIL/UNKNOWN verdict, command, logs, toolchain and fixture hash; never promote source intent, consumer claim or independent warrant. Cheapest truthful first step.
- Future: prove an elaborated two-way binding from fixture to exact reference and candidate declarations, then make essential-use PASS a candidate repair gate. Stronger but requires explicit Lean AST correspondence and cross-run trust design.
- Rejected: parse proof text for candidate name or trust user/model-supplied PASS receipt. Both can accept dead references or forged statuses.

## Contract

Both `--proof-fixture FILE` and `--proof-fixture-sha SHA256` must appear together on `generic-semanteq-cli-v1.mjs`. The input is first-party operator-selected and byte-checked; there is no untrusted GitHub webhook path. `proof_fixture_audit` retains exact source, source SHA, command, stdout/stderr, native exit, wall time and same environment pins as the formal comparison. Native PASS/FAIL is a diagnostic of **this fixture only**; any malformed output, exit failure, missing or drifted environment remains UNKNOWN. `proof_binding: UNBOUND_ADVISORY` is permanent in v1. The full report continues to set `intent_fidelity` and `evidence_warrant` to UNKNOWN. Optional fixture failure must not become apparent CLI or mathematical success.

## Verification

Negative: unpinned/missing fixture refuses before execution; unavailable environment fails closed; a library proof of the reference that never uses the assumed candidate returns native FAIL; a dead fake candidate touch returns FAIL. Positive: an original proof genuinely using the assumed candidate by symmetry returns native PASS. All remain UNBOUND_ADVISORY. Regression: existing generic comparison and consumer tests remain unchanged and pass.

## Non-goals

No arbitrary PR Lean execution, independent human source review, authenticated semantic warrant, production App route, model API calls, or publication of private experiment fixtures/results in GitHub.
