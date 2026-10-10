# MathGraph Agent Interoperability and Record Population Design

## Status

Approved conversational direction for the next MathGraph.org increment. This design extends the existing qualified V1 website without changing the qualified L4YAML record or weakening its publication gate.

## Intent

Make MathGraph.org useful as a growing public evidence registry for both humans and agents. The increment must provide stable discovery, versioned identities, schema-validated record metadata, and an honest authoring path for future records while preserving the distinction between evidence and presentation.

The public message remains precise:

- Primary headline: **Evidence you can inspect. Results you can reuse.**
- Supporting phrase: **Receipts for machine claims.**
- Agent call to action: **Point your agent to `mathgraph.org/agents`.**

The canonical public origin is `https://mathgraph.org`. Preview deployments use that origin in canonical metadata and public contract examples so preview hostnames never become record identities.

## Product principles

1. A qualified record is immutable evidence, not mutable website content.
2. Presentation metadata may enrich discovery but may not strengthen a record's warrant.
3. `UNKNOWN` is a first-class result, not an error and not an implied rejection.
4. Versioned URLs identify historic records; unversioned URLs are human conveniences that resolve to a declared latest version.
5. Machine and human surfaces must make the same substantive claims.
6. Proposed integrations remain visibly proposed until qualified receipts exist.
7. New or unsupported semantic object types fail closed and remain inspectable; they are not coerced into known types.

## Selected approach

Build a static interoperability layer around the existing immutable publisher output.

This is preferred over a database-backed registry because the current corpus is small, immutable publication is the dominant requirement, and static output is easier to inspect, reproduce, cache, and qualify. It is preferred over documentation-only changes because agents require stable machine contracts rather than prose alone.

Astro remains the presentation layer. Build-time validators assemble a read-only record catalogue from committed manifests and immutable evidence resources. The browser never calculates verification outcomes.

## Public surfaces

### Human routes

- `/agents`: agent-builder onboarding, trust boundaries, discovery sequence, and copyable integration examples.
- `/records`: data-driven index of genuinely published records.
- `/records/{record-id}`: convenience route for the version declared current by the catalogue.
- `/records/{record-id}/v{version}`: permanent human-readable versioned record page.
- `/protocol/profiles/lean`: the Lean evidence-profile specification with field maturity labels.

The existing Check, Protocol, Developers, and record routes remain available. Navigation adds Agents without creating a premature registry search experience.

### Machine routes

- `/llms.txt`: concise discovery document pointing to the agent guide, record index, schemas, immutable evidence resources, and usage limits.
- `/.well-known/mathgraph.json`: versioned discovery manifest for clients that should not parse prose.
- `/records/index.json`: canonical record catalogue containing identifiers, versions, qualified resource links, digests, status summaries, and sidecar links.
- `/schemas/record-index-v1.schema.json`: schema for the catalogue.
- `/schemas/presentation-metadata-v1.schema.json`: schema for non-authoritative citation and discovery metadata.
- `/schemas/lean-evidence-profile-v1.schema.json`: forward-compatible Lean evidence-profile schema.
- Existing immutable JSON, evidence JSON, badge, and OpenAPI URLs remain valid.

Discovery documents contain absolute `https://mathgraph.org` URLs. Every contract declares its own schema version.

## Record package and data model

Each published version is registered by a small catalogue manifest. The manifest references, rather than copies or rewrites, the immutable qualified resources.

Required catalogue fields include:

- record ID and integer version;
- permanent human and machine URLs;
- immutable record resource and SHA-256 digest;
- evidence resource and digest when available;
- schema identity;
- snapshot date;
- historic qualification state;
- current lifecycle state;
- explicitly scoped status summary;
- presentation-metadata sidecar URL, schema version, and digest.

Historic qualification and current lifecycle are separate. A record may remain historically warranted while its current lifecycle is superseded or revoked. The catalogue must never overwrite that distinction.

The presentation sidecar is deliberately outside the qualified record digest. It is independently versioned and checksum-linked from the catalogue so editorial changes remain auditable without being mistaken for a requalification. It may contain:

- title and short description;
- authors and maintainers;
- SPDX license identifier and license URL;
- citation exports and bibliographic references;
- arXiv, DOI, MSC, and prior-formalization references;
- external registry references;
- classifications and search terms;
- social-card presentation fields.

Missing enrichment fields are omitted or represented as typed `UNKNOWN` where the schema calls for an epistemic result. They are never guessed. Changing a sidecar requires a new sidecar version and catalogue digest update, but does not change or upgrade the associated evidence warrant. The current L4YAML sidecar must avoid implying JPL, NASA, Palomar, Tau Ceti, or Lean community endorsement.

The qualified L4YAML `record.json` remains byte-for-byte unchanged. Its existing record ID and content digest remain the authority checked by the build gate.

## Population workflow

A future record is added by committing:

1. qualified immutable record and evidence resources;
2. a versioned catalogue manifest that references their digests;
3. an optional presentation sidecar;
4. any profile-specific receipt references;
5. tests or qualification material required by the record's evidence class.

The build validates schemas, verifies referenced digests, rejects duplicate `(record ID, version)` pairs, checks that the declared latest version exists, and prevents unsupported status promotion. Astro then generates the index and versioned pages from the validated catalogue.

Adding catalogue metadata alone cannot turn a candidate into a warranted record. A warranted entry requires the applicable qualified evidence and publication-gate success.

No general-purpose submission UI, mutable database, or registry-scale search is introduced in this increment.

## Status language and UNKNOWN

The shared visual vocabulary is:

- `WARRANTED · BOUNDED`
- `UNKNOWN`
- `EXPERIMENTAL`
- `PROPOSED`
- `REJECTED`
- `SUPERSEDED`
- `REVOKED`

Each status has text, a simple glyph, and a restrained colour treatment. Colour never carries meaning alone. `UNKNOWN` receives enough visual prominence to make the edge of the qualified boundary immediately legible, but MathGraph's brand remains calibrated evidence rather than ignorance by itself.

The site must not claim that every competing product hides uncertainty, and it must not use a universal green verification mark.

## Homepage boundary explorer

The homepage gains a compact, evidence-derived boundary explorer above or immediately following the first fold. It is not an open claim checker and does not pretend to execute arbitrary submissions.

For the L4YAML record it shows, from the shared validated record data:

- exact source and test-suite pins;
- 48/48 decoded cases matching source labels;
- 31 expected acceptances and 17 expected rejections;
- four additional executable controls;
- 52/52 Lean guard evaluations;
- source-scoped Lean proof replay;
- known recursive-anchor semantic difference;
- corrected historic input-decoding discrepancy;
- `UNKNOWN` whole-language correctness, natural-language fidelity, generalization, and newer-version qualification.

Progressive enhancement may let a visitor step through these layers. With JavaScript disabled, the same facts and boundaries remain readable. The component must not accept arbitrary code, claims, URLs, or proof input.

## Shareable records and badge

Each versioned record page receives deterministic Open Graph metadata and a static social card derived from the catalogue plus qualified record. The card shows the real record ID, truncated digest, qualified boundary, bounded observation, and a visible UNKNOWN boundary. It does not assign an invented sequence such as “Record 001.”

The existing scoped badge remains the basis of the embed. Documentation provides a one-line Markdown/HTML example and explains that the badge links to a bounded record rather than certifying general truth. Badge copy and machine metadata must agree with the record.

## Lean evidence profile

The Lean profile defines how a future Lean record can describe:

- `formalization.yaml` authorship, source status, maintainers, licensing, automation or AI use, limitations, and classifications;
- exact declaration and theorem names;
- permitted axioms and axiom observations;
- statement and proof separation;
- source, statement, proof, workflow, and report digests;
- Lean, Lake, Mathlib, operating environment, and verifier identities;
- optional Comparator receipts;
- optional independent-kernel receipts;
- source/declaration links and reproducible Playground links;
- review policy and rubric URI, commit, and digest;
- statement fidelity, proof validity, execution, provenance, and generalization as separate axes.

The schema supports unknown future extensions without discarding their raw content. Implementations consuming an unsupported extension return typed `UNKNOWN` or an explicit unsupported result.

For this increment the profile itself is `PROPOSED`. Comparator, Playground, and independent-kernel fields remain absent from the L4YAML record and are not displayed as completed capabilities. They become implemented only when a suitable record carries real, validated receipts.

## Agent contract

The agent onboarding sequence is:

1. read `/llms.txt` or `/.well-known/mathgraph.json`;
2. fetch `/records/index.json`;
3. select an explicit record version;
4. fetch the immutable record and relevant schema;
5. verify the advertised digest;
6. compare the agent's intended use with the record's exact scope and UNKNOWN axes;
7. cite the permanent versioned URL and digest.

The documentation gives examples of a reusable in-scope observation, a mismatched source pin, and an unsupported claim. Incorrect pins and unsupported claims remain `UNKNOWN` or explicit errors; they never inherit a nearby warrant.

No MCP server is advertised in this increment. A future MCP adapter must wrap these static contracts or the qualified resolver without broadening their semantics and must receive separate qualification and abuse review.

## Security and operational boundaries

The increment remains static and read-only. It introduces no public code execution, proof compilation, anonymous submissions, external URL fetching, agent-triggered writes, or dynamic verdict generation.

Schemas and catalogue validators enforce reasonable size and shape constraints. URLs referenced by committed metadata are reviewed during publication; browser visitors cannot inject new fetch targets. Generated pages escape sidecar content and retain the site's existing security headers.

The static contracts are designed so a future service can reuse their identities without changing current public URLs.

## Qualification and tests

The existing full `npm run qualify` suite remains mandatory. New coverage includes:

- JSON Schema validation for the catalogue, sidecars, discovery manifest, and Lean profile examples;
- rejection of duplicate record versions and missing latest-version targets;
- rejection of record and evidence digest mismatches;
- rejection of unqualified warrant/status promotion;
- preservation of the qualified L4YAML record bytes, identity, source pins, counts, and UNKNOWN axes;
- agreement between the record page, index, sidecar, social metadata, badge, and immutable JSON;
- resolution of both versioned and unversioned record routes;
- complete and valid `/llms.txt` and well-known discovery links;
- an isolated consumer that discovers the index, verifies the record digest, accepts the exact bounded source-qualified result, and yields `UNKNOWN` for an incorrect pin or unsupported claim;
- internal-link, HTML, accessibility, keyboard, mobile overflow, console, and production-build checks;
- deterministic social-card rendering at desktop and mobile review sizes.

No test may be weakened to accommodate presentation changes.

## Delivery and production rollout

Implementation is developed on a feature branch and submitted as a reviewable pull request. If it builds on an unmerged branding branch, the pull request is explicitly stacked and is retargeted after the dependency merges.

The release sequence is:

1. run the complete local qualification suite;
2. push the feature branch and obtain green GitHub checks;
3. inspect the protected Vercel preview at desktop, tablet, and mobile sizes;
4. verify protected preview contracts through authenticated tooling;
5. obtain final production confirmation if the deployment state differs materially from this approved design;
6. merge or promote through the repository's normal protected workflow;
7. attach the qualified deployment to `https://mathgraph.org` using the existing Vercel project.

The user has requested the canonical main URL rather than a preview-only result. This authorizes a production promotion after the implementation, evidence-integrity checks, CI, and visual review pass. It does not authorize DNS replacement, nameserver changes, email-record changes, unrelated production configuration, or bypassing branch protection. Existing Namecheap MX, SPF, DKIM, DMARC, and mail-related records remain untouched.

After promotion, verify the production title, canonical URLs, primary routes, discovery resources, immutable record resources, HTTPS, and domain behavior. Roll back the deployment if the production checks disagree with the qualified preview.

## Explicit deferrals

- arbitrary public record numbering;
- registry-scale search and filtering with only one published record;
- a public “Boundary Board” without a sufficient qualified corpus;
- public challenge bounties without submission, moderation, safety, and credit policies;
- a public MCP endpoint;
- user-supplied claim checking or proof execution;
- CI cost and throughput dashboards before recurring activity justifies them;
- independent-kernel or “high trust” labels without actual receipts;
- animated fog, shimmering hashes, or other decorative effects that could distract from evidence status;
- any language implying endorsement by Palomar, Tau Ceti, Lean, JPL, NASA, or their contributors.

These deferrals keep the first population-ready release small, inspectable, and truthful while preserving compatible routes and schemas for later expansion.
