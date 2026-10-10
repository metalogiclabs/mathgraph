# MathGraph.org V1

Static Astro product, documentation, and evidence interface for MathGraph. The site renders its qualified L4YAML result from the exact frozen public record in `src/data/l4yaml-record.json`; verification authority remains in the Python publisher, resolver, archived receipts, and qualification tests.

## Local qualification

Use Node 24.15 and npm 12.2, then run:

```sh
npm ci
npm run qualify
```

`qualify` runs Astro diagnostics, data tests, a production build, rendered-page contracts, page/JSON integrity and claim checks, the actual Python resolver documentation contract, HTML validation, internal-link and fragment checks, and an isolated HTTP consumer. The consumer imports no MathGraph verifier code and recomputes the canonical digest: exact pins resolve to `WARRANTED_BOUNDED`, while changed content, incorrect pins, or unsupported inputs resolve to `UNKNOWN`.

To inspect the built site:

```sh
npm run build
npm run preview -- --host 127.0.0.1 --port 4321
```

The exact 13-test publisher and resolver qualification also requires the two original receipt archives. CI retrieves them by immutable artifact ID, verifies both SHA-256 digests, regenerates the publication, and byte-compares every preserved output.

## Public interface

- `/` — product overview and qualified record
- `/check/` — independent verification axes
- `/records/` — immutable record index
- `/records/mg-l4yaml-source-check-20261010/` — full evidence boundary
- `/protocol/` — implemented, experimental, and proposed architecture
- `/developers/` — record and local resolver contract

The `/v1/resolve` resolver is a qualified localhost preview, not a publicly deployed service. The committed static JSON record is the V1 machine-readable public interface.

## Visual review evidence

Exact-width Chrome captures are committed in [`qa/screenshots`](qa/screenshots/): 1440 px desktop, 768 px tablet, and 390 px mobile. The capture gate asserted `scrollWidth === clientWidth` for every captured route. Browser review also covered focus order, visible copy feedback, code-block containment, semantic headings, and console warnings/errors.

## Deployment

The repository-root `vercel.json` installs and builds this workspace, then publishes `website/dist`; the colocated `website/vercel.json` is the matching workspace policy for direct local use. Both supply the restrictive site CSP and permanent read-only redirects from the three resource links in the byte-preserved publisher page to their durable `/evidence/` assets; neither exposes `POST /v1/resolve`. A preview may be created through an existing authenticated Vercel project or Git integration. Do not alias `mathgraph.org`, promote, or deploy with `--prod` without explicit release approval.
