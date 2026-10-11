# MathGraph Website, Product & Architecture Audit

**Reconciled:** 11 October 2026<br>
**Repository:** [`metalogiclabs/mathgraph`](https://github.com/metalogiclabs/mathgraph)<br>
**Original audit baseline:** [`11944c2b44ac890ecc03c7f183ae74ea4640246c`](https://github.com/metalogiclabs/mathgraph/commit/11944c2b44ac890ecc03c7f183ae74ea4640246c)<br>
**Audit purpose:** identify the first unfinished product and protocol gates after the qualified publication of MathGraph Resolve record 002.

**Post-audit update:** Sections 1–8 preserve the audit baseline at `11944c2b…`.
Section 9 records subsequently observed local implementation and qualification at
`fbd3994642735f7599ec66bc89c2b9394a7b6b53`. It does not change the P0 release
authority, claim a new production release, or supersede any immutable evidence.

**Current-state correction, 11 October 2026:** Sections 1–9 are historical
observations, including their stage-specific references to “current,” “draft,”
and “production untouched.” PR #156 subsequently merged and deployed at
`4edc77cb1a4ff3a345b5feffcf7f2b38d3fbab0c`. Sections 10–14 reconcile that
foundation with V2 implementation through `7a43e7ff45eda96aee11c9efe056542f2498bbd8`.
Their Task 8 PENDING statements preserve the Task 7 checkpoint and are
explicitly superseded by [Section 15](#15-final-v2-release-candidate-reconciliation).
V2 remains unreleased, but exact implementation commit `9da8dbd…` has completed
the bounded draft-candidate qualification described there. See the
[current authority record](mathgraph_v2_release_authority_2026-10-11.md).

## 1. Executive correction

P0 Resolve publication is complete. It must not be reopened or represented as pending.

PR [#155](https://github.com/metalogiclabs/mathgraph/pull/155) merged the independently replayable Resolve publication into `main`. The merge commit is `11944c2b44ac890ecc03c7f183ae74ea4640246c`; its Git tree is byte-identical to the qualified PR head `7ec9f6224f933e68f66ad3f7cb2f40cc1b62d6c4`. The associated production deployment reports that exact `main` commit. Record 002 is published at [`/records/mg-living-warrant-openai-jpl-20261010/v1/`](https://mathgraph.org/records/mg-living-warrant-openai-jpl-20261010/v1/), and the isolated offline replay and website qualification both passed.

The first genuinely unfinished gate is now:

> Publish the already-used offline bundle and trust-policy formats as explicit, versioned, fail-closed protocol contracts, and qualify them with an independent schema/semantic consumer.

The next gates are modular, local Discover and Develop contracts; portable capability descriptions and qualification profiles; then the smallest truthful external-interoperability adapter. None requires a hosted service, central orchestrator, production mutation, or rewrite of an immutable record.

## 2. Release authority and observed current state

### 2.1 Source, qualification, and deployment

| Authority | Observed identity | Result | Exact boundary |
| --- | --- | --- | --- |
| Current `main` | [`11944c2b44ac890ecc03c7f183ae74ea4640246c`](https://github.com/metalogiclabs/mathgraph/commit/11944c2b44ac890ecc03c7f183ae74ea4640246c) | Current reviewed source | PR #155 merge; not a new research qualification by itself |
| Qualified PR head | [`7ec9f6224f933e68f66ad3f7cb2f40cc1b62d6c4`](https://github.com/metalogiclabs/mathgraph/commit/7ec9f6224f933e68f66ad3f7cb2f40cc1b62d6c4) | Qualified | Same full Git tree as current `main`: `93222c13b5013f22c5b8ccc3b4fdedba81e693d1` |
| Offline Resolve CI | [Actions run 38093442916](https://github.com/metalogiclabs/mathgraph/actions/runs/38093442916) | Passed | Isolated Python 3.11 replay, pinned bundle/policy, adversarial controls; no network during replay |
| Website/evidence CI | [Actions run 38093442852](https://github.com/metalogiclabs/mathgraph/actions/runs/38093442852) | Passed | Astro diagnostics, record integrity, contracts, rendering, build, HTML/link and independent consumer checks |
| Production deployment | Vercel deployment `6988066047`; [`mathgraph.org`](https://mathgraph.org) | Associated with `11944c2b…` | Website deployment only; it does not expand the evidence boundary |

The absence of a second Actions run on the merge commit is not treated as a missing qualification because the qualified head and merge commit have the same complete tree. That equivalence is a source-reconciliation fact, not a claim that arbitrary future merges inherit qualification.

### 2.2 Preserved website lineage

| Change | Authority | Current state |
| --- | --- | --- |
| MathGraph.org V1 | [PR #152](https://github.com/metalogiclabs/mathgraph/pull/152), merge `9ad69aa966ad4e07539a80d66d08a89948247a64` | Preserved |
| Supplied brand mark | [PR #153](https://github.com/metalogiclabs/mathgraph/pull/153), merge `39d33913550ce4ce6163b34153dc1f34754a1864` | Preserved |
| Agent discovery and exact-scope contract | [PR #154](https://github.com/metalogiclabs/mathgraph/pull/154), merge `6dc18ef159814d1125299eb7608b4af04d606511` | Preserved |
| Resolve record 002 and explorer | [PR #155](https://github.com/metalogiclabs/mathgraph/pull/155), merge `11944c2b44ac890ecc03c7f183ae74ea4640246c` | Published and qualified |

The current Astro site remains the implementation base. Its primary source is [`website/`](https://github.com/metalogiclabs/mathgraph/tree/11944c2b44ac890ecc03c7f183ae74ea4640246c/website); the immutable evidence catalogue is projected from committed records, not recomputed in browser code.

### 2.3 Record 002 immutable identities

| Object | SHA-256 |
| --- | --- |
| Offline bundle | `957080db79555f982fd3a314c263cf5177ef506969229e856897f0b19ccc1d62` |
| Separate trust policy | `09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a` |
| Independent Python consumer | `27a9be606040cc94a47c9b903dfc1cb24a86cbbc4e05ce71040c6c3d6e8d527b` |
| Record 002 transport | `0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87` |
| Resolve scenarios | `ed458ccbee85e3aa3f49d9d38e7ad5380515d00d707bac09c584cc4955b88181` |
| TypeScript consumer | `e7360df24b2fd0900c8ea88ccb1689163cec73a6c2e2347e4ab2b23b4d01bc2e` |
| Expected replay report | `8c7b30e1eb2a24d2960e170d36652ca95aa71b41075f673abe394e154ae66668` |

The exact reproduction boundary is documented in [`docs/mathgraph_resolve_v1_reproduction.md`](https://github.com/metalogiclabs/mathgraph/blob/11944c2b44ac890ecc03c7f183ae74ea4640246c/docs/mathgraph_resolve_v1_reproduction.md) and implemented by [`conformance/resolve_v1/consumer.py`](https://github.com/metalogiclabs/mathgraph/blob/11944c2b44ac890ecc03c7f183ae74ea4640246c/conformance/resolve_v1/consumer.py). The replay uses a digest-pinned `python:3.11-slim` image. Its accepted historical results remain exactly:

- three withdrawn documentary support paths: `STALE`;
- the three corresponding mathematical propositions: `UNKNOWN`;
- the unrelated, exactly scoped JPL 48-case observation: `WARRANTED_BOUNDED`.

The RealityGraph replay [run 38025236380](https://github.com/heathsanchez/realitygraph/actions/runs/38025236380) is implementation-independent but same-owner. It did not rerun the original Lean proofs and is not outside-organization adoption.

### 2.4 Local baseline recheck for this audit

From a clean worktree at `11944c2b…`:

- `npm ci` completed from the committed website lockfile.
- With the declared Node line (`24.15.0`), `npm run qualify` passed: Astro reported 0 errors, warnings, or hints; data checks were 68/68; contract checks 6/6; rendering checks 37/37; 13 pages built; built-site integrity, both independent consumers, and 37 internal links passed.
- `python -m pytest tests/test_mathgraph_resolve_publication_v1.py conformance/resolve_v1/test_consumer.py -q` passed: 27 tests and 52 subtests.
- The full monorepo command `python -m pytest -q` is **not** a clean repository-wide baseline: 1,946 passed, 1 skipped, 10 failed, and 19 errored. The 19 errors require three source fixtures supplied through `MATHGRAPH_OPENAI_HISTORY_MD`, `MATHGRAPH_V1_EVIDENCE_ZIP`, and `MATHGRAPH_V2_EVIDENCE_ZIP`. The 10 failures are older SorryDB/cache/generated-summary tests outside this website/protocol release slice. This residual must not be hidden, but it does not invalidate the independently isolated PR #155 gates.

No regenerated test artifact from the full-suite inspection was retained.

## 3. Product and protocol state

### 3.1 The four modules remain independent

| Module | Existing implementation | Public maturity on 11 October 2026 | Independence statement |
| --- | --- | --- | --- |
| Check | Record 001, publisher/resolver, OpenAPI preview and exact-scope consumer | Bounded-qualified record; public hosted resolver not deployed | Claims can be checked without Discover or Develop |
| Resolve | Strict offline consumer, immutable record 002, scenarios, read-only explorer | Bounded-qualified offline historical replay; published | Runs without website, network, LLM, or the other modules |
| Discover | `discovery_scheduler.py`, source adapters, residual/root machinery | Experimental research; no portable public operation contract | Can become a local advisory interface without Check/Resolve/Develop services |
| Develop | VDN Lean certificates and bounded finite developmental experiment | Experimental research; no portable public capability contract | May consume pinned evidence packages; no hosted dependency is justified |

The website is a publisher and consumer of these contracts. It is not the protocol authority. No new microservice is required for the unfinished gates.

### 3.2 Status axes remain separate

The current record model correctly keeps these axes independent:

1. **Epistemic result:** warranted within scope, refuted by qualified evidence, or unknown.
2. **Lifecycle:** current, stale, superseded, revoked, or requiring requalification.
3. **Research maturity:** proposed, experimental, bounded-qualified, or production-qualified.
4. **Action policy:** permit, deny, or require more evidence.
5. **Freshness:** historical snapshot versus checked current state.

A byte hash establishes identity, not truth. A signature establishes an authenticated statement under a policy, not mathematical truth. Documentary withdrawal makes a support route stale; it does not refute a theorem. A valid historical replay does not prove there is no newer revocation.

## 4. Gap and acceptance matrix

Priorities mean: **P0-next** is the first unfinished release gate; **P1** is required for practical modularity; **P2** is subsequent qualified research; **P3** is ecosystem expansion. “Existing implementation” identifies code or evidence already present rather than proposing a replacement.

| Area | Exact existing implementation | Missing distinction | Priority | Verification obligation | Smallest qualifying next action |
| --- | --- | --- | --- | --- | --- |
| Release authority ledger | PRs #152–#155; `.well-known/mathgraph.json`; record index; release workflows | No single committed ledger reconciles source tree, qualification run, production deployment, immutable digests, and known suite residuals | P1 | Ledger entries must be exact, linked, and incapable of expanding evidence scope | Maintain this audit plus a small machine-readable release sidecar on future qualified releases; do not edit historic record bytes |
| Resolve bundle contract | [`conformance/resolve_v1/fixtures/bundle.json`](https://github.com/metalogiclabs/mathgraph/blob/11944c2b44ac890ecc03c7f183ae74ea4640246c/conformance/resolve_v1/fixtures/bundle.json) and strict consumer checks | `mathgraph.resolve-bundle.v1` is implemented but has no normative versioned JSON Schema independent of the consumer code | **P0-next** | Reject duplicate keys, unknown fields/types, non-base64 data, byte-size/hash mismatch, unsupported versions, and member substitution | Publish a strict Draft 2020-12 schema outside `website/`, mirror it byte-for-byte for public download, and test the existing immutable bundle without modifying it |
| Resolve trust-policy contract | [`conformance/resolve_v1/trust-policy.json`](https://github.com/metalogiclabs/mathgraph/blob/11944c2b44ac890ecc03c7f183ae74ea4640246c/conformance/resolve_v1/trust-policy.json) plus exact admissions in `consumer.py` | Implemented policy shape is implicit; authenticity, semantic admission, freshness, and action authority need explicit orthogonal semantics | **P0-next** | Exact kind/scope/source/verifier/assumptions; unauthorized rehash rejected; unknown verifier or relation remains `UNKNOWN`; policy hash supplied independently | Publish strict schema and prose contract, then validate with a separate schema consumer plus the existing independent semantic replay |
| Independent contract conformance | Python offline consumer and website TypeScript/static consumers | Existing consumers validate semantics, but no separately implemented schema-conformance package proves portable decoding rules | **P0-next** | A consumer that imports neither producer nor website logic must accept exact fixtures and reject mutations, duplicate keys, versions, unknown semantic types, and forged producer statuses | Add a small isolated conformance runner using an independent implementation and fixed positive/negative corpus; run without network |
| Check interface | Qualified L4YAML record, public JSON, source pins, [`openapi.preview.json`](https://mathgraph.org/evidence/mg-l4yaml-source-check-20261010/openapi.preview.json) | No generic public Check protocol; the resolver remains a preview/local contract | P1 | New profiles cannot inherit the L4YAML warrant; exact verifier, source, environment, claim kind and scope are mandatory | Inventory the current bounded profile as a versioned adapter; do not generalize or deploy a hosted service merely to satisfy architecture |
| Resolve expansion | Qualified least-support replay, alternative-route and rootless-cycle controls, static/interactive parity | Current applicability monitoring and authenticated lifecycle publication are not implemented | P2 | Historical qualification, current applicability, freshness, revocation, and authorization remain separate | Keep record 002 immutable; define any current-state/lifecycle profile as a new independently authenticated contract |
| Discover operation | [`mathgraph/discovery_scheduler.py`](https://github.com/metalogiclabs/mathgraph/blob/11944c2b44ac890ecc03c7f183ae74ea4640246c/mathgraph/discovery_scheduler.py), [`discovery_candidate_sources.py`](https://github.com/metalogiclabs/mathgraph/blob/11944c2b44ac890ecc03c7f183ae74ea4640246c/mathgraph/discovery_candidate_sources.py), active residual and root discovery | Website “discovery” schemas are agent-site manifests, not a Discover operation; no strict portable request/result contract exists | P1 | Output always advisory; no terminal form; finite/bounded status preserved; exact source artifact pointers; deterministic policy; malformed/unsupported input fails closed | Add `mathgraph.discover.request.v1` and `.result.v1`, a stdlib local adapter/CLI, and one source-grounded historical example without running a solver |
| Discover validation | Existing `DiscoveryCandidate`, `make_policy`, `validate_candidate`, `allocate_attention` | Current internal loaders coerce malformed numbers, allow duplicate IDs to break `top_k`, overwrite attempted authority promotion, and conflate negated status prose with promotion | P1 | Reject duplicates, booleans-as-integers, NaN/Infinity, authority attempts, and invalid targets; legitimate boundary disclaimers remain valid | Put strict decoding in the public boundary before reuse of scoring; add positive and adversarial tests first |
| Discover provenance | Evidence-pack manifests and locally copied source artifacts | Loader reads declared hashes but does not verify every referenced source; missing optional files can disappear rather than produce diagnostics | P1 | Digest/size/locator agreement; missing and corrupt are distinct; source correspondence does not authenticate authorship or validate the historical experiment | Add an explicit source adapter with artifact checks and diagnostics for the selected read-only example |
| Discover packaging independence | Scheduler/source modules are largely standard-library code | Importing a submodule executes the large `mathgraph/__init__.py` and can require optional `pandas`, while base dependencies are empty | P1 | Clean base-install import and CLI smoke with no pandas, hosted service, network, Lean, or solver | Establish a small protocol package/import boundary rather than duplicating the scoring algorithm |
| Develop research | [`verified-developmental-navigation`](https://github.com/metalogiclabs/mathgraph/tree/11944c2b44ac890ecc03c7f183ae74ea4640246c/verified-developmental-navigation) and [`experiments/developmental_capability_growth_v1`](https://github.com/metalogiclabs/mathgraph/tree/11944c2b44ac890ecc03c7f183ae74ea4640246c/experiments/developmental_capability_growth_v1) | Lean structures and bounded experiments are not portable capability contracts or registry admissions | P1 | Preserve declared carrier, action language, coverage proof, sham, ablation, source pins, retention, and exact cost model | Publish a strict capability-description schema plus an explicit evaluation object; expose the bounded finite experiment as `EXPERIMENTAL` until independently admitted |
| Bounded Develop profile | Eight-state closure change and complete 256 Boolean one-bit-refinement audit; audit rerun produced two `PASS` verdicts | Standard-output verdicts do not bind a reusable constructor, boundary, verifier, evidence, or consumer trust policy | P1 | Independent finite-profile consumer must recompute old exclusion, new witness, sham failure, ablation, distinct reuse, and all-refinement counts | Package pinned inputs and write a different small replay implementation before any `QUALIFIED_BOUNDED` registry entry |
| VDN Lean capability evidence | `CapabilityPhaseChangeCertificate` and Palomar seed theorems in committed Lean sources | No declaration/toolchain/axiom/source receipt binds the Lean theorem to a public portable contract | P2 | Native Lean replay; exact declaration names, source hashes, toolchain, axioms, applicability and contract correspondence | Create a candidate descriptor now; admit it only after a pinned native replay and independent contract-to-declaration binding |
| Capability Family Compiler | Historical MDA/lift-x references and bounded precursor research | No compiler, general lift-x family theorem, independently qualified synthesis trace, or portable family-constructor receipt is present in current `main` | P2 | Actual Lean theorem over `n`; fresh instances; invalid-domain and parent-removal controls; restart; strong baselines and full costs | Do not claim it. After P1 portability, build it as a separate prospective experiment |
| Capability contract | Internal adapter capability descriptions and VDN/finite evidence | No public `mathgraph.capability-contract.v1`; qualification is currently liable to be confused with description | P1 | Contract identity, exact types/scope, preconditions, guarantees, assumptions, boundary, implementation, receipts, limitations and critical-extension rules | Publish a strict descriptor and separate evaluation schema; a descriptor cannot self-assert `VERIFIED` |
| Capability registry | Protocol page and discovery manifest say `PROPOSED`, zero entries | No registry schema/admission policy; no current artifact meets a new portable qualification profile | P1 | Empty registry is valid; only independently admitted entries appear; unsupported critical extensions yield `UNKNOWN` | Publish versioned empty/candidate indices and the admission contract first; add the first entry only after independent finite-profile replay |
| Developer consumers | Resolve Python/TypeScript examples and local Check preview | No common local CLI for inspect/verify/resolve/discover/capability contract validation | P1 | Each command must expose exact authority, freshness, scope, reason codes and nonzero structural errors; no arbitrary execution/fetch | Extend local, read-only tools only after schemas stabilize; do not advertise a hosted endpoint |
| Website information architecture | `/`, `/check/`, `/resolve/`, `/records/`, `/agents/`, `/developers/`, `/protocol/` | No `/discover/`, `/develop/`, or `/capabilities/`; navigation cannot yet show modular work without overstating maturity | P1 | Static pages and machine contracts agree; experimental/proposed labels explicit; mobile/accessibility/build/link checks pass | Add restrained static pages backed by qualified contract/examples; keep the capability catalogue empty until admission |
| Machine discovery | `/llms.txt`, `/.well-known/mathgraph.json`, record index and exact-scope rules | Manifest source pointer predates PR #155 even though indexed record bytes agree; new contract locations are absent | P1 | Exact artifact hashes and current qualified source; no implied hosted service | Update the sidecar and discovery pointers in the next qualified release without changing immutable record bytes |
| in-toto interoperability | Exact content-addressed records and policies already exist | No standard artifact-attestation wrapper | P1 | Round-trip must preserve subject digest, object schema, claim kind/scope, assumptions and evidence references; wrapper grants no trust | Implement one deterministic **unsigned** [in-toto Statement v1](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md) binding profile and negative round-trip tests |
| Sigstore | None in the current release | No signer identity, issuer/root policy, bundle verifier, fixture or signature lifecycle | P2 | Signature, signer policy, transparency, semantic qualification and freshness are separate outcomes | Document the extension point using the official [Sigstore bundle specification](https://docs.sigstore.dev/about/bundle/); defer implementation until real signing policy and test vectors exist |
| SCITT | None in the current release | No COSE/receipt verification or trusted transparency service policy | P3 | Registration receipt proves attributable log inclusion under policy, not truth | Map concepts to [RFC 9943](https://datatracker.ietf.org/doc/rfc9943/); preserve attachments opaquely until an actual verifier is qualified |
| RATS | None in the current release | No RATS evidence/appraisal wire-format implementation | P3 | Device-attestation evidence must not be relabelled as mathematical proof evidence | Use [RFC 9334](https://datatracker.ietf.org/doc/rfc9334/) only as an architectural comparison until a real consumer requires a profile |
| Publisher authenticity | Independent pins and self-hashes detect substitution | Same-origin catalogue and artifact hashes do not alone authenticate a publisher or prove an uncompromised host | P2 | Separate authenticated signer/root policy and rollback/replay controls; authenticity cannot promote semantic qualification | First bind exact artifacts through unsigned in-toto; later add a detached authenticated statement under a documented external trust root |
| Lean evidence profile | `lean-evidence-profile-draft-1.schema.json` and protocol page | No qualified adopter; first real record may change the schema | P2 | Native proof replay, theorem names, source/toolchain/Mathlib pins, axioms, license, and statement correspondence | Keep identity explicitly `draft`; qualify against a real record before stable `v1` |
| Crystal/MGSO and cryptographic warrants | Historical semantic-object design and bounded ML-DSA experiment | No normative MGSO implementation/test vectors in current tree; no audited production authentication protocol | P3 | Preserve historic bytes; unknown semantic types retained or declined; no “quantum-proof” or truth-from-signature claim | Locate and pin the normative format before an adapter; keep ML-DSA work research-only |
| Hosted resolver and MCP | OpenAPI preview/local resolver; manifest says not deployed | No qualified public read-only service or MCP adapter | P2/P3 | Method/input/resource protections, exact pins, malformed input, abuse bounds, logging boundary, fail-closed semantics | Do not deploy for architectural symmetry; qualify the local contract first, then add a service only for a concrete consumer need |
| Monorepo qualification ergonomics | Strong isolated workflows for Check/Resolve/site | Full pytest requires externally supplied source fixtures and has unrelated older failures | P1 | Release workflows declare exact fixture prerequisites and isolate relevant gates; failures remain visible | Add a documented test matrix distinguishing hermetic release gates, externally provisioned evidence suites and known unrelated residuals |

## 5. Concrete next contract boundaries

### 5.1 Resolve bundle v1

The immutable bundle already uses only:

- `schema` — exact `mathgraph.resolve-bundle.v1`;
- `provenance` — pinned producer and prior replay identities;
- `members` — a map whose values contain exact `encoding`, `data`, `size`, and `sha256`.

The schema must describe these existing bytes; it must not regenerate them. Semantic replay continues to be governed by an independently supplied policy. A conforming decoder rejects duplicate JSON keys before schema validation and checks decoded size and SHA-256 independently.

### 5.2 Resolve trust policy v1

The policy already separates admitted member identities from receipt admission. Its schema must preserve exact:

- member names, sizes and hashes;
- receipt identifiers;
- evidence kind;
- claim scope;
- source member;
- verifier identity;
- assumptions;
- admitted outcome.

The policy digest must arrive through an independent pin. A record containing its own policy hash cannot authorize itself. Unsupported schema versions, evidence kinds, verifier identities, assumption contexts or semantic relationships remain `UNKNOWN` or are rejected structurally; they are never coerced into known semantics.

### 5.3 Discover v1

The minimum operation is a pure local advisory ranking interface, not a discovery service:

`discover(request) -> result`

Its request supplies a versioned policy and source-bound advisory candidates. Its result supplies deterministic ranks, allocation weights, rejections and diagnostics. The result always says `advisory_only: true`, `can_promote_truth: false`, and `verification_status: NOT_CHECKED`; it contains no accepted terminal claim.

The first example should use the existing `recursive_transfer_replay_candidate` derived from the locally checked historical evidence pack. Its referenced `gate_results.csv` has SHA-256 `195f17d394125df425b3cd8481d3121886534474996ea5943f83bbbb6fa78869`; its `route_summary.csv` has SHA-256 `b9c6b402297194dfa687361d8bb5171a311f291b77e0f56c59fe5bba693fab4e`. This proves local byte correspondence only. It does not rerun or authenticate the historical experiment.

### 5.4 Capability contract v1

The smallest portable descriptor must identify:

- exact immutable `id`, `version`, and semantic `profile`;
- claim `id`, `kind`, and exact `scope`;
- typed input/output schema references;
- explicit preconditions, guarantees and assumptions;
- a pinned boundary artifact;
- a pinned implementation artifact;
- pinned evidence references;
- nonempty limitations;
- versioned critical/noncritical extensions.

Qualification belongs in a separate evaluation object. A structurally valid descriptor with no admitted verifier receipt has `qualification: UNKNOWN`, `current_applicability: UNKNOWN`, `freshness: NOT_CHECKED`, and `action_authorization: NONE`. Capability qualification does not introduce a fourth mathematical terminal form.

### 5.5 First external binding

The first adapter should be a deterministic unsigned in-toto Statement v1 whose subject is the exact SHA-256 of a MathGraph contract or record and whose predicate binds the exact object schema and claim boundary. “Unsigned” must be explicit. Importing the wrapper verifies byte and field correspondence only; it does not authenticate a publisher or qualify the claim.

Sigstore, SCITT and RATS remain documented extension points until independently exercised trust policies and fixtures exist.

## 6. Smallest safe implementation sequence

1. **Freeze and qualify the existing Resolve contracts.** Add root protocol schemas, exact public mirrors, prose semantics and a separate conformance runner. Preserve every record 001/002 byte and digest.
2. **Establish the independent package boundary.** Add a small standard-library protocol package whose import does not execute the existing monolithic `mathgraph/__init__.py` or require optional research dependencies.
3. **Ship local Discover v1.** Strict request/result decoding, deterministic reuse of existing ranking semantics, a real source-backed advisory example, CLI and negative tests. Do not change the manifest to “hosted.”
4. **Ship capability description/evaluation v1.** Add an empty qualified registry and an experimental bounded finite example. Independently replay the finite profile before admitting an entry.
5. **Add the first external adapter.** Deterministic unsigned in-toto export/import with wrong-subject, field-stripping and scope-mutation controls.
6. **Project the contracts into Astro.** Add `/discover/`, `/develop/`, and `/capabilities/`; update protocol/developer/agent discovery pages; retain the current visual system and explicit maturity labels.
7. **Requalify the release candidate.** Run protocol conformance, targeted historical suites, Node/Astro qualification, byte-parity checks, desktop/tablet/mobile review, and an isolated preview deployment. Production promotion remains a separate authorized action.

## 7. Explicitly deferred work

The following are not P0-next acceptance requirements:

- a hosted resolver, public proof compiler, database or microservice mesh;
- MCP;
- authenticated Sigstore/SCITT/RATS operation;
- stable Lean evidence profile v1;
- MGSO/Crystal transport without its normative implementation and vectors;
- Capability Family Compiler V1;
- a claim of automatically discovered general constructors;
- a living scientific-paper editor;
- outside-organization adoption;
- production deployment or DNS changes.

## 8. Acceptance statement

The architecture is ready to advance without repeating P0. Resolve record 002 is a qualified historical publication with an offline, fail-closed replay. The remaining work is to turn implicit formats and experimental research seams into independently implementable contracts while retaining conservative semantics.

Success for the next release candidate is therefore narrower than the full programme:

1. an independent consumer validates the versioned Resolve bundle and trust policy and recomputes their bounded meaning;
2. Discover can run locally and emit only source-bound advisory results;
3. Develop artifacts can be described portably without self-qualification;
4. a bounded profile can be independently evaluated before registry admission;
5. an external in-toto wrapper can preserve exact identity and scope without adding trust;
6. the website accurately projects those contracts while all historical identities stay unchanged.

Anything beyond those observations remains experimental, proposed, or `UNKNOWN` until its own acceptance gate passes.

## 9. Observed post-audit release candidate

The local branch `codex/mathgraph-contracts-and-modules-v1` now implements the
contract sequence in Section 6 through the Astro projection. The implementation
head was `b7bbdc8a3e0d30fb752882f0ed83048c2543bec1`; release qualification found
and fixed a combined-pytest module-name collision with two empty package markers
in `0037dbe515c43481ba02426e56bc7eaefc296285` (tree
`83506b3979ea5f8cf56e9e76d2a7f190dffb80fd`). No consumer, fixture, or test logic
changed in that correction. Independent whole-branch review then found three
interface gaps: incomplete CI coverage, omitted public discovery links for the
Resolve schemas, and unnormalized Python parser-limit exceptions. Commits
`d335223d…`, `ae65f940…`, and `fbd39946…` close those gaps; the reviewed executable
head is `fbd3994642735f7599ec66bc89c2b9394a7b6b53`, tree
`5eb51b98b76a75e2395dfce319799f54d4781d67`. The detailed commands, artifact
pins, screenshots, and limits are in the [release-candidate evidence report](mathgraph_modular_contracts_release_candidate_2026-10-11.md).

| Audit gate | Observed local outcome | Retained boundary |
| --- | --- | --- |
| Resolve format contracts | Eight normative schemas across the release, including explicit Resolve bundle/policy v1, have exact public mirrors; separate structural validation and historical semantic replay pass | The new structural consumer does not itself replay the graph; policy pins remain external trust inputs |
| Module independence and Discover | Dependency-free package, shared ranking arithmetic, strict advisory request/result, local CLI, and source checks implemented | The example is `PARTIAL` / `NOT_CHECKED`; nine local artifacts match; absent candidate-score CSV and SQLite ledger leave full historical replay unavailable |
| Capability description and admission | Descriptor/evaluation separation and one independently replayed finite registry entry implemented | `QUALIFIED_BOUNDED` covers the exact eight-state profile only; same-owner implementation independence, not external adoption |
| Finite Develop replay | Original scripts and separate consumer agree on old closure size 4, refined size 16, sham/ablation/reuse controls, 256 refinements, 32 successes, eight partition classes, and 4/28 successful three-/four-cell features | Original implementation provenance is not a general runtime certification; VDN Lean remains experimental and the Capability Family Compiler is not implemented |
| Interoperability | Deterministic unsigned in-toto correspondence profile and negative controls implemented | No signer authentication, semantic promotion, transparency, freshness, or action authority; Sigstore/SCITT/RATS remain unimplemented |
| Website projection | `/discover/`, `/develop/`, `/capabilities/`, exact artifact downloads, and discovery V3 implemented | Static local candidate; V1/V2 schema identities and all historical evidence remain unchanged |

Fresh final-head checks on 11 October 2026 passed: expanded combined conformance,
interoperability, protocol-import and legacy-compatibility coverage **311 tests
and 72 subtests**; historical publication/import **24 tests**. Earlier standalone
replay checks additionally passed **15 tests and 52 subtests** for Resolve and
**147 tests** for capability. Both macOS isolation
harnesses enforced IPv4/IPv6 denial and repository unavailability, audited
standard-library imports, and produced identical replay pairs. Resolve output
remains `8c7b30e1eb2a24d2960e170d36652ca95aa71b41075f673abe394e154ae66668`;
finite capability output is
`5d85d7117532fd777d7b2948ab1138bec47db81176327fdb9591e0be7fe2a006`.
The enforced-isolation test requires host permission to create its nested
sandbox; a restricted final repeat failed that prerequisite, and the complete
gate was rerun with the required permission. No isolation test was skipped.

Complete website `qualify` under cached Node **24.15.0** / npm **12.2.0** passed:
Astro 49 files with zero diagnostics; data **68/68**, contracts **16/16**,
rendering **37/37**; 16 Astro pages, 17 checked HTML pages, 32,206 client bytes;
HTML validation, **58 links**, and both independent consumers passed. The first
sandboxed attempt stopped at loopback `listen EPERM`; the complete rerun with
local-server permission exited zero. Browser checks covered **21 route/viewport
combinations**; nine new representative screenshots are preserved under
`website/qa/screenshots/`. These are accessibility-oriented checks, not a full
accessibility certification.

All Section 2.3 immutable hashes were rechecked unchanged. Git comparisons with
`11944c2b…` also preserve record 001/002 evidence, source/data projections, original
developmental scripts, consumers, lockfile, and deployment configuration. Eight
schema mirrors, the registry mirror, and ten built artifact downloads matched
their normative sources byte-for-byte. The finite contract remains
`24e639b9181af313100504e0aa525536197d868810e6ffdb5093fd13501577a8` and the registry
remains `7ae45ef09ce492856234872c12adc6999667b14899a008baddc19687934b1358`.

Task-scoped and whole-branch reviews completed. The final review found no
authority or immutable-evidence regression; its three interface findings were
fixed and the scoped re-review approved the fixes with no remaining finding.

The branch was then published in draft PR
[#156](https://github.com/metalogiclabs/mathgraph/pull/156) at exact head
`eabed36460e3a6dbc4681ebdc154d8c745c49cfc`. Fresh remote gates passed:
[Linux protocol conformance 38104216174](https://github.com/metalogiclabs/mathgraph/actions/runs/38104216174),
[independent Resolve replay 38104217672](https://github.com/metalogiclabs/mathgraph/actions/runs/38104217672),
[published evidence 38104216146](https://github.com/metalogiclabs/mathgraph/actions/runs/38104216146),
and both jobs in [website/evidence run 38104216133](https://github.com/metalogiclabs/mathgraph/actions/runs/38104216133).
Vercel deployment `6989732937` associated the same head with the protected
[preview](https://mathgraph-iak1skcjt-over-market.vercel.app/). Authenticated
smoke checks returned 200 for the new routes and machine contracts; downloaded
manifest, Resolve schemas, registry, and `/llms.txt` matched the qualified local
bytes exactly. Discover, Develop, and Capabilities were rendered and visually
inspected on the preview.

Production remains untouched. No promotion, merge, production alias, DNS,
registrar, mail, or hosted execution-service change occurred. The original
full-suite fixture and SorryDB residual in Section 2.4 remains documented and
was not rerun. Current applicability remains `UNKNOWN`; freshness/revocation
remain `NOT_CHECKED`; no action is authorized. Further research and adoption
gaps in Sections 4 and 7 remain open unless explicitly closed above. Human
review and separate explicit approval remain necessary before any production
promotion.

## 10. Current authority and V2 implementation checkpoint

GitHub authority was rechecked on 2026-10-11 at approximately 10:24 UTC.
Remote `main` is `4edc77cb1a4ff3a345b5feffcf7f2b38d3fbab0c`, the merge of
[PR #156](https://github.com/metalogiclabs/mathgraph/pull/156). Its final head
`349764269756bc6c679ee99cc9147609980963d8` and merge share the complete Git tree
`a2efc76cb1b95b617e60173d01a85ecd7cdd65d7`. Four final-head release gates passed;
no merge-commit Actions run was returned. Production deployment `6990666088`
reports that merge commit and success. Exact CI/deployment links, immutable
hashes and the V2 commit ledger are in the [authority record](mathgraph_v2_release_authority_2026-10-11.md).

This closes the historical Section 1/4/5/6 proposals for Resolve format
contracts, a dependency-free protocol package, local advisory Discover,
capability description/evaluation, the independent finite profile and the
unsigned in-toto binding. It does not close their research or current-state
obligations. Discover remains `PARTIAL` / `NOT_CHECKED`; the general capability
descriptor evaluator remains `UNKNOWN`; one exact finite profile is
`QUALIFIED_BOUNDED`; VDN Lean is `EXPERIMENTAL`; CFC is `NOT_IMPLEMENTED`.

[PR #157](https://github.com/metalogiclabs/mathgraph/pull/157) remains OPEN/draft
at `ba94d2827fbc0dc296ea3507ae034f00f9c58a5e`. Its consequence envelope is
candidate research, not a normative replacement for any existing contract.
Conditional Lean laws do not establish that a real imported certificate
discharges their premises. An archival workflow does not establish retained
artifact availability. These distinctions remain in the
[obligations register](mathgraph_v2_unresolved_obligations_2026-10-11.md).

At this Task 7 checkpoint, V2 Tasks 1–6 were implemented through `7a43e7ff…`.
The task reports recorded local tests and browser checks at their respective
commits; they were not V2 remote CI, a protected-preview receipt or final
release approval. The PENDING Task 8 statement here is historical and
superseded by Section 15. No V2 production promotion or DNS change has been
performed.

The separate axes are historical epistemic result, lifecycle, research
maturity, freshness, current applicability and action authorization. Import
receipt validation, finite-profile replay and original native proof replay
are different operations; a browser recognition or map export has authority
`NONE`. These distinctions supplement the historical Section 3 list.

## 11. V2 feature and gap disposition

This section preserves the Task 7 gap snapshot. Its Task 8 action cells are
superseded by Section 15; the missing distinctions remain valid unless that
section explicitly changes them. `Release` means a gate of the V2 candidate,
not a completed release.
`Research` and `Separate production` do not block the bounded V2 implementation.
Commit labels T1–T6 below refer to exact identities in the
[implementation ledger](mathgraph_v2_release_authority_2026-10-11.md#implementation-ledger).
Each test citation identifies executable coverage, not an assertion that Task 8
has already run it. The [browser report](mathgraph_v2_browser_qualification_2026-10-11.md)
separates prior local observations from all pending preview checks.

| Area | Exact existing implementation | Missing distinction | Priority | Verification obligation | Smallest qualifying next action |
| --- | --- | --- | --- | --- | --- |
| Supported import | T1: [consumer](../conformance/import_v1/consumer.py), [schema](../protocol/schemas/import-result-v1.schema.json), [tests](../conformance/import_v1/test_consumer.py) | Historical record/policy validation is not original Lean/source-suite replay | Release | Standalone deterministic output; strict parsing; source/scope/verifier/policy substitutions; presentation rejection | Repeat final-head conformance in Task 8; retain replay NOT_PERFORMED |
| Browser workflow | T3/T4: [workbench](../website/src/scripts/import-workbench.ts), [fixture](../website/tests/fixtures/import-workflow.json), [browser test](../website/tests/import-workbench.browser.mjs) | Exact-byte recognition has no warrant authority; only the declared record-bound handoff applies | Release | Identity/scope/evidence/unknowns through all six stages; changed bytes reset; actual export rejected by Python; no interaction fetch | Exercise protected preview success/failure/unsupported paths |
| Object adapters | T2: [adapters](../website/src/lib/object-projections.ts), [tests](../website/src/lib/object-projections.test.ts) | Partial views are not source round trips or a universal ontology | Release | Source parity, independent axes, noninterference, critical-extension rejection | Recheck exact adapters and disclose losses in Section 12 |
| Object detail | T5: [detail component](../website/src/components/ObjectDetail.astro), [routes](../website/src/pages/objects/[slug].astro), [rendering tests](../website/tests/rendering.test.ts) | Missing projected attribution is UNKNOWN; lineage locator is not chronology or equivalence | Release | All 14 detail routes, source/export links, six axes and honest absent fields | Preview source-backed details at all target widths |
| Knowledge map | T2/T5: [map contract/reader](../website/src/lib/knowledge-map.ts), [tests](../website/src/lib/knowledge-map.test.ts), [component](../website/src/components/KnowledgeMap.astro) | Display traversal is not certified path composition; current relations require same-source provenance | Release | Directed typed endpoints, exact occurrences, provenance, source pins, omissions, separate reader and evidence rejection | Preview filters, traversal, actual downloads and no-JS fallback |
| Map history navigation | T5 fix `e1b13678…`: [script](../website/src/scripts/knowledge-map.ts), [browser regression](../website/tests/knowledge-map.browser.mjs) | Fragment/reload/Back/Forward selection must agree without hijacking unrelated fragments | Release | Existing exact-fragment and history checks at 1440/768/390 | Repeat on immutable preview |
| Outcome navigation/homepage | T4: [layout](../website/src/layouts/BaseLayout.astro), [home](../website/src/pages/index.astro), [navigation test](../website/tests/outcome-navigation.browser.mjs) | Outcome navigation does not expand supported inputs or module maturity | Release | Active child groups, disclosure focus, keyboard/no-JS, stable legacy routes, real source-derived examples | Preview navigation and measure transfer/loading |
| Searchable catalogues | T6/fix: [component](../website/src/components/CatalogueFilter.astro), [script](../website/src/scripts/catalogue-filter.ts), [browser test](../website/tests/catalogue-filter.browser.mjs) | Filtering changes display only; qualified and experimental entries stay distinct | Release | Keyboard search/select/reset, honest no-match, full no-JS content, 390/901/1024 regression | Repeat on preview, including breakpoint cases |
| Agent/developer/protocol docs | T6: [agents](../website/src/pages/agents.astro), [developers](../website/src/pages/developers.astro), [protocol](../website/src/pages/protocol.astro), [contract tests](../website/tests/contracts.test.ts) | Object/Relation/Evidence/Resolution/Transition are responsibilities, not a new ontology; CLOSE/ACT/REFINE remain distinct | Release | Executable commands, exact artifacts, correspondence-only in-toto, no hosted/MCP/action promotion | Run final documentation/consumer gates |
| Discover/Develop boundaries | PR #156 source retained; T6 [rendering tests](../website/tests/rendering.test.ts) | Advisory discovery and one finite replay do not qualify CFC, VDN Lean or autonomous growth | Release | PARTIAL/NOT_CHECKED versus QUALIFIED_BOUNDED/EXPERIMENTAL/NOT_IMPLEMENTED remain explicit | Check machine/UI agreement on preview |
| TypeScript MIME | T6: synchronized [root config](../vercel.json) / [site config](../website/vercel.json), [built checks](../website/scripts/check-built-site.mjs) | Local header configuration is not observed deployed HTTP behavior | Release | Exact-path text/plain; charset=utf-8, nosniff retained, original byte digest, direct browser rendering | Task 8 preview header/digest/browser check PENDING |
| About/Contact | T6: [About](../website/src/pages/about.astro), [Contact](../website/src/pages/contact.astro), rendering tests | Public repository contact is not a response SLA or endorsement | Release | Correct routes and facts; no fabricated relationships | Preview route/link inspection |
| Record 002 social card | T6/fix: [generator](../website/scripts/generate-social-card.mjs), rendering mismatch regression | Presentation metadata is outside immutable evidence digests | Release | Derive actual counts/statuses; reject inconsistent temporary source; preserve record bytes | Check preview metadata and image |
| Machine discovery | T6 [llms.txt](../website/src/pages/llms.txt.ts); existing [.well-known manifest](../website/public/.well-known/mathgraph.json) unchanged; [module tests](../website/tests/modules.test.ts) | Discovery metadata is not qualification or a hosted endpoint | Release | Contract locations/bytes and advertised boundaries agree | Verify final built and preview downloads |
| Evidence integrity | Existing record 001/002, Resolve/capability artifacts; T1 schema/fixture parity tests | Integrity is not publisher authenticity or current truth | Release | Compare historical bytes and all public mirrors at exact final source | Repeat parity audit in Task 8 |
| Release reconciliation | These Task 7 docs; historical PR #156 evidence remains separate | No final V2 source/CI/preview/review identity yet | Release | One clean final commit bound to immutable deployment, successful gates and browser/review report | Complete Task 8; all such identities PENDING |
| www redirect | Baseline observation in [design](superpowers/specs/2026-10-11-mathgraph-v2-foundation-design.md) | Duplicate 200 is a production-domain policy issue | Separate production | Explicit authorization plus redirect/canonical-host checks | Leave deferred; do not alter DNS or aliases |

## 12. Two-domain extension test and protected future

The [adapter matrix test](../website/src/lib/object-projections.test.ts)
compares source contracts, verifier authority, assumptions, lifecycle, replay
boundary, unknowns and unsupported semantics directly with committed inputs.

| Distinction | Record 001 evidence | Finite capability |
| --- | --- | --- |
| Contract | `mathgraph.public-consequence-record.v1` | `mathgraph.capability-contract.v1`, profile `mathgraph.finite-representation-refinement.v1` |
| Historical result / maturity | WARRANTED_BOUNDED; projected research maturity UNKNOWN | QUALIFIED_BOUNDED; projected research maturity UNKNOWN |
| Scope | 48 decoded pinned YAML-suite cases plus four controls; separately scoped original Lean lemmas | Eight ordered Boolean states, five named refinements, all 256 Boolean one-bit refinements; discovery AND and distinct reuse OR targets |
| Verifier authority | Historical LEAN_GUARDS_AND_COMPILED_TRYPARSE and ORIGINAL_JPL_LEAN_PROOF_OBJECTS | `urn:mathgraph:verifier:finite-refinement-independent:v1`, separately pinned consumer and policy; independent implementation, same owner |
| Assumptions | Source/suite commits, specified decoder, finite case selection, toolchain and scoped theorem interpretation; empty receipt list is not unconditional correctness | Exact carrier; total deterministic Boolean policies; distinct reuse means two target functions within one owned source |
| Replay | Import validates historical receipt/policy; original Lean, kernel admission and source suite NOT_PERFORMED | Profile consumer recomputes finite gates; original candidate program is provenance, not executed or runtime-certified; website adapter only displays pinned results |
| Lifecycle/freshness | Website catalogue lifecycle CURRENT; projected freshness NOT_CHECKED_AFTER_SNAPSHOT; importer lifecycle UNKNOWN and freshness NOT_CHECKED | Lifecycle UNKNOWN; freshness/revocation/supersession NOT_CHECKED |
| Applicability/authorization | Current applicability UNKNOWN; read-only, no automatic authorization | Current applicability UNKNOWN; action authorization NONE |
| Unknown/unsupported | Whole-language correctness, statement fidelity, generalization, human digestion, whole-input extraction and current requalification | Universal invention, autonomous improvement, global feature uniqueness, external adoption and current-state authority |
| Projection loss | Attribution/publisher, evidence-run links, normalization and known separator are omitted from the object projection | Opaque contract extensions and full policy/receipt bodies are omitted; pins remain |
| New extensions | Unknown source kinds/versions refused | Critical extensions refused; changed descriptor bytes fail exact registry pins, including new noncritical extensions |

See the [original record](../website/src/data/l4yaml-record.json),
[import boundary](../conformance/import_v1/README.md),
[capability descriptor](../conformance/capability_v1/fixtures/capability-contract.json)
and [finite replay boundary](../conformance/capability_v1/README.md).
Pins provide recovery locators and byte identities, not availability guarantees
or lossless semantic round trips. Object details display absent attribution as
UNKNOWN and link the full original; this is a known presentation limitation.

The noninterference test loads records without capability support, with it,
then without it again and requires identical canonical record-001 projections.
It also rereads record 001/002 transport bytes and content identities. Mutation
of a returned projection does not mutate its source. This tests these exact
adapters only; arbitrary future extensions remain unqualified.

The [map reader/tests](../website/src/lib/knowledge-map.test.ts) preserve
explicit noncritical opaque map extensions and reject critical extensions,
unsupported versions, invented relation types, wrong endpoints/provenance and
authority injection. Current types are EVIDENCE_FOR, PREMISE_FOR and WITHDRAWS,
with same-source provenance. Exports and reader wrappers have authority NONE;
record-schema and actual browser/import controls reject presentations as evidence.

The foundation preserves the following seams, with no universal compatibility claim:

| Protected future | Present extension seam | Smallest new-profile qualification |
| --- | --- | --- |
| Authored Brains | Exact source/version identities, read-only collections and separate axes | One versioned authored manifest; distinguish attributed commentary from admitted claims; test ownership/edit history and source preservation |
| Portable Maps | Directed bounded export, pins, selection and completeness, separate reader | A separately implemented consumer with positive/negative vectors, explicit extension/loss rules and authority NONE |
| Verified capabilities | Descriptor/evaluation separation and finite profile | New exact scope, inputs, assumptions, verifier and independent policy; replay and mutation controls before admission |
| Certified Paths | Declared Resolve routes and least-support replay | Step/input/output correspondence, composition preconditions, assumption discharge, broken-step and cycle controls |
| Collaboration/living papers | Immutable claim/evidence pointers, original attribution, withdrawal and surviving support | One paper/claim/evidence manifest plus versioned correction; distinguish authorship, review and mathematical evidence; no editor implied |
| Cross-prover/domain transport | Native-verifier identities and narrow unsigned external binding | One real source-to-target mapping with statement/axiom/toolchain pins, losses, native replay and wrong-semantics controls; discharge actual Lean premises |
| Agent exchange | Local CLIs, reason codes, source-bound advisory proposals | Independent recipient policy and untrusted-status controls; separate permission contract before any operational action |
| Federation | Offline replay independent of MathGraph.org and explicit recipient policies | Two independently administered publishers; authenticated identity, conflicts, delegated authority and replay/rollback controls |
| Compounding | Finite retention/reuse/sham/ablation controls | Prospective new families, parent-removal, retained old capabilities, restartable lineage, strong comparator and full costs |
| Independent requalification | Standalone import, Resolve and finite consumers | Durable original artifacts and exact native replay; distinguish implementation independence, outside-owner trust and authenticated current state |
| Network sharing | Static downloadable bundles/contracts and exact pins | Independently retrieve exact artifacts; separately qualify authentication, retention, freshness/revocation and recipient permission |

## 13. Deliberately omitted abstractions

| Omission | Why the present boundary is smaller | Preserved seam |
| --- | --- | --- |
| Universal Unit/Brain/Map/Path ontology | Two source domains justify a view adapter, not universal semantics | Versioned source contracts and explicit per-domain adapters |
| Inferred equivalence/support | Names, proximity, hashes and graph layout cannot establish semantic relations | Each future relation needs its own evidence/profile |
| Universal verified badge | Collapsing validity, warrant, lifecycle, freshness, applicability and permission changes decisions | Independent machine-readable axes |
| General composition/CFC/autonomous growth | Existing finite controls and conditional research do not qualify general constructors | Separately verified path/family profiles |
| Accounts/database/editor/marketplace | The current slice needs no mutable multi-user store or transaction authority | Immutable manifests and independent clients |
| Hosted proof execution/arbitrary imports/MCP | Local exact-input consumers need no remote execution/fetch surface | A future bounded service over a qualified contract if demanded |
| New trust root | Same-origin hashes do not authenticate publishers | Independently selected policy and future detached authentication |
| Heavy graph framework | Fourteen objects/seven declared occurrences fit bounded semantic HTML/SVG | Replaceable renderer over explicit projections |

These choices reduce trusted code and maintenance while retaining a concrete
place for future profiles. They are not a proof that those profiles will fit
without changes. They follow the [approved design](superpowers/specs/2026-10-11-mathgraph-v2-foundation-design.md).

## 14. Unresolved obligations and release disposition

The [obligations register](mathgraph_v2_unresolved_obligations_2026-10-11.md)
records present status, acceptance gate and smallest action for durable JPL
retention, certificate-to-Lean premises, outside-owner adoption, semantic
transport, VDN admission, CFC, compounding, authenticated lifecycle, agent
authorization, federation, monorepo residuals and the deferred www redirect.

The bounded extension test is satisfied by the existing source-derived tests
and the local task observations, subject to final-head release requalification.
It establishes neither universal interchange nor certified composition,
autonomous growth, authenticated federation or outside-owner adoption.
At the preserved Task 7 checkpoint, Task 8's final review, preview, CI, browser
matrix and performance comparison were PENDING. Section 15 supersedes that
release-gate status. V2 promotion remains NOT_PERFORMED; the production
authority above has not been changed by the implementation or this
documentation task.

## 15. Final V2 release-candidate reconciliation

Observed 11 October 2026 UTC / 12 October 2026 NZDT. This section supersedes
only the Task 8 PENDING/NOT_PERFORMED release-gate statements in Sections
10–14; it does not rewrite the historical audit, expand a warrant, close a
research obligation, or authorize production.

### 15.1 Exact source, CI and deployment

The exact implementation candidate is
[`9da8dbd4b877bbcc5ea39005b5c7c40618c14abc`](https://github.com/metalogiclabs/mathgraph/commit/9da8dbd4b877bbcc5ea39005b5c7c40618c14abc)
on open draft [PR #158](https://github.com/metalogiclabs/mathgraph/pull/158).
The protected preview is deployment `dpl_A1MDVoRhCDnpGcu4UyhahJ485qJr` at
[mathgraph-loomaaug7-over-market.vercel.app](https://mathgraph-loomaaug7-over-market.vercel.app).
The Vercel build log associated it with branch
`codex/mathgraph-v2-foundation`, commit `9da8dbd`, and a successful 36-page
Astro static build. The candidate is not merged or promoted.

All required exact-head PR checks passed:

- [published evidence, run 38167753906](https://github.com/metalogiclabs/mathgraph/actions/runs/38167753906),
  artifact `11712802985`, SHA-256
  `9951bbe2410711320a452a13df498f150b7d530bed6837210dc9256e9a66c2bc`;
- [finite capability conformance, run 38167753876](https://github.com/metalogiclabs/mathgraph/actions/runs/38167753876),
  artifact `11712023975`, SHA-256
  `783d41bda7ea921ff803bc72f01adc5be47f2c6cea68550dc7700f529cbf0899`;
- [independent offline Resolve replay, run 38167753925](https://github.com/metalogiclabs/mathgraph/actions/runs/38167753925),
  artifact `11712148740`, SHA-256
  `4249c7b853f58b00fdd8512fe86a4426b35ae821cb5c4154a5ecbf8d1f9bb33c`;
  and
- [website and evidence integrity, run 38167753899](https://github.com/metalogiclabs/mathgraph/actions/runs/38167753899),
  artifact `11712424203`, SHA-256
  `75b25fa241fdd65a9ca2e91c493a5b0c390b757c78f6c5a7104e8534ee9f98a8`.

The exact-head local Python gates passed 387 tests plus 72 subtests, and 119
focused tests plus 72 subtests. Resolve recomputed three `STALE`, three
`UNKNOWN`, and one exact JPL observation `WARRANTED_BOUNDED`; applicability
remained `UNKNOWN`, freshness/revocation `NOT_CHECKED`, and authorization
`NONE`. The exact-head site qualification passed 72 Astro files with zero
diagnostics; 82 data, 19 contract and 63 rendering tests; 36 routes / 37 HTML
files; 97 published artifact files; 53,365 client bytes; 83 internal links;
and both independent consumers. All four serial local browser suites passed.
A same-owner whole-branch review was approved with no P0–P2 findings; the P3
projection-loss observation remains disclosed in Section 12.

The protected-preview run passed 10/10 suites over 24 routes and 34 hashed
screenshots at desktop, tablet, mobile and catalogue breakpoint widths, with
and without JavaScript where declared. Deployment protection and `noindex`
were retained. Import, map, catalogue, navigation, Contact, About, social,
reduced-motion, long-content, security/MIME and byte-parity checks passed with
zero console/page/request/HTTP-resource failures. See the
[browser qualification](mathgraph_v2_browser_qualification_2026-10-11.md#final-protected-preview-qualification)
and [visual-evidence manifest](assets/mathgraph-v2/README.md). Generated
screenshots remain outside Git under repository policy; their hashes record
the reviewed bytes but the machine-local capture directory is not durable
artifact storage.

Final qualification found and corrected four consequential delivery defects
before this exact candidate: the displayed acquisition command was incorrectly
executed by the browser test harness; catalogue controls collided at responsive
breakpoints; Contact used an undefined grid span; and the static CI artifact
omitted `/.well-known/mathgraph.json`. The corrections are commits
`f52753fc…`, `6ea4bf4a…`, `9eb635e6…`, and `9da8dbd…` respectively. Gates were
rerun after each affected change; none was weakened to manufacture success.

Production is unchanged at
[`4edc77cb1a4ff3a345b5feffcf7f2b38d3fbab0c`](https://github.com/metalogiclabs/mathgraph/commit/4edc77cb1a4ff3a345b5feffcf7f2b38d3fbab0c),
deployment `dpl_3L7v4EWE4SJB8hxiMNhpRWJ1Jaq9`. No merge, promotion,
production alias, DNS, registrar, nameserver, mail, trust-policy, immutable
record, or hosted execution-service change occurred.

### 15.2 Final gap and obligation matrix

`Candidate-qualified` below means qualified for this exact draft source and
protected preview. It does not mean production-qualified, universally correct,
currently applicable, externally adopted, or authorized for action.

| Area | Exact existing implementation | Missing distinction | Priority | Verification obligation | Smallest qualifying next action |
| --- | --- | --- | --- | --- | --- |
| Supported import | [Standard-library consumer](../conformance/import_v1/consumer.py), result schema/tests and immutable replay command pinned at `1204a1d…`; candidate-qualified locally and in CI | Receipt/policy validation is not original Lean/kernel/source-suite replay | P0 boundary retained | Exact bytes, source/scope/verifier/policy pins, strict parsing and mutation/presentation rejection | Preserve `original_verifier_replay: NOT_PERFORMED`; add native replay only with durable original artifacts and a separately qualified adapter |
| Import-to-result browser workflow | [Workbench](../website/src/scripts/import-workbench.ts), fixtures and browser regression; candidate-qualified on `/`, `/verify/`, `/check/` | Exact-byte recognition and a presentation export have authority `NONE` | P0 release complete | Six stages preserve identity/scope/evidence/unknowns; mutations and unsupported goals fail closed; zero arbitrary requests | Keep regressions on any supported-input change; add a new input family only through an independently qualified adapter |
| Object projections/details | [Projection adapters](../website/src/lib/object-projections.ts), 14 stable details and source links; candidate-qualified | Views intentionally omit attribution/evidence/normalization or opaque contract bodies; not round trips or universal Units | P1 | Source parity, independent axes, noninterference and fail-closed critical extensions | Extend one adapter only when a protected consumer needs an omitted field; preserve the original source as authority |
| Typed knowledge map | [Bounded map/reader](../website/src/lib/knowledge-map.ts) and semantic/SVG explorer; candidate-qualified with 14 nodes/7 declared edges | Display traversal is not certified path composition; no inferred equivalence | P1 | Directed types/endpoints/provenance/pins, completeness and authority `NONE`; wrong edges/versions rejected | Qualify one independent map consumer before claiming portable cross-implementation Maps |
| Homepage/outcome navigation | [Layout](../website/src/layouts/BaseLayout.astro), V2 home and accessible disclosure; candidate-qualified | Product framing does not expand supported inputs or module maturity | P0 release complete | Stable legacy URLs, active groups, keyboard/focus/no-JS and real evidence examples | Retain regression suite; production publication requires separate merge/promotion approval |
| Records/capabilities catalogues | [Catalogue component](../website/src/components/CatalogueFilter.astro) and filter script; candidate-qualified at 390/901/1024 | Filtering is presentation only; experimental entries remain distinct from qualified ones | P0 release complete | Exact token filters, no-match state, complete no-JS content and no collisions | Add an entry only after its own admission/qualification; never use display state as warrant |
| Agent/developer/protocol guidance | `/agents/`, `/developers/`, `/protocol/`, exact commands and contracts; candidate-qualified | Responsibility vocabulary is not a new ontology; no hosted resolver/MCP/action authority exists | P1 | Commands reproduce bounded consumers; CLOSE/ACT/REFINE and authority boundaries remain separate | Keep hosted/MCP claims absent until a concrete service is independently qualified |
| Discover | Existing dependency-free request/result/CLI and source-grounded `PARTIAL` example from PR #156 | Full historical replay is unavailable because candidate-score CSV and full ledger are missing; advice is not a terminal form | P1 research | Exact source artifacts/digests, bounded-search diagnostics and advisory-only output | Recover and validate one missing pinned artifact; do not rerun a generic solver or promote bounded exhaustion |
| Develop/capabilities | Portable descriptor/evaluation, empty/candidate registries and one finite `QUALIFIED_BOUNDED` profile | VDN Lean correspondence, general Capability Family Compiler and autonomously discovered family remain unqualified | P2 research | Native theorem/premise bridge, fresh instances, invalid-domain, parent-removal, restart, strong baseline and cost controls | Qualify one real certificate-to-Lean premise adapter before beginning the bounded family-compiler experiment |
| TypeScript consumer delivery | Synchronized Vercel header configs and exact consumer SHA-256 `e7360df2…`; candidate-qualified as `text/plain; charset=utf-8` with `nosniff` | Preview delivery is not production delivery or semantic authority | P0 release complete | Source/CI/deployed bytes and exact headers agree | After approved promotion, repeat the same check on production |
| About, Contact and social metadata | Static routes and source-derived social generator; candidate-qualified after Contact grid correction | Contact is not an SLA; social/presentation bytes are outside warrant identity | P0 release complete | Truthful links, responsive/no-JS layout, source-derived facts and unchanged record bytes | Publish only through approved promotion; retain the source-mismatch negative control |
| Machine discovery | `/llms.txt`, unchanged `/.well-known/mathgraph.json`, record index and candidate static-artifact inclusion | Discovery metadata neither authenticates a publisher nor qualifies a claim | P0 release complete | Exact bytes, locations, boundaries and static artifact presence | Add authenticated publication only under a separate external trust-root policy |
| Evidence integrity/authenticity | Immutable records 001/002, bundle/policy, CI artifact parity and hashes | Same-origin digests prove integrity, not publisher authenticity, mathematical truth, freshness or authorization | P0 integrity; P2 authenticity | Preserve historic bytes; distinguish content/transport identity and recipient policy | Retain a durable archive; then qualify one detached authenticated statement without changing semantic status |
| Durable JPL artifacts | Committed small records plus external historical CI references | Original Actions ZIP retention/retrieval remains unqualified | P1 operations | Retrieve exact archives by independent path and verify pinned digests | Execute the already gated archival workflow only with authority, then independently retrieve its output |
| Semantic/cross-prover transport | Unsigned in-toto exact-correspondence wrapper and explicit native verifier identities | No real source-to-target semantic correspondence or cross-prover proof exists | P2 research | Statement/axiom/toolchain pins, declared losses, native target replay and wrong-semantics controls | Qualify one narrow real transport profile; do not infer meaning from names, hashes or shape |
| Authenticated lifecycle/current applicability | Historical Resolve snapshots and recipient policy; current applicability `UNKNOWN` | No authenticated current-state channel excludes later revocation/supersession | P2 protocol | Issuer/root policy, expiry, replay/rollback, conflict and offline-staleness semantics | One signed lifecycle fixture plus independent verifier and negative controls |
| Agent action authorization | Read-only consumers; action authorization `NONE` | Warrant/applicability/viability/permission are not an operational policy | P3, demand-driven | Exact actor/resource/action authority and denial/liveness/safety controls | Define one bounded action profile only when a real consumer requires it |
| Federation/outside-owner adoption | Offline independent implementations and same-owner cross-repository replay | No independently administered recipient or multipublisher trust policy is established | P2/P3 ecosystem | Independent policy choice, publisher authentication, conflict/delegation/revocation handling | Recruit one actual external recipient for one exact artifact and record ownership distinctly |
| Capability compounding | Exact finite retention/reuse/sham/ablation experiment | No general, economic or recursive compounding result | P2 research | Prospective held-out family, parent removal, retained prior abilities, restart, strong executable-memory baseline and total costs | Run one frozen second-family transfer only after the premise bridge; retain negative results |
| Full monorepo baseline | Targeted V2 gates are green | Historical 10 SorryDB and 19 external-fixture failures were not rerun or repaired here | Separate maintenance | Provision prerequisites and reproduce failures without weakening V2 gates | Track and repair in a separate branch; do not call the entire monorepo green |
| Performance | 53,365 static client bytes and a three-sample warmed-edge production/preview transfer check | No Lighthouse, Core Web Vitals, field, capacity or causal comparison | P1 release follow-up | Reproducible browser/lab conditions and explicit budget before making a performance claim | Define and run a performance budget only if required for promotion; current small sample supports no speed conclusion |
| `www` canonical host | Existing production apex and duplicate-200 baseline observation | Redirect/canonical-host policy is an operational production decision | Separate production | Explicit authority plus alias/DNS and redirect verification | Leave unchanged until separately approved; it is not needed for this candidate |
| Release/Research OS | Exact draft PR, CI, protected preview, captures and review are reconciled in committed docs | Production release and Research OS synthesis are distinct from qualification | P0 release governance | Production source association, rollback, exact final checks and explicit approval; ROS cites evidence rather than replacing it | Record the exact checkpoint in ROS; then seek human approval to merge/promote PR #158 without DNS/mail changes |

### 15.3 Performance and architectural boundary

The [browser report](mathgraph_v2_browser_qualification_2026-10-11.md#performance-boundary--operational-sample-only)
records the limited warmed-edge numbers. Preview response times were higher in
this small sample and the V2 root body was substantially larger than production,
but the sample had only three sequential requests, high variability and
deployment-protection overhead. It supports no comparative performance or
production-capacity conclusion.

The architectural future test in Section 12 remains the accepted boundary.
Two materially different source domains—record 001 and the finite capability
profile—pass through explicit adapters without changing one another, while
unknown critical extensions fail closed. This provides concrete seams for
future Brains, Maps, Paths, living papers, federation and capability families;
it does not prove universal future compatibility. The deliberate omissions in
Section 13 remain the smallest architecture consistent with the protected
future: no database, accounts, universal ontology, hosted proof execution,
inferred relations, new trust root or heavy graph framework was added.

The final release action is therefore small and explicit: after Research OS
records these exact receipts and a human separately approves production,
merge draft PR #158 and promote its reviewed source, then repeat the production
HTTP/MIME/byte/browser smoke checks. No DNS or mail change is required. Until
that action occurs, MathGraph V2 is an independently replayable, protected
release candidate—not the production site.
