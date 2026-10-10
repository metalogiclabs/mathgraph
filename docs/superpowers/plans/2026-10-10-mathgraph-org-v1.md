# MathGraph.org V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and qualify a production-ready static Astro interface for MathGraph's exact L4YAML public evidence record.

**Architecture:** Integrate the qualified Python release unchanged, publish its exact generated assets under `website/`, and render every human-facing claim from a build-validated frozen JSON record. Keep the resolver local/preview-only while proving static record reuse through an isolated consumer.

**Tech Stack:** Astro, TypeScript, modern CSS, Vitest, Astro Check, HTML Validate, Linkinator, Python unittest/pytest, GitHub Actions, Vercel static hosting.

**Spec:** `docs/superpowers/specs/2026-10-10-mathgraph-org-v1-design.md`

## Global Constraints

- Preserve record ID `mg-l4yaml-source-check-20261010` and content SHA-256 `f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb`.
- Preserve qualified commit `7c1fd9be80966ece12ba455375319961194ae7f4` as evidence authority.
- Do not present the resolver as publicly deployed.
- Do not claim universal YAML correctness, source-to-formalization fidelity, JPL/NASA endorsement, general post-quantum security, or production security review.
- Keep V1 static, read-only, dependency-light, responsive, accessible, and production-domain neutral.

## Review Focus

- A rehashed but semantically altered record must fail the pinned digest gate.
- A wrong source commit, suite commit, record ID, or unsupported goal must produce `UNKNOWN` in the consumer.
- Mobile record tables and code blocks must scroll or reflow without clipping content.
- Unknown and not-requalified states must remain visible in both the HTML and JSON surfaces.
- External URLs must be exact source/run links and must not imply affiliation or endorsement.

---

### Task 1: Integrate the qualified evidence authority

**Files:**
- Create from qualified commit: `mathgraph_check/`, `tests/test_mathgraph_public_evidence_v1.py`, `.github/workflows/mathgraph-check-public-evidence-v1.yml`, `docs/mathgraph_check_public_evidence_v1.md`

**Interfaces:**
- Consumes: qualified commit `7c1fd9be80966ece12ba455375319961194ae7f4`.
- Produces: unchanged Python publisher, resolver, tests, and expected record digest.

- [ ] Verify `main` is the qualified commit's exact parent.
- [ ] Cherry-pick the qualified commit without rewriting its contents.
- [ ] Obtain the exact generated public artifact from run `38021785401` and verify its record digest.
- [ ] Run the qualified test with the exact evidence archives if available; otherwise retain the cited CI result and make local unavailability explicit.
- [ ] Commit only if integration requires a new commit beyond the preserved cherry-pick.

### Task 2: Establish the Astro shell and frozen data gate

**Files:**
- Create: `website/package.json`, `website/package-lock.json`, `website/astro.config.ts`, `website/tsconfig.json`, `website/vercel.json`
- Create: `website/src/data/l4yaml-record.json`, `website/public/evidence/mg-l4yaml-source-check-20261010/*`
- Test: `website/src/lib/evidence.test.ts`
- Create: `website/src/lib/evidence.ts`

**Interfaces:**
- Consumes: exact generated record/evidence/badge/OpenAPI files.
- Produces: `loadQualifiedRecord(): QualifiedRecord` and durable static resources.

- [ ] Write failing tests for exact ID/digest/pins/counts/unknowns and forged rehash rejection.
- [ ] Run the unit test and verify failure because the evidence loader does not exist.
- [ ] Add the minimal Astro configuration, exact lockfile, frozen assets, and typed evidence loader.
- [ ] Run unit tests and verify the gate passes.
- [ ] Commit the data and site foundation.

### Task 3: Build the design system, homepage, and record detail

**Files:**
- Create: `website/src/styles/global.css`, `website/src/layouts/BaseLayout.astro`
- Create: `website/src/components/{StatusTag,EvidenceAxis,Metric,SourceLink,CopyButton,EvidenceFlow,RecordSummary,RecordDetail}.astro`
- Create: `website/src/pages/index.astro`, `website/src/pages/records/index.astro`, `website/src/pages/records/mg-l4yaml-source-check-20261010.astro`
- Test: `website/tests/rendering.test.ts`

**Interfaces:**
- Consumes: `QualifiedRecord`.
- Produces: shared accessible UI and the primary evidence experience.

- [ ] Write failing rendering tests for route output, record agreement, navigation, headings, status scope, and prohibited universal claims.
- [ ] Run and verify failure because pages/components are absent.
- [ ] Implement the token system, shared shell, homepage, record index, and full record detail.
- [ ] Run the rendering tests and production build until green.
- [ ] Commit the primary visitor experience.

### Task 4: Derive Check, Protocol, and Developer documentation

**Files:**
- Create: `website/src/pages/check.astro`, `website/src/pages/protocol.astro`, `website/src/pages/developers.astro`, `website/src/pages/404.astro`
- Modify: `website/tests/rendering.test.ts`
- Create: `website/src/scripts/copy.ts`

**Interfaces:**
- Consumes: shared components, frozen record, qualified resolver contract, and bounded protocol research notes.
- Produces: all required public surfaces and progressive copy interaction.

- [ ] Add failing tests for all routes, capability labels, endpoint deployment caveat, and 404 state.
- [ ] Run and verify the expected missing-route failures.
- [ ] Implement the pages from the exact contracts, labeling protocol elements as implemented, experimental, or proposed.
- [ ] Add minimal progressive copy behavior with visible confirmation and no dependency.
- [ ] Run unit/rendering/build tests until green.
- [ ] Commit the completed public surface.

### Task 5: Add independent consumption and release qualification

**Files:**
- Create: `website/tests/consumer.mjs`, `website/scripts/check-built-site.mjs`
- Create: `.github/workflows/mathgraph-org-v1.yml`
- Modify: `website/package.json`

**Interfaces:**
- Consumes: built `website/dist` and the documented immutable record URL.
- Produces: exact-pin reuse result, typed `UNKNOWN` negative controls, link/accessibility/build gates, and CI evidence.

- [ ] Write the consumer test first and verify failure before the built static interface exists.
- [ ] Implement a separate-process static server/fetch consumer with literal expected pins and no MathGraph imports.
- [ ] Add built-page/JSON consistency, prohibited-claim, missing-state, and artifact-size checks.
- [ ] Add CI for clean install, type check, tests, build, HTML validation, links, and the existing Python evidence tests.
- [ ] Run every local gate and fix failures without weakening evidence assertions.
- [ ] Commit qualification infrastructure.

### Task 6: Browser QA and delivery

**Files:**
- Modify only files implicated by observed defects.
- Create: `website/README.md` with local build and preview instructions.

**Interfaces:**
- Consumes: final production build.
- Produces: visually reviewed branch, draft PR, screenshots, and preview when credentials permit.

- [ ] Read local preview guidance, start the Astro preview, and inspect 1440, 768, and 390 widths.
- [ ] Check typography, layout, navigation, focus, evidence readability, overflow, missing state, and console output.
- [ ] Fix each observed issue through a failing regression test where behavior is automatable.
- [ ] Run the complete Python and website verification suite fresh.
- [ ] Request whole-branch code review and address Critical/Important findings.
- [ ] Commit final fixes, push `website/mathgraph-org-v1`, and create a draft PR to `main`.
- [ ] Attempt a protected Vercel preview only if an existing authenticated project connection is available; never alias production.
- [ ] Report branch, commit, PR, preview status, routes, exact tests, evidence qualification, visual evidence, blockers, and the smallest production-release step.
