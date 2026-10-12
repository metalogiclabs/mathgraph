# MathGraph Living Knowledge Network Design

**Date:** 2026-10-12  
**Status:** Approved architecture; implementation pending  
**Product:** MathGraph.org  
**Base authority:** `metalogiclabs/mathgraph@50b74559551d4935d7b5237ff5e98438f09d5d26`  
**Production deployment at approval:** Vercel `dpl_A5y8eC32p7p5M9Kg6LLK5ehX9ahz`, serving `mathgraph.org` from the same commit  
**Implementation branch:** `codex/living-knowledge-network`

## 1. Objective

Turn the existing MathGraph V2 site into an immediately useful living mathematical knowledge network without weakening its evidence boundaries.

A first-time visitor must be able to:

1. find a real mathematical declaration;
2. inspect its exact source occurrence and source-index status;
3. navigate genuine typed relations without mistaking them for proof or implication;
4. inspect an independently qualified MathGraph result and reproduce its bounded conclusion; and
5. use the qualified Resolve example to see how a source change affects dependent warrants while unrelated support survives.

The homepage keeps the existing headline:

> Knowledge you can verify. Capabilities you can build on.

It also keeps the existing Explore / Verify / Build journeys and the Check / Resolve / Discover / Develop module distinctions.

## 2. Governing boundaries

This increment is a source-index and presentation expansion, not a new verifier, ontology, graph authority, or terminal truth system.

- Accepted claims still terminate in exactly one of `VERIFIED_PROOF`, `FINITE_COUNTERMODEL`, or `NAMED_OBSTRUCTION`.
- A source-indexed Mathlib declaration is not an accepted MathGraph claim and has no terminal form.
- Parsing, indexing, a hash, a signature, a successful import, or graph proximity does not establish mathematical truth.
- `DECLARES`, `IMPORTS_MODULE`, and `TYPE_REFERENCES` do not mean implication, equivalence, proof dependency, evidence support, or semantic correspondence.
- The browser remains a presentation and inspection layer with authority `NONE`.
- Immutable records 001 and 002, their canonical bytes, digests, receipt identities, and qualified interpretations remain unchanged.
- Existing capability contracts, qualification policies, and source authority remain unchanged.
- Unsupported schemas, source revisions, relations, extensions, and requested generalizations fail closed.
- Action authorization remains `NONE`.
- No graph database, hosted ingestion service, arbitrary source fetching, public proof execution, autonomous agent framework, or new backend is introduced.

## 3. Current authority and reusable implementation

### 3.1 Qualified production baseline

Production and `origin/main` both resolve to `50b74559551d4935d7b5237ff5e98438f09d5d26`, the merge commit for PR #158.

The current site already provides:

- an Astro 7 static website;
- canonical object projections and permanent object routes;
- an authority-free knowledge-map contract with provenance validation;
- accessible semantic object and relation lists;
- bounded graph export;
- immutable Check record 001;
- immutable Resolve record 002 and offline replay;
- a read-only Resolve scenario explorer;
- a qualified finite capability registry;
- `/agents`, `/llms.txt`, and `/.well-known/mathgraph.json` discovery surfaces; and
- static build, schema, contract, rendering, link, resolver, and independent-consumer qualification.

The public graph is real but currently small: 14 objects and 7 source-backed relations.

### 3.2 Components to extend

Reuse rather than replace:

- `website/src/lib/object-projections.ts`
- `website/src/data/object-projections.ts`
- `website/src/lib/object-locators.ts`
- `website/src/pages/objects/`
- `website/src/components/ObjectDetail.astro`
- `website/src/components/ObjectRelations.astro`
- `website/src/lib/knowledge-map.ts`
- `website/src/components/KnowledgeMap.astro`
- `website/src/scripts/knowledge-map.ts`
- `website/src/components/CatalogueFilter.astro`
- `website/src/components/ResolveExplorer.astro`
- `website/src/scripts/resolve-explorer.ts`
- `website/public/.well-known/mathgraph.json`
- `website/src/pages/llms.txt.ts`

Existing Mathlib inspection code supplies useful boundary discipline but is not publication authority:

- `mathgraph/mathlib_declaration_discovery.py` is regex-based and advisory;
- `mathgraph/mathlib_module_verification.py` checks import and named-declaration availability, not proof reconstruction;
- `mathgraph/mathlib_digest.py` treats printed references as hints; and
- `mathgraph/mathlib_local_allowlist.py` already distinguishes advisory extraction from verifier-bound acceptance.

The new catalogue reuses these distinctions but uses a Lean-native extractor for published declaration data.

### 3.3 Orthogonal open work

PR #159 at `ee0f928d92b9c28d71069259da7abb158e6975c1` is an unmerged favicon-only draft. This branch does not absorb, supersede, or merge it. The implementation must remain rebaseable if that PR lands independently.

## 4. Mathlib source authority

The initial catalogue pins the latest audited stable Mathlib release rather than a moving branch:

| Field | Value |
| --- | --- |
| Repository | `https://github.com/leanprover-community/mathlib4` |
| Release label | `v4.34.1` |
| Commit | `d13f23b723b8a846827a245b89c10fc7d3f11612` |
| Git tree | `efa132418a56d0e38c56cc412a06df22178dac5c` |
| Lean toolchain | `leanprover/lean4:v4.34.1` |
| License | Apache-2.0 |
| Citation | The mathlib Community, CPP 2020, DOI `10.1145/3372885.3373824` |

The manifest records and validates SHA-256 digests for the upstream `LICENSE`, `CITATION.md`, `lean-toolchain`, `lake-manifest.json`, and `Mathlib.lean` files. The tag is descriptive only; commit and tree identities are authoritative.

### 4.1 Initial bounded source selection

Catalogue ID: `mathlib-v4.34.1-foundations-v1`.

The initial coherent slice contains exactly these 13 origin modules:

1. `Mathlib/Data/Nat/Basic.lean`
2. `Mathlib/Data/Int/Basic.lean`
3. `Mathlib/Data/List/Basic.lean`
4. `Mathlib/Data/Finset/Basic.lean`
5. `Mathlib/Data/Set/Basic.lean`
6. `Mathlib/Logic/Function/Basic.lean`
7. `Mathlib/Algebra/Group/Basic.lean`
8. `Mathlib/Algebra/Ring/Basic.lean`
9. `Mathlib/Order/Basic.lean`
10. `Mathlib/Data/Nat/Prime/Basic.lean`
11. `Mathlib/Combinatorics/SimpleGraph/Basic.lean`
12. `Mathlib/Topology/Basic.lean`
13. `Mathlib/Analysis/SpecialFunctions/Pow/Real.lean`

The pinned source files total 382,266 bytes. A preliminary textual scan found roughly 1,755 declaration commands, but this number is not published as authoritative. The Lean-native extraction result supplies the exact declaration and relation counts.

This slice is intentionally broad enough for useful navigation across arithmetic, data structures, algebra, order, graph theory, topology, and analysis while remaining small enough for exact review, deterministic regeneration, and static publication.

## 5. Catalogue contracts

The catalogue adds two non-evidence contracts. They are source-publication adapters, not foundational MathGraph semantic object types.

### 5.1 `mathgraph.source-catalogue-manifest.v1`

Required fields:

- schema and catalogue version;
- catalogue ID;
- source repository, commit, tree, and descriptive tag;
- license and citation identity;
- Lean toolchain and Lake manifest digests;
- selected module paths and their byte digests;
- extractor source commit and extractor contract version;
- deterministic selection and ordering policy;
- exact object, module, in-slice relation, and omitted-reference counts;
- status and authority boundary;
- shard paths, byte sizes, SHA-256 digests, and object/relation counts;
- global size limits and whether any explicit truncation occurred; and
- independently reproducible generation command.

The manifest has no wall-clock field in its content identity. Publication or HTTP freshness metadata is a separate presentation wrapper.

### 5.2 `mathgraph.source-catalogue-shard.v1`

Each module shard contains:

- its source module identity and file digest;
- declaration occurrence objects;
- exact source ranges;
- declaration kinds and fully qualified names;
- rendered declaration types/statements;
- in-slice typed relations;
- named out-of-slice type references as omissions rather than fabricated graph nodes; and
- the explicit source-index and no-authority boundary.

Shards are content-addressed and listed by digest in the manifest.

### 5.3 Static publication routes

- `/catalogues/mathlib/v4.34.1/manifest.json`
- `/catalogues/mathlib/v4.34.1/search.json`
- `/catalogues/mathlib/v4.34.1/shards/{sha256}.json`

The machine routes are immutable for the declared version. A later Mathlib revision receives a new versioned catalogue and new occurrence identities.

## 6. Identity and status model

### 6.1 Declaration occurrence identity

A canonical declaration occurrence binds:

- source repository;
- exact commit;
- module/path;
- fully qualified declaration name; and
- object-contract version.

The canonical serialization is hashed using SHA-256 to form the existing `object-{digest}` route style. A rendered statement hash is included as an integrity field but is not the semantic identity of the mathematical content.

The same name at a new commit is a new source occurrence. No cross-version equivalence is inferred.

### 6.2 Catalogue status axes

Every Mathlib catalogue declaration has:

- source status: `SOURCE_INDEXED`;
- independent MathGraph verification: `NOT_CHECKED`;
- current applicability: `NOT_CHECKED`;
- freshness: `PINNED_HISTORICAL_SOURCE`;
- action authorization: `NONE`;
- authority: `NONE`; and
- terminal form: absent.

The UI must not map these values to `WARRANTED`, `VERIFIED_PROOF`, or a broad green truth badge.

An optional future exact `#check` receipt may attach to a named occurrence, but it can establish only import and declaration availability within the pinned environment unless a stronger verifier contract is separately qualified.

## 7. Extraction and deterministic publication

### 7.1 Acquisition boundary

External source acquisition occurs before offline generation:

1. obtain the exact Mathlib commit;
2. verify repository, commit, tree, tag target, toolchain, Lake manifest, license, and citation digests;
3. reject a dirty or substituted source checkout; and
4. enter the network-disabled extraction phase.

### 7.2 Lean-native extractor

A committed fixed-module Lean command runs under the pinned Mathlib environment and reads Lean environment data.

For each declaration originating in the selected modules it extracts:

- `ConstantInfo` kind;
- fully qualified name;
- declaration type;
- originating module;
- imported declaration range/source range where available; and
- direct `Expr.const` occurrences in the declaration type.

Proof bodies are not published in V1. Comments, documentation text, strings, pretty-printed tokens, and name similarity cannot generate graph edges.

The extractor emits a sorted intermediate stream to temporary or external artifact storage. A Python-standard-library canonicalizer validates it and writes the compact manifest, search index, and shards. Raw streams, `.olean` files, caches, archives, and full proof bodies are not committed.

### 7.3 Relation meanings

Only these relations are admitted:

| Relation | From | To | Meaning |
| --- | --- | --- | --- |
| `DECLARES` | selected module | source occurrence | the pinned module contains the declaration occurrence |
| `IMPORTS_MODULE` | selected module | selected module | the source contains the direct module import |
| `TYPE_REFERENCES` | source occurrence | source occurrence | the elaborated declaration type directly contains the target `Expr.const` and both endpoints are in the selected slice |

All three are source/elaboration relations with authority `NONE` and explicit fields `logical_implication: false` and `semantic_equivalence: false`.

Out-of-slice references remain named omissions. The generator does not manufacture external nodes or edges merely to make the graph look connected.

### 7.4 Determinism and limits

Generation must run twice from a clean pinned checkout with byte-identical output under fixed locale and time-zone settings.

Hard limits:

- no more than 2,500 public declarations;
- no more than 25,000 in-slice relations;
- search index at most 2 MiB raw and 256 KiB under deterministic gzip;
- each module shard at most 2 MiB raw and 256 KiB under deterministic gzip;
- the complete catalogue at most 12 MiB raw and 1.5 MiB under deterministic gzip; and
- each browser graph projection at most 50 nodes and 100 edges.

Exceeding a limit fails qualification. Nothing is silently dropped. Any deliberate bounded omission is counted and described in the manifest.

Execution ruling, 13 October 2026: exact Lean extraction of the approved
13-module slice produced 2,345 occurrences and 3,571 relations. The complete
canonical publication measured 9,022,416 raw bytes and 1,150,269 bytes under
deterministic gzip; the largest raw shard was 1,730,897 bytes and the search
index was 1,624,539 raw / 200,901 gzip bytes. This invalidated the preliminary
raw-JSON estimates while satisfying the intended transfer budget. V1 therefore
keeps one exact shard per selected source module and the full statement data,
raises only the bounded raw parsing ceilings shown above, and retains the
independently enforced 1.5 MiB compressed-publication ceiling. Splitting source
modules, introducing a string-table format, or dropping statements would add
new representation semantics without improving transferred bytes enough to
justify them in this release.

## 8. Product experience

### 8.1 Homepage

The homepage preserves its headline, proposition, and journey model. The supported entry point becomes a genuine network search rather than a generic arbitrary-URL field.

Above the first major scroll boundary:

- search real source-indexed Mathlib declarations, records, and qualified capabilities;
- see that results carry different evidence statuses;
- open a representative declaration and its bounded neighborhood; and
- reach the existing real evidence examples.

The page adds a compact network preview using real catalogue objects and typed relations. It does not render a decorative or full-corpus graph.

### 8.2 Unified Explore catalogue

`/explore/` becomes the primary living-network surface and includes:

- deterministic local search;
- source-project, object-kind, module, and status filters;
- exact-name, namespace/name-token, and stable canonical-ID ranking;
- source-derived result counts;
- clear separation among `SOURCE_INDEXED`, independently qualified evidence, advisory discovery, and reusable capabilities;
- a complete no-JavaScript list and search guidance; and
- direct links to permanent object pages.

Ranking order:

1. exact fully qualified name;
2. exact final declaration name;
3. ordered namespace/name token matches;
4. other source metadata matches;
5. deterministic canonical-ID tie-break.

Verification status does not boost relevance as though it implied importance or truth.

### 8.3 Canonical object pages

Existing `/objects/{object-id}/` pages support Mathlib declaration occurrences. Each page shows:

- identity and object kind;
- exact repository, commit, tree, module, path, source range, and source URL;
- declaration kind and rendered type/statement;
- source-index, verification, applicability, freshness, and authorization axes;
- assumptions and omissions where applicable;
- incoming and outgoing typed relations;
- bounded graph neighborhood;
- portable JSON projection download;
- independent catalogue validation instructions; and
- explicit UNKNOWN / NOT_CHECKED boundaries.

Existing qualified record, claim, receipt, and capability pages remain available and use their current evidence adapters.

### 8.4 Bounded knowledge map

The existing knowledge-map schema and validation remain authoritative for presentation projections.

The visual layer is adapted from fixed lanes to a bounded neighborhood layout that remains deterministic and accessible. It must provide:

- selected central object;
- one-hop incoming and outgoing declared relations;
- optional bounded second-hop expansion;
- kind and relation filters;
- exact relation labels;
- semantic lists matching every visible node and edge;
- keyboard selection and traversal;
- mobile horizontal/vertical containment;
- progressive rendering; and
- exported subgraph with `authority: NONE`.

The browser never computes proof closure, semantic equivalence, or live warrant resolution from catalogue edges.

### 8.5 Separate source-derived metrics

The homepage and Explore surface display distinct metrics for:

- indexed mathematical objects;
- independently qualified claims;
- typed source-backed relations;
- external source projects; and
- qualified reusable capabilities.

The metrics come from validated static manifests. They are never summed into one network, verification, adoption, or activity number.

## 9. Signature Consequence Explorer

The Resolve interaction reuses immutable record 002 and existing `mathgraph.resolve-scenarios.v1` fixtures.

Initial historical view: `published-after`.  
Comparison baseline: `modeled-before`.

The primary 15-second interaction is an explicitly labeled counterfactual simulation:

1. select an existing modeled publisher support route;
2. toggle its withdrawal in the simulation;
3. see that route become `STALE`;
4. see the corresponding proposition remain `UNKNOWN`, not `REFUTED`; and
5. see the unrelated source-bound JPL observation remain `WARRANTED_BOUNDED` at its exact scope.

Existing synthetic conformance scenarios for alternative support, localized invalidation, and rootless cycles remain labeled `SYNTHETIC_CONFORMANCE` / `KERNEL_TEST`. They are not historical claims.

No toggle mutates record bytes, changes publication state, or creates a browser-side qualification.

## 10. Qualified research surfaced in this increment

### 10.1 Published and reusable now

- Check record 001: exact L4YAML/JPL finite source-bound qualification.
- Resolve record 002: three documentary support paths `STALE`, three propositions `UNKNOWN`, and one unrelated bounded JPL observation preserved.
- `urn:mathgraph:capability:finite-developmental-growth` v1: qualified finite representation-refinement capability, with applicability and freshness still not checked and authorization `NONE`.

### 10.2 Not promoted in this increment

- bounded PVS/Lean correspondence remains research pending a durable bundle, versioned adapter, and independent negative conformance;
- finite quantum experiments remain research-only pending a MathGraph evidence bundle and independent replay;
- VDN and capability-family compiler claims remain experimental or unimplemented; and
- external adoption, current applicability, universal correctness, proof equivalence, quantum physical validity, autonomous improvement, and economic compounding remain unclaimed.

These candidates may be referenced as explicitly scoped future qualification residuals, not added as verified catalogue content.

## 11. Agent and developer access

The human-facing call to action remains:

> Point your agent to `mathgraph.org/agents`.

`/agents/` then directs machine consumers to:

- `/llms.txt` for concise discovery;
- `/.well-known/mathgraph.json` for versioned machine discovery;
- the immutable Mathlib catalogue manifest and search index;
- versioned record and capability catalogues;
- bounded object and graph projection examples; and
- the existing independent replay instructions.

The discovery manifest adds catalogue contract versions, immutable URLs, digests, and freshness semantics. It does not claim that `llms.txt` is a formal standard.

A minimal independent catalogue consumer must:

1. start from separately pinned manifest identity;
2. validate schema, repository, commit, tree, toolchain, and shard digests;
3. recompute canonical object IDs;
4. validate relation endpoint closure and allowed meanings;
5. reject forged verification or terminal-form fields;
6. preserve unknown critical extensions by declining the object; and
7. return source-index results without granting action authority.

No MCP adapter or hosted resolver is advertised as part of this increment.

## 12. Security and failure behavior

The catalogue reader and website build fail closed for:

- wrong commit, tree, tag target, toolchain, Lake manifest, license, or citation digest;
- dirty or mutated source bytes;
- duplicate or ambiguous JSON fields;
- duplicate IDs or fully qualified names within the declared occurrence scope;
- path traversal, symlink escapes, missing modules, or out-of-bounds source ranges;
- unsupported schemas, critical extensions, or constant kinds;
- cross-pin or missing relation endpoints;
- comments, strings, or textual name matches becoming relations;
- any relation relabeled as implication, equivalence, evidence, or proof support;
- forged `WARRANTED`, `VERIFIED`, accepted terminal-form, freshness, or authorization states;
- silent truncation or omission;
- nondeterministic regeneration; and
- status inheritance across unsupported source revisions.

The site serves static untrusted text as escaped content. It does not execute catalogue source, proof terms, or user inputs.

## 13. Qualification campaign

### 13.1 Source and generator integrity

- validate all upstream pins and provenance digests;
- generate from a clean checkout with networking disabled after acquisition;
- run twice and compare byte-for-byte;
- validate exact object IDs, source ranges, sorted order, counts, shard sizes, and shard digests;
- verify every page and machine result maps back to one catalogue occurrence; and
- confirm unchanged inputs never require repeated semantic qualification.

### 13.2 Adversarial controls

Tests must demonstrate rejection or conservative decline for:

- source, commit, tree, toolchain, manifest, and shard mutations;
- duplicate JSON fields and IDs;
- invalid source ranges and paths;
- false equivalence or implication edges;
- textual mention leakage;
- cross-revision edge substitution;
- forged verified or terminal status;
- unsupported semantic extensions;
- source revision changes inheriting old status;
- corrupted search entries; and
- silent object or relation truncation.

### 13.3 Product correctness

- exact-name search ranks first;
- namespace and token search is deterministic;
- every search result opens the correct permanent object occurrence;
- graph nodes and edges agree with semantic lists and exported projections;
- object pages expose exact source and status axes;
- Resolve static and interactive views agree with published scenarios;
- selective invalidation preserves independent and unrelated support; and
- public metrics equal validated manifest counts.

### 13.4 Regression and browser qualification

Run:

- relevant Python catalogue and protocol tests;
- existing Check, Resolve, Discover, Develop, capability, and terminal-form tests;
- website Astro diagnostics and production build;
- website data, contract, rendering, static-artifact, HTML, link, resolver, and consumer tests;
- independent catalogue consumer;
- browser tests for search, object navigation, graph traversal/export, and Resolve scenarios;
- keyboard and reduced-motion checks; and
- desktop 1440px, tablet 768px, and mobile 390px screenshot review.

The browser suites become explicit release gates rather than optional local scripts.

### 13.5 Performance budgets

Measure and record:

- committed catalogue and compressed transfer sizes;
- generated page count and static artifact size;
- production build duration;
- search response time over the complete static index;
- bounded graph render and interaction time;
- primary-page JavaScript bytes;
- mobile layout containment; and
- Lighthouse or equivalent accessibility and performance evidence on the protected preview.

Budgets are set from the measured V2 baseline before feature code and must prevent unexplained regressions. The build must remain static and avoid shipping the complete graph into every page.

## 14. Release sequence

1. Commit this approved design on the isolated branch.
2. Produce a detailed TDD implementation plan.
3. Implement and qualify the source manifest, extractor, canonicalizer, and independent consumer.
4. Generate and review the pinned compact catalogue.
5. Add unified search and Mathlib object projections.
6. adapt the bounded graph and object-detail experience;
7. elevate the real Resolve interaction;
8. update homepage, metrics, agents, developers, sitemap, and machine discovery;
9. run exact-head regression, adversarial, browser, accessibility, and performance qualification;
10. obtain a fresh architecture/security/claims review;
11. push `codex/living-knowledge-network`;
12. open a draft pull request with exact results, evidence, screenshots, limits, and residuals; and
13. create a protected Vercel preview if the existing project authorization permits it.

Production remains unchanged. No merge, production promotion, DNS change, mail change, or trust-policy expansion occurs without separate authorization.

## 15. Acceptance journeys

### Explore

A visitor searches for a genuine Mathlib declaration, opens its permanent occurrence page, verifies the exact pinned source location, and follows one `TYPE_REFERENCES` or module relation whose non-logical meaning is visible.

### Verify

A visitor opens Check record 001, sees the 48/48 finite observation and its exact limits, downloads the real record, and follows the existing independent replay instructions without being told that the whole language is verified.

### Discover

A visitor opens Resolve record 002, runs the labeled source-withdrawal simulation, sees dependent support become stale and the proposition remain UNKNOWN, and sees an unrelated bounded observation remain supported.

### Agent

An independent read-only consumer follows `/agents/`, obtains the pinned catalogue manifest, validates a shard and canonical object identity, and returns `SOURCE_INDEXED` without manufacturing verification, applicability, or permission.

## 16. Architectural extension points

This design supports later growth without asserting universal compatibility:

- new source revisions become new versioned catalogues and occurrence identities;
- new proof systems require separate adapters and evidence profiles;
- qualified semantic transport requires its own relation and correspondence receipt;
- additional source projects require explicit license, provenance, extraction, and relation contracts;
- Maps remain bounded projections over portable objects and typed relations;
- future Brains may select Maps, policies, evidence, and capabilities without changing historic object identities;
- living papers can link exact objects and receipts without publishing through MathGraph;
- capability lookup can attach only through qualified contracts; and
- federation can add discovery locations without centralizing verification authority.

The smallest-warranted-present principle removes a database, full-corpus graph, generic ontology, MCP server, arbitrary importer, and speculative research records from this release. It preserves the distinctions needed next: exact source occurrence, typed non-logical relations, independent evidence status, immutable Resolve semantics, and portable read-only consumption.

## 17. Known baseline residuals

The clean branch website qualification passes unchanged.

The repository-wide Python suite is not a clean standalone baseline without external inputs. At the approved base commit it produced 1,958 passes, 1 skip, 10 failures, and 19 setup errors. The errors require deliberately external `MATHGRAPH_*` source archives; the failures concern absent ignored SorryDB runner summaries/source caches and environment-sensitive research-ledger regeneration. They predate this branch and are outside the website/catalogue increment. The implementation must not weaken or silently skip them, must run relevant focused suites, and must preserve the exact residual report alongside final-head qualification.

