# V9 — structured author-native pytest scope and exact testcase identity

**Status at freeze:** CANDIDATE. Source-independent method only; *no prospective source files, native tests, or behavior have been inspected*. Date 2026-10-20 NZ.

## Current objective / original residual
ROS records V7 `python-markdown2` author driver executed 276 source-native tests while naïve pytest found only 29; this exposed a verifier-coverage problem. V8 [Bottle prospect #39356728013](https://github.com/metalogiclabs/mathgraph/actions/runs/39356728013) passed 364 generic pytest cases, but the already-frozen prose-only author-runner grammar returned UNKNOWN, with zero author command claims; the only subsequently observed relevant source authorities were structured `Makefile` target and `pyproject.toml [tool.pytest.ini_options].testpaths`, so V8 remains UNKNOWN. This is an EXPOSED training source, never a V9 blind prospect.

**V9 falsifier:** Can a completely frozen, source-independent *structured* test-authority observer extract source-authored pytest roots from a previously unopened repository, qualify exactly that scope using original native executions/testcase identities, and causally revoke only altered configuration authority? Compare against **actual default pytest** (which already honors project configuration) and a separately authored equally informed conventional rulebook. No novel observer-type autometagenesis or proprietary advantage is inferred from a tie.

## What source may be examined before execution
Exact pinned revision and **only** these bounded files (max 160 KB each):
- `pyproject.toml`, parsed by stdlib `tomllib` for `tool.pytest.ini_options.testpaths`
- `pytest.ini` `[pytest].testpaths`
- `setup.cfg` `[tool:pytest].testpaths`
- `Makefile` a `test/tests/check` target with recipe containing a direct pytest reference. The entire recipe is **not** executed; it only indicates a structural test target.
Only safe, existing package-relative roots without traversal or symlink escape are admitted. Duplicated conflicting definitions give UNKNOWN, not guessed precedence. The scanner retains source authority filename and SHA256. Invalid/dynamic metadata is not a correct source-root warrant. A `Makefile` test signal without a valid testpaths declaration does NOT warrant complete author suite semantics.

## Two equal-information arms and strongest ordinary baseline
- **Candidate:** `scan.py scan`, with the above structured rules and source graph; `CANDIDATE_SOURCE_CONFIGURED_PYTEST_ROOTS` only if a valid unambiguous testpaths declaration exists. Otherwise explicit UNKNOWN or candidate Makefile signal with no root authority.
- **Expert-rulebook comparator:** a separate `scan.py cookbook` implementation with the SAME four source files, source revision, Python 3.12 parser, same allowed scope/testpaths. This is an expert-authored deterministic cookbook, NOT an independent human reviewer. Both arms' outputs are SHA256-sealed before executing tests.
- **Strong incumbent:** `python -m pytest -q` from original source root, which automatically loads source's original pytest configuration. Never compare solely to an intentionally restricted `pytest tests/specific.py`. Run that exact default arm, then the candidate and comparator's original-safe explicit test roots under the **same** interpreter, dependency environment, cwd, and source pin. Duplicate native execution remains visible in receipts and costs.
- Native authority: pytest original JUnit testcase identity triples `(file, classname, name)`, exit status, counts, skips/fails/errors, stdout SHA256 and elapsed time. Compare exact sets and missing/different identities; do NOT infer subset/equivalence from counts. If original pytest cannot collect or source test dependencies are absent, report `UNKNOWN_NATIVE_EXECUTION_FAILED`. Never silently install post-outcome source-specific dependencies, retune pool, or count CI setup GREEN as science.

## Source-authority withdrawal and requalification
On a **synthetic** source before freeze, physically delete exactly the structured `testpaths` key (without changing implementation/tests), verify that the selected authority edge disappears while independent Makefile signal survives, then byte-restore file and require identical original source SHA, original selected claim and exact native-case set on the restored source. Preserve invalid root, conflicting declarations and missing metadata negative controls.
On a prospective source, after original native executions, one bounded `testpaths = [...] ` single-line edit may withdraw the cited config-authority edge **only** if this grammar can unambiguously identify it. Remaining alternative source evidence must remain. Byte-restore and re-evaluate source static scope. If source format is unsupported, `UNKNOWN_UNSUPPORTED_PHYSICAL_TESTPATH_WITHDRAWAL`. No new native repair claims from temporary config mutation; original native suite never executed on mutant.

## Preregistration, novelty, and hard stops
Before inspecting prospective code/tests, freeze exact method/protocol/preflight/withdrawal scripts and runner workflow, pass preflight using **only synthetic fixtures and EXPOSED Bottle V8 training**. Freeze deterministic metadata-only first-eligible pool:
1. `pallets/itsdangerous`
2. `pytest-dev/pluggy`
3. `python-attrs/attrs`
4. `hynek/structlog`
5. `encode/starlette`

Eligibility is public GitHub, not archived, primary language Python, nonempty default branch, no direct prior native source study found in canonical Notion ROS (bounded negative search, not global novelty proof). Record ineligible entries and source SHA; lock one exact 40-hex revision **before any source file/test code examination**. Do not skip a selected source for missing config, failing native tests, setup difficulty, a tie, wrong program behavior or an inconvenient output.
- Only frozen `pytest==8.3.5` + `pytest-cov==6.2.1` and `pip install -e ./external-native` allowed on the runner. No extra target-specific packages/flags after source outcomes. Absence of original test dependencies is scientific UNKNOWN_NATIVE_ENV, not a software bug or method success. No execution of arbitrary Makefile shell recipes.
- Executor strictly strips common secret-bearing environment vars; only GitHub Actions read-only checkout credentials exist, no upstream writes/changes, no credential/public posting/deploy. Leave source original git worktree byte-clean after any withdrawal.
- Success is **WARRANTED_BOUNDED_STRUCTURED_TEST_SCOPE** for the exact original config roots and original testcase IDs, not author-suite completeness or unique reviewer value. A default pytest tie is legitimate and expected; no advantage claim without actual quality difference and independent competent reviewer. Stronger G2/L7 or semantic meaning inference remain UNKNOWN.
- Scientific stop after first eligible native source. Additional source inspection/tuning turns it into EXPOSED TRAINING, not another V9 prospective trial.
