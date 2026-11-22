# Retained report status implementation plan

Use the existing Node/Python/Lean local pipeline. Keep changes small and preserve
the default 19-case contract. Spec: `../specs/2026-11-22-retained-report-status-design.md`.

- [x] Freeze eight cases and explicit PASS/FAIL/SKIP policy; implement the independent
  ElementTree reference with literal expected controls.
- [x] Add native JSON observations and source/probe-bound status assessment; test
  real values, incomplete evidence, controls and truthful report presentation.
- [x] Add opt-in profile dispatch and human-readable comparison; keep default
  corpus, admission and result semantics unchanged.
- [x] Qualify pinned original, one-line candidate, withdrawal, unchanged, old
  envelope profile and absent module, with exact Git/method provenance.
- [x] Run relevant regressions, fix independent review findings, publish draft
  PR/Actions evidence, and reconcile the existing ROS checkpoint.

External human use and comparative human effort remain NOT_RUN.

Completed engineering qualification is recorded in
`experiments/check-report-status-v1/README.md`: method `4ca35c4f`, Actions
`44985830241`, draft PR #284 and the existing ROS checkpoint. Preserved local
timeout attempts remain unqualified; they were not overwritten by CI success.
