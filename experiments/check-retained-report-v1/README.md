# Retained report check: first source-reuse qualification

The existing report-integrity investigation now runs through one local command on
compatible committed Git revisions. This record establishes finite source reuse.
The product change remains an open draft; external operator use and comparative
human effort remain NOT_RUN.

## Frozen method and evidence

- [Draft PR #283](https://github.com/metalogiclabs/mathgraph/pull/283), stacked on RC1.
- Method commit: `2aace4f4b144e912ee7dc08df5fb31b3738b718d`.
- Method tree: `2fa4c6a4bab714fe69f20a8dc92b94aac9c2c9ac`.
- Qualifier SHA-256: `a11effe0c78af98662af4ab22ca1ea044531beea24db56eccc3e617733fa1338`.
- [Actions run 44982949534](https://github.com/metalogiclabs/mathgraph/actions/runs/44982949534): SUCCESS, contracts and native jobs.
- [Full evidence artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/44982949534/artifacts/14738536487), SHA-256 `a28b3f2c97a368d42d33188539ab843c26331cea521e0568f699630638a8c07e`. Archive and all 414 inventoried evidence-file hashes verified after download. Artifact retention expires 2026-12-22; the committed qualifier and pinned sources preserve replay.

The later source was selected by metadata and the method committed before its
contents were opened. The cases, expectations and method stayed unchanged across
all four comparisons. This is a familiar-project reuse trial, not blind discovery.

## Exact sources

Repository: `nasa-jpl/L4YAML`; module: `Tests/SuiteRunner/Reports.lean`.

| Role | Commit | Reports source identity |
| --- | --- | --- |
| Historical original | `3e855548afa1c70bcc2aa77f7b86587de5658743` | SHA-256 `670b65c829bffcc3dcafb2fbdfe8aee5a1ec8dede7ce4d0547d11bb600848fae` |
| Later owner integration | `14eb6dbab845d2ac61f171a9ed61906d3f9ffb2f` | Blob `d02b18f300bd547dabf83d58ee97d35219516e83`; SHA-256 `8e9bc2716fbfde4fbedf4f9a82fd1a0607878898c99c4700f55765a384393542` |
| Default main selection | `122064d0c853be8d6c2f4cd255c6fcd67acc4ae8` | Module absent; retained UNKNOWN |

## Observations

| Comparison | Cases per source | Discrepancies base → head | Result | CI wall seconds |
| --- | --- | --- | --- | ---: |
| Original → later | 19 / 19 | 6 → 0 | OBSERVED_AGREEMENT | 10.505 |
| Later → original | 19 / 19 | 0 → 6 | OBSERVED_MISMATCH | 10.661 |
| Later → later | 19 / 19 | 0 → 0 | OBSERVED_AGREEMENT | 10.884 |
| Later → default main | Not executed | Not assessed | UNKNOWN: module absent | 0.012 |

Each complete comparison invoked 57 native subprocesses. All four comparisons
used zero model calls. The complete CI qualification took 32.280 seconds, excluding
installation and the separate test suites. Local qualification independently
reproduced the same decisions in 52.592 seconds. These are observed execution
costs, not stable latency guarantees or measurements of human savings.

The smallest failing historical input in the frozen corpus was
`garbage<testsuite><testcase name="ok"/></testsuite>`: accepted by original source,
rejected by the later source and independent XML reference.

Check regression: 633 passed, 14 skipped, 0 failed. The separate native entry-point
suite passed all 9 tests; its 3 native test groups account for 3 regression skips.
Relevant Python suites passed 51 tests. Whole-project pytest could not start
locally because pytest was not installed; no whole-project Python pass is claimed.

## Boundary and next experiment

The unchanged Reports bytes and original guards were compiled under Lean 4.35.0
with the declared empty HtmlReport stub. The finite profile covers six malformed
XML envelopes, six valid inputs and seven legacy refusals. It does not qualify the
original full dependency environment, report CLI, all JUnit status semantics, full
XML conformance or whole-repository correctness. Local success grants no hosted
admission or automatic repair permission.

Independent review corrected incomplete-result presentation, launcher behavior and
frozen-commit provenance. The qualifier rejects dirty/untracked verifier inputs and
requires complete method identity to remain equal across every invocation. Existing
hosted admission still refuses source outside its historical exact-source whitelist.

[Operator handoff](../../integrations/mathgraph-check-github/pr-pilot-v1/LOCAL_REPORT_CHECK.md)
contains prerequisites, the command, interpretation, rerun procedure and human-trial
measurements. The next decisive experiment is an actual engineer using this profile
on two successive consequential changes, with setup, correction and review effort
compared against ordinary review under equal inputs and coverage. That trial,
customer adoption and a 10x advantage remain NOT_RUN.
