# MathGraph Resolve Record 002 — P0 Design

## Intent

P0 extends the currently deployed MathGraph.org product with one independently replayed Resolve record. It demonstrates how a typed evidence withdrawal changes only dependent support while mathematical truth remains `UNKNOWN` and unrelated qualified evidence remains warranted at its original scope.

The release does not claim live monitoring, theorem refutation, general semantic transport, autonomous development, or an open-ended trust service. Discover, Develop, Capabilities, hosted resolution, SDKs, and MCP remain later stages unless a concrete P0 dependency requires a small interface placeholder.

## Release authority

The integration base is `93850c7d66740699e8ad52452d1fe9bd38a4fc51`, the exact reviewed commit currently served by Vercel deployment `dpl_CWUMpTovnYsFhsks2RDaaVqLT62k`. GitHub `main` is `9ad69aa966ad4e07539a80d66d08a89948247a64`; branding PR #153 and agent-interoperability PR #154 remain open and stacked. P0 therefore branches from the deployed #154 head, preserving that build as the rollback point.

The Resolve source authority is producer commit `040456fc8862c79c8b384ce63846628274b678be`. Its immutable snapshot is:

- ID: `mg-living-warrant-openai-jpl-20261010`
- schema: `mathgraph.living-warrant-snapshot.v1`
- transport SHA-256: `0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87`
- canonical payload SHA-256: `b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41`
- producer qualification: Actions run `38025044631`
- independent RealityGraph replay: commit `9b3189a64825e2cb6ebc7b5c17f5f193bdf5cfe3`, Actions run `38025236380`

The public record must preserve those snapshot bytes exactly. Presentation metadata, registry lifecycle, page copy, and visual state live outside the snapshot and cannot change its resolution result.

## Selected architecture

### 1. One authoritative resolution kernel

The qualified Python reclosure logic becomes a small module with typed objects for claims, evidence receipts, assumptions, native verifiers, qualified relations, dependency routes, obstructions, resolutions, historical snapshots, and lifecycle events.

The kernel remains fail-closed:

- all referenced claims, receipts, assumptions, relations, and verifiers must exist;
- every route is conjunctive and routes to the same conclusion are alternatives;
- cycles without a qualified root establish nothing;
- kind or scope changes require an explicitly qualified relation with verifier evidence;
- withdrawing evidence produces localized `STALE` or `UNKNOWN`, never implicit `FALSE`;
- self-hashes establish byte integrity only and never admit evidence.

`mathgraph_check.living_warrants` will consume this kernel. Its generated historical snapshot must remain byte-identical to the qualified publication.

### 2. Precomputed public scenarios

A deterministic publisher invokes the Python kernel and emits canonical JSON scenarios. The committed artifact is regenerated and byte-compared in CI.

It contains two visibly separated classes:

1. `PUBLISHED_RECORD` scenarios derived only from record 002, including its frozen before/after state and dependency-selection outcomes.
2. `SYNTHETIC_CONFORMANCE` scenarios that demonstrate alternative support, localized invalidation, and an unsupported cycle. These are kernel tests, not historical claims.

Astro renders a complete static default state from this artifact. Minimal same-origin JavaScript only selects an already-published scenario and updates the display; it does not perform reclosure or manufacture status fields.

### 3. Versioned heterogeneous record catalogue

`/records/index.json` advances to `mathgraph.record-index.v2`, while the existing v1 schema remains permanently available. V2 adds an explicit `record_kind` and schema-specific adapter metadata rather than weakening record 001's hard-coded qualification gate.

The two initial kinds are:

- `SOURCE_CHECK`: existing L4YAML public consequence record.
- `RESOLUTION_SNAPSHOT`: exact Living Warrants snapshot.

Each adapter independently validates its immutable transport digest, internal content digest, identity, known source pins, expected bounded outcomes, and presentation sidecar. Unknown kinds and schemas fail closed.

Record 002 receives permanent routes:

- `/records/mg-living-warrant-openai-jpl-20261010/v1/`
- `/records/mg-living-warrant-openai-jpl-20261010/`
- `/evidence/mg-living-warrant-openai-jpl-20261010/record.json`
- `/evidence/mg-living-warrant-openai-jpl-20261010/scenarios.json`

Its presentation title is **MathGraph Resolve — When Mathematical Evidence Changes**. The catalogue may describe it as the second published record, but the immutable historical ID is never renamed or replaced.

### 4. Public experience

`/resolve/` explains the product operation and hosts the read-only graph explorer. The permanent record page supplies exact source pins, before/after tables, producer and consumer qualification links, reproduction steps, limitations, and machine-readable resources.

The homepage introduces the cycle in plain language:

> Discover what matters. Check what holds. Resolve what remains justified. Develop what becomes possible.

Navigation groups product operations instead of placing every future subsystem in the header. P0 adds Resolve directly and links later operations from the homepage/protocol with explicit maturity labels.

The UI always presents status on independent axes:

- epistemic result;
- lifecycle;
- research maturity;
- action policy when applicable.

`STALE` is a lifecycle/evidence-support outcome, not `REFUTED`. The OpenAI publisher notice is documentary source evidence, not a formal theorem verifier. The independent consumer replays the published graph but does not rerun the original JPL Lean proof.

## Security and provenance

The release is static and read-only. It accepts no arbitrary claims, URLs, repositories, proof code, or mutations. The explorer has no execution endpoint.

The public documentation and threat model must state:

- a transport or content hash detects byte substitution relative to a trusted expected digest but does not authenticate the publisher by itself;
- GitHub commit pins are provenance references under a separate repository/key trust policy;
- the exact OpenAI history blob authenticates the publisher notice only, not the truth or falsity of the mathematical statements;
- the RealityGraph consumer is implementation-independent but not an independently owned external adoption milestone;
- unknown schemas, relations, versions, source pins, and semantic transports are rejected or returned as typed `UNKNOWN`.

No production deployment, domain, DNS, nameserver, registrar, or mail setting changes are part of P0 staging.

## Qualification

P0 is reviewable only when all of the following pass:

- the original record 001 assets and digests remain byte-identical;
- the original record 002 snapshot is exactly 5,290 bytes with the pinned transport and canonical hashes;
- regenerated record 002 remains byte-identical to the qualified snapshot;
- conjunctive routes, alternative routes, localized withdrawal, unsupported cycles, cross-boundary transport, malformed references, and self-hash forgery have protected tests;
- the independent RealityGraph contract is represented by exact commit/run identities without claiming new Lean replay;
- catalogue and built-site tests reject altered record 002 bytes, forged statuses, unsupported kinds, and unknown versions;
- static and interactive Resolve states consume the same scenarios artifact;
- Astro diagnostics, build, HTML, links, accessibility-oriented rendering assertions, independent consumer tests, and deployment smoke checks pass;
- desktop 1440 px, tablet 768 px, and mobile 390 px screenshots are inspected;
- a protected Vercel preview is verified before any separate production-release decision.

## Explicitly deferred

The following are outside this P0 release and remain `PROPOSED`, `EXPERIMENTAL`, or `UNKNOWN` as appropriate:

- hosted arbitrary record resolution;
- an MCP adapter;
- generalized Discover Frontier publication;
- Capabilities Registry entries;
- Capability Family Compiler V1 and its Lean theorem;
- authenticated publication signatures;
- in-toto, Sigstore, SCITT, or RATS conformance;
- proof of autonomous or economical recursive capability improvement.

Deferral is intentional: record 002 and its common kernel must qualify before later product pillars build on them.
