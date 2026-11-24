# Review-ready libcsp routing-table correction

2026-11-24. Base source remains `libcsp/libcsp develop@5ba0ccf66ec0301e65160b41e035cb8a7c916949`. The [preceding checkpoint](https://github.com/metalogiclabs/mathgraph/commit/027cad80d64c1ab8073432f60b3c3573288ee788) contains the independent 114-observation matrix, fork comparison, source hashes and source-history analysis. This record qualifies the actual proposed contribution in the project's Check framework.

## Final change

`upstream-review.patch` changes three files:

- `src/csp_rtable_cidr.c`: count every active entry; overwrite the last slot only when all slots are active. Preserve the historical replacement policy from #350 and 5f8f0d07.
- `unittests/route.c`: three registered Check regressions cover final-slot visibility, last-slot replacement on a full table and updating an existing entry without eviction. They are guarded by `CSP_USE_RTABLE`.
- `.github/workflows/unit-test.yml`: configure with `CSP_USE_RTABLE=ON`, because the previous unit job used the default OFF and would otherwise omit these regressions.

No public API, default library configuration or full-table rejection policy changes. The added tests follow the existing suite and coding conventions. The patch SHA-256 is `0d4713b6756a2429102f0e8304b400fa389a43566cfe495539f8aa4537a17eea`.

## Native execution

| Actual registered Check tests | Before production change | Candidate | Production withdrawal |
|---|---:|---:|---:|
| Static, routing enabled | Original 12 pass; added 3 fail | 15/15 pass | Original 12 pass; added 3 fail |
| Shared, routing enabled | Original 12 pass; added 3 fail | 15/15 pass | Original 12 pass; added 3 fail |
| Static, routing disabled | — | 12/12 pass | — |
| Shared, routing disabled | — | 12/12 pass | — |

Raw Check XML and verbose output identify every executed test. All twelve original test identities retain success in every enabled arm. The three new failures are assertion failures, not build or environment errors. The default disabled feature does not register or link the additional route tests, and still builds and runs normally. XML records and executable digests are in `review-receipt.json`.

This is local Linux x86-64/GCC 14.2.0 qualification using the unmodified project CMake files, CMake 4.4.5 and libcheck 0.15.2. Clang, hosted workflows, optional ZeroMQ tests, other targets and full transport/integration suites have not been executed for this final contribution. A changed workflow file is not evidence that hosted CI ran. The previously qualified independent capacity-1/2/10 matrix is separate evidence for the production repair; these added Check regressions were qualified at the default capacity 10.

The candidate exists in an isolated local Git worktree. The original upstream checkout remains unmodified. Intervention/withdrawal refers to production source during the qualification; the isolated review checkout is intentionally left with the candidate source. Build cache contents alone are not a qualification receipt.

## Reproduce

Apply `upstream-review.patch` to the pinned upstream commit. The ordinary project build should configure with `-DCSP_USE_RTABLE=ON` and run `csp_tests`. To reconstruct the local counterfactual qualification exactly, use `unit-review-qualify.py` in the previously documented directory/dependency layout. It preserves original production bytes from the pinned Git commit, leaves the added tests present in every arm, and changes only production source for the failure/success/withdrawal comparison.

`route-minimal.c` is a separately compiled compact reproduction against the actual unmodified upstream static library. Its raw output is retained and is suitable for a focused report. It calls only routing-table APIs and performs no network or hardware operations.

## Current residual

The repair is concrete and reviewable; the draft report is prepared. Source and targeted duplicate searches were rechecked before this qualification. The report acknowledges #350 and the 2025 correction rather than claiming an unrelated or first-ever discovery. Maintainer acceptance, deployment relevance, operational consequences and commercial demand remain UNKNOWN. No external issue, PR, comment or email is established by this record.
