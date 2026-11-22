# Run the retained report-integrity check

Compare committed `Tests/SuiteRunner/Reports.lean` at two local Git revisions. The
default profile retains the same 19 XML acceptance cases and three obligation
groups. An explicit status profile checks eight separate test-outcome cases through
the parser and HTML renderer. Both revisions run afresh for the selected profile.
This local command does not require the private GitHub App.

For both profiles plus per-case agreement and refusal/apparatus checks in one
invocation, use the [retained failure-check command](../catalogue-check-v1/README.md).
It also records all 104 catalogue prompts, with unsupported and omitted checks
explicitly separated from bounded observations.

## Run

Requirements: Node 24, Git, Python 3, a reviewed Lean 4.35.0 installation, and a local
Git repository containing both revisions. Use source you have reviewed; this is a
local subprocess runner, not a hostile-source sandbox.

From the MathGraph checkout:

```bash
node integrations/mathgraph-check-github/pr-pilot-v1/local-report-check.mjs \
  --repo /path/to/L4YAML \
  --base BASE_REVISION \
  --head HEAD_REVISION \
  --out /path/to/new-check-output \
  --lean /path/to/lean-4.35.0/bin/lean
```

To check test outcomes and rendered counts, select the separate status profile:

```bash
node integrations/mathgraph-check-github/pr-pilot-v1/local-report-check.mjs \
  --repo /path/to/L4YAML \
  --base BASE_REVISION \
  --head HEAD_REVISION \
  --out /path/to/new-status-check-output \
  --lean /path/to/lean-4.35.0/bin/lean \
  --profile junit-status-preservation-v1
```

| Profile | Question and fixed inputs |
| --- | --- |
| `junit-report-integrity-v1` (default) | Are six malformed envelopes refused, six valid reports accepted, and seven existing refusals preserved? The original 19-case corpus is unchanged. |
| `junit-status-preservation-v1` (opt-in) | Do eight fixed cases preserve accepted test outcomes, row order, rendered status cells and totals? Checks pass, failure, skip, two error forms, error followed by pass, mixed outcomes, and harmless error text. |

The profiles have separate corpus, reference and method identities. Passing the
envelope profile does not establish status preservation. Run each profile into a
different output directory when both questions matter.

`--lean` defaults to `MATHGRAPH_LEAN_BIN`, then `lean` on PATH. A launcher is resolved
through its reported toolchain prefix after checking the exact required version.
`--python` defaults to `python3`; `--timeout-seconds` defaults to a 120-second total
native execution budget (1–600 permitted). Prerequisites must already be installed.

Branches, tags and commit IDs resolve to actual local Git commit objects. Uncommitted
changes are not included. The output directory must not exist and its parent must
exist. An existing output directory is preserved.

| Exit | Meaning |
| --- | --- |
| 0 | Both revisions were completely checked; the head agrees with the retained finite expectations. |
| 1 | Both revisions were completely checked; the head has a reproduced discrepancy. |
| 2 | The comparison is UNKNOWN because source or execution evidence is unavailable, unsupported or incomplete. |

## Read and repeat

Open `report.md` first. It presents the requirement, exact revisions, obligation
comparison, a distinguishing input if present, costs, next action and scope.
`result.json` includes each actual case observation. Raw sources, probes, reference,
native observations and hashed logs remain available in the output directory.

The status report distinguishes XML acceptance from the returned case rows,
rendered rows/status cells, function-returned count, section totals, and grand
totals. These are actual observations from `junitCases` and `pythonFfiHtml`, with
the emitted JSON and HTML retained; a failed Boolean assertion is not used to
guess which status the source returned.

For a subsequent change, use the previous head as `--base`, the new revision as
`--head`, and a new output directory. The method, expectations and corpus are
retained. Earlier verdicts are never inherited as evidence about new source.
The local profile can evaluate a compatible source outside the two historical
fixture hashes; the hosted pilot still requires its existing exact-source admission.

UNKNOWN gives a concrete reason. Supply a missing Git revision/module, choose a
working Lean 4.35.0 binary, or resolve the recorded compile/execution problem, then
rerun into a new directory. A build error is not classified as a counterexample.

## Status policy and applicability

The status profile adopts this finite policy for the selected PASS/FAIL/SKIP
renderer: a direct `error` or `failure` child produces `FAIL`/`fail`; otherwise a
direct `skipped` child produces `SKIP`/`skip`; otherwise the case is `PASS`/`pass`.
Errors contribute to the failed total and require a failing grand-total class.
Escaped text, comments and CDATA containing the word `error` do not establish an
error outcome.

[The pinned pytest JUnit producer](https://github.com/pytest-dev/pytest/blob/13ba5cba07f56728d25d89cc7f5f0b24b06c3b95/src/_pytest/junitxml.py)
provides the error/nonpassing distinction. Mapping errors and assertion failures
to the same displayed `FAIL` is this profile's explicit three-status policy;
Python ElementTree supplies XML structure, not semantic authority or independent
customer approval. This profile does not preserve the finer error-versus-failure
distinction or specify every JUnit dialect.

The HTML projection accepts only the selected single-section layout and stylesheet.
Unsupported markup or layout changes produce `UNKNOWN`, even if a person could
interpret the new report. Missing observations, source bindings or native controls
also produce `UNKNOWN`. Rejection of a declared supported, valid fixture is a
recorded discrepancy; a failure to execute or interpret the observation is not.

A report-generation command may return exit code zero while successfully rendering
failed tests. Zero alone is not a failed-test discrepancy. The exit table above
describes the MathGraph comparison command; this profile does not impose a new exit
policy on the source project's report CLI.

## Verification boundary

The actual source bytes and original guards are preserved, but the selected module
uses an explicit empty `HtmlReport.lean` stub, as in the earlier isolated pilot.
This does not establish correspondence to upstream's full dependency environment,
full reports CLI, XML conformance or whole-repository correctness. The runtime and
stub identities are recorded. Local Git metadata is not remote issuer authentication.

The default three requirement groups and 19 cases are the existing operator-adopted
finite profile. Python ElementTree independently evaluates their XML acceptance
each run. The opt-in status profile uses its separate eight-case outcome reference
and the explicit policy above. Neither supplies customer-specific requirement
approval. Output is a finite observation, not automatic repair permission or hosted
warrant admission.

No models or hosted credentials are needed. Execution time and subprocess counts
are measured. External engineer use, human reviewer savings and 10x advantage remain
NOT_RUN until an actual person performs that separate trial.

For that trial, choose a consequential change within this profile before running.
Record setup time, failed attempts, review/correction time and whether the result
changed or supported the engineer's decision. Repeat on a subsequent revision with
the same retained requirement. Compare total human effort with ordinary review
given equal inputs and coverage; a correct UNKNOWN is a legitimate result. Do not
fill in human effort from machine execution time.

## Reproduce the engineering qualification

The frozen later-source selection is the owner integration
`14eb6dbab845d2ac61f171a9ed61906d3f9ffb2f`, whose Reports blob is
`d02b18f300bd547dabf83d58ee97d35219516e83`. Its contents were not used to tune the
retained cases. The default main selection `122064d0c853be8d6c2f4cd255c6fcd67acc4ae8`
has no Reports module and remains a distinct unsupported result.

```bash
git init /tmp/l4yaml-report-subject
git -C /tmp/l4yaml-report-subject remote add origin https://github.com/nasa-jpl/L4YAML.git
git -C /tmp/l4yaml-report-subject fetch --depth 1 origin \
  3e855548afa1c70bcc2aa77f7b86587de5658743 \
  14eb6dbab845d2ac61f171a9ed61906d3f9ffb2f \
  122064d0c853be8d6c2f4cd255c6fcd67acc4ae8
python3 experiments/check-retained-report-v1/qualify.py \
  --repo /tmp/l4yaml-report-subject --out /tmp/new-retained-report-evidence \
  --lean /path/to/lean-4.35.0/bin/lean
```

The qualification preserves forward, reverse, unchanged and module-absent results.
It is source-reuse engineering evidence, not an unseen-project discovery tournament
or an external operator trial. Actions artifacts retain the full execution evidence.

[Qualified observations and exact run](../../../experiments/check-retained-report-v1/README.md)
record the first completed replay. No cases or expectations were retuned for the
selected later source.

### Qualify the separate status profile

The status qualification reuses the known EA04 error-to-PASS finding. It starts
from the same pinned integration and constructs a local candidate that recognizes
`error` alongside `failure`. The candidate is an actual Git child commit with an
explicitly synthetic author/date. Its source, parent, patch and commit object are
retained in the output; no upstream candidate identity is asserted. Git plumbing
and a temporary index preserve the subject's branch, index and checkout.

Using the fetched subject above and a committed, clean MathGraph verifier:

```bash
python3 experiments/check-report-status-v1/qualify.py \
  --repo /tmp/l4yaml-report-subject --out /tmp/new-report-status-evidence \
  --lean /path/to/lean-4.35.0/bin/lean
```

This runs six comparisons: original against itself, original against candidate,
candidate against original for withdrawal, candidate against itself, the unchanged
default envelope profile on original/candidate, and candidate against the absent
module control. Inspect each report and `summary.json`; the qualifier retains
progress and failure diagnostics and records `PASSED` only after every required
control and provenance check succeeds. The workflow retains `status-qualification`
as a separate artifact for 30 days, including partial evidence after a failure.

The [completed status qualification](../../../experiments/check-report-status-v1/README.md)
records exact source/method identities, original/repair/withdrawal observations,
Actions evidence and preserved unsuccessful local attempts. This is known-case
reuse and a local candidate, not a new discovery or an upstream repair. The human
trial and comparative advantage remain `NOT_RUN`.
