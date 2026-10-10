# MathGraph.org V1 Design

## Intent

MathGraph.org V1 is the public product, documentation, and evidence interface for MathGraph, the open verification and trust infrastructure developed by Metalogic Labs. A visitor should understand the product direction in ten seconds; a developer should be able to inspect a genuine source-pinned record in thirty seconds; a researcher should be able to locate the exact boundary, source identities, qualification runs, negative lineage, and unknowns without trusting marketing language.

The implementation must not claim unfinished capabilities. It must preserve the distinction between proof validity, finite execution observations, statement fidelity, generalization, authenticity, and historic qualification status.

## Reconciled authority

- Repository base: `metalogiclabs/mathgraph` at `e80fed62b6e58d2f4b62e2ceb012646c60dd1e28`.
- Qualified public-evidence release: commit `7c1fd9be80966ece12ba455375319961194ae7f4`, successful run `38021785401`, 13/13 release assertions.
- Qualified record: `mg-l4yaml-source-check-20261010`, content SHA-256 `f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb`.
- Parser/proof replay: successful run `38018495536` at `d49a17d2786e6d071af37d2aeba2f2dad7765b75`.
- Decoded source replay: successful run `38020008793` at `988afbf9a6ec69488b63af5c7ff986fde26d673c`.
- Experimental protocol research: successful run `38022424353` at `82fb6815b61d35f70d0d74531f077fc6e28f330e`, 23/23 bounded tests; not a released or independently security-audited protocol.
- The two supplied Notion pages require sign-in and no Notion connector is installed. Their private contents are unavailable and will not be paraphrased or invented.
- The current `mathgraph.org` is a separate Website Builder deployment with broad marketing copy and no inspectable evidence routes. Production remains untouched.

## Architecture

The qualified Python publisher and read-only resolver remain the evidence authority. Their commit is integrated without changing its record identity or expected digest. The website is an Astro static projection under `website/`; it does not reimplement verifier or qualification logic.

The exact qualified `record.json`, `evidence.json`, scoped badge, and OpenAPI contract are committed as durable, immutable website assets. The record page and all human-facing metrics import the same `record.json`. A build-time integrity module checks the record ID, content digest, pins, bounded counts, and non-promotion fields before Astro renders any page. Changing a qualified claim therefore fails the website build unless a separately qualified record is deliberately introduced.

The resolver remains a documented localhost/preview interface. V1 does not present `/v1/resolve` as a deployed production endpoint. A static record consumer demonstrates reuse without importing or duplicating the MathGraph verifier.

## Information architecture

- `/`: concise explanation, qualified L4YAML evidence feature, Claim → Source → Verification → Evidence → Reuse flow, and portable-evidence direction.
- `/check`: current verification axes, exact L4YAML boundary, status distinctions, and current versus research-only capabilities.
- `/records`: a record index containing only genuine published records.
- `/records/mg-l4yaml-source-check-20261010`: full record detail with pins, observations, digests, assumptions, negative lineage, unknowns, and durable resource links.
- `/protocol`: implemented, experimental, and proposed architecture; MGSO envelope and post-quantum warrant are described only as qualified research candidates.
- `/developers`: quickstart, static record consumption, qualified localhost resolver contract, response semantics, reproduction steps, versioning, and limits.
- `/404`: honest missing state with routes back to evidence and docs.

## Visual system

The visual language is editorial developer infrastructure: warm off-white canvas, near-black text, cool blue accent, fine neutral borders, restrained status colours, a compact geometric wordmark, and strong typographic rhythm. The serif display face is a local/system editorial stack; body and code use local/system sans and monospace stacks so the site has no runtime font dependency.

Layout uses a 12-column desktop grid, a readable 70–76 character measure, fluid type and spacing tokens, and one shared content shell. Evidence is shown through aligned definition tables, axis rows, source references, and explicit status labels. Status text always appears with its label; colour is supplemental. Motion is limited to focus, hover, disclosure, and copy confirmation, and respects `prefers-reduced-motion`.

## Components and data flow

- `BaseLayout`: metadata, skip link, navigation, footer, canonical URL, and shared assets.
- `StatusTag`: implemented/experimental/proposed and warranted/unknown/scoped states with text-first semantics.
- `EvidenceAxis`: one axis, its authority, scope, and unknown boundary.
- `Metric`: qualified number plus its exact measurement label.
- `SourceLink`: external link treatment with host and commit context.
- `CopyButton`: progressively enhanced copy interaction; the value remains selectable without JavaScript.
- `EvidenceFlow`: compact accessible ordered sequence.
- `RecordSummary` and `RecordDetail`: both receive the validated record object from `src/lib/evidence.ts`.

The data flow is: qualified publisher output → committed immutable JSON → digest and invariant validation → Astro render → static HTML and JSON. No visitor input can alter the record or create a status.

## Status model

The site uses explicit labels: `WARRANTED — BOUNDED`, `IMPLEMENTED`, `EXPERIMENTAL`, `PROPOSED`, `UNKNOWN`, `REJECTED`, and `SUPERSEDED`. It never uses a universal “verified” badge.

For L4YAML, the site may state only that 48/48 decoded pinned cases matched their source labels, including 31 expected acceptances and 17 expected rejections; four additional executable controls bring the Lean guard total to 52/52; named source-scoped Lean theorems replayed; the recursive-anchor difference and 26DV decoding correction remain visible; universal YAML correctness, natural-language source fidelity, generalization, and post-snapshot requalification remain unknown/not checked.

## Security and operations

V1 is static and read-only. There is no arbitrary code execution, proof compilation, user-supplied URL fetching, repository mutation, credential handling, or public resolver deployment. The site uses a restrictive content security policy compatible with its tiny inline module, no third-party analytics, safe external-link attributes, and immutable caching guidance for evidence assets.

Vercel configuration describes only the static Astro build and security headers. Deployment is attempted only if an existing authenticated project connection is discoverable; production aliases, DNS, and the current domain are never changed.

## Testing and acceptance

- Python: preserve and rerun the qualified 13-test evidence gate using exact archived receipts where available.
- Unit: validate the frozen record and fail closed on changed digest, pins, counts, truth promotion, or unknown statuses.
- Rendering: assert all routes build, the record page and JSON agree, navigation landmarks and labels exist, and no universal badge text appears.
- Consumer: isolated Node process fetches the built static record, accepts the exact pins, and returns `UNKNOWN` for a changed source pin or unsupported goal without importing verifier code.
- Quality: Astro type check, production build, internal-link scan, HTML semantics/accessibility scan, and bundle inspection.
- Browser: rendered desktop (1440), tablet (768), and mobile (390) review; primary routes checked for console errors, keyboard focus, code overflow, record-table readability, and missing-state behavior.
- Delivery: logical commits, pushed feature branch, draft PR, protected preview only when existing credentials permit, and no production change.

## Out of scope

Public resolver hosting, continuous source monitoring, revocation automation, proof execution as a service, general source-to-formalization validation, general cryptographic warrant deployment, production cutover, DNS changes, and partner outreach are not part of V1.
