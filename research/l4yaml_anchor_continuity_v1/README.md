# L4YAML × MathGraph Check — source-native semantic continuity

This is an **independent Metalogic audit**, not an upstream L4YAML change, JPL endorsement, security finding, or general YAML correctness proof. It reuses the retained 2026-10-24 native probe/independent verifier and adds a source-scoped warrant projection. It can be rerun against a later immutable upstream commit.

## First replay

The original native replay against `nasa-jpl/L4YAML@82cdb78e8909f25d9079d9bb05ed7c6f508ee95c` with `leanprover/lean4:v4.35.0` returned:

| Scope | Observed |
|---|---|
| Upstream native target build | 56/56 jobs completed |
| Acyclic anchor rebinding mismatches | 5/5 reproduced in direct, public and indexed paths |
| Acyclic unaffected controls | 5/5 passed |
| Undefined alias | rejected by all observed paths |
| Cycle inputs | 2 observed; **excluded** from acyclic conformance conclusion |

One separator: `[&x [&x 1], *x]` has reference value `[[1], 1]`, but the pinned native L4YAML source returns `[[1], [1]]`. The latter reflects re-applying the enclosing anchor after the nested declaration. This is a **bounded observation** checked against an independent `ruamel.yaml==0.18.17` snapshot and YAML 1.2.2 normative anchor semantics. It is not a terminal formal theorem or proof that every input fails.

## Reusable execution

The owned workflow at `.github/workflows/mathgraph-check-l4yaml-semantic-continuity.yml` freezes the current `fix-a-grammar-completeness` branch into one 40-character commit SHA (or accepts an explicit SHA), checks out the exact upstream source, installs declared Lean 4.35.0, compiles the required native APIs, re-runs the 13-case `Probe.lean`, reacquires the independently hashed ruamel wheel, and executes `run_oracle.py` plus `analyze.py`. It then runs `python -m mathgraph_check.l4yaml_continuity` and publishes source-bound native logs, verifier receipt, warrant report and withdrawal simulations as a GitHub Actions artifact.

The verifier is not an interchangeable generic Lean checker: it verifies exact JSONL schema and case membership, fixed raw source trees, values and controls, agreement across multiple L4YAML entry points, independently obtained oracle interpretations, empty stderr, toolchain and committed source bytes. Exit 0 attests *bounded characterization* (mismatching, partly repaired or repaired inputs); a repaired result does **not** imply general parser correctness.

The warrant projection (`mathgraph_check/l4yaml_continuity.py`) distinguishes:

- `SOURCE_DOCUMENTED`: independently qualified identity of the pinned source;
- `WARRANTED_BOUNDED`: native, specific behavioral observation and retained controls (not the MathGraph theorem kernel);
- `UNKNOWN` on stale commit or withdrawn oracle, native, verifier or source evidence;
- `NOT_AUTHORIZED` for downstream merge, release or deployment **regardless of audit outcome**.

The projection is only safe after executing the native verifier. Receipt labels, SHA strings or GitHub success badges alone are not authentication. A later source commit must earn its own native replay; byte-identical `Types.lean` does not transfer a whole-run receipt automatically.

## Broader V2 differential qualification

The adjacent `research/l4yaml_semantic_diff_v2/` expands the audit to **532 generated acyclic inputs** without changing upstream: 180 anchor-interaction variations and 352 ordinary Core YAML variations. Both legacy and indexed native JSON paths are checked against a newly regenerated value oracle from the pinned ruamel wheel on every run. All 352 ordinary cases are also corroborated by a **second byte-checked PyYAML 6.0.3 implementation**; PyYAML is not used as an independent oracle for the duplicate-anchor cases it refuses. Its dynamically supplied Lean inputs are complete JSONL files; the report retains exact source and input hashes, mismatch families, examples, unchanged controls, and `UNKNOWN` on stale source.

At upstream commit `82cdb78e8909f25d9079d9bb05ed7c6f508ee95c`, independent [GitHub Actions run 40068175209](https://github.com/metalogiclabs/mathgraph/actions/runs/40068175209) reproduced 105/180 anchor-family mismatches, 0/352 ordinary-family mismatches, and 0 legacy/indexed disagreements. These variants are **not 105 independent defects**; they are consistent with the previously demonstrated single ordered-binding cause. Qualification is bounded to the exact native run and its artifact.

## Source-revision transition and style-sensitive typed controls

`SchemaProbe.lean` and `schema_continuity.py` add eight independently checked
`parseTyped` value controls for quoted/plain `true`, `null`, `42` and two
explicit tags. The integration-branch workflow re-runs these controls on each
new frozen upstream SHA; they guard a behavior that is correct at the pinned
baseline, rather than suggesting an outstanding defect.

The separate owned `mathgraph-check-l4yaml-pr89-transition.yml` workflow replays
two immutable upstream revisions and compares their **same 532** value cases,
eight typed controls and 19 source-derived scanner accept/reject witnesses.
Its local prospective PR #89 experiment observed 11 accepted→refused changes,
eight unchanged acceptance controls, no disagreement between L4YAML's two
native parser paths, and no movement in the older 532-case value residual.
The two independent YAML parsers themselves disagree on 11 of the 19 new flow
inputs; `flow_transition.py` retains those conflicts without granting either
implementation normative specification authority. PR #89 is an **unmerged
prospective** change at this snapshot. The newer paired workflow's GitHub CI
qualification must be inspected separately; local results are not CI receipts.

## Local replay

1. Clone `https://github.com/nasa-jpl/L4YAML` at an exact commit, without editing upstream.
2. In that source checkout run `lake build L4YAML.Output.Json L4YAML.Output.Events L4YAML.Output.JsonIx`, then `lake env lean --run /absolute/path/to/Probe.lean > native_results.jsonl 2> native_stderr.log`.
3. Obtain the exact `ruamel_yaml-0.18.17-py3-none-any.whl` (`sha256:9c8ba9eb3e793efdf924b60d521820869d5bf0cb9c6f1b82d82de8295e290b9d`), install it into `install/` without dependencies and run `run_oracle.py` to reconstruct the oracle JSON.
4. Execute `python -m mathgraph_check.l4yaml_continuity` with the `--verifier-script`, `--native`, `--stderr`, `--oracle`, `--checkout`, `--lean`, `--expected-head`, `--receipt-out` and `--report-out` arguments. The frozen GitHub Actions workflow is the reference command implementation.

## Residuals

- Proof that the YAML 1.2.2 textual normative requirement is faithfully modeled in Lean is **UNKNOWN**; this is an executable differential audit, not a Lean proof of the full standard.
- Any reported source fix requires a replay at the new exact commit. Changes to API, Lean toolchain, oracle or semantic grammar must be explicitly requalified.
- No upstream maintainer has reviewed or endorsed this particular new pilot; no JPL source or PR was changed by it.
