# OpenAI math evidence audit — v1 (2026-10-09)

**Status:** candidate experiment; independent Lean verification **UNKNOWN** until
a fresh, pinned Comparator run completes. No theorem has been newly proved here.

## Objective

Audit one flagship formalization plus a real withdrawal cascade on an external
research corpus. Keep statement alignment, proof execution, and dependency
propagation as **different** evidence boundaries.

**Immutable upstream snapshot:**
[openai/math@fd4aeeb2ee4f](https://github.com/openai/math/tree/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb)
(after [PR #1](https://github.com/openai/math/pull/1)).

### A. Claimed theorem and formalization interface

- Informal [Exact derandomization of logarithmic space: L = RL = BPL](https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/preprints/Exact-Derandomization-of-Logarithmic-Space-L-equals-RL-equals-BPL-September-23-2026/build/sections/introduction.tex) states the headline equality and explicit randomized Turing-machine resource bounds.
- [Formalization manifest](https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/lean/formalization.yaml) maps it to theorem OAI.ExactDerandomization.exact_logarithmic_space_derandomization, file lean/OAI/Computability/Logspace/Equality.lean.
- [Comparator config](https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/lean/ComparatorChallenges/LogspaceEquality.json) permits propext, Quot.sound, and Classical.choice.
- [Comparator challenge template](https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/lean/ComparatorChallenges/LogspaceEquality.lean) **does contain a sorry placeholder** by design. Do not confuse it with the [separate purported solution](https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/lean/OAI/Computability/Logspace/Equality.lean), where the corresponding theorem has a proof body referencing imported results.

**Warranted from source inspection if audit script passes:** precise declaration mapping and surface equality of headline theorem. **Not warranted:** trusted kernel recheck, axiom closure through imports, agreement between formal machine definitions and the paper's intended complexity classes, correctness of all accompanying mathematics. In particular, lexical absence of sorry from a single file is **not** proof closure.

### B. Withdrawal dependency separator

[Release history](https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/history.md)
records the three-paper cascade. The notices say withdrawn on October 6;
the public release history dates the update October 7.

1. **Root** — [Weil classes on split abelian eightfolds](https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/preprints/Algebraicity-of-Weil-classes-on-split-abelian-eightfolds-September-18-2026/README.md). The notice identifies a reverse-stabilization sign error: claimed +1 contributions were actually -1 under the stated orientations, so the count becomes -2m rather than zero.
2. **Dependent** — [Kuga–Satake correspondences for K3 surfaces](https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/preprints/Algebraicity-of-Kuga-Satake-Correspondences-for-K3-Surfaces-October-3-2026/README.md). The notice attributes withdrawal to an adaptation of that flawed construction.
3. **Dependent** — [Rational Hodge conjecture for products of K3 surfaces](https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/preprints/The-rational-Hodge-conjecture-for-products-of-K3-surfaces-October-4-2026/README.md). The notice likewise attributes withdrawal to the flawed construction.

These are **attested dependency edges**, not an independently checked source-level proof dependency graph. Withdrawal rejects the reported **proof**, not the truth of the theorem. The withdrawn sources link to their pre-withdrawal revision
[adc7f1241b42](https://github.com/openai/math/tree/adc7f1241b42e322a6451854ab7e4b4c146bf78a).

## Reproduce the bounded checks

From this directory, with Python 3.10+ and network connectivity:

    python3 audit.py --output openai-math-audit-report.json

The script fetches **13** UTF-8 text files from the immutable upstream revision,
recomputes their native Git blob hashes, checks the manifest/config/theorem
references, confirms that the challenge's placeholder is separate from the submitted
solution, and asserts all withdrawal notices and both direct dependency citations.
It exits nonzero if a source hash or expected fact disagrees. Its output is
machine-readable, with **UNKNOWN** explicitly assigned to unrun checks.

A GitHub Actions workflow executes this bounded validation and publishes its JSON
evidence. The upstream PR notes it did **not** run Lean builds as part of its
release synchronization; source publication is not external verification.

### Independent Lean gate (not yet earned)

The upstream instructions are at
[lean/ComparatorChallenges/README.md](https://github.com/openai/math/blob/fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb/lean/ComparatorChallenges/README.md).
An independent checker needs a pinned Lean/Mathlib environment and comparator,
landrun and lean4export on PATH, followed by:

    cd lean
    lake update
    lake exe cache get
    lake env comparator ComparatorChallenges/LogspaceEquality.json

**Important:** before calling it a verified main theorem, capture exact toolchain
commits, trusted checker version, execution log, exit status, imported-declaration
axiom closure, and a separate paper-to-formal-statement analysis. Do not claim
that this command has run merely because it is documented.

## Promotion rule

- **INTERESTING → CANDIDATE:** fixed upstream paths and hashes, inspection of both positive and withdrawn evidence.
- **WARRANTED (bounded):** hosted run passes the 13 pinned file and stated structural/textual checks.
- **UNKNOWN:** imported proof dependencies, fresh independent Comparator replay, genuine complexity-class model equivalence, and independent mathematical confirmation of the sign error.
- **REUSABLE** only after testing on a second held-out update/withdrawal family.
- **REJECTED** if a negative control (tampered SHA, removed dependency citation) is wrongly accepted; preserve the counterexample.

This is a deliberately *small* first slice of the broader MathGraph evidence
engine. It does not imply that all 719 papers have been audited.
