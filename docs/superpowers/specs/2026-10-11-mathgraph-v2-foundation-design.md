# MathGraph V2 Foundation — Design Specification

**Date:** 2026-10-11  
**Status:** Approved implementation design derived from the MathGraph V2 master mission  
**Release boundary:** Draft pull request and protected preview only; production, DNS, immutable evidence, and trust-policy authority remain unchanged

## 1. Authority and starting point

MathGraph V2 extends the qualified PR #156 foundation on `origin/main` at
`4edc77cb1a4ff3a345b5feffcf7f2b38d3fbab0c`. The production Vercel deployment is
associated with that exact commit. PR #157 remains a non-normative draft: its
conditional Lean laws are bounded research evidence, while its consequence
envelope is not a public protocol authority.

The existing Astro site, record 001, Resolve record 002, strict JSON parser,
versioned Resolve/Discover/capability contracts, offline consumers, agent
discovery files, and qualified negative controls are reused without changing
their immutable bytes or identities.

Notion Research OS is a human-readable control surface. Pinned source commits,
CI runs, verifier outputs, record bytes, and qualified artifacts remain the
evidence authority.

## 2. Product outcome

V2 provides one coherent, safe vertical slice:

> Import → Interpret → Check → Resolve → Explore → Export

The first supported artifact is the exact, published L4YAML evidence record.
The browser recognizes local bytes, verifies their digest and declared pins,
and renders a consumer report. It does not execute proof code, fetch arbitrary
URLs, or become a warrant authority. The independently runnable Python
consumer derives the authoritative bounded result under its explicit pinned
policy. Unsupported, mutated, generalized, or ambiguous inputs fail closed.

The site communicates this through outcome-oriented journeys:

- **Explore** — records, claims, relationships, capabilities, and research.
- **Verify** — supported imports, Check, Resolve, evidence, and replay.
- **Build** — qualified capability reuse and bounded developmental research.
- **Developers** — contracts, schemas, consumers, conformance, and integration.

Existing public URLs remain valid.

## 3. Minimal architecture

### 3.1 No new authority or service

V2 adds no database, authentication system, job queue, hosted execution
service, arbitrary URL fetcher, proof compiler, or new trust root. Static Astro
publishing remains the delivery mechanism. The browser is a view and local
recognizer; independent consumers remain the executable qualification path.

This is the smallest warranted architecture because the protected V2 future is
inspection, portable replay, and typed navigation—not mutable user accounts or
remote computation.

### 3.2 Independent import contract

Add a versioned `mathgraph.import-result.v1` consumer result and a standalone
standard-library Python consumer under `conformance/import_v1/`.

The consumer:

1. strictly parses bounded JSON;
2. validates the exact supported schema, identity, source/test pins, verifier
   receipts, assumptions, scope, publication digest, and declared status axes;
3. derives the supported outcome rather than trusting producer labels;
4. emits source, evidence, scope, lifecycle, freshness, applicability,
   authorization, and UNKNOWN fields separately;
5. returns a deterministic portable result;
6. declines unsupported artifacts and extensions.

The trust policy is an existing exact record/source authority expressed as a
versioned local fixture. This release does not expand what is trusted.

Negative conformance covers source-byte mutation, source/test commit changes,
content-digest changes, forged status, scope/generalization changes, verifier
and assumption changes, duplicate keys, non-finite values, oversize input,
unsupported versions/types, and unauthorized action promotion.

### 3.3 Presentation-only object projections

The canonical object explorer uses an internal TypeScript `ObjectProjection`
view model. It is not a universal Unit ontology and is never serialized as a
new evidence authority.

Adapters project existing qualified objects into shared fields:

- identity and type;
- source occurrence and attribution;
- evidence and verifier;
- assumptions and exact scope;
- epistemic result, lifecycle, freshness, applicability, and authorization;
- declared typed relations and lineage;
- reproduction and portable exports;
- explicit unknowns.

At least two materially different domains exercise the adapter boundary:
record 001 (finite/source-bound verification) and the finite capability
contract. Resolve record 002 supplies dependency/lifecycle relationships.
Unknown types preserve their original bytes where the underlying contract
allows it and are otherwise declined; they are never coerced into known
semantics.

### 3.4 Knowledge map projection

The knowledge map is derived only from committed identities and declared typed
relations. It does not infer equivalence, implication, or support from names,
layout, proximity, or hashes.

For the current graph size, accessible semantic HTML plus a small SVG/TypeScript
projection is preferred over Cytoscape.js or React Flow. This avoids a React
runtime and graph dependency while satisfying selection, traversal, filtering,
lineage, mobile layout, keyboard access, and subgraph export. A node limit and
explicit truncation state prevent accidental unbounded rendering.

Every exported subgraph declares `authority: NONE`, its projection schema, and
the source identities/digests from which it was derived.

### 3.5 Local browser import

The import workbench accepts a local `.json` file with a conservative size
limit. It uses strict shape checks and Web Crypto for digest comparison, then
matches only supported exact artifacts. It performs no network fetch and no
code execution.

The UI labels its result as a local recognition/inspection result, links to the
independent replay command, and keeps current applicability and action
authorization separate. Unsupported inputs return `UNKNOWN` with concrete
supported import paths.

## 4. Information architecture and UX

### 4.1 Navigation

The primary navigation becomes Explore, Verify, Build, and Developers, with an
accessible mobile disclosure. Secondary landing pages link to existing module
routes. Existing `/check/`, `/resolve/`, `/records/`, `/discover/`,
`/develop/`, `/capabilities/`, `/agents/`, `/developers/`, and `/protocol/`
routes remain stable.

### 4.2 Homepage

Headline:

> Knowledge you can verify. Capabilities you can build on.

Supporting proposition:

> Bring a claim, proof, repository, or research artifact. Discover what has
> been established, what remains unknown, how it connects, and what can be
> reused.

The page includes the supported local import entry point, the three outcome
journeys, record 001 as the source-to-result example, a real map projection,
the bounded capability example, independent verification explanation, an
executable quick start, and carefully scoped long-term direction.

### 4.3 Reusable explorer surfaces

- `/objects/` indexes projected objects.
- `/objects/[slug]/` renders the canonical object-detail architecture.
- `/explore/`, `/verify/`, and `/build/` provide outcome landing pages.
- `/records/` and `/capabilities/` gain local search/filtering and honest empty
  states.
- `/check/` embeds the supported workbench.
- `/resolve/` retains its qualified explorer and links into the common map.
- `/discover/` remains advisory.
- `/develop/` keeps unqualified family/compiler claims visibly UNKNOWN.
- `/agents/` and `/developers/` use commands exercised by conformance tests.
- `/protocol/` is organized around Object, Relation, Evidence, Resolution, and
  Transition, with CLOSE/ACT/REFINE kept distinct. Historical schemas remain
  unchanged.

### 4.4 Status treatment

No universal green badge is introduced. The UI displays separate axes for:

- epistemic result;
- lifecycle;
- maturity;
- freshness;
- applicability;
- action authorization.

UNKNOWN is textual and first-class. Color is supplementary only.

## 5. Security and integrity boundary

- No arbitrary execution, proof compilation, URL fetching, or state mutation.
- No producer-controlled promotion.
- No browser-side warrant authority.
- Byte identity, authenticity, mathematical truth, applicability, freshness,
  and permission remain distinct.
- Existing immutable records, digests, schemas, and historical routes are
  regression-checked byte-for-byte.
- All supported imports have size, encoding, duplicate-key, numeric, schema,
  version, identity, scope, and authority checks.
- Current applicability is UNKNOWN when freshness cannot be authenticated.
- Projection exports cannot be replayed as qualified evidence.

## 6. Qualification strategy

Qualification is layered:

1. **Contract tests:** fail first, then cover the import consumer and all
   mutation controls.
2. **Projection tests:** exact source-derived fields, no invented edges,
   two-domain adapter coverage, deterministic export, unknown-type refusal.
3. **Rendering tests:** all new routes, metadata, status axes, quick-start
   commands, stable historical links, and import/map hooks.
4. **Existing suites:** full website qualification plus protocol, Resolve,
   Discover, capability, interoperability, and research regression suites.
5. **Browser QA:** actual protected preview at desktop, tablet, and mobile;
   keyboard navigation, reduced motion, input errors, graph selection,
   filtering, export, downloads, console, headers, and cache behavior.
6. **Independent review:** architecture/security/claims review against exact
   final commit. Same-owner replay is described accurately and never promoted
   to outside-owner adoption.

## 7. Explicit deferrals and residuals

V2 does not implement Brains, a marketplace, accounts, collaboration editing,
arbitrary repository import, hosted proof execution, MCP, a universal semantic
object model, general cross-prover transport, automatic literature
formalization, a Capability Family Compiler, autonomous capability growth, or
agent action authorization.

The most consequential research residual is a real pinned
certificate-to-Lean-premise adapter with malicious source/adapter controls and
an implementation-independent consumer. It is not required to complete this
product-integration release and must not be implied by its UI.

Durable retention for historical JPL Actions artifacts also remains unqualified;
V2 must not claim otherwise.

## 8. Demonstrating the foundational principle

The implementation applies “the smallest warranted present that preserves the
protected future” concretely:

- it adds a view adapter instead of a competing ontology;
- it adds a local consumer instead of a hosted execution service;
- it retains exact evidence bytes and projects only fields needed for the
  current task;
- it keeps unknown, lifecycle, freshness, applicability, and authorization as
  separate distinctions because collapsing them would change protected future
  decisions;
- it rejects inferred edges and unsupported imports rather than promoting
  nearby warrant;
- it exercises two distinct existing domains before adding another
  foundational abstraction.

Future Maps, Brains, Paths, capabilities, federation, and living-paper clients
can consume the versioned records, relations, portable consumer results, and
non-authoritative projections without requiring MathGraph.org. Their broader
semantic adequacy remains an extension obligation, not a V2 claim.
