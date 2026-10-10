# MathGraph Modular Contracts and Interoperability Implementation Plan

> **Execution note:** This plan begins after the completed PR #155 P0 Resolve publication. It must not regenerate record 001 or 002, alter their bytes, or promote production.

**Goal:** Turn the implicit offline formats and existing research seams into independently consumable, fail-closed protocol contracts, then project only the qualified boundaries into the existing Astro site.

**Architecture:** Add a small dependency-free `mathgraph_protocol` package for strict decoding and deterministic local interfaces. Normative schemas live outside the website under `protocol/schemas/`; public schema files are byte-identical projections. Independent conformance implementations consume pinned fixtures without importing producer or website code. The Astro website remains a static consumer and documentation surface.

**Technology:** Python 3.11+ standard library, JSON Schema Draft 2020-12, pytest, Astro 7, TypeScript, Vitest/Ajv, GitHub Actions. No database, hosted execution service, arbitrary URL fetching, or production deployment.

---

## Task 1: Freeze Resolve bundle and trust-policy contracts

**Files:**

- Create: `protocol/schemas/resolve-bundle-v1.schema.json`
- Create: `protocol/schemas/resolve-trust-policy-v1.schema.json`
- Create: `website/public/schemas/resolve-bundle-v1.schema.json`
- Create: `website/public/schemas/resolve-trust-policy-v1.schema.json`
- Create: `docs/resolve_bundle_trust_policy_v1.md`
- Create: `conformance/protocol_v1/consumer.py`
- Create: `conformance/protocol_v1/test_consumer.py`
- Create: `conformance/protocol_v1/README.md`
- Modify: `.github/workflows/mathgraph-resolve-offline-v1.yml`
- Modify: `website/tests/contracts.test.ts`

### Step 1: Write failing conformance tests

Cover the exact bundle and policy, duplicate keys, extra fields, bad base64, size/hash substitution, unsupported versions, unknown semantic kinds, missing members, wrong source, wrong scope, wrong verifier, changed assumptions, and rehashed-but-unauthorized records. Assert that root and public schemas are byte-identical.

Run:

```bash
python -m pytest conformance/protocol_v1/test_consumer.py -q
```

Expected: FAIL because the schemas and independent consumer do not exist.

### Step 2: Implement the strict independent consumer and schemas

The consumer must use only the standard library, reject duplicate JSON keys before validation, verify decoded member bytes independently, and return structural/semantic reason codes without importing MathGraph producer code. It does not replace the existing Resolve semantic replay.

### Step 3: Re-run focused and historical gates

Run:

```bash
python -m pytest conformance/protocol_v1/test_consumer.py conformance/resolve_v1/test_consumer.py tests/test_mathgraph_resolve_publication_v1.py -q
```

Expected: PASS with immutable bundle, policy, record, and expected replay hashes unchanged.

### Step 4: Commit

```bash
git add protocol/schemas website/public/schemas docs/resolve_bundle_trust_policy_v1.md conformance/protocol_v1 .github/workflows/mathgraph-resolve-offline-v1.yml website/tests/contracts.test.ts
git commit -m "Publish Resolve bundle and trust-policy contracts"
```

## Task 2: Establish the dependency-free protocol package

**Files:**

- Create: `mathgraph_protocol/__init__.py`
- Create: `mathgraph_protocol/json_strict.py`
- Create: `mathgraph_protocol/discovery_ranking.py`
- Create: `tests/test_mathgraph_protocol_import.py`
- Modify: `mathgraph/discovery_scheduler.py`

### Step 1: Write failing import and parity tests

Verify the new package imports in an isolated subprocess with optional modules blocked, rejects duplicate keys/nonfinite JSON, and produces exactly the existing four policy-weight maps, candidate scores, probabilities, and stable tie order.

### Step 2: Move the pure ranking kernel

Implement one standard-library ranking kernel and make the existing scheduler delegate its weight, score, and softmax calculations to it. Do not copy independent scoring implementations.

### Step 3: Verify no regression

Run the new tests plus current discovery scheduler/source tests selected by `rg`.

### Step 4: Commit

```bash
git commit -m "Add independent MathGraph protocol package"
```

## Task 3: Implement modular Discover v1

**Files:**

- Create: `protocol/schemas/discover-request-v1.schema.json`
- Create: `protocol/schemas/discover-result-v1.schema.json`
- Create: `website/public/schemas/discover-request-v1.schema.json`
- Create: `website/public/schemas/discover-result-v1.schema.json`
- Create: `mathgraph_protocol/discover_v1.py`
- Create: `mathgraph_protocol/discover_sources_v1.py`
- Create: `scripts/mathgraph_discover_v1.py`
- Create: `conformance/discover_v1/fixtures/request.json`
- Create: `conformance/discover_v1/fixtures/result.json`
- Create: `conformance/discover_v1/test_discover.py`
- Create: `conformance/discover_v1/README.md`
- Create: `docs/discover_contract_v1.md`

### Step 1: Write failing contract/advisory/source tests

Test exact schema versions, duplicate keys/IDs, booleans as integers, negative and nonfinite values, unknown fields, invalid descension targets, attempted truth promotion, legitimate boundary disclaimers, empty/all-invalid/partial input, `top_k=0`, deterministic ties, and source digest mismatch.

### Step 2: Implement a pure local operation

Implement `discover(request) -> result` with `OK`, `PARTIAL`, `UNKNOWN`, and `ERROR` outcomes. Every result is advisory, cannot promote truth, and reports `NOT_CHECKED`; no terminal form is emitted.

### Step 3: Add one real source adapter

Derive the example request from the checked local copies in `recursive_residual_transfer_v1_20260523`. Verify exact manifest sizes/hashes and retain locators and missing/full-replay diagnostics. Do not rerun or authenticate the historical experiment.

### Step 4: Verify offline independence and deterministic output

Run with no network, no optional scientific packages, and no other MathGraph modules. Compare the committed result byte-for-byte.

### Step 5: Commit

```bash
git commit -m "Add advisory MathGraph Discover v1 contract"
```

## Task 4: Define portable capability contracts

**Files:**

- Create: `protocol/schemas/capability-contract-v1.schema.json`
- Create: `protocol/schemas/capability-evaluation-v1.schema.json`
- Create: `protocol/schemas/capability-registry-v1.schema.json`
- Create matching byte-identical public schema files
- Create: `mathgraph_protocol/capability_v1.py`
- Create: `scripts/mathgraph_capability_v1.py`
- Create: `conformance/capability_v1/test_contract.py`
- Create: `docs/capability_contract_v1.md`

### Step 1: Write failing validation and UNKNOWN tests

Test exact identities, pinned artifact references, required limitations, duplicate keys/IDs, malformed digests, changed scopes/assumptions, unsupported profiles and critical extensions, producer-supplied status injection, and structurally valid but unqualified descriptors.

### Step 2: Implement descriptor/evaluation separation

A descriptor cannot declare itself verified. The evaluator reports validation, bounded qualification or `UNKNOWN`, freshness, revocation/supersession, current applicability, action authorization, and reason codes independently.

### Step 3: Publish an empty qualified registry

The registry contract accepts zero entries and separately lists experimental candidates. No entry is admitted merely because it is described.

### Step 4: Commit

```bash
git commit -m "Define portable capability contracts"
```

## Task 5: Independently qualify the bounded finite capability profile

**Files:**

- Create: `conformance/capability_v1/fixtures/finite-representation-refinement-v1.json`
- Create: `conformance/capability_v1/fixtures/capability-contract.json`
- Create: `conformance/capability_v1/trust-policy.json`
- Create: `conformance/capability_v1/consumer.py`
- Create: `conformance/capability_v1/test_consumer.py`
- Create: `conformance/capability_v1/README.md`
- Create: `protocol/registries/capabilities-v1.json`
- Create: `website/public/capabilities/index-v1.json`
- Create: `.github/workflows/mathgraph-protocol-conformance-v1.yml`

### Step 1: Write failing independent replay tests

Without importing `experiments/.../run.py`, recompute the eight-state old closure, obstruction, named refinements, new witness, sham, ablation, source-distinct reuse, all 256 Boolean refinements, 32 successes, and eight successful partition classes.

Add mutation controls for omitted states, changed target/refinement, incomplete closure, sham substitution, lost retention, scope/source/verifier changes, unsupported transport, and circular/self-reported qualification.

### Step 2: Implement the independent finite-profile consumer

Use supplied finite vectors and a separately pinned trust policy. Recompute results rather than accepting fixture verdicts. Keep the original experiment sources as provenance; the independent consumer qualifies only the exact finite profile and exact contract.

### Step 3: Admit one bounded entry only after replay passes

The registry entry must say `QUALIFIED_BOUNDED`, explain its finite scope, and explicitly deny universal invention or autonomous improvement claims.

### Step 4: Commit

```bash
git commit -m "Qualify finite capability profile independently"
```

## Task 6: Implement the first external interoperability profile

**Files:**

- Create: `protocol/schemas/external-binding-v1.schema.json`
- Create matching public schema
- Create: `mathgraph_protocol/in_toto_v1.py`
- Create: `adapters/in_toto_v1.py`
- Create: `conformance/interoperability_v1/statement.json`
- Create: `conformance/interoperability_v1/test_in_toto.py`
- Create: `docs/external_interoperability_v1.md`

### Step 1: Write failing round-trip/negative tests

Cover exact subject digest, schema, media type, size, claim identity/kind/scope, evidence references, unsigned state, wrong artifact, valid digest over changed scope, stripped assumptions, unsupported predicate, and unknown extensions.

### Step 2: Implement deterministic unsigned in-toto Statement v1 mapping

Export/import exact artifact bindings. Do not sign, authenticate, fetch arbitrary URLs, or promote qualification. Document Sigstore, SCITT RFC 9943, and RATS RFC 9334 as non-implemented extension boundaries.

### Step 3: Commit

```bash
git commit -m "Add unsigned in-toto interoperability profile"
```

## Task 7: Project modular contracts into the Astro site

**Files:**

- Create: `website/src/pages/discover/index.astro`
- Create: `website/src/pages/develop/index.astro`
- Create: `website/src/pages/capabilities/index.astro`
- Modify: `website/src/layouts/BaseLayout.astro`
- Modify: `website/src/pages/index.astro`
- Modify: `website/src/pages/protocol.astro`
- Modify: `website/src/pages/developers.astro`
- Modify: `website/src/pages/agents.astro`
- Modify: `website/src/pages/llms.txt.ts`
- Modify: `website/public/.well-known/mathgraph.json`
- Modify website data/contract/render/link tests as needed

### Step 1: Write failing route/content/contract tests

Assert the three routes, exact maturity language, source/digest links, registry parity, schema mirrors, and no hosted-service or broad verification claim.

### Step 2: Build restrained static pages

Show the real advisory Discover example, exact bounded Develop result, and qualified capability contract. Keep conceptual loop language explicitly non-mandatory and non-autonomous.

### Step 3: Verify visual and machine parity

Run Astro diagnostics/build/HTML/link/accessibility-oriented checks and inspect rendered desktop, tablet, and mobile screenshots. Check overflow, focus order, labels, and console errors.

### Step 4: Commit

```bash
git commit -m "Publish modular protocol interfaces on MathGraph.org"
```

## Task 8: Release-candidate qualification and review

**Files:**

- Update: `docs/mathgraph_full_product_audit_2026-10-11.md` only for observed implementation outcomes
- Create: `docs/mathgraph_modular_contracts_release_candidate_2026-10-11.md`
- Create: screenshot artifacts under a dedicated review directory if repository policy permits

### Step 1: Run all relevant isolated gates

Run:

```bash
python -m pytest conformance/protocol_v1 conformance/resolve_v1 conformance/discover_v1 conformance/capability_v1 conformance/interoperability_v1 -q
python -m pytest tests/test_mathgraph_resolve_publication_v1.py tests/test_mathgraph_protocol_import.py -q
cd website && npx -y node@24.15.0 node_modules/npm/bin/npm-cli.js run qualify
```

Also run original developmental scripts read-only and confirm all immutable Resolve hashes.

### Step 2: Request independent code review

Review for evidence-boundary regressions, producer/consumer coupling, schema ambiguity, duplicate-key/nonfinite paths, UI overclaim, and accidental production/config mutation. Fix all material findings and rerun affected gates.

### Step 3: Push and open a draft PR

Push `codex/mathgraph-contracts-and-modules-v1`, create a draft PR with exact commands/outcomes, CI links, hashes, screenshots, preview URL if Vercel automatically creates one, and unresolved obligations. Do not promote or alias production.
