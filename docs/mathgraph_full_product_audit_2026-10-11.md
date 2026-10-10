# MathGraph Website, Product & Architecture Audit

**Reconciled:** 11 October 2026  
**Repository:** [`metalogiclabs/mathgraph`](https://github.com/metalogiclabs/mathgraph)  
**Source authority:** [`11944c2b44ac890ecc03c7f183ae74ea4640246c`](https://github.com/metalogiclabs/mathgraph/commit/11944c2b44ac890ecc03c7f183ae74ea4640246c)  
**Audit purpose:** identify the first unfinished product and protocol gates after the qualified publication of MathGraph Resolve record 002.

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
