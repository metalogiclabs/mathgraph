# MathGraph V2 — browser qualification checkpoint

Status: **PROTECTED_PREVIEW_NOT_PERFORMED**. Prepared 11 October 2026 from
accepted implementation `7a43e7ff45eda96aee11c9efe056542f2498bbd8`.
This is a record of existing local task observations plus the pending Task 8
matrix. It is not a completed preview report or accessibility certification.
See the [authority checkpoint](mathgraph_v2_release_authority_2026-10-11.md).

## Earlier local browser observations

The ignored Task 3–6 reports record the following successful local build/browser
runs. They were reviewed during Task 7, not rerun as preview tests. Their source
tests are committed; temporary screenshots are not durable release evidence.

| Task/commit | Executable test | Recorded local coverage |
| --- | --- | --- |
| T3 `3fcb4e74dad22bd02f00b6232584b18c2970a8d3` | [import-workbench.browser.mjs](../website/tests/import-workbench.browser.mjs) | Verify/Check at 390px; real local file, every workflow stage, keyboard, no-JS, mutation/reset, unsupported route, actual download rejected by Python; rendered command executed; zero interaction requests |
| T4 `ce5d19e8d2c685e6e6752e41c938a7b34647a1da` | [outcome-navigation.browser.mjs](../website/tests/outcome-navigation.browser.mjs), import suite | 1440/768/390, JS/no-JS, Enter/Tab/Escape and focus return, outside-pointer/focus closure, breakpoint reset, active groups, old routes and readable landing-page layouts; homepage added to import suite |
| T5 `16e6b0782c9a2c7452f9dcd275f7b721a6f54443`, fix `e1b13678c4680fee76e196c7e10b6f89506ac500` | [knowledge-map.browser.mjs](../website/tests/knowledge-map.browser.mjs) | 1440/768/390, JS/no-JS, reduced motion, semantic/SVG keyboard selection, direct fragments/reload/Back/Forward, unrelated fragments, filters, directed display-only traversal, actual export/reader/evidence rejection, truncation, all 14 routes; homepage 2/1 graph; zero overflow/errors |
| T6 `a34e91523f34f9cddb4dcbd9586b47efbbfa4564`, fix `7a43e7ff45eda96aee11c9efe056542f2498bbd8` | [catalogue-filter.browser.mjs](../website/tests/catalogue-filter.browser.mjs) | Records/capabilities at 390/901/1024, JS/no-JS, reduced motion, keyboard text/select/reset, no-match state, complete fallback, no page/container overflow or console/page errors |

T4 temporary screenshots were reported under
`/tmp/mathgraph-task4-browser.J0SqCh`; T5 under
`/tmp/mathgraph-task5-browser.WoLBsW`; final T6 review screenshots under
`/tmp/mathgraph-task6-review-browser-final.GnWlgh`. Their continued availability
has not been qualified. They are not protected-preview screenshots and must not
be presented as an immutable release archive. Task 8 retained evidence is PENDING.

The reports used the bundled Node 24 runtime and external browser tooling:

```text
Node directory: /Users/heath/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin
PLAYWRIGHT_MODULE=/Users/heath/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs
CHROMIUM_EXECUTABLE=/Users/heath/Library/Caches/ms-playwright/chromium_headless_shell-1187/chrome-mac/headless_shell
```

T4 explicitly recorded Node 24.19.0. Task 8 must record its actual Node/npm,
Playwright/browser versions, operating system and viewport heights; this report
does not infer a browser version from a cache directory. The local browser
harnesses start loopback servers and required scoped execution permission.

Reproducible local entry points from `website/` are `npm run test:import-browser`,
`npm run test:navigation-browser`, `npm run test:map-browser`, and
`npm run test:catalogue-browser`, with an existing compatible browser installed
and the above optional overrides. These local-server harnesses do not themselves
prove hosted protection, deployed headers or cache behavior.

## Task 8 protected-preview identity

| Field | Status |
| --- | --- |
| Final source commit/tree and CI | PENDING |
| Immutable Vercel preview deployment ID/URL | PENDING |
| Protection and authorized access verified | NOT_PERFORMED |
| Actual browser/runtime/OS/version and test timestamp | PENDING |
| Capture manifest, image locations and content hashes | PENDING |
| Browser-report commit tied to deployment | PENDING |

## Pending preview matrix

Every row below is **PENDING / NOT_PERFORMED on the protected preview**. Local
task success above is not substituted for any row. Test at approximately 1440,
768 and 390 pixels; include the 901/1024 catalogue breakpoint regressions.

| Surface | Required observation | Preview result |
| --- | --- | --- |
| Import → Interpret → Check → Resolve → Explore → Export | Exact supported record retains identity/scope/evidence/unknowns; real file/download; mutation, malformed/oversize and unsupported-route reset; no new resolution semantics | PENDING |
| Import authority | Browser output authority NONE; original replay NOT_PERFORMED; downloaded presentation rejected by actual independent importer; supported offline command works | PENDING |
| Map | Node/detail synchronization, filters, incoming/outgoing traversal, parallel occurrences, endpoint/direction/provenance and source pins; actual download through read-only reader; evidence rejection | PENDING |
| Map navigation | Direct fragment/reload, Back/Forward, unrelated fragment, native Tab exit, permanent detail URLs | PENDING |
| Map bounds | Limit/filter omissions, completeness context, no dangling edges, honest empty state and selection export | PENDING |
| Navigation | All outcomes and active descendants, mobile disclosure Enter/Escape/focus restoration, no trap, skip link and legacy routes | PENDING |
| Catalogues | Keyboard text/select/reset, exact token filters, qualified/experimental separation, live counts, no-match copy and narrow-container layout | PENDING |
| Accessibility | Keyboard completion of navigation/map/filter/export; visible focus; status announcements; measured touch targets and contrast; reduced motion | PENDING |
| No JavaScript | Full catalogue/map semantic content, visible navigation, disabled recognition with offline path; original Resolve fail-closed fallback | PENDING |
| MIME/security headers | Exact TypeScript path text/plain; charset=utf-8, nosniff retained, direct browser rendering, immutable source/built/download digest match | PENDING |
| Other delivery behavior | HTTP status, security/cache headers, no console/page errors, unexpected requests or arbitrary fetches; protection/noindex | PENDING |
| About/Contact/social | Truthful organization/contact links; both record social metadata/images; no evidence-byte mutation | PENDING |
| Performance | Same-route production/preview total transfer, client JavaScript and loading measurements under stated conditions; explain material differences | PENDING |
| Visual evidence | Desktop/tablet/mobile actual screenshots and readable long identifiers/status boundaries; record route, dimensions, commit and hashes | PENDING |

## Performance boundary

Prior local built-site totals were 43,619 client bytes at T4, 50,282 after the T5
history fix, and 53,218 at accepted T6. The historical PR #156 report recorded
32,206. These are build-check totals from different source boundaries, not
same-route browser transfer or timing measurements. No speed/performance claim
or numerical comparison of real loading is qualified by them. Task 8 must
measure the live production baseline and exact preview under matching conditions.

## Completion rule

Replace PENDING cells only with observed results and evidence at one immutable
deployment. Record failures and fixes with affected gates rerun; never inherit a
prior result after changing its source. A documentation-only final report may
follow the deployment, but must identify its exact source and run the required
document/link/CI checks. Production promotion remains NOT_PERFORMED.
