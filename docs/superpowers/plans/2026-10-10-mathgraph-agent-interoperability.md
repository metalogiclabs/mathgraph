# MathGraph Agent Interoperability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make MathGraph.org population-ready with versioned record packages, agent discovery contracts, a proposed Lean evidence profile, and an evidence-derived public interface, then qualify and promote the approved build to `https://mathgraph.org`.

**Architecture:** Keep the qualified publisher output immutable and add a static Astro catalogue around it. Build-time loaders validate JSON Schemas, content digests, lifecycle/status constraints, and an explicit evidence-schema adapter before generating human and machine routes; presentation sidecars remain separately versioned and cannot promote authority.

**Tech Stack:** Astro 7.3.8, TypeScript 6.0.3, Vitest 5.0.3, Ajv 8.17.1, Sharp 0.35.5, modern CSS, static Vercel deployment.

**Spec:** `docs/superpowers/specs/2026-10-10-mathgraph-agent-interoperability-design.md`

## Global Constraints

- Preserve `website/src/data/l4yaml-record.json` and `website/public/evidence/mg-l4yaml-source-check-20261010/record.json` byte-for-byte with content digest `f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb`.
- Use `https://mathgraph.org` for every canonical public identity, manifest URL, schema ID, and example.
- Never infer whole-language correctness, statement fidelity, generalization, or newer-version qualification from the finite suite.
- Keep `WARRANTED · BOUNDED`, `UNKNOWN`, `EXPERIMENTAL`, `PROPOSED`, `REJECTED`, `SUPERSEDED`, and `REVOKED` text-visible; colour is supplementary.
- Do not expose arbitrary execution, anonymous submissions, visitor-controlled URL fetching, repository writes, a public resolver, or an MCP endpoint.
- Do not imply endorsement by Palomar, Tau Ceti, Lean, JPL, NASA, or their contributors.
- Keep client JavaScript and CSS below the existing 100 kB qualification ceiling.
- Production promotion is authorized only after local qualification, green CI, authenticated preview checks, and desktop/tablet/mobile visual review; do not modify DNS, nameservers, or mail records.

## Review Focus

- A catalogue entry with a valid JSON shape but a forged record digest must fail with `CATALOG_RECORD_DIGEST_MISMATCH`; Task 1 pins this.
- A sidecar that changes its own digest or attempts to declare a warrant must fail with `PRESENTATION_DIGEST_MISMATCH` or `PRESENTATION_AUTHORITY_FIELD_FORBIDDEN`; Task 1 pins this.
- Duplicate versions, a missing declared latest version, and an unsupported evidence schema must fail closed; Task 1 pins all three.
- An agent using a wrong source pin, unsupported claim, unknown record, or unknown version must receive `UNKNOWN` without truth promotion; Task 6 pins this.
- Unversioned and versioned pages must never disagree or let preview hostnames become canonical identities; Tasks 3 and 6 pin this.

---

## File structure

### Catalogue and integrity

- `website/src/lib/integrity.ts`: canonical JSON and SHA-256 helpers shared by qualified-record and sidecar validation.
- `website/src/lib/catalog.ts`: catalogue types, Ajv validation, package loading, digest checks, lifecycle rules, and explicit record-schema dispatch.
- `website/src/data/record-index.json`: authoritative committed catalogue source.
- `website/public/records/mg-l4yaml-source-check-20261010/v1/metadata.json`: independently versioned presentation sidecar.
- `website/public/schemas/*.schema.json`: public versioned contracts for the qualified consequence record, catalogue, presentation metadata, discovery, and proposed Lean evidence profiles.

### Generated public surfaces

- `website/src/pages/llms.txt.ts`: generated text discovery document.
- `website/src/pages/records/index.json.ts`: generated machine catalogue.
- `website/src/pages/sitemap.xml.ts`: generated sitemap including catalogue records.
- `website/public/.well-known/mathgraph.json`: small versioned discovery manifest checked against the generated catalogue.
- `website/src/pages/agents.astro`: human agent onboarding.
- `website/src/pages/protocol/profiles/lean.astro`: proposed Lean profile documentation.
- `website/src/pages/records/[id]/index.astro`: unversioned current-record projection.
- `website/src/pages/records/[id]/[version].astro`: permanent versioned projection, where `version` is `v1`, `v2`, and so on.

### Presentation and qualification

- `website/src/components/EvidenceBoundary.astro`: non-interactive-first boundary explorer sourced from the validated record.
- `website/scripts/generate-social-card.mjs`: deterministic record-card generator and check mode.
- `website/public/social/records/mg-l4yaml-source-check-20261010-v1.png`: committed 1200×630 record card.
- Existing rendering, built-site, consumer, resolver, link, HTML, CI, and screenshot assets are extended rather than replaced.

---

## Execution setup

Before Task 1, use `superpowers:using-git-worktrees` to create an isolated worktree and `codex/mathgraph-agent-interface` branch from the current approved design commit. If PR #153 is still open, open this work as a stacked pull request against `website/mathgraph-brand-assets`; retarget only after the dependency merges. Do not add implementation commits to the branding branch.

---

### Task 1: Catalogue, schemas, and fail-closed integrity loader

**Files:**
- Create: `website/src/lib/integrity.ts`
- Create: `website/src/lib/catalog.ts`
- Create: `website/src/lib/catalog.test.ts`
- Create: `website/src/data/record-index.json`
- Create: `website/public/records/mg-l4yaml-source-check-20261010/v1/metadata.json`
- Create: `website/public/schemas/public-consequence-record-v1.schema.json`
- Create: `website/public/schemas/record-index-v1.schema.json`
- Create: `website/public/schemas/presentation-metadata-v1.schema.json`
- Create: `website/public/schemas/discovery-v1.schema.json`
- Create: `website/public/schemas/lean-evidence-profile-v1.schema.json`
- Modify: `website/src/lib/evidence.ts`
- Modify: `website/src/lib/evidence.test.ts`
- Modify: `website/package.json`
- Modify: `website/package-lock.json`

**Interfaces:**
- Produces: `canonicalJson(value: unknown): string` and `canonicalContentDigest(value: Record<string, unknown>, digestField?: string): string` from `integrity.ts`.
- Produces: `RecordCatalog`, `PublishedRecordEntry`, `PresentationMetadata`, and `PublishedRecordPackage` types.
- Produces: `validateRecordCatalog(value: unknown): RecordCatalog`, `loadPublishedRecords(): Promise<PublishedRecordPackage[]>`, `getPublishedRecord(id: string, version?: number): Promise<PublishedRecordPackage>`, and `getLatestPublishedRecord(id: string): Promise<PublishedRecordPackage>`.
- Guarantees: the current package has ID `mg-l4yaml-source-check-20261010`, version `1`, slug `v1`, historic status `WARRANTED_BOUNDED`, lifecycle `CURRENT`, and exact qualified digest.

- [ ] **Step 1: Add catalogue tests that fail before the loader exists**

Add tests named `loads the exact qualified package`, `validates the qualified record against its public schema`, `rejects a forged immutable digest`, `rejects a changed presentation digest`, `rejects presentation authority fields`, `rejects duplicate id and version`, `rejects a missing latest version`, and `rejects unsupported record schemas`. Assert the exact error codes from Review Focus and verify the existing source pins and UNKNOWN axes survive package loading.

- [ ] **Step 2: Run the focused tests and verify the new suite fails**

Run: `cd website && npx vitest run src/lib/evidence.test.ts src/lib/catalog.test.ts`

Expected: FAIL because `catalog.ts`, the schemas, and catalogue data do not exist.

- [ ] **Step 3: Add exact validation dependencies and public schemas**

Run: `cd website && npm install --save-dev --save-exact ajv@8.17.1 sharp@0.35.5`

Define the exact existing consequence-record shape plus closed core objects in the record-index, presentation, and discovery schemas. Permit future Lean extensions only through a namespaced `extensions` object whose unknown values remain raw JSON. Mark the Lean schema and its Comparator, Playground, and independent-kernel receipt fields as proposed/optional rather than satisfied capabilities.

- [ ] **Step 4: Add the catalogue source and checksum-linked presentation sidecar**

Register only the existing L4YAML V1 record. Include absolute canonical URLs, canonical content digest `f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb`, record transport SHA-256 `7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703`, evidence transport SHA-256 `03b4bfff642c097757c88f12b578e2d903a999a4949393aefb8c91609ce74c63`, snapshot date, bounded status, current lifecycle, visible unknowns, and sidecar digest. Put citation, classification, and explicit license/registration unknowns in the sidecar; include no endorsement or fabricated third-party metadata.

- [ ] **Step 5: Implement shared digest helpers and the async catalogue loader**

Use Ajv to validate the schemas, verify the record's canonical content digest, verify evidence bytes, verify the sidecar's canonical digest, reject duplicate identities and missing latest targets, forbid authority-bearing sidecar keys, and dispatch `mathgraph.public-consequence-record.v1` through `validateQualifiedRecord`. Reject any unregistered record schema with `UNSUPPORTED_RECORD_SCHEMA`.

- [ ] **Step 6: Re-run focused tests and type checking**

Run: `cd website && npx vitest run src/lib/evidence.test.ts src/lib/catalog.test.ts && npm run check`

Expected: all tests PASS and Astro reports 0 errors.

- [ ] **Step 7: Commit the catalogue integrity layer**

```bash
git add website/package.json website/package-lock.json website/src/lib website/src/data/record-index.json website/public/records website/public/schemas
git commit -m "feat(website): add validated record catalogue"
```

### Task 2: Agent discovery and machine contracts

**Files:**
- Create: `website/src/pages/llms.txt.ts`
- Create: `website/src/pages/records/index.json.ts`
- Create: `website/src/pages/sitemap.xml.ts`
- Create: `website/public/.well-known/mathgraph.json`
- Create: `website/tests/contracts.test.ts`
- Delete: `website/public/sitemap.xml`
- Modify: `website/package.json`

**Interfaces:**
- Consumes: `loadPublishedRecords()` from Task 1.
- Produces: static `/llms.txt`, `/.well-known/mathgraph.json`, `/records/index.json`, and `/sitemap.xml` resources.
- Guarantees: every machine URL is absolute under `https://mathgraph.org`; capabilities say static records `IMPLEMENTED`, public resolver `NOT_DEPLOYED`, Lean profile `PROPOSED`, and MCP `PROPOSED`.

- [ ] **Step 1: Write failing machine-contract tests**

Assert schemas validate the built discovery and index documents; `/llms.txt` links the agent guide, catalogue, schemas, immutable L4YAML JSON, and usage boundary; the well-known manifest contains no preview hostname; and the sitemap contains `/agents/`, `/protocol/profiles/lean/`, the unversioned record, and `/records/mg-l4yaml-source-check-20261010/v1/`.

- [ ] **Step 2: Run the contract tests and verify failure**

Run: `cd website && npm run build && npx vitest run tests/contracts.test.ts`

Expected: FAIL because the four new resources do not exist.

- [ ] **Step 3: Implement the three generated Astro endpoints and the discovery manifest**

Set explicit UTF-8 content types. Serialize the validated catalogue without adding verification claims. Keep `/llms.txt` concise and state that an agent must verify the digest and compare its intended use with the explicit boundary.

- [ ] **Step 4: Add `test:contracts` to `test:unit` and re-run**

Run: `cd website && npm run build && npm run test:contracts`

Expected: PASS with schema-valid documents and only canonical production URLs.

- [ ] **Step 5: Commit machine discovery**

```bash
git add website/package.json website/src/pages website/public/.well-known website/tests/contracts.test.ts website/public/sitemap.xml
git commit -m "feat(website): publish agent discovery contracts"
```

### Task 3: Data-driven versioned record pages

**Files:**
- Create: `website/src/pages/records/[id]/index.astro`
- Create: `website/src/pages/records/[id]/[version].astro`
- Delete: `website/src/pages/records/mg-l4yaml-source-check-20261010.astro`
- Modify: `website/src/components/RecordDetail.astro`
- Modify: `website/src/components/RecordSummary.astro`
- Modify: `website/src/layouts/BaseLayout.astro`
- Modify: `website/src/pages/records/index.astro`
- Modify: `website/tests/rendering.test.ts`

**Interfaces:**
- Consumes: `PublishedRecordPackage`, `loadPublishedRecords()`, and `getLatestPublishedRecord()` from Task 1.
- Produces: one unversioned route per record ID and one permanent route per registered version.
- Extends `BaseLayout` props with `canonicalPath?: string`, `socialImage?: string`, and `ogType?: 'website' | 'article'`.

- [ ] **Step 1: Add failing rendering tests for catalogue-driven routes**

Assert both L4YAML URLs render the same record ID, digest, pins, bounded counts, discrepancy, and unknowns; both link to `/records/index.json`; the versioned page canonically identifies itself; the unversioned page canonically identifies V1; an unknown record has no generated path; and preview hostnames never appear.

- [ ] **Step 2: Run the rendering test and verify failure**

Run: `cd website && npm run build && npx vitest run tests/rendering.test.ts`

Expected: FAIL because `/records/mg-l4yaml-source-check-20261010/v1/` is absent.

- [ ] **Step 3: Replace the hand-authored route with catalogue-backed static paths**

Generate paths only from validated packages. Pass the package to `RecordDetail` and `RecordSummary`; display the version, lifecycle, presentation metadata link, and permanent URL without modifying the immutable record. Reject unknown renderers at build time rather than rendering a generic warranted page.

- [ ] **Step 4: Add canonical and social metadata support to `BaseLayout`**

Use `canonicalPath` instead of `Astro.url.pathname` when supplied. Add absolute `og:image`, `og:image:width`, `og:image:height`, and `twitter:card=summary_large_image` only when a social card is supplied.

- [ ] **Step 5: Re-run the route and type tests**

Run: `cd website && npm run check && npm run build && npx vitest run tests/rendering.test.ts`

Expected: PASS for both routes with identical substantive evidence.

- [ ] **Step 6: Commit versioned records**

```bash
git add website/src/pages/records website/src/components/RecordDetail.astro website/src/components/RecordSummary.astro website/src/layouts/BaseLayout.astro website/tests/rendering.test.ts
git commit -m "feat(website): add permanent record versions"
```

### Task 4: Agent guide and proposed Lean profile

**Files:**
- Create: `website/src/pages/agents.astro`
- Create: `website/src/pages/protocol/profiles/lean.astro`
- Modify: `website/src/layouts/BaseLayout.astro`
- Modify: `website/src/pages/developers.astro`
- Modify: `website/src/pages/protocol.astro`
- Modify: `website/tests/rendering.test.ts`

**Interfaces:**
- Consumes: canonical discovery URLs and the current `PublishedRecordPackage`.
- Produces: human onboarding sequence and a clearly `PROPOSED` Lean evidence-profile page.

- [ ] **Step 1: Add failing rendering tests for `/agents` and the Lean profile**

Assert the Agents page contains “Point your agent to mathgraph.org/agents”, starts machines at `/llms.txt`, demonstrates exact digest/pin checks, and returns `UNKNOWN` for unsupported scope. Assert the Lean page covers `formalization.yaml`, declaration names, axioms, statement/proof hashes, Lean and Mathlib pins, Comparator, policy digests, optional kernel receipts, and source fidelity while marking the profile `PROPOSED`.

- [ ] **Step 2: Run the focused rendering tests and verify failure**

Run: `cd website && npm run build && npx vitest run tests/rendering.test.ts`

Expected: FAIL because both routes and the Agents navigation item are missing.

- [ ] **Step 3: Implement the pages and navigation**

Use real current URLs and current L4YAML data only. State that `/v1/resolve` is local/preview, no MCP endpoint exists, Comparator and Playground links require future receipts, and signatures or hashes do not establish semantic truth.

- [ ] **Step 4: Extend developer and protocol cross-links**

Add machine-discovery, versioning, sidecar, scoped badge, and Lean-profile links. Keep the existing resolver example unchanged and explicitly local.

- [ ] **Step 5: Re-run type, rendering, and HTML checks**

Run: `cd website && npm run check && npm run build && npm run test:rendering && npm run check:html`

Expected: PASS with accessible landmarks and no maturity inflation.

- [ ] **Step 6: Commit agent and Lean documentation**

```bash
git add website/src/pages website/src/layouts/BaseLayout.astro website/tests/rendering.test.ts
git commit -m "feat(website): add agent and Lean profile guides"
```

### Task 5: UNKNOWN visual language, boundary explorer, share card, and embed

**Files:**
- Create: `website/src/components/EvidenceBoundary.astro`
- Create: `website/scripts/generate-social-card.mjs`
- Create: `website/public/social/records/mg-l4yaml-source-check-20261010-v1.png`
- Modify: `website/src/components/StatusTag.astro`
- Modify: `website/src/pages/index.astro`
- Modify: `website/src/components/RecordDetail.astro`
- Modify: `website/src/pages/developers.astro`
- Modify: `website/src/styles/global.css`
- Modify: `website/package.json`
- Modify: `website/tests/rendering.test.ts`

**Interfaces:**
- Consumes: current validated record and catalogue entry.
- Produces: `EvidenceBoundary` with `record: QualifiedRecord`; `StatusTag` supports `superseded` and `revoked` tones and renders a decorative glyph plus visible label; social-card generator supports `--check`.

- [ ] **Step 1: Add failing tests for status semantics and the boundary explorer**

Assert each status includes visible text and an `aria-hidden` glyph; the homepage says “Receipts for machine claims”, no longer says “record 001”, shows the exact bounded metrics and explicit UNKNOWN axes, accepts no user input, and links to `/agents/`. Assert record metadata references the 1200×630 social card and badge instructions call it scoped rather than universal.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `cd website && npm run build && npx vitest run tests/rendering.test.ts`

Expected: FAIL on the missing explorer, glyphs, social image, and updated copy.

- [ ] **Step 3: Implement the status component and evidence-derived boundary explorer**

Use a restrained text-and-symbol system with a distinct UNKNOWN treatment, responsive ordered layers, and no simulated execution. Render all figures from `QualifiedRecord`; do not expose individual case replay because the immutable record contains aggregate evidence rather than all 48 case transcripts.

- [ ] **Step 4: Generate and bind the deterministic social card**

Generate a 1200×630 PNG from catalogue and record values using Sharp. Include the full record ID, a readable shortened digest, `WARRANTED · BOUNDED`, `48/48`, and an explicit UNKNOWN boundary. Add `generate:social` and `check:social` scripts; `--check` must fail if committed bytes drift.

- [ ] **Step 5: Document the existing scoped badge embed**

Add exact Markdown and HTML examples that link the badge to `/records/mg-l4yaml-source-check-20261010/v1/`. State that it warrants only the pinned finite observation and is not a universal truth badge.

- [ ] **Step 6: Run presentation checks**

Run: `cd website && npm run generate:social && npm run check:social && npm run check && npm run build && npm run test:rendering && npm run check:html`

Expected: PASS; social-card check is deterministic and the site remains usable without client-side JavaScript.

- [ ] **Step 7: Commit the public evidence experience**

```bash
git add website/src/components website/src/pages website/src/styles/global.css website/scripts/generate-social-card.mjs website/public/social website/package.json website/tests/rendering.test.ts
git commit -m "feat(website): expose evidence boundaries for agents"
```

### Task 6: Cross-surface qualification and independent consumer

**Files:**
- Modify: `website/tests/consumer.mjs`
- Modify: `website/scripts/check-built-site.mjs`
- Modify: `website/tests/contracts.test.ts`
- Modify: `website/tests/rendering.test.ts`
- Modify: `website/package.json`
- Modify: `website/vercel.json`
- Modify: `vercel.json`
- Modify: `.github/workflows/mathgraph-org-v1.yml`

**Interfaces:**
- Consumes: all static contracts and versioned routes.
- Produces: a qualification suite that proves discovery → catalogue → digest → bounded consumption without importing verifier implementation.

- [ ] **Step 1: Extend the consumer test and make it fail against the old flow**

Fetch `/.well-known/mathgraph.json`, follow its catalogue URL, select V1, fetch the immutable record, recompute the canonical digest, and accept only the exact supported finite goal. Assert `UNKNOWN` for wrong source pin, wrong suite pin, unsupported goal, unknown record, unknown version, altered record, and unknown extension type.

- [ ] **Step 2: Extend built-site integrity assertions**

Check the sidecar and evidence digests, cross-surface status/metrics equality, canonical versioned URLs, discovery resources, social card dimensions, scoped badge link, forbidden language, and preservation of all qualified publisher bytes.

- [ ] **Step 3: Update Vercel policies and CI paths**

Keep existing permanent API redirects. Add immutable caching for versioned schemas, versioned sidecars, social cards, and immutable record pages; give `/records/index.json`, `/llms.txt`, and the well-known manifest short revalidation. Keep root and website Vercel policies identical. Update CI push/path filters for the active feature branch and design/plan inputs without weakening evidence-integrity regeneration.

- [ ] **Step 4: Run the entire qualification suite**

Run: `cd website && npm ci && npm run qualify`

Expected: Astro check 0 errors; catalogue, record, contract, and rendering tests green; built-site and resolver checks green; HTML and links green; independent consumer reports exact `WARRANTED_BOUNDED` plus all negative cases as `UNKNOWN`; client assets remain below 100 kB.

- [ ] **Step 5: Verify repository cleanliness and immutable asset hashes**

Run: `git diff --check && shasum -a 256 website/src/data/l4yaml-record.json website/public/evidence/mg-l4yaml-source-check-20261010/record.json website/public/evidence/mg-l4yaml-source-check-20261010/evidence.json`

Expected: no whitespace errors; both record files retain their established bytes; evidence SHA-256 remains `03b4bfff642c097757c88f12b578e2d903a999a4949393aefb8c91609ce74c63`.

- [ ] **Step 6: Commit the qualification expansion**

```bash
git add website/tests website/scripts/check-built-site.mjs website/package.json website/vercel.json vercel.json .github/workflows/mathgraph-org-v1.yml
git commit -m "test(website): qualify agent record contracts"
```

### Task 7: Visual review, pull request, preview, and production promotion

**Files:**
- Modify: `website/qa/screenshots/home-desktop-1440.png`
- Modify: `website/qa/screenshots/home-tablet-768.png`
- Modify: `website/qa/screenshots/home-mobile-390.png`
- Modify: `website/qa/screenshots/record-desktop-1440.png`
- Modify: `website/qa/screenshots/record-mobile-390.png`
- Create: `website/qa/screenshots/agents-desktop-1440.png`
- Create: `website/qa/screenshots/agents-mobile-390.png`
- Create: `website/qa/screenshots/record-v1-mobile-390.png`
- Modify: `website/README.md`

**Interfaces:**
- Consumes: the fully qualified static build.
- Produces: review evidence, pushed branch, draft PR, protected preview, and—only after every gate passes—the production deployment at `https://mathgraph.org`.

- [ ] **Step 1: Start the built site and capture required viewports**

Run the production preview and capture 1440px desktop, 768px tablet, and 390px mobile views for the homepage, Agents page, record index, unversioned record, versioned record, Lean profile, and developer guide.

- [ ] **Step 2: Perform and record the visual/accessibility review**

Check typography, alignment, navigation wrapping, keyboard focus, status glyph labels, boundary-explorer reading order, tables, code overflow, social metadata, empty/missing routes, and browser console output. Fix defects through focused failing tests and repeat `npm run qualify` after any code change.

- [ ] **Step 3: Document population and deployment workflows**

Update `website/README.md` with the exact record-package files, schema adapter requirement, digest update commands, qualification command, preview process, and the prohibition on metadata-only warrant promotion.

- [ ] **Step 4: Commit visual evidence and documentation**

```bash
git add website/qa/screenshots website/README.md
git commit -m "docs(website): document record publication workflow"
```

- [ ] **Step 5: Push the feature branch and create or update the draft pull request**

Push without force. Describe implemented routes, immutable-record handling, exact local test results, screenshots, preview URL, production intent, and remaining limitations. If the branding PR is still open, make the dependency explicit and use a stacked base until it merges.

- [ ] **Step 6: Wait for GitHub and Vercel preview qualification**

Require green website and evidence-integrity jobs. Use authenticated Vercel tooling to verify the protected preview's HTML plus `/llms.txt`, `/.well-known/mathgraph.json`, `/records/index.json`, schemas, versioned record, immutable JSON, and social card.

- [ ] **Step 7: Promote the exact qualified preview to the main URL**

Use Vercel's normal promotion mechanism for the already-qualified deployment; do not edit Namecheap DNS, nameservers, MX, SPF, DKIM, DMARC, or unrelated Vercel settings, and do not merge `main` unless separately authorized by the repository workflow.

- [ ] **Step 8: Verify production and prepare rollback evidence**

Check `https://mathgraph.org` for the exact SEO title, canonical URLs, all human routes, all discovery resources, immutable record hashes, HTTPS, console cleanliness, and mobile layout. If any production response differs from the qualified preview, immediately roll back to the prior Vercel deployment and report the mismatch.

- [ ] **Step 9: Deliver the exact release report**

Report branch, full commit, draft PR, production and preview URLs, routes, local and CI results, evidence-integrity hashes, screenshot paths, deferred features, and whether any step still requires repository-owner action.
