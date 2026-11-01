# MathGraph Check: resolved Lean/Lake environment closure V1

The original Artin replay established that Lean 4.28 and Mathlib v4.28.0 were requested and a native proof run succeeded. Those requested version labels do **not** by themselves identify the resolved transitive dependencies. This new, separately pinned V2 replay workflow records the exact `lake-manifest.json` bytes as another short-lived GitHub Actions artifact.

## Version and provenance pins

- Lean toolchain file must be exactly `leanprover/lean4:v4.28.0`; observed `lean --version` must report 4.28.0.
- Mathlib package must have `inputRev=v4.28.0`, the expected upstream Git URL, and resolved revision `8f9d9cff6bd728b17a24e163c9402775d9e6a365`. The revision was independently checked against the official `leanprover-community/mathlib4` tag `v4.28.0`.
- Every resolved dependency must have a unique name, a Git URL, and a full 40-character commit SHA. Local/unpinned path dependencies are rejected.
- The original `lake-manifest.json` bytes receive their own SHA-256. A domain-separated canonical identity containing that hash, the toolchain hash, observed version strings and all resolved dependency revisions receives an **environment SHA-256**. This is a reproducible identity, not a Lean proof or a semantic review.

## V2 workflow and artifact

`.github/workflows/mathgraph-check-proofnet-artin-replay-v2.yml` repeats the independently pinned third-party Artin gold proof replay, scoped axiom audit and Native Lean 4.28/Mathlib build. It retains the existing two-file machine evidence artifact and additionally uploads a separate `mathgraph-proofnet-artin-environment` artifact with precisely five small files:

1. `lake-manifest.json`
2. `artin-toolchain.txt`
3. `artin-lean-version.txt`
4. `artin-lake-version.txt`
5. `artin-environment.json`

`math-source-environment-closure-v1.mjs` verifies the five-file archive against a GitHub artifact SHA-256 obtained independently from the authenticated REST API, then rederives the report from the four underlying source files. ZIP CRC, filename, size, duplicate, symlink and path-traversal checks reuse the fail-closed byte parser from the previous milestone. The gold proof itself is **not** put in the artifact.

Local unit tests:

```sh
node integrations/mathgraph-check-github/math-source-environment-closure-v1.test.mjs
```

The V2 workflow runs the genuine Lean replay on the dedicated `research/mathgraph-check-math-source-environment-*` branch and produces time-limited GitHub artifacts. A test passed on a synthetic Lake manifest is **not** evidence of a new native replay; the actual workflow run and uploaded artifact must be examined separately.

## Remaining linkage and authority

The existing read-only V1 collector still correlates the original two-file evidence ZIP. A subsequent tightly scoped integration must fetch this **separate** environment artifact from the same authenticated run/head/attempt, compare its verified environment SHA-256 with the independently administered trust manifest, and recheck all GitHub identities after retrieval. Until then, the new environment artifact is independently verifiable but **not contract-bound** to a full MathGraph intent receipt.

There has been no independent human mathematical source-to-formal review. No installation, protected action, Check Run write, PR approval or automatic mathematical-equivalence claim is authorized. Always `ADVISORY_ONLY`, `intent_verification=NOT_ESTABLISHED`, `receipt_qualification=NOT_YET_CONTRACT_BOUND`.
