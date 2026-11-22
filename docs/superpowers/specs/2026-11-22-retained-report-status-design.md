# Retain the report's actual test outcome

## Intent and authorization

Continue the authorized MathGraph Check reuse work. Convert the known EA04
JUnit error-to-PASS finding into a reusable consumer check, with a candidate
repair and withdrawal control. The prior 19-case acceptance result stays intact.
Human operator use and a 10x advantage remain unmeasured.

## Choice and boundary

Add one predefined opt-in `--profile junit-status-preservation-v1` to the existing
local command. The default remains `junit-report-integrity-v1`. Changing the old
corpus would obscure its evidence; a separate runner would duplicate source and
runtime machinery. Reuse the coordinator and native driver with an explicit JSON
observation mode, plus one pure profile module, corpus and independent reference.

The requirement is anchored in pytest's JUnit producer at
`13ba5cba07f56728d25d89cc7f5f0b24b06c3b95`, `src/_pytest/junitxml.py`:
setup, teardown and collection failures produce error elements. For this selected
renderer with PASS/FAIL/SKIP vocabulary, error and failure rows must be FAIL/fail,
contribute to Failed, and make the grand-total class fail. This bounded policy
does not preserve the finer error-versus-assertion-failure distinction or specify
all JUnit dialects. ElementTree supplies structure, not semantic authority.

## Contract

- Eight fixed cases: pass, failure, skip, two error forms, error followed by pass,
  mixed pass/failure/skip/error, and harmless escaped/comment/CDATA error text.
- Capture actual `junitCases` rows and `pythonFfiHtml` HTML/count as native JSON.
  Never infer a concrete status from a failed Boolean equality guard.
- Separate XML acceptance, full row values, returned count, rendered rows, section
  totals and grand totals. Require the selected single-section HTML layout and
  stylesheet; unsupported markup or layout changes make projection UNKNOWN.
  Display every compared field so a discrepancy remains visible to the reviewer.
  Parse rejection of these supported valid inputs is an observed discrepancy;
  invalid/missing native observations, controls, source or rendering projection
  make the comparison UNKNOWN.
- Retain exact input/observer/source/runtime identities and complete fixed coverage.
  Use the same positive and negative runner controls and selected-module gate.
- Keep original source guards; disclose the empty HtmlReport dependency. No
  hosted admission change, upstream mutation, CLI-exit requirement or whole-repo
  conformance claim. A reporting program may return zero after displaying failure.
- Check known pinned integration `14eb6dbab845d2ac61f171a9ed61906d3f9ffb2f`;
  source SHA-256 `8e9bc2716fbfde4fbedf4f9a82fd1a0607878898c99c4700f55765a384393542`.
  Candidate changes only the failure-tag condition to recognize error too. Its
  actual local Git commit is recorded; no upstream identity is invented.
- Qualify original, candidate, unchanged, withdrawal, legacy-envelope and missing
  module controls. This is known-case reuse, not a new or blind discovery.

## Completion

Meaningful negative tests, real native replay, independent code review, exact
Actions artifacts, draft PR stacked on #283 and concise canonical ROS update.
