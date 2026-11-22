# Retained report-integrity check

## Goal and authorization

The user authorized implementing the proposed reuse improvement: make an existing
MathGraph Check investigation independently runnable across source revisions, with
fresh evidence and measured execution costs. This implementation supplies the local
engineering handoff. External human use, reviewer-time savings and a 10x advantage
remain unmeasured.

## Approach

Reuse the existing JUnit report-integrity corpus, independent ElementTree reference,
Lean probe rendering/assessment and base/head comparison. Add one local command over
an exact pair of Git revisions. This avoids requiring the private GitHub App and
avoids merely replaying the two historical allowlisted files.

Alternatives considered: a hosted expansion would require deployment and external
installation work; an exact-fixture-only wrapper would not test reuse on a later
compatible source. The chosen local profile evaluates the existing finite question
on fresh compatible source without granting hosted admission or repair permission.

## Contract

- Node 24 and a reviewed local Lean 4.35.0 installation; Python 3 standard library.
- Inputs: `--repo`, `--base`, `--head`, `--out`, optional `--lean`, `--python`,
  `--timeout-seconds`. The source path is `Tests/SuiteRunner/Reports.lean`.
- Resolve Git refs to actual commits and read exact Git blobs. No checkout edits,
  invented GitHub run identities, model calls or hosted mutations.
- Preserve source bytes and original guards. Compile the isolated module using the
  explicitly recorded empty `HtmlReport.lean` dependency already used by the pilot.
  This does not establish full-repository dependency or CLI correspondence.
- Freeze and reuse the existing 19 inputs, three obligation groups, reference and
  generated probes. Execute both revisions afresh, including positive/negative
  runner controls and individual case observations. No cached verdict inheritance.
- Exact-source hosted admission remains unchanged. Local success means only
  `OBSERVED_AGREEMENT` on the finite isolated profile; discrepancies mean
  `OBSERVED_MISMATCH`; unsupported/incomplete execution means `UNKNOWN`.
- Retain source, corpus, reference, checker, toolchain and stub identities, raw logs,
  actual observed counts and wall/native-call costs. Human and comparative costs
  remain `NOT_RUN`. Locally observed Git identity is not remote issuer authentication.
- Produce `report.md`, `result.json` and inspectable raw evidence. Never overwrite an
  existing output directory. Exit 0 for complete head agreement, 1 for complete head
  discrepancy, 2 for incomplete/unsupported checks. Base incompleteness makes the
  comparison UNKNOWN even if separately observed head evidence is available.
- Local execution is for reviewed source; this is not a hostile-source sandbox.

## Qualification and frozen next source

Historical calibration: existing original/candidate fixtures, including reverse and
no-change comparisons. Before opening later source content, select the owner
integration `nasa-jpl/L4YAML@14eb6dbab845d2ac61f171a9ed61906d3f9ffb2f`, Reports blob
`d02b18f300bd547dabf83d58ee97d35219516e83` (29,878 bytes). Run the unchanged method on
that different source. This is source-reuse qualification, not blind discovery.
Preserve the earlier default-main selection at
`122064d0c853be8d6c2f4cd255c6fcd67acc4ae8` as module-absent/UNKNOWN.

## Completion

The CLI and handoff work on actual native Lean; old hosted gates still pass; a later
source is evaluated or honestly refused; an independent code reviewer checks the
change. Preserve exact code/run evidence and update the existing ROS checkpoint.
The human pilot remains prepared, not performed.
