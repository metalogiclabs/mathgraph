# Retained failure checks with 104-prompt accounting

This local Check command executes five retained profiles on two exact Git
revisions and writes an outcome for every prompt in the canonical catalogue.
All five profiles run by default, including when an earlier profile reports a
discrepancy or cannot complete.

```bash
node integrations/mathgraph-check-github/catalogue-check-v1/run.mjs \
  --repo /path/to/local/L4YAML \
  --base BASE_COMMIT --head HEAD_COMMIT \
  --out /path/to/new-output-directory \
  --lean /path/to/lean-4.35.0/bin/lean
```

The subject must be reviewed local source. The command reads committed Git
objects and executes them with Lean 4.35.0, Python 3 and GNU `timeout`; it is
not an isolation environment for hostile source. No model call or external
operator is required. The default execution budget is 120 seconds per profile,
with the underlying adapters retaining their separate process deadlines. Use
`--timeout-seconds 1..600` to declare another budget for a new invocation.

## Executable obligations

| Profile | Fixed cases | Protected distinction |
| --- | ---: | --- |
| `junit-report-integrity-v1` | 19 | Malformed XML envelopes versus accepted reports and existing refusals |
| `junit-status-preservation-v1` | 8 | Error/failure versus success through JUnit rows and HTML |
| `suite-per-case-agreement-v1` | 5 | Keyed per-case agreement versus equal aggregate totals |
| `suite-refusal-integrity-v1` | 18 | Deliberate parser refusal versus failed test apparatus |
| `capstone-axiom-admission-v1` | 4 | Kernel, permitted-foundation and native controls versus an unauthorized private axiom |

The five agreement fixtures each contain four backends and five presets. They
exercise actual Reports consumers on controlled evidence, not four parser
implementations. The refusal profile executes the unchanged `runTest` function
and required declarations extracted from Main, with actual small source
dependencies and controlled child programs. Its explicit Lean-backend contract
requires an exact stdout marker and matching exit status. That contract is not a
universal interpretation of nonzero exit codes.

Each adapter declares its source projection, assumptions and remaining boundary
in its receipt. Full CLI, whole-repository, complete XML, AST/value agreement,
general failure recovery and complete catalogue coverage are not established.

## What the 104 rows mean

`catalogue.json` preserves the stable IDs, names and prompts of revision
**2026-11-26-r4**. The r3 publication correction retitled item 104 from `Value` to
`Assurance value`, distinguishing measured assurance benefit from item 4's
governing `Values`. IDs, prompt texts, groups and finite mappings are unchanged.
This public file is the complete editorial candidate catalogue, developed during
MathGraph assurance research with AI assistance. It is not an established
literature-derived taxonomy. Revision r4 removes private drafting metadata and
the backward provenance link to a historical snapshot. No private file is needed
to inspect the prompts or reproduce the five profiles. Run receipts identify
the exact verifier commit and catalogue digest; historical revisions are not
changed by this correction.
Every entry remains `CANDIDATE_PROMPT`. The executable mappings in `catalogue.mjs`
are editorial connections to finite obligations and may overlap.

Currently **17 prompts have a mapped finite facet** and **87 have no executable
connected to this command**. Neither number is a coverage percentage. Every row
records `full_family_coverage: UNESTABLISHED`; even an observed agreement cannot
close all the mechanisms represented by a broad prompt.

| Row state | Meaning |
| --- | --- |
| `BOUNDED_AGREEMENT` | Every connected retained profile completed and the head satisfied its finite obligations |
| `BOUNDED_MISMATCH` | At least one connected profile observed a discrepancy; any other UNKNOWN or omitted checks remain visible |
| `UNKNOWN` | A connected profile lacks complete execution evidence |
| `NOT_RUN` | At least one connected retained profile was explicitly omitted |
| `UNSUPPORTED_BY_THIS_COMMAND` | No executable is connected to the prompt here; this is not a finding of inapplicability or absence of capabilities elsewhere in Check |

`--profiles` accepts a comma-separated subset of the five exact profile IDs.
Omitted profiles are recorded as `NOT_RUN`; a partial run cannot become a
completed all-profile result. Missing modules, unsupported source shapes,
unavailable tools and incomplete process observations are `UNKNOWN`, not
inapplicable or passing. Discrepancies remain visible when another check is
unknown. No earlier acceptance verdict is reused.

## Output and exit status

- `report.md` presents the profile changes, all 104 dispositions and boundaries.
- `result.json` records both resolved commits, catalogue and dispatcher hashes,
  profile result hashes, costs, all prompts, mappings and unassessed residuals.
- `checks/PROFILE/` retains each adapter's source/method identities, observations,
  raw logs, result and scoped report.

The output directory must be new, preserving prior failures and UNKNOWNs. Exit
**0** means all five retained profiles completed and agreed with their finite
head obligations. Exit **1** means complete execution with discrepancies. Exit
**2** means UNKNOWN, NOT_RUN or a command error. No exit code asserts full
104-family coverage, permission to deploy, or a measured improvement in value.

## Qualification and lineage

See [the frozen qualification](../../../experiments/check-catalogue-v1/README.md)
for original, partial repair, combined repair, withdrawal, unchanged and missing
source controls. Existing XML and status qualifications remain separate evidence.
The frozen qualification documents the controlled EA01/EA03/EA04 witness lineage.
The capstone profile adds four controls through pinned production gate bytes;
[PR #287](https://github.com/metalogiclabs/mathgraph/pull/287) identifies the
five-profile qualification at `58ddb19e00e6097d2196d7a1a4760ccb653924d5` and its
original, repair and withdrawal runs. The older four-profile qualification is
retained as historical lineage, not a description of the current dispatcher.
Theorem adequacy/vacuity, numerics, composition, general input coverage and value
still need their own retained obligations.

The successful historical [five-profile Actions run 45005108553](https://github.com/metalogiclabs/mathgraph/actions/runs/45005108553)
qualified the earlier source commit `58ddb19e00e6097d2196d7a1a4760ccb653924d5`,
not this r3 provenance and title correction. Source qualification must identify
the exact revision used; neither the old run nor a repository merge is an
institutional endorsement or a whole-family coverage result.
