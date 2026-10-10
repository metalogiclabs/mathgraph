# MathGraph.org V1

Static Astro product, documentation, and evidence interface for MathGraph. The site renders its qualified L4YAML result from the exact frozen public record in `src/data/l4yaml-record.json`; verification authority remains in the Python publisher, resolver, archived receipts, and qualification tests. The catalogue and presentation layer may describe that evidence, but cannot promote its authority.

## Local qualification

Use Node 24.15 and npm 12.2, then run:

```sh
npm ci
npm run qualify
```

`qualify` checks the evidence-derived social-card source plus the reviewed PNG artifact's exact digest and dimensions, runs Astro diagnostics and data tests, creates a production build, validates machine and rendered-page contracts, checks page/JSON integrity and claims, exercises the actual Python resolver documentation contract, validates HTML and links, and runs an isolated HTTP consumer. The source/PNG split avoids treating platform-dependent font rasterization as evidence drift while still failing on either source-data drift or changed published bytes. The consumer imports no MathGraph verifier code. It follows discovery → catalogue → immutable record, recomputes transport and canonical digests, accepts only the exact ID/version/source pin/suite pin/goal tuple, and returns `UNKNOWN` for altered content, wrong pins, unsupported goals, unknown identities or versions, and unknown extension types.

To inspect the built site:

```sh
npm run build
npm run preview -- --host 127.0.0.1 --port 4321
```

The exact 13-test publisher and resolver qualification also requires the two original receipt archives. CI retrieves them by immutable artifact ID, verifies both SHA-256 digests, regenerates the publication, and byte-compares every preserved output.

## Public interface

- `/` — product overview and qualified record
- `/check/` — independent verification axes
- `/records/` — human-readable record index
- `/records/mg-l4yaml-source-check-20261010/` — full evidence boundary
- `/records/mg-l4yaml-source-check-20261010/v1/` — permanent V1 record page
- `/protocol/` — implemented, experimental, and proposed architecture
- `/protocol/profiles/lean/` — proposed, unstable Lean evidence profile
- `/agents/` — deterministic agent-consumption contract
- `/developers/` — record and local resolver contract
- `/llms.txt`, `/.well-known/mathgraph.json`, and `/records/index.json` — machine discovery and short-lived lifecycle catalogue

The `/v1/resolve` resolver is a qualified localhost preview, not a publicly deployed service. The committed static JSON record is the V1 machine-readable public interface.

## Publishing another record

Every published version is a package with separately governed evidence and presentation:

- Immutable verifier output under `public/evidence/<record-id>/`, produced by a qualified publisher.
- A registered entry in `src/data/record-index.json` with an exact version, schema, canonical record digest, transport digests, source pins, lifecycle, and structured scope contract.
- A versioned sidecar at `public/records/<record-id>/vN/metadata.json`. It may contain citation, classification, license, and display metadata. It may not contain a warrant, evidence axes, lifecycle, admission, or verification status. Its content digest and visible history make editorial changes auditable without changing qualified evidence bytes.
- A public JSON Schema under `public/schemas/` and an explicit adapter in `src/lib/catalog.ts`. Unknown record schemas fail closed with `UNSUPPORTED_RECORD_SCHEMA`; do not add a catalogue entry before its adapter exists.
- A permanent `/records/<record-id>/vN/` page and an unversioned route that resolves only to the declared `latest_versions` entry.

Population workflow:

1. Qualify and freeze the verifier outputs outside the presentation layer. Never hand-edit an existing qualified record.
2. Copy the immutable outputs into `public/evidence/<record-id>/` and record their byte hashes with `shasum -a 256`.
3. Create the metadata sidecar with `history[].evidence_changed: false`; compute and register its canonical content digest through the catalogue test helpers.
4. Register the version, exact pins, supported goals, and explicit unknowns in `src/data/record-index.json`. A metadata-only change must never change `historic_status` or make a new goal reusable.
5. Add or update the schema-specific renderer. Generate the evidence-derived share card with `npm run generate:social`.
6. Run `npm ci && npm run qualify`. Confirm the consumer returns `WARRANTED_BOUNDED` only for the exact supported tuple and `UNKNOWN` for every negative case.
7. Review desktop, tablet, and mobile output before pushing. Lifecycle changes belong in the short-lived catalogue; historic evidence bytes and permanent URLs remain unchanged.

The committed digest proves integrity and byte identity, not origin authenticity or semantic truth. The current GitHub catalogue link is second-origin provenance marked `UNSIGNED_PROVENANCE_ONLY`; a signed tag or Sigstore statement remains future work until a real key policy is qualified.

## Visual review evidence

Exact-width Chrome captures are committed in [`qa/screenshots`](qa/screenshots/): 1440 px desktop, 768 px tablet, and 390 px mobile. The current capture gate visits the homepage, Agents, record index, current and permanent record routes, Lean profile, and developer guide at all three widths. It asserts `scrollWidth === clientWidth`, one H1 and one main landmark, and no browser console warnings or errors. Browser review also covers keyboard focus order, text-visible status glyphs, code-block containment, and mobile navigation.

## Deployment

The repository-root `vercel.json` installs and builds this workspace, then publishes `website/dist`; the colocated `website/vercel.json` is the matching workspace policy for direct local use. Both supply the restrictive site CSP, immutable caching for evidence, schemas, and deterministic social images; short revalidation for discovery, lifecycle, versioned HTML, and presentation sidecars; and permanent read-only redirects from the three resource links in the byte-preserved publisher page to their durable `/evidence/` assets. Versioned page URLs remain stable while their lifecycle and metadata projection may be refreshed. Neither configuration exposes `POST /v1/resolve`.

Create previews only through the already linked Vercel project or Git integration. Promote the exact qualified preview through Vercel's normal promotion mechanism only after local qualification, green GitHub checks, authenticated preview checks, and visual review. Never change Namecheap DNS, nameservers, MX, SPF, DKIM, DMARC, or unrelated Vercel settings as part of a website release.
