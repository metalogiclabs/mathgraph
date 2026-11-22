# Retain JUnit outcomes through the report consumer

The known EA04 error-to-PASS finding now has a reusable, opt-in local check.
The finite observations below are qualified. The product implementation remains
an open draft, and human usefulness or a 10x advantage is not established.

The existing 19-case XML acceptance profile passes on both the selected original
and candidate. The new eight-case status profile distinguishes them by observing
actual parser rows, rendered rows, returned count, section totals and grand totals.
Successful acceptance alone does not establish preservation of a test's outcome.

## Exact evidence

- [Draft PR #284](https://github.com/metalogiclabs/mathgraph/pull/284), stacked on
  [#283](https://github.com/metalogiclabs/mathgraph/pull/283).
- Executable method commit: `4ca35c4f33b0c8893265abb0f2a147c0e1a17cf0`.
- Method tree: `54677556125675521ecb0258955c50be5336a424`.
- Qualifier SHA-256:
  `c199a042cba670d417c2d18efbf1b03cf7685c12807ebf61c4a15904b419bb23`.
- [Exact-commit push run 44985830241](https://github.com/metalogiclabs/mathgraph/actions/runs/44985830241)
  and [PR run 44985858561](https://github.com/metalogiclabs/mathgraph/actions/runs/44985858561):
  both SUCCESS. The results and costs below come from the push run.
- [Full status evidence artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/44985830241/artifacts/14739980897):
  archive SHA-256 `063155178eaba01a9aaa0c06ad7085e56671b5bc596bb2fef9e3e105a3692b37`.
  The downloaded archive, all 466 inventoried evidence-file digests, six result
  digests, candidate source/patch/commit-object digests, and actual candidate Git
  commit identity were checked. Artifact retention expires 2026-12-22; the
  committed qualifier and pinned upstream objects preserve replay.

The five status invocations retain exactly the same method identity. The five
executed comparisons, including the legacy profile, have identical recorded
runtime identities within this CI campaign. The missing-module control does not
execute a runtime or borrow another comparison's evidence.

## Sources and candidate lineage

Subject repository: `nasa-jpl/L4YAML`; path: `Tests/SuiteRunner/Reports.lean`.

| Role | Commit | Source SHA-256 |
| --- | --- | --- |
| Pinned owner integration | `14eb6dbab845d2ac61f171a9ed61906d3f9ffb2f` | `8e9bc2716fbfde4fbedf4f9a82fd1a0607878898c99c4700f55765a384393542` |
| Actual local synthetic child | `35aebb3f853ef83bac7dafc1d3cdc46b447e72ca` | `d9e149f37f0b864f2a4d0b907280cbda362d59fe05b424157464eaabfed564c2` |
| Selected default main | `122064d0c853be8d6c2f4cd255c6fcd67acc4ae8` | Module absent; UNKNOWN |

The original Reports blob is `d02b18f300bd547dabf83d58ee97d35219516e83`.
The candidate changes only the existing failure-tag condition to recognize error
tags as well. Its parent is the pinned integration. The qualifier constructs it
using a private Git index with an explicitly synthetic author and date, verifies
the single changed path and exact bytes, and preserves the subject's checkout,
HEAD, refs and index. It does not publish that candidate to upstream.

This is known-case reuse, not blind discovery. The source and EA04 finding were
known before the new profile was implemented. The cases and method were not
changed between the six qualified comparisons.

## Qualified observations

| Comparison | Cases per executed source | Discrepancies base → head | Result | CI wall seconds |
| --- | --- | --- | --- | ---: |
| Original → original | 8 | 4 → 4 | OBSERVED_MISMATCH | 7.394 |
| Original → candidate | 8 | 4 → 0 | OBSERVED_AGREEMENT | 7.364 |
| Candidate → original, withdrawing repair | 8 | 0 → 4 | OBSERVED_MISMATCH | 7.375 |
| Candidate → same candidate | 8 | 0 → 0 | OBSERVED_AGREEMENT | 7.369 |
| Original → candidate, default envelope profile | 19 | 0 → 0 | OBSERVED_AGREEMENT | 13.016 |
| Candidate → absent module | Not executed | Not assessed | UNKNOWN | 0.015 |

The four mismatch identities are `error_empty`, `error_text`, `error_then_pass`
and `mixed_outcomes`. Pass, assertion-failure, skip and harmless-error-text controls
retain their expected outcomes. Each executed status comparison uses 29 native
subprocesses; the envelope comparison uses 57. The complete qualification took
42.981 seconds, excluding toolchain installation and separate test suites. All
invocations used zero model calls. These are observed costs, not latency guarantees
or measurements of human attention saved.

The smallest distinguishing input in this fixed corpus is:

```xml
<testsuite><testcase name="bad"><error message="setup"/></testcase></testsuite>
```

Both versions accept this valid XML. The original returns and renders PASS/pass,
reports one passed and zero failed tests, and gives the grand total a pass class.
The candidate returns and renders FAIL/fail, reports zero passed and one failed
test, and gives the grand total a fail class. Withdrawing the candidate reproduces
the original discrepancy through fresh execution.

## Verification and preserved unsuccessful attempts

CI Check regression: 638 passed, 16 skipped, 0 failed. Both native-enabled entry
suites passed separately: 9/9 for the existing path and 4/4 for status, with no
skips. These cover five native test groups skipped in the broad run; the other
eleven broad-suite skips remain skips. Relevant Python suites passed 66 tests.
No whole-project pytest result is claimed.

Independent review found that a loose HTML projection could mistake comment text
for rendered output and that count/metadata discrepancies could be invisible in
the witness. The fixed projector now requires the selected complete layout and
stylesheet; the report displays all compared fields. The three targeted regression
tests reproduced those failures before the fix and passed afterward. Fresh CI
native replay qualifies the revised projector. Separate review found no blocking
candidate-provenance or qualification-control defect.

Local execution also produced unsuccessful attempts, which remain unqualified:

- One native test run passed 3/4 tests; its original comparison exhausted the
  120-second budget and returned UNKNOWN after 120.190 seconds. Its console
  summary survives; the test harness removed that attempt's temporary native files.
- An unchanged persistent diagnostic completed in 53.893 seconds, observed all
  eight cases in both arms, and reproduced the four original discrepancies without
  a timeout.
- A subsequent local qualification hit per-process and total execution limits on
  both original and repair comparisons. It was stopped during withdrawal after
  the independent CI qualification succeeded. The local campaign stays INCOMPLETE;
  its remaining controls were not run. No expectations or execution budgets were
  changed to turn those local attempts into successful receipts.

The retained `MathGraph_Status_Local_Timeout_Evidence_2026-11-22.zip` artifact,
linked from the Research OS checkpoint, contains the unmodified summaries,
completed native outputs, diagnostic replay, and explicit interruption disposition.
Archive SHA-256:
`6bbb7833837b87d07b21732ea0d41626782323745f090fa73a65da9ab4fa976d`;
182 local evidence-file hashes verified. The cause of wall-time variability is
not established; a reliable local latency bound remains UNKNOWN.

## Requirement, scope and reuse

The policy adopts the selected renderer's PASS/FAIL/SKIP vocabulary: a direct
error or failure child must yield FAIL/fail and count as failed; otherwise a
direct skipped child yields SKIP/skip; otherwise PASS/pass. The
[pinned pytest JUnit producer](https://github.com/pytest-dev/pytest/blob/13ba5cba07f56728d25d89cc7f5f0b24b06c3b95/src/_pytest/junitxml.py)
anchors the error/nonpassing distinction. ElementTree independently supplies XML
structure; it does not authorize the policy or preserve error versus assertion
failure as separate categories.

The actual Reports source and original guards run under Lean 4.35.0 with the
declared empty HtmlReport dependency. HTML interpretation is restricted to the
selected single-section layout and stylesheet; unsupported markup becomes UNKNOWN.
Full JUnit/HTML conformance, full dependency-environment correspondence, report
CLI and whole-repository correctness remain outside this result. A report CLI may
return zero after successfully rendering failed tests. No new exit policy, hosted
admission or automatic repair permission is inferred.

[Operator handoff](../../integrations/mathgraph-check-github/pr-pilot-v1/LOCAL_REPORT_CHECK.md)
provides the opt-in command, separate profile selection, qualification command
and rerun procedure. The earlier acceptance qualification and the broader EA04
audit remain separate evidence; this profile does not supersede that audit.

The highest-leverage residual is useful decisions per unit of human attention.
The smallest next experiment is an engineer using the handoff on two successive
consequential compatible changes, recording setup, failed attempts, review and
correction effort against ordinary review under equal inputs and coverage.
External operator use, human savings and a 10x advantage remain NOT_RUN.
