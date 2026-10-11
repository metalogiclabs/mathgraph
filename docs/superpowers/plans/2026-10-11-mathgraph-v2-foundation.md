# MathGraph V2 Foundation Implementation Plan

> **For Codex:** Execute this plan with subagent-driven development and strict test-first steps. Production, DNS, immutable evidence bytes, and trust-policy authority are out of scope.

**Goal:** Deliver a protected-preview release candidate that adds an independently replayable supported import workflow, outcome-oriented product navigation, canonical object projections, and a real typed knowledge map while preserving all PR #156 contracts and evidence.

**Architecture:** Keep Astro static and dependency-light. Add one standard-library independent import consumer and a browser-only local recognizer. Project existing records and capability contracts into an internal TypeScript view model rather than creating a new protocol ontology. Render declared relations with accessible HTML/SVG and minimal client JavaScript. All portable projections disclaim authority and retain exact source identities.

**Technology:** Python 3.11+, pytest, JSON Schema Draft 2020-12, Astro 7, TypeScript 6, Vitest, native SVG/Web Crypto, Vercel protected preview.

---

## Task 1: Qualify the independent supported-import contract

**Files:**

- Create: `protocol/schemas/import-result-v1.schema.json`
- Create: `website/public/schemas/import-result-v1.schema.json`
- Create: `conformance/import_v1/__init__.py`
- Create: `conformance/import_v1/consumer.py`
- Create: `conformance/import_v1/test_consumer.py`
- Create: `conformance/import_v1/fixtures/record.json`
- Create: `conformance/import_v1/fixtures/trust-policy.json`
- Create: `conformance/import_v1/fixtures/result.json`
- Create: `conformance/import_v1/README.md`
- Create: `scripts/mathgraph_import_v1.py`
- Modify: `.github/workflows/mathgraph-protocol-conformance-v1.yml`
- Modify: `website/tests/contracts.test.ts`

### Step 1: Write failing independent-consumer tests

Assert strict bounded parsing, deterministic output, and derivation of the exact
L4YAML record result without importing website or producer implementation.
Include source/test commit and digest, verifier, assumptions, exact finite scope,
lifecycle, freshness, applicability, authorization, and explicit UNKNOWNs.

Add mutations for source bytes, source/test commit, content digest, scope,
generalization, verifier, assumption context, status injection, authorization,
duplicate keys, non-finite values, unsupported schema/type, and oversize input.
Also reject a substituted policy even when self-consistently rehashed and reject
presentation/browser/projection outputs presented under the legitimate policy,
including copies of valid record identifiers and digests.

Run:

```bash
python -m pytest conformance/import_v1/test_consumer.py -q
```

Expected: FAIL because the consumer and schema are absent.

### Step 2: Implement the smallest independent consumer

Use the standard library and a separately declared exact trust policy. Validate
and derive; never accept a producer verdict as authority. Return `UNKNOWN` or a
typed error for unsupported goals and current-state questions whose freshness
was not checked.

The output must carry a fixed independent-offline processing mode, a consumer
authority boundary limited to exact historical receipt/policy validation, and
separate `NOT_PERFORMED` values for original kernel/proof and source-suite
replay. The receipt's historical native-verifier authority remains distinct.

### Step 3: Freeze deterministic fixtures and CLI output

The fixture record must be byte-identical to the existing public record. The
CLI accepts a local path only, emits the deterministic result, and performs no
network access.

### Step 4: Run focused and regression gates

```bash
python -m pytest conformance/import_v1 conformance/protocol_v1 conformance/resolve_v1 -q
cd website && npm run test:contracts
```

### Step 5: Commit

```bash
git commit -m "Add independent supported import contract"
```

## Task 2: Add non-authoritative object and map projections

**Files:**

- Create: `website/src/lib/object-projections.ts`
- Create: `website/src/lib/object-projections.test.ts`
- Create: `website/src/lib/knowledge-map.ts`
- Create: `website/src/lib/knowledge-map.test.ts`
- Create: `website/src/data/object-projections.ts`
- Modify: `website/package.json`

### Step 1: Write failing projection tests

Test adapters for record 001, Resolve record 002, and the finite capability
contract. Require separate status axes, exact source identities, explicit
unknowns, and only declared typed relations. Assert deterministic ordering,
node/edge limits, no inferred equivalence, unsupported-kind refusal, and an
export with `authority: NONE` plus its source digests.

The two materially different extension domains are record evidence and a
portable capability contract.

Add a checked two-domain matrix for source contract, verifier authority,
assumptions, lifecycle, replay boundary, preserved unknowns, and unsupported
semantics. Prove that adding or declining the capability adapter leaves record
001 unchanged, and exercise one unsupported critical extension.

### Step 2: Implement presentation-only view models

Define `ObjectProjection`, `RelationProjection`, and `KnowledgeMapProjection`
inside the website. Do not publish them as evidence/protocol schemas or change
the source objects. Keep adapter functions explicit by source contract/version.

Define a small versioned projection-export shape with directed typed edges,
valid endpoints, provenance, selection/filter context, source pins,
completeness/truncation, and `authority: NONE`. Add a separate read-only reader
that declines unsupported versions/critical extensions and cannot feed the
evidence importer.

### Step 3: Verify exact source parity

Test all projected values against imported committed JSON, not copied literals.
Verify record 001/002 bytes and digests remain unchanged.

### Step 4: Commit

```bash
git commit -m "Project qualified objects and relations"
```

## Task 3: Build the safe import workbench

**Files:**

- Create: `website/src/components/ImportWorkbench.astro`
- Create: `website/src/scripts/import-workbench.ts`
- Create: `website/src/pages/verify/index.astro`
- Modify: `website/src/pages/check.astro`
- Modify: `website/src/styles/global.css`
- Modify: `website/tests/rendering.test.ts`
- Modify: `website/tests/contracts.test.ts`

### Step 1: Write failing rendering and browser-contract tests

Assert a local file control, accepted type/size disclosure, no URL input, no
execution claim, exact supported artifact link, UNKNOWN state, source/evidence/
scope output regions, replay command, and portable result download.

Add one integration fixture and browser scenario that carries the exact record
identity, scope, evidence reference, and unknowns through Import, Interpret,
Check, Resolve, Explore, and Export. Resolve may select only the existing
qualified record-bound outcome; an unsupported route must remain UNKNOWN.

### Step 2: Implement local recognition

Read only a bounded local JSON file. Parse, validate the supported shape,
calculate the relevant digest with Web Crypto, compare exact pins, and render a
non-authoritative consumer preview. Unsupported or changed inputs fail closed.
No network requests or code execution are permitted.

The browser download declares its processing mode and `authority: NONE`,
preserves original replay as not performed, and cannot satisfy the independent
import contract. Prefer exact raw-byte recognition before semantic parsing so
duplicate/non-finite/encoding variants are never interpreted as the supported
artifact.

### Step 3: Connect Check without changing its authority

Embed or link the same workbench on `/check/`. Preserve all current L4YAML
boundary language and evidence links.

### Step 4: Verify unit, rendering, and static builds

```bash
cd website && npm run test:unit && npm run build
```

### Step 5: Commit

```bash
git commit -m "Add fail-closed local verification workbench"
```

## Task 4: Implement outcome navigation and Homepage V2

**Files:**

- Create: `website/src/pages/explore/index.astro`
- Create: `website/src/pages/build/index.astro`
- Modify: `website/src/layouts/BaseLayout.astro`
- Modify: `website/src/pages/index.astro`
- Modify: `website/src/styles/global.css`
- Modify: `website/tests/rendering.test.ts`
- Modify: `website/scripts/check-built-site.mjs`

### Step 1: Write failing navigation/homepage tests

Require Explore, Verify, Build, and Developers; an accessible mobile
disclosure; preserved old routes; the exact V2 headline and proposition; a
working import component; three outcome journeys; the real JPL example; map,
capability, independent-verification, quick-start, and scoped-future sections.
Require each outcome group to expose the correct active state for contained
routes, including Discover, Develop, and Capabilities.

### Step 2: Implement the compact navigation system

Use semantic links and a keyboard-operable disclosure with progressive
enhancement. Keep header density low and retain the GitHub/source affordance.

### Step 3: Rebuild the homepage from existing evidence

Use the actual record/capability projections. No decorative or invented
metrics, endorsements, or implied universal support.

### Step 4: Verify responsive markup and route stability

Run rendering/link/build checks before committing.

### Step 5: Commit

```bash
git commit -m "Reframe MathGraph around verifiable outcomes"
```

## Task 5: Build the object explorer and typed knowledge map

**Files:**

- Create: `website/src/components/ObjectDetail.astro`
- Create: `website/src/components/KnowledgeMap.astro`
- Create: `website/src/scripts/knowledge-map.ts`
- Create: `website/src/pages/objects/index.astro`
- Create: `website/src/pages/objects/[slug].astro`
- Modify: `website/src/pages/resolve/index.astro`
- Modify: `website/src/pages/records/index.astro`
- Modify: `website/src/pages/records/[id]/[version].astro`
- Modify: `website/src/styles/global.css`
- Modify: `website/tests/rendering.test.ts`

### Step 1: Write failing view tests

Require identity/type, source, attribution, evidence, verifier, assumptions,
scope, all status axes, declared relations, lineage, replay, exports, and
unknowns. Require accessible node controls, synchronized detail panel, typed
edge list, filtering, dependency traversal, alternative support display,
keyboard use, mobile fallback, node limit/truncation, and subgraph export.
Export tests must retain edge direction/type/endpoints/provenance,
selection/filter context, source pins, and completeness/truncation state.

### Step 2: Implement the reusable detail view

Render only fields present in the projection. Missing values are `UNKNOWN`, not
invented prose. Link every projected field back to its source object/export.

### Step 3: Implement the dependency map

Render semantic HTML first and an SVG projection second. Use declared edges
only. Selection and filters update both views. Export the selected bounded
subgraph with `authority: NONE`.

### Step 4: Integrate with Resolve and records

Keep the existing qualified Resolve scenarios and static fallback. Add links
between the common graph/object view and historical record views without
altering record bytes.

### Step 5: Commit

```bash
git commit -m "Add canonical object explorer and knowledge map"
```

## Task 6: Finish searchable catalogues and executable documentation

**Files:**

- Create: `website/src/components/CatalogueFilter.astro`
- Create: `website/src/scripts/catalogue-filter.ts`
- Modify: `website/src/pages/records/index.astro`
- Modify: `website/src/pages/capabilities/index.astro`
- Modify: `website/src/pages/agents.astro`
- Modify: `website/src/pages/developers.astro`
- Modify: `website/src/pages/protocol.astro`
- Modify: `website/src/pages/discover/index.astro`
- Modify: `website/src/pages/develop/index.astro`
- Modify: `website/src/pages/records/[id]/[version].astro`
- Modify: `website/src/pages/llms.txt.ts`
- Modify: `website/public/.well-known/mathgraph.json`
- Create: `website/src/pages/about.astro`
- Create: `website/src/pages/contact.astro`
- Create: `website/public/examples/resolve-consumer-v1.js`
- Create: `website/public/social/records/mg-living-warrant-openai-jpl-20261010-v1.source.svg`
- Create: `website/public/social/records/mg-living-warrant-openai-jpl-20261010-v1.png`
- Modify: `website/scripts/generate-social-card.mjs`
- Modify: `website/vercel.json`
- Modify: `website/tests/rendering.test.ts`
- Modify: `website/tests/contracts.test.ts`

### Step 1: Write failing documentation/catalogue tests

Require client-side search/filter and honest empty states, exact import/replay
commands, no hosted resolver/MCP claims, current protocol contracts, separate
CLOSE/ACT/REFINE descriptions, advisory Discover status, and explicit UNKNOWN
for the Capability Family Compiler and action authorization.

Require `/about/` and `/contact/`, a directly viewable/runnable JavaScript
consumer plus downloadable TypeScript source, a correct MIME/header smoke test,
and presentation-only social metadata for record 002 outside its evidence
digest. Keep the `www` redirect explicitly deferred as a separately authorized
production-domain action.

### Step 2: Implement lightweight catalogue controls

Use progressively enhanced HTML; catalogues remain usable without JavaScript.

### Step 3: Update agent/developer/protocol surfaces

Document commands that run in CI. Present Object, Relation, Evidence,
Resolution, and Transition as responsibilities over existing contracts, not a
new universal object format. Preserve historical schema links and machine
discovery compatibility.

Link the already-qualified unsigned in-toto external-binding workflow with its
correspondence-only and authenticity-not-checked boundaries. Do not imply that
projection export qualifies general semantic transport.

### Step 4: Commit

```bash
git commit -m "Complete V2 catalogues and developer contracts"
```

## Task 7: Reconcile authority and release documentation

**Files:**

- Modify: `docs/mathgraph_full_product_audit_2026-10-11.md`
- Create: `docs/mathgraph_v2_release_authority_2026-10-11.md`
- Create: `docs/mathgraph_v2_browser_qualification_2026-10-11.md`
- Create: `docs/mathgraph_v2_unresolved_obligations_2026-10-11.md`
- Modify: `docs/release_index.md`

### Step 1: Add evidence-linked corrections to the audit

Record production at `4edc77c…`, merged PR #156, open draft PR #157, the exact
qualified/tested status of each V2 feature, existing implementation, missing
distinction, priority, verification obligation, and smallest qualifying next
action. Do not rewrite historical evidence.

### Step 2: Document architecture and research residuals

Cover durable artifact retention, certificate-to-Lean premise discharge,
outside-owner adoption, generic semantic transport, CFC, autonomous growth,
freshness/authenticated lifecycle, and operational agent authorization.

Add a V2 extension analysis for the record-evidence and capability domains,
including semantic losses and unsupported extensions, plus a residual
disposition table for the production MIME failure, About/Contact, record 002
social metadata, mobile/active navigation, and deferred `www` redirect.

### Step 3: Commit

```bash
git commit -m "Document V2 authority and remaining obligations"
```

## Task 8: Exact-head qualification, protected preview, and review delivery

**Files:**

- Modify as required by verified failures only.
- Add screenshot evidence under `docs/assets/mathgraph-v2/` if repository policy
  permits; otherwise link exact protected preview captures in the browser report.

### Step 1: Run exact-head local qualification

Use the pinned Node 24 runtime and run:

```bash
python -m pytest conformance/protocol_v1 conformance/resolve_v1 conformance/discover_v1 conformance/capability_v1 conformance/interoperability_v1 conformance/import_v1 tests/test_mathgraph_protocol_import.py tests/test_discovery_scheduler.py tests/test_discovery_candidate_sources.py -q
cd website && npm run qualify
```

Also run repository evidence/publication tests selected from the affected paths.
Record unrelated monorepo residuals separately; never weaken a gate.

### Step 2: Conduct a separate code/security/claims review

Review exact diff for authority escalation, fabricated edges, browser-side
warrant decisions, unsafe inputs, stale links, overclaims, source parity,
accessibility, and mobile behavior. Fix findings and rerun all gates.

### Step 3: Deploy a protected Vercel preview

Deploy the exact committed head to the existing `mathgraph` project as preview
only. Do not promote or alter domains. Verify deployment protection using an
authorized mechanism.

### Step 4: Perform browser qualification

Inspect at approximately 1440, 768, and 390 pixels. Exercise import success and
mutation/unsupported paths, graph selection/filter/export, mobile navigation,
catalogue search, keyboard focus, downloads, console errors, network behavior,
headers, and cache policy. Preserve screenshots and exact observations.

Require keyboard completion of map/navigation/filter/export tasks, disclosure
focus restoration, status announcements, touch target checks, contrast,
reduced-motion behavior, and no-JavaScript fallbacks. Record total transfer,
client JavaScript, and loading measurements against the live qualified
production baseline and explain material regressions.

### Step 5: Push and open a draft PR

Push `codex/mathgraph-v2-foundation`, open a draft PR with the exact commit,
preview, evidence identity, tests, screenshots, security boundary, and residuals.
Wait for final-head CI and fix any failures without weakening controls.

### Step 6: Reconcile one exact release identity

Bind one clean final source commit to successful CI, an immutable protected
preview deployment, the browser report, screenshots, and the final review. Any
subsequent change invalidates and repeats every affected gate. If the browser
report itself is a later documentation-only commit, name the immutable preview
commit it describes and rerun document/link/CI checks on the report commit.

### Step 7: Update Research OS with the exact release-candidate checkpoint

Write only observed commit/CI/preview facts and remaining UNKNOWNs. Do not
promote the draft or change production authority.

### Step 8: Final report

Report branch/commit, draft PR, protected preview, routes, tests/CI, evidence
parity, browser evidence, implemented versus experimental/UNKNOWN, production
unchanged, and the smallest separately authorized production-promotion step.
