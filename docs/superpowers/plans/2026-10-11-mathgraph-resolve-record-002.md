# MathGraph Resolve Record 002 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove that the qualified Living Warrants snapshot can be independently replayed offline, then publish it as MathGraph Resolve record 002 with one reusable producer kernel and a read-only, precomputed graph explorer.

**Architecture:** Preserve the qualified snapshot as immutable authority, extract its Python reclosure algorithm into a typed fail-closed producer kernel, and independently reimplement the declared Resolve v1 semantics in a standard-library consumer that runs with no network and no MathGraph application imports. Only after that replay qualifies, extend the website catalogue through a schema-specific adapter and render canonical precomputed scenarios without duplicating resolution logic in the browser.

**Tech Stack:** Python 3.12 standard library plus pytest/unittest, OS/container network isolation, Astro 7, TypeScript 6, Vitest, JSON Schema/Ajv, minimal browser JavaScript, Vercel protected preview.

**Spec:** `docs/superpowers/specs/2026-10-11-mathgraph-resolve-record-002-design.md`

## Global Constraints

- Integration base is exact deployed commit `93850c7d66740699e8ad52452d1fe9bd38a4fc51`.
- Record 001 immutable assets and canonical digest `f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb` must not change.
- Record 002 source bytes must remain SHA-256 `0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87`; its canonical payload digest remains `b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41`.
- `UNKNOWN`, `STALE`, `WARRANTED_BOUNDED`, lifecycle, maturity, and action policy remain distinct.
- Browser code displays precomputed outcomes and must not implement warrant resolution.
- Historical and synthetic scenario data must be structurally and visibly separate.
- Unknown schemas, source pins, versions, relations, and object types fail closed.
- MathGraph applications may depend on the protocol; the protocol and offline replay must not depend on MathGraph applications, hosted services, LLMs, or the website.
- P0 website catalogue and UI integration is blocked until the standalone consumer derives the qualified outcomes under enforced network isolation.
- The offline trust-policy digest is supplied separately from the bundle; bundle and record self-hashes are integrity checks, not publisher authentication.
- Offline replay establishes a pinned historical snapshot only. Current applicability and freshness remain `UNKNOWN` or `NOT_CHECKED` absent authenticated current-state evidence.
- No production promotion or DNS/mail/registrar change is authorized by this plan.

## Review Focus

- A valid-looking record 002 with altered bytes or a recomputed self-hash must be rejected by the external pinned digest.
- A withdrawn documentary receipt must not refute a formal claim or cross the source/formal boundary.
- Multiple routes must preserve support until every independent route is unavailable.
- A cycle with no admitted evidence root must remain `UNKNOWN`.
- Client selection must never show a state absent from the immutable scenarios artifact.
- The independent consumer must recompute outcomes from claims, receipts, routes, and withdrawals; producer-reported status tables are assertions to compare, never resolution authority.
- Synthetic alternative support and refutation fixtures must remain outside the historical record; `REFUTED` requires an actually checked, appropriately scoped refutation witness.

---

### Task 1: Reconcile and import the qualified Resolve authority

**Files:**
- Create: `docs/mathgraph_p0_authority_report_2026-10-11.md`
- Create from qualified lineage: `.github/workflows/mathgraph-living-warrants-v1.yml`
- Create from qualified lineage: `evidence/living_warrant_openai_jpl_20261010.json`
- Create from qualified lineage: `mathgraph_check/living_warrants.py`
- Create from qualified lineage: `tests/test_mathgraph_living_warrants_v1.py`

**Interfaces:**
- Consumes: deployed commit `93850c7d…`, producer commit `040456fc…`, RealityGraph commit `9b3189a…`.
- Produces: exact qualified snapshot and source implementation available on the P0 branch; auditable authority report.

- [ ] **Step 1: Import the ten qualified #151 commits in order**

Cherry-pick `b99cdc16^..040456fc` onto the P0 branch; resolve only genuine path conflicts and preserve the final four-file diff exactly.

- [ ] **Step 2: Verify immutable source identity**

Run `wc -c` and `shasum -a 256` on the snapshot and compare it byte-for-byte with `040456fc:evidence/living_warrant_openai_jpl_20261010.json`.

- [ ] **Step 3: Write the authority report**

Record the exact production deployment, main/#153/#154/#151 states, producer and consumer commits/runs, immutable hashes, qualification boundary, rollback point, and P0 integration order. Distinguish control-plane evidence from GitHub deployment metadata.

- [ ] **Step 4: Run existing source-independent graph tests**

Run `python -m pytest tests/test_mathgraph_living_warrants_v1.py -k 'not RealSourceTests' -q` and record skipped fixture-bound coverage separately.

- [ ] **Step 5: Commit**

Commit the imported authority and report without modifying record 001.

### Task 2: Extract and qualify the common warrant-resolution kernel

**Files:**
- Create: `mathgraph_check/warrant_resolution.py`
- Create: `tests/test_mathgraph_warrant_resolution_core.py`
- Modify: `mathgraph_check/living_warrants.py`
- Modify: `tests/test_mathgraph_living_warrants_v1.py`

**Interfaces:**
- Consumes: record 002's existing `Claim`, `Receipt`, `Route`, `reclose`, and `compare_snapshots` behavior.
- Produces: `resolve_graph(...) -> ResolutionSet` and typed kernel objects; compatibility exports for historical producer code.

- [ ] **Step 1: Write failing kernel tests**

Cover conjunctive premises, surviving alternative routes, localized withdrawal, rootless cycles, unknown references, duplicate identities, documentary/formal boundary violations, unqualified relations, and no implicit refutation.

- [ ] **Step 2: Run the tests and confirm expected import/API failures**

Run `python -m pytest tests/test_mathgraph_warrant_resolution_core.py -q`.

- [ ] **Step 3: Implement the minimal typed kernel**

Define immutable typed objects and deterministic least-fixed-point resolution. Qualified relations may change kind/scope only when their named verifier and evidence receipts are admitted; unsupported relations fail closed.

- [ ] **Step 4: Adapt the historical producer**

Re-export compatible names from `living_warrants.py`, regenerate the snapshot in tests, and assert no byte or digest change.

- [ ] **Step 5: Run focused and historical tests**

Run both kernel and source-independent Living Warrants suites, then verify snapshot SHA-256.

- [ ] **Step 6: Commit**

Commit kernel extraction only after the historical snapshot identity is proven unchanged.

### Task 3: Publish record 002 and deterministic scenario artifacts

**Files:**
- Create: `scripts/publish_mathgraph_resolve_v1.py`
- Create: `tests/test_mathgraph_resolve_publication_v1.py`
- Create: `website/public/evidence/mg-living-warrant-openai-jpl-20261010/record.json`
- Create: `website/public/evidence/mg-living-warrant-openai-jpl-20261010/scenarios.json`
- Create: `website/src/data/resolve-record.json`
- Create: `website/src/data/resolve-scenarios.json`

**Interfaces:**
- Consumes: `resolve_graph` and exact record 002 snapshot.
- Produces: canonical, byte-checked published record and scenario data with separate `PUBLISHED_RECORD` and `SYNTHETIC_CONFORMANCE` sections.

- [ ] **Step 1: Write failing publication tests**

Assert exact snapshot bytes, canonical scenario output, before/after outcomes, alternative-route preservation, localized invalidation, cycle `UNKNOWN`, and rejection of altered source bytes.

- [ ] **Step 2: Run tests and confirm publisher/artifacts are missing**

Run `python -m pytest tests/test_mathgraph_resolve_publication_v1.py -q`.

- [ ] **Step 3: Implement the minimal deterministic publisher**

Generate all public scenarios from the Python kernel, include provenance and maturity fields, and serialize canonical UTF-8 JSON with one trailing newline.

- [ ] **Step 4: Generate and copy publication assets**

Write website source/public copies and verify record copies are byte-identical to the qualified snapshot.

- [ ] **Step 5: Run publication and kernel tests**

Run the two focused suites and digest checks.

- [ ] **Step 6: Commit**

Commit generator, tests, and generated small JSON assets together.

### Task 4: Qualify standalone offline Resolve replay

**Files:**
- Create: `conformance/resolve_v1/consumer.py`
- Create: `conformance/resolve_v1/test_consumer.py`
- Create: `conformance/resolve_v1/README.md`
- Create: `conformance/resolve_v1/trust-policy.json`
- Create: `conformance/resolve_v1/fixtures/bundle.json`
- Create: `scripts/package_mathgraph_resolve_v1.py`
- Create: `.github/workflows/mathgraph-resolve-offline-v1.yml`

**Interfaces:**
- Consumes: an immutable canonical bundle plus a separately hash-pinned trust policy.
- Produces: a deterministic historical replay report and fail-closed conformance result without importing or calling any MathGraph application.

- [ ] **Step 1: Write failing independent-consumer tests**

Cover strict duplicate-key parsing, exact bundle/member pins, the seven historical outcomes, deterministic output, and a physical-import audit proving the consumer does not load `mathgraph_check`, publisher, website, Check, Discover, or Develop code.

- [ ] **Step 2: Add adversarial and synthetic conformance tests**

Reject mutated bytes, wrong commits/digests/verifiers/assumptions, recomputed self-hashes, replaced policies, forged producer statuses, unsupported schema/type/relation/transport, ambiguous canonical fields, unsupported generalization, and withdrawn evidence replayed as current. Separately test surviving alternative support, total support loss, dependent descendants, unrelated claims, rootless cycles, missing premises, exact scope matching, and a checked finite-countermodel refutation.

- [ ] **Step 3: Implement the deterministic bundle packager**

Package the exact 5,290-byte record, exact OpenAI notice bytes, exact public JPL record bytes, and precise provenance into canonical JSON without adding resolution logic. Pin every member length/hash and keep the policy outside the bundle.

- [ ] **Step 4: Implement the minimal independent consumer**

Use only the Python standard library. Strictly validate fields, source/receipt identities, scopes, references, and unsupported extensions; independently compute the least fixed point and compare it with, but never trust, published status claims.

- [ ] **Step 5: Emit distinct temporal semantics**

Report historical evidence qualification, historical resolution, current applicability, freshness, lifecycle, and action authorization separately. Offline current applicability must remain `UNKNOWN`/`NOT_CHECKED`.

- [ ] **Step 6: Prove isolation locally and in dedicated CI**

Copy only consumer source, bundle, and policy to the isolated replay directory; run `python -I -S`. Deny network with an enforced macOS sandbox locally and a network-disabled Linux container or namespace in CI. Include a negative connectivity probe; missing isolation is a failure, never a skip.

- [ ] **Step 7: Review, commit, push, and require green P0 CI**

Run the standalone suite, focused producer parity suite, digest checks, and `git diff --check`. After task review, push the isolated branch and do not begin catalogue/UI integration until the dedicated workflow is green.

### Task 5: Extend the record catalogue with a fail-closed record 002 adapter

**Files:**
- Create: `website/public/schemas/record-index-v2.schema.json`
- Create: `website/public/schemas/living-warrant-snapshot-v1.schema.json`
- Create: `website/public/schemas/resolve-scenarios-v1.schema.json`
- Create: `website/src/lib/resolve-record.ts`
- Create: `website/src/lib/resolve-record.test.ts`
- Modify: `website/src/lib/catalog.ts`
- Modify: `website/src/lib/catalog.test.ts`
- Modify: `website/src/data/record-index.json`
- Create: `website/public/records/mg-living-warrant-openai-jpl-20261010/v1/metadata.json`

**Interfaces:**
- Consumes: exact record/scenario assets from Task 3.
- Produces: `PublishedRecordPackage` discriminated union and schema-specific record 002 validation.

- [ ] **Step 1: Write failing TypeScript tests**

Cover the valid adapter, altered bytes, recomputed self-hash, forged resolution status, unsupported record kind/schema, unknown version, presentation authority fields, and record 001 regression.

- [ ] **Step 2: Run data tests and confirm record 002 support is absent**

Run `npm run test:data` with Node 24.

- [ ] **Step 3: Add v2 schemas and discriminated catalogue types**

Keep v1 schemas unchanged. Dispatch validation by exact `record_kind` and `record_schema`; retain record 001's existing hard-coded authority checks.

- [ ] **Step 4: Add record 002 entry and presentation sidecar**

Use the immutable historical ID, permanent v1 URL, exact hashes, lifecycle `CURRENT`, maturity `BOUNDED_QUALIFIED`, and explicit unknowns.

- [ ] **Step 5: Run data tests and schema checks**

Run `npm run test:data` and `npm run check`.

- [ ] **Step 6: Commit**

Commit the catalogue version and adapter as one reviewable change.

### Task 6: Build the Resolve pages and read-only graph explorer

**Files:**
- Create: `website/src/components/ResolveExplorer.astro`
- Create: `website/src/components/ResolveRecordDetail.astro`
- Create: `website/src/scripts/resolve-explorer.ts`
- Create: `website/src/pages/resolve/index.astro`
- Modify: `website/src/pages/records/[id]/[version].astro`
- Modify: `website/src/pages/records/index.astro`
- Modify: `website/src/components/RecordSummary.astro`
- Modify: `website/src/layouts/BaseLayout.astro`
- Modify: `website/src/pages/index.astro`
- Modify: `website/src/styles/global.css`
- Modify: `website/tests/rendering.test.ts`
- Modify: `website/tests/contracts.test.ts`

**Interfaces:**
- Consumes: validated union packages and scenarios artifact.
- Produces: static `/resolve/`, permanent record 002 detail, accessible scenario selection, updated homepage cycle and navigation.

- [ ] **Step 1: Write failing rendering and contract tests**

Assert route generation, exact historical caveats, static/scenario identity, synthetic-label separation, four status axes, accessible controls, no inline scenario manufacture, and homepage cycle copy.

- [ ] **Step 2: Run focused tests and confirm missing routes/components**

Run rendering and contract tests.

- [ ] **Step 3: Implement server-rendered pages and default graph**

Render the qualified post-withdrawal state without JavaScript and dispatch record detail by `record_kind`.

- [ ] **Step 4: Implement display-only interaction**

Fetch the same immutable scenarios JSON, select only existing scenario IDs, update labels/tables/graph classes, and fail closed to the static default on any error.

- [ ] **Step 5: Update homepage and grouped navigation**

Introduce the four-pillar cycle while keeping Inspect evidence primary and Protocol secondary. Add Resolve to primary navigation without exposing unimplemented registry/API features as working.

- [ ] **Step 6: Run focused tests, Astro diagnostics, and build**

Run rendering/contracts, `npm run check`, and `npm run build`.

- [ ] **Step 7: Commit**

Commit the public Resolve experience and tests.

### Task 7: Complete protocol, developer, security, CI, and discovery contracts

**Files:**
- Modify: `website/src/pages/protocol/index.astro`
- Modify: `website/src/pages/developers/index.astro`
- Modify: `website/src/pages/agents/index.astro`
- Modify: `website/src/pages/llms.txt.ts`
- Modify: `website/public/.well-known/mathgraph.json`
- Modify: `website/src/pages/sitemap.xml.ts`
- Create: `docs/mathgraph_resolve_v1_threat_model.md`
- Create: `docs/mathgraph_resolve_v1_reproduction.md`
- Modify: `.github/workflows/mathgraph-org-v1.yml`
- Modify: `website/scripts/check-built-site.mjs`
- Modify: `website/tests/consumer.mjs`

**Interfaces:**
- Consumes: P0 record and routes.
- Produces: discoverable machine contracts, precise threat/reproduction docs, branch-isolated CI qualification, independent HTTP consumption of both records.

- [ ] **Step 1: Write failing discovery and consumer tests**

Assert new URLs, v2 schema references, exact record 002 digest, wrong-version/tampering rejection, and truthful `public_resolver: NOT_DEPLOYED` capability.

- [ ] **Step 2: Run focused tests and confirm missing contracts**

Run contracts, built-site, and consumer checks.

- [ ] **Step 3: Update protocol and discovery surfaces**

Document implemented kernel objects and boundaries; keep generalized transports, hosted APIs, signatures, Discover, Develop, and Capabilities labeled proposed/experimental.

- [ ] **Step 4: Add threat model and reproduction guide**

Cover trust roots, replay, source substitution, self-hash limits, durable retention, security reporting, and exact producer/consumer commands and pins.

- [ ] **Step 5: Extend CI safely**

Add the P0 branch/paths and record 002 publication tests without broadening unrelated research workflow triggers. Keep record 001 qualification gates intact.

- [ ] **Step 6: Run focused consumer/discovery checks**

Run contracts, build, built-site, and isolated consumer tests.

- [ ] **Step 7: Commit**

Commit documentation and qualification integration.

### Task 8: Full qualification, visual review, protected preview, and draft PR

**Files:**
- Create: `website/qa/screenshots/resolve-desktop-1440.png`
- Create: `website/qa/screenshots/resolve-tablet-768.png`
- Create: `website/qa/screenshots/resolve-mobile-390.png`
- Create: `website/qa/screenshots/resolve-record-desktop-1440.png`
- Create: `website/qa/screenshots/resolve-record-mobile-390.png`

**Interfaces:**
- Consumes: complete P0 branch.
- Produces: fresh qualification evidence, protected Vercel preview, and reviewable draft PR; no production promotion.

- [ ] **Step 1: Run complete Python qualification**

Run kernel/publication suites, the historical Living Warrants source qualification with its exact fixtures, and record 001 publisher qualification. Preserve precise errors if archived fixtures are unavailable.

- [ ] **Step 2: Run complete website qualification**

Run `npm ci`, `npm run qualify`, `npm audit --json`, and digest/parity checks with Node 24. Rerun loopback-bound checks with scoped permission when sandboxing alone blocks them.

- [ ] **Step 3: Perform rendered visual/accessibility review**

Inspect 1440 px, 768 px, and 390 px outputs; assert no overflow, one main landmark, one H1, keyboard-operable controls, readable graphs/tables, and no browser console errors.

- [ ] **Step 4: Request task and whole-branch review**

Resolve all Critical/Important findings and re-run affected tests.

- [ ] **Step 5: Push branch and create protected preview**

Push `codex/mathgraph-resolve-record-002`, create a draft PR stacked on #154, and deploy/identify a protected Vercel preview from the exact reviewed commit.

- [ ] **Step 6: Smoke-test preview**

Verify HTTP status, hashes, record/catalog parity, cache headers, primary routes, and rollback readiness. Do not promote production.

- [ ] **Step 7: Publish the unresolved-obligations report in the PR**

List implemented/qualified, implemented-awaiting-qualification, experimental, proposed, unknown, and rejected-by-evidence items with exact CI/deployment URLs.
