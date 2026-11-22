# Run the retained report-integrity check

Compare committed `Tests/SuiteRunner/Reports.lean` at two local Git revisions using
the same 19 XML acceptance cases and three obligation groups. Both revisions run
afresh. This local command does not require the private GitHub App.

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

For a subsequent change, use the previous head as `--base`, the new revision as
`--head`, and a new output directory. The method, expectations and corpus are
retained. Earlier verdicts are never inherited as evidence about new source.
The local profile can evaluate a compatible source outside the two historical
fixture hashes; the hosted pilot still requires its existing exact-source admission.

UNKNOWN gives a concrete reason. Supply a missing Git revision/module, choose a
working Lean 4.35.0 binary, or resolve the recorded compile/execution problem, then
rerun into a new directory. A build error is not classified as a counterexample.

## Verification boundary

The actual source bytes and original guards are preserved, but the selected module
uses an explicit empty `HtmlReport.lean` stub, as in the earlier isolated pilot.
This does not establish correspondence to upstream's full dependency environment,
full reports CLI, XML conformance or whole-repository correctness. The runtime and
stub identities are recorded. Local Git metadata is not remote issuer authentication.

The three requirement groups and 19 cases are the existing operator-adopted finite
profile. Python ElementTree independently evaluates their XML acceptance each run;
this does not provide customer-specific requirement approval. Output is a finite
observation, not automatic repair permission or hosted warrant admission.

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
