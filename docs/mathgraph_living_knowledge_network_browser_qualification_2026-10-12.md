# MathGraph living knowledge network — browser qualification checkpoint

Status: **LOCAL_RELEASE_GATE_OBSERVED** on 12 October 2026 UTC / 13 October
2026 NZDT. These results cover the existing built `dist/` from branch
`codex/living-knowledge-network`; final-commit GitHub CI and protected-preview
qualification are **PENDING**. They are not a universal accessibility,
performance or production-capacity certification.

## Accessibility and responsive matrix

The mandatory Chromium accessibility gate exercised 16 primary routes at
1440×900, 768×900 and 390×844: **48/48 route-viewports passed**.

Routes covered `/`, `/explore/`, `/verify/`, `/build/`, `/developers/`,
`/check/`, `/resolve/`, `/records/`, `/discover/`, `/develop/`,
`/capabilities/`, `/protocol/`, `/agents/`, both versioned record pages and one
real Mathlib source-occurrence page.

Each observation required:

- HTTP 200, one nonempty title, main landmark and h1;
- meaningful status text appropriate to that page;
- first-Tab skip-link focus and successful keyboard activation;
- no document-level horizontal overflow; intentionally wide code, graph and
  table regions remain contained in labelled, keyboard-focusable scrollers;
- reduced-motion rendering;
- zero browser console or page errors; and
- axe WCAG 2 A/AA analysis.

The final local run on Chrome 155.0.8059.39 reported **zero axe violations and
zero incomplete findings**, including zero serious or critical findings. The
gate initially exposed horizontally scrollable source, contract and provenance
code blocks that were not keyboard-focusable. It also retained 46 incomplete
contrast checks covering 3,334 nodes because of decorative gradient and text
glyphs, and later exposed mobile Resolve overlap. The release candidate removes
those decorative ambiguities, uses CSS geometry for non-text status marks,
reflows the Resolve comparison/table, and gives the existing scrollable
`<pre>` elements `tabindex="0"` without changing evidence content or authority.

The generated source-neighbourhood SVG is explicitly `aria-hidden` and excluded
from Axe. Its exact nodes, relations, labels, links, selection and traversal are
qualified separately through the adjacent semantic HTML lists and dedicated
source-map browser tests; the exclusion does not hide an authoritative or
interactive-only content path.

## Search performance

The deterministic workload uses 20 rounds each of an exact-name query, ordered
token query and no-result query over all 2,372 searchable semantic entries,
including 2,345 source occurrences. JavaScript keeps the full corpus in memory
but mounts a deterministic initial window of 50 matching entries; “Show more”
expands that window by 50. Static/no-JavaScript HTML still publishes all 2,372
entries. Timings include two animation frames after each input rather than only
the synchronous handler.

| Workload | Observed p95 | Budget |
| --- | ---: | ---: |
| Navigation to ready, 4× CPU slowdown | 1,285.0 ms | < 2,000 ms |
| First exact-name use, 4× CPU slowdown | 26.9 ms | < 250 ms |
| Clear/reset, 4× CPU slowdown | 22.8 ms | < 250 ms |
| Search, combined normal CPU | 30.8 ms | < 50 ms |
| Search, combined 4× CPU slowdown | 29.1 ms | < 100 ms |
| Exact name, 4× CPU slowdown | 29.7 ms | < 100 ms |
| Ordered token query, 4× CPU slowdown | 28.8 ms | < 100 ms |
| No result, 4× CPU slowdown | 28.7 ms | < 100 ms |

The strengthened gate first remained red: the old full-DOM implementation
measured roughly 72–79 ms combined normally, 403–425 ms at 4× CPU, 1.37–1.40 s
on first use and 306–362 ms on clear/reset. The correction preserves search
semantics while caching immutable normalized titles, tokens and metadata once
per page, normalizing the query once per render, and mounting only the bounded
ranked window. Existing relevance, exact-count, no-JavaScript and browser tests
remain the behavior guard; no source entry or match was dropped to satisfy the
budget.

## Bounded graph performance

The graph test deterministically selected the largest published neighbourhood,
centred at
`object-02bf55aa275bdcbc49ce17a7389ca67fbb29f33c4cbe1a15706545f686e566ce`
(`SimpleGraph.neighborSet`), exercising that route's declared 8-node/12-edge
display cap. Under 4× CPU slowdown it observed:

| Measurement | Observed | Budget |
| --- | ---: | ---: |
| Initial interactive | 277.6 ms | < 500 ms |
| Node selection p95 | 7.2 ms | < 200 ms |
| Directed display-only traversal p95 | 0.8 ms | < 200 ms |

The graph is a bounded presentation projection with `authority: NONE`. These
timings do not qualify relation composition, closure, implication, equivalence
or browser-side verification.

## Static publication budgets

The budget gate byte-compares the built catalogue with the committed bytes,
validates manifest counts/digests, measures deterministic gzip at level 9, and
scans every built graph projection.

| Artifact / output | Raw bytes | Deterministic gzip bytes | Boundary |
| --- | ---: | ---: | --- |
| Complete catalogue | 9,024,472 | 1,106,556 | ≤ 12 MiB / ≤ 1.5 MiB |
| Search index | 1,624,539 | 197,281 | ≤ 2 MiB / ≤ 256 KiB |
| Largest shard | 1,730,897 | 160,305 | ≤ 2 MiB / ≤ 256 KiB |
| Homepage | 32,455 | 8,885 | ≤ 96 KiB / ≤ 24 KiB |
| Explore | 838,574 | 115,600 | ≤ 1 MiB / ≤ 200 KiB |
| Largest source/object detail page | 37,888 | 6,974 | ≤ 96 KiB raw |

Additional exact observations:

- 2,360 graph projections scanned; maximum 14 nodes and 12 edges, below the
  50/100 ceilings;
- client JavaScript plus CSS: 76,308 bytes, below the 100,000-byte ceiling;
- complete static output: 58,814,026 bytes, below 64 MiB; and
- 2,395 HTML files, below the 2,400-file ceiling.

These figures describe local built bytes. They are not network transfer size,
field performance or a production traffic benchmark.

## Evidence handling and pending work

The tests write reports, traces and screenshots only when
`BROWSER_EVIDENCE_DIR` is supplied. Generated images are never committed. The
[visual-evidence README](assets/mathgraph-living-knowledge-network/README.md)
records this retention boundary.

Still pending at this checkpoint:

- the exact-final-commit aggregate browser and performance jobs in GitHub CI;
- retained CI accessibility, timing, size and screenshot artifacts;
- protected-preview HTTP/header/cache and browser replay;
- 1440×900, 768×900 and 390×844 preview screenshots and visual inspection; and
- source association between one final commit, draft pull request and immutable
  Vercel preview.

No production alias, domain, DNS, registrar, mail or deployment setting was
changed.
