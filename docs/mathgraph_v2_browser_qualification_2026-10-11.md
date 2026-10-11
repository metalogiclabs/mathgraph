# MathGraph V2 — browser qualification checkpoint

Historical status: **PROTECTED_PREVIEW_NOT_PERFORMED**. This checkpoint was
prepared 11 October 2026 from accepted implementation
`7a43e7ff45eda96aee11c9efe056542f2498bbd8`. Its pending Task 8 matrix is
preserved below and explicitly superseded by the
[final protected-preview qualification](#final-protected-preview-qualification).
Neither the historical nor final record is a general accessibility
certification. See the
[authority checkpoint](mathgraph_v2_release_authority_2026-10-11.md).

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

## Historical Task 8 protected-preview identity — superseded

| Field | Status |
| --- | --- |
| Final source commit/tree and CI | PENDING |
| Immutable Vercel preview deployment ID/URL | PENDING |
| Protection and authorized access verified | NOT_PERFORMED |
| Actual browser/runtime/OS/version and test timestamp | PENDING |
| Capture manifest, image locations and content hashes | PENDING |
| Browser-report commit tied to deployment | PENDING |

## Historical pending preview matrix — superseded

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

## Final protected-preview qualification

The historical PENDING/NOT_PERFORMED cells above were closed for the exact
implementation commit
[`9da8dbd4b877bbcc5ea39005b5c7c40618c14abc`](https://github.com/metalogiclabs/mathgraph/commit/9da8dbd4b877bbcc5ea39005b5c7c40618c14abc).
No result below is inherited from an earlier deployment.

| Field | Observed result |
| --- | --- |
| Draft PR | [#158](https://github.com/metalogiclabs/mathgraph/pull/158), open/draft at the exact implementation commit |
| Immutable deployment | `dpl_A1MDVoRhCDnpGcu4UyhahJ485qJr`, [protected preview](https://mathgraph-loomaaug7-over-market.vercel.app), READY |
| Source association | Vercel build log cloned `codex/mathgraph-v2-foundation`, commit `9da8dbd`; build produced 36 static pages |
| Protection | Unauthenticated request returned 302 to `vercel.com`, `Cache-Control: no-store, max-age=0`, `X-Robots-Tag: noindex`, and `X-Frame-Options: DENY`; authorized route checks retained `noindex` |
| Runtime | Node `v24.19.0`; Playwright `1.62.1`; Chromium `155.0.8059.39`; `darwin 25.4.0 arm64` |
| Completion time | `2026-10-11T19:27:14.525Z` |
| Viewports | Main responsive matrix: 1440×900, 768×900 and 390×900; selected mobile fallback checks: 390×844; catalogue matrix: 390×900, 901×900 and 1024×900 |
| Result | 10/10 suites passed; 24 routes checked; 34 screenshots captured and hashed; zero recorded failures |
| Visual evidence identities | [Five representative observations and small manifest](assets/mathgraph-v2/README.md); generated PNGs remain outside Git under repository policy |
| Full transient evidence identities | Capture manifest SHA-256 `07875522e8bee5c41f95c8122986b2ef5cf8f5eb536ef82f9f42a4e73296c108`; all supporting hashes are in the [committed identity manifest](assets/mathgraph-v2/manifest.json), but the machine-local capture directory is not claimed as durable storage |

### Final preview matrix

| Surface | Exact observed result | Boundary |
| --- | --- | --- |
| Import → Interpret → Check → Resolve → Explore → Export | PASS at `/` 1440, `/verify/` 768 and `/check/` 390: exact supported input returned historical `WARRANTED_BOUNDED`; three mutation cases reset; unsupported goal returned `UNKNOWN`; export completed; interaction requests remained zero | Browser result authority is `NONE`; original native proof/source-suite replay remains NOT_PERFORMED |
| Import authority | PASS: the local pinned consumer command ran; presentation export was rejected as evidence; policy/source/scope mutations stayed fail-closed | Historical receipt/policy validation is not original Lean checking |
| Typed map | PASS at 1440/768/390 with and without JavaScript: 14 nodes, 7 declared edges; selection, filtering, traversal, export, fragments and history agreed | Graph is a projection, not evidence or certified relation composition |
| Navigation | PASS at 1440/768/390 with and without JavaScript: outcome grouping, disclosure keyboard/focus behavior and no document overflow | No module maturity or supported-input expansion follows from navigation |
| Catalogues | PASS for records and capabilities at 390/901/1024 with and without JavaScript: two entries each, exact filtering/no-match behavior, no overlap | Filtering changes presentation only |
| Contact | PASS at 1440/768/390 with and without JavaScript: 576px half-width cards on 1180px desktop grid; 736px and 370px full-width stacked cards on tablet/mobile | Contact links are not a response SLA or endorsement |
| About, social and content bounds | PASS: About rendered; both social cards were 1200×630 with expected hashes; inspected object/developer/protocol/record pages had no document overflow offenders; reduced-motion durations were effectively suppressed | Visual review does not establish semantic qualification |
| MIME, security and immutable bytes | PASS: `.well-known`, records 001/002 and TypeScript consumer matched exact SHA-256; the TypeScript path returned `text/plain; charset=utf-8` and `nosniff`; configured CSP, referrer and permissions boundaries were present | Hash/MIME checks establish delivery integrity, not truth or publisher authenticity |
| Browser health | PASS: no console errors, page errors, request failures or HTTP resource errors | Same-owner review, not outside-owner adoption |
| Visual review | PASS on the selected desktop/mobile home, object map, catalogues, import, About and Contact captures; a pre-fix Contact overlap was retained by hash and corrected before the exact preview | This is scoped rendered review, not a universal accessibility certificate |

### Fixes found during final qualification

Final qualification did not weaken a gate. It found and corrected:

1. a browser replay harness that attempted to execute the displayed network
   acquisition text instead of only the local pinned consumer command;
2. catalogue label/control collisions around responsive breakpoints;
3. an undefined Contact grid span that collapsed cards into overlapping
   slivers at mobile width; and
4. omission of `/.well-known/mathgraph.json` from the static CI artifact.

The Contact pre-fix capture from deployment
`dpl_H6rphUX8JY5mWPjSqn1HgHXb1G2c`, commit `6ea4bf4a…`, has SHA-256
`2988b8e18b7985dfb81abe52e7755ad89c137edbf358e9ae5b4fe938c16df026`.
The corrected implementation was rerun through local qualification, exact-head
CI, source-exact preview qualification and visual review.

### Performance boundary — operational sample only

A three-sample warmed-edge check used the same local client and sequential
`vercel curl` requests. The pairs below are median time-to-first-byte / total
time in milliseconds; they are not Lighthouse, lab-browser, field, Core Web
Vitals or causal performance evidence.

| Route | Preview median | Production median | Preview/production body bytes |
| --- | --- | --- | --- |
| `/` | 201 / 211 ms | 118 / 118 ms | 61,669 / 13,991 |
| Record page | 125 / 125 ms | 114 / 116 ms | 31,512 / 30,904 |
| Record JSON | 216 / 216 ms | 113 / 114 ms | Identical |
| TypeScript consumer | 218 / 218 ms | 115 / 115 ms | Identical |

One warmed gzip root response was 12,677 bytes on preview and 4,079 bytes on
production. The richer V2 homepage accounts for most raw-body growth; the
protected-preview toolbar contributed 163 bytes to the captured root. The
sample is small and variable, so **no comparative speed, Core Web Vitals or
production-capacity conclusion is warranted**. The final local static check
reported 53,365 client bytes; it is a build boundary, not a runtime benchmark.

Production remained unchanged at `4edc77cb1a4ff3a345b5feffcf7f2b38d3fbab0c`
and deployment `dpl_3L7v4EWE4SJB8hxiMNhpRWJ1Jaq9`. Promotion, merge and domain
changes remain NOT_PERFORMED.
