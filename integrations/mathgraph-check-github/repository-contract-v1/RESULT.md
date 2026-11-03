# Fixed-contract multi-file PR qualification

**WARRANTED_BOUNDED:** one unchanged repository contract and frozen regression
corpus ran successfully on a fresh PR snapshot, an intentional regression and
its withdrawal, and a real module rename. No per-PR adapter, prompt or expectation edits were used.

This establishes reuse of the configured native audit. Whole-PR correctness,
new tool semantics, external-operator installation and comparative superiority
over other reviewers remain **UNKNOWN**. The deployed App is unchanged.

## Exact execution

- Selection and contract freeze before fresh-PR diff inspection:
  [`5e8db3d`](https://github.com/metalogiclabs/mathgraph/commit/5e8db3da8bdf2d082b89af107f1da2e219f0b5e9).
- Qualified controller: `4eb622d4505bd60f65bac9cf7e47dc37e0d5cc3c`.
- [Final native run41563491947](https://github.com/metalogiclabs/mathgraph/actions/runs/41563491947): all three jobs complete successfully.
- Contract SHA256: `1566c4204fce9d302c1da5e25f5e38a9ef880487cbbd0a94c06bda1b4204f14f`.
- Corpus SHA256: `dd1018417533191afb737481c990b453080b78a6e8c45e378dfbf1da30bf64ff`.
- Toolchain: Lean4.35.0. Runtime image identities, source/archive hashes,
  changed-file records, module roots and raw native logs are in the artifacts.

The contract and corpus hashes are identical across every arm. Request PR/base/
head identifiers are execution inputs; they do not select custom checker logic.

## Results

| Owned-fork PR | Pinned base → head | Isolated source builds | Frozen probes, base → head | Classification |
|---|---|---|---|---|
| [19](https://github.com/metalogiclabs/L4YAML/pull/19), fresh upstream213 snapshot | `809014dd` → `815695d6` | Both succeed | 1367/1367 → 1367/1367 pass | No failure in frozen corpus |
| [20](https://github.com/metalogiclabs/L4YAML/pull/20), labelled regression | `815695d6` → `b3031971` | Both succeed | 1367/1367 → 1366/1367 pass | New frozen-probe failure |
| [21](https://github.com/metalogiclabs/L4YAML/pull/21), withdrawal | `b3031971` → `31d8470d` | Both succeed | 1366/1367 → 1367/1367 pass | Frozen-probe failure resolved |
| [22](https://github.com/metalogiclabs/L4YAML/pull/22), actual module rename + importer | `815695d6` → `7baeb1b7` | Both succeed | 1367/1367 → 1367/1367 pass | No failure in frozen corpus |

The same1367-case corpus was replayed eight times, not10936 distinct cases. Expected outcomes did not enter the checker or its contract.

The regression changes `labelNumbers "Reflection 999"` from `[999]` to `[]`
without removing the module's original guards. The independently frozen probe
`204:10` rejects it even though the selected source still builds. Withdrawal
restores that same probe. This is authored sensitivity calibration, not an
unknown upstream discovery. It does not show that another reviewer missed it.

For fresh PR19, the checker automatically discovered and compiled the new
`Scripts.Main.PuntPrice` and `Scripts.Punt.Price` modules in addition to the
four protected regression roots. No new Punt-specific behavioral adapter was
written. Accordingly, this verifies compilation of those new modules and the
existing protected behavior; it does **not** establish Python/Lean parity for
the new Punt tool or execution correctness of its CLI.

PR19 has ten changed files. Its eight uncovered paths include three proof files,
the original `lakefile.lean`, the removed Python implementation, ledger,
documentation and agent instructions. They remain explicitly uncovered. The
original repository-wide gates, linking configuration and scientific proof
pipeline were not executed: a trusted isolated Scripts build is the declared
boundary. Every result retains `whole_pr_correctness=UNKNOWN`.

## Review-driven improvements

The first candidate controller passed the same three native source pairs in
[run41563081271](https://github.com/metalogiclabs/mathgraph/actions/runs/41563081271).
Independent review then exposed two generalization gaps not demonstrated by
those static snapshots:

1. The live PR file list could drift from the pinned source, including a
   force-push-away-and-back race. Changed files now come from exact Git-object
   comparison; incomplete comparisons and missing required modules fail closed.
2. Renames omitted the original base path. Both old/base and new/head Scripts
   module paths are now retained, including moves outside the Scripts tree.

New tests reproduced these gaps before the fixes. All13 contract tests pass.
The existing GitHub Check suite reports422 pass,0 fail and9 pre-existing skips
at the qualified controller. All three final jobs re-ran those checks and native
source comparisons. No production policy or deployment was modified.

Native source, external probes and trusted Lake configuration are read-only
container mounts; execution has no network or credentials. Compiled outputs
remain writable. This evidence is for the reviewed owned-fork source cohort,
not an arbitrary hostile-source security qualification.

## Additional native rename replay

[Run41564258045](https://github.com/metalogiclabs/mathgraph/actions/runs/41564258045)
qualifies the actual rename and importer change in PR22 at request-controller
`27a4aebeaba797af6127f5e3b64201dac4649dff`. Compared with controller4eb622d,
only execution-request data and documentation changed; the checker implementation,
contract and corpus files are identical. Both revisions compile, including the
old `Scripts.Punt.Price` at base and new `Scripts.Punt.PriceRenamed` at head.
Both arms pass1367/1367 frozen probes. This supplements the rename unit tests
with native dependency/import validation without a per-PR code change.

## Artifact receipts

All final ZIP digests and ZIP integrity were independently checked. Reports
also bind the exact controller, contract, corpus and source revisions.

| PR | Artifact | SHA256 |
|---|---|---|
|19|13197508335|`ca59de6e3dbd26ee34995c0b497b01bd691ff2831030c25745fbbc9bfe425d11`|
|20|13197428397|`cb063465814bb6844032dbec7f7fc71a194f01aab90fea5abb3935b96afa9182`|
|21|13197502822|`f7611f70689c81c9dd21e59cef033d8afea981a3058cb9893d59363ce127316e`|
|22|13197874054|`b71b826bb07b36735688ac6fccbc1177c36f80cea634d23e957a068c5ce6e891`|

## Reuse and next residual

The [runner instructions](README.md) accept a PR number and exact source
revisions. A new supported fork PR requires new request inputs, not adapter or
expectation changes. This is a reusable fixed-regression audit with automatic
source compilation, not automatic discovery or authorization of new semantics.

The next product step is to connect this qualified scoped runner to the existing
neutral App report and make uncovered obligations visible there. Broader proof/
CLI obligations and external installation need their own qualification. No
upstream PR, review comment, email or endorsement claim was made.
