# MathGraph V2 — unresolved obligations

Original checkpoint: 11 October 2026, accepted implementation
`7a43e7ff45eda96aee11c9efe056542f2498bbd8`. The research obligations remain
current unless explicitly changed below. The original release-gate rows are
preserved as history and superseded by the
[final Task 8 disposition](#final-task-8-disposition) for implementation commit
`9da8dbd4b877bbcc5ea39005b5c7c40618c14abc`. This register distinguishes
release gates, research qualification and separately authorized production
work. It does not widen existing trust policies or accepted mathematical
terminal forms. See the
[authority record](mathgraph_v2_release_authority_2026-10-11.md) and
[current audit](mathgraph_full_product_audit_2026-10-11.md#10-current-authority-and-v2-implementation-checkpoint).

## Research and operational obligations

| Obligation | Present status and evidence boundary | Acceptance gate | Smallest qualifying next action |
| --- | --- | --- | --- |
| Durable JPL retention | UNQUALIFIED. Public small records/bundle are retained; upstream Actions ZIP availability is not a durable archive guarantee. [Resolve threat model](mathgraph_resolve_v1_threat_model.md) | Exact original ZIPs retained, independently retrieved and digest checked; documented retention/recovery policy | Execute and qualify the explicitly gated archival path only with its required authority; verify retrieval, not just workflow existence |
| Certificate-to-Lean premise bridge | UNQUALIFIED. PR #157 conditional laws do not show a real imported certificate discharges their premises | Exact source/certificate/declaration/toolchain/axiom pins; native replay; independent premise correspondence; malicious source and adapter controls | Qualify one real pinned adapter and independently implemented consumer |
| Outside-owner adoption | NOT_ESTABLISHED. [Finite replay](../conformance/capability_v1/README.md) and historical external-repository Resolve replay are same-owner | Independently administered recipient chooses its own policy and reproduces bounded outcome | Recruit one actual external recipient for an exact artifact; record ownership separately from implementation independence |
| Generic semantic transport | UNQUALIFIED. [Unsigned in-toto](external_interoperability_v1.md) checks exact capability-contract correspondence only | Real second-domain/prover mapping with scope/assumption preservation, explicit losses, native target replay and wrong-semantics controls | One source-to-target profile; no universal compatibility inference |
| VDN Lean admission | EXPERIMENTAL. [Capability contract](capability_contract_v1.md) and [VDN sources](../verified-developmental-navigation/README.md) remain separate from finite registry admission | Pinned declaration/toolchain/axiom/source receipt and independent contract-to-declaration correspondence | Package one candidate and replay its native Lean boundary before admission |
| Capability Family Compiler | NOT_IMPLEMENTED. Finite named-family repair and conditional research are not a general compiler | Prospective family theorem/constructor, fresh instances, invalid-domain and parent-removal controls, restart, baselines and costs | Design a separate bounded family experiment after premise correspondence |
| Autonomous compounding | NOT_ESTABLISHED. [Finite experiment](../experiments/developmental_capability_growth_v1/README.md) establishes exact retention/reuse within eight states | Prospective new families; sham/ablation/parent-removal; retained old capability; restartable lineage; strong executable-ledger baseline and total costs | One held-out second-family transfer under a frozen protocol |
| Authenticated lifecycle/freshness | NOT_CHECKED; current applicability UNKNOWN. [Historical Resolve](mathgraph_resolve_v1_threat_model.md) does not exclude later revocation/supersession | New authenticated current-state contract, trusted issuer/channel, replay/rollback and expiry semantics | One versioned lifecycle fixture with independent policy and negative controls |
| Operational agent authorization | NONE. Import/read-only/capability results grant no permission; [Discover](discover_contract_v1.md) allocates attention only | Explicit actor/resource/action policy, authenticated authority, enforcement and denial tests; epistemic warrant kept separate | Define one concrete action profile only when a consumer needs it |
| Multi-publisher federation/authentication | UNIMPLEMENTED. Static sharing and recipient policy are available; signatures/trust federation are not | Two independently administered publishers, signer/root policy, identity/conflict/delegation handling, revocation and rollback controls | Real signed fixtures and a bounded verifier profile; retain unsigned correspondence meaning |
| Full monorepo baseline | NOT_GREEN historically: 10 SorryDB failures and 19 external-fixture errors at original audit; not freshly rerun here | Supply documented fixture prerequisites and reproduce/resolve unrelated failures separately; no weakening release gates | Track fixture provisioning and SorryDB repair outside this website/protocol slice |
| Discover full historical replay | UNAVAILABLE. [Discover contract](discover_contract_v1.md) keeps PARTIAL/NOT_CHECKED; candidate-score CSV and full ledger are missing | Recover exact referenced artifacts and independently replay/authenticate the historical experiment | Validate one recovered missing artifact against pinned provenance |

The three mathematical terminal forms remain VERIFIED_PROOF,
FINITE_COUNTERMODEL and NAMED_OBSTRUCTION. Consumer reports, map projections,
capability evaluations, archival receipts and signatures do not add a fourth
form or silently admit a claim.

## PR #157 precision

Read-only GitHub observation at approximately 10:24 UTC on 11 October 2026:
[PR #157](https://github.com/metalogiclabs/mathgraph/pull/157) is OPEN/draft at
`ba94d2827fbc0dc296ea3507ae034f00f9c58a5e`. The immutable
[candidate-envelope description](https://github.com/metalogiclabs/mathgraph/blob/ba94d2827fbc0dc296ea3507ae034f00f9c58a5e/docs/consequence_foundation_v0.md)
calls the common envelope a hypothesis, not a new authority. The
[stateful checkpoint](https://github.com/metalogiclabs/mathgraph/blob/ba94d2827fbc0dc296ea3507ae034f00f9c58a5e/docs/consequence_foundation_v0_stateful_checkpoint_2026-10-11.md)
distinguishes same-owner finite replay/receiver reuse, source-pinned JPL and a
reported rather than newly replayed WebArena result.

Its [CompositionalWarrant](https://github.com/metalogiclabs/mathgraph/blob/ba94d2827fbc0dc296ea3507ae034f00f9c58a5e/conformance/consequence_v0/CompositionalWarrant.lean),
[GeneralWarrantCalculus](https://github.com/metalogiclabs/mathgraph/blob/ba94d2827fbc0dc296ea3507ae034f00f9c58a5e/conformance/consequence_v0/GeneralWarrantCalculus.lean),
[ProtectedFutureRefinement](https://github.com/metalogiclabs/mathgraph/blob/ba94d2827fbc0dc296ea3507ae034f00f9c58a5e/conformance/consequence_v0/ProtectedFutureRefinement.lean),
and [EconomicCompoundingBoundary](https://github.com/metalogiclabs/mathgraph/blob/ba94d2827fbc0dc296ea3507ae034f00f9c58a5e/conformance/consequence_v0/EconomicCompoundingBoundary.lean)
are conditional research laws. V2 neither requalifies that branch nor promotes
its envelope to a public standard. The
[archival workflow](https://github.com/metalogiclabs/mathgraph/blob/ba94d2827fbc0dc296ea3507ae034f00f9c58a5e/.github/workflows/archive-pinned-jpl-evidence.yml)
alone is not evidence of successful durable retention.

## Historical product residual disposition — superseded for release gates

| Baseline issue | Implementation disposition through accepted T6 | Remaining gate |
| --- | --- | --- |
| TypeScript served as video/mp2t | Exact-path text/plain; charset=utf-8 in both [Vercel configs](../vercel.json); nosniff and consumer bytes retained; config/digest tests exist | Actual preview header/direct-render/digest/cache check PENDING; no production fix claimed |
| About/Contact missing | [About](../website/src/pages/about.astro), [Contact](../website/src/pages/contact.astro), footer/sitemap and rendering tests added | Preview routes/links PENDING |
| Record 002 social metadata missing | Source-derived [generator](../website/scripts/generate-social-card.mjs), image and temporary mismatch rejection; evidence bytes unchanged | Preview image/metadata PENDING |
| Mobile navigation clipped; active groups missing | Responsive disclosure and active child groups, local 1440/768/390 browser coverage | Final preview keyboard/focus/no-JS/visual gate PENDING |
| Catalogue breakpoint overflow | Container-responsive control count/track/min-width correction at `7a43e7ff…`; local 390/901/1024 coverage | Repeat protected-preview breakpoint checks PENDING |
| www duplicate 200 | DEFERRED; baseline observation only, not requalified in Task 7 | Separately authorized production redirect/canonical-host change and subsequent verification |
| V2 release evidence | Local implementation/task observations exist | Exact final source/CI/preview/browser/review reconciliation PENDING; production promotion NOT_PERFORMED |

## Final Task 8 disposition

The table above records the Task 7 state. The following is the exact later
disposition for draft [PR #158](https://github.com/metalogiclabs/mathgraph/pull/158),
source `9da8dbd4b877bbcc5ea39005b5c7c40618c14abc`, and protected deployment
`dpl_A1MDVoRhCDnpGcu4UyhahJ485qJr`.

| Obligation | Final candidate evidence | Remaining distinction / smallest action |
| --- | --- | --- |
| TypeScript MIME | QUALIFIED_ON_PREVIEW. Direct response was `text/plain; charset=utf-8`, retained `nosniff`, and matched source/CI/download SHA-256 `e7360df24b2fd0900c8ea88ccb1689163cec73a6c2e2347e4ab2b23b4d01bc2e` | Production still serves the old release. Merge and promote only after explicit approval; then repeat the deployed response check |
| About/Contact | QUALIFIED_ON_PREVIEW. Both routes returned 200; Contact passed 1440/768/390 with and without JavaScript after the exact `9eb635e6…` grid correction | No response SLA or endorsement is implied; production publication still requires approval |
| Record 002 social metadata | QUALIFIED_ON_PREVIEW. 1200×630 image SHA-256 `82f8bd0fdc14df7d0f4e12fe6ba3e9aea7944d36ffc13a3634e7b147440ee5f1`; evidence bytes unchanged | Presentation remains outside immutable warrant identity |
| Mobile navigation | QUALIFIED_ON_PREVIEW. Responsive, keyboard/focus and no-JavaScript checks passed at 1440/768/390 | This does not establish a general accessibility certification; retain regression coverage |
| Catalogue breakpoints | QUALIFIED_ON_PREVIEW. Records/capabilities passed at 390/901/1024 with and without JavaScript, without overlap | Filter state remains presentation-only; retain exact breakpoint tests |
| Machine-discovery artifact | QUALIFIED_IN_CI_AND_PREVIEW. `/.well-known/mathgraph.json` was added to the static artifact at `9da8dbd…`; deployed SHA-256 `3bde9969e635a39153f58b7f237979b954302c48878c2266dffe2ab9afd16540` | The manifest is discovery metadata, not qualification or publisher authentication |
| V2 release evidence | QUALIFIED_AS_DRAFT_CANDIDATE. Exact-head local tests, four required CI workflows, source-exact protected preview, 10-suite browser QA, hashed visual observations and same-owner review passed | Production merge/promotion is NOT_PERFORMED and requires explicit approval; generated captures are not committed, durable capture storage and outside-owner adoption remain NOT_ESTABLISHED |
| Performance | BOUNDED_OPERATIONAL_SAMPLE_ONLY. Three warmed-edge sequential samples and static client-byte totals were recorded | No Lighthouse/Core Web Vitals/field/capacity or comparative speed claim; add a reproducible browser/lab budget only when a release requirement needs it |
| Research OS | NOT_PERFORMED at this documentation checkpoint | Write a synthesis checkpoint that names the exact Git/CI/Vercel identities; do not treat Notion as evidence authority |
| `www` canonical host | DEFERRED and unchanged | Separately authorize a production redirect/canonical-host policy and verify aliases/DNS afterward |
| Production release | NOT_PERFORMED. Production remains `4edc77cb…`, deployment `dpl_3L7v4EWE4SJB8hxiMNhpRWJ1Jaq9` | Human approval to merge PR #158 and promote its reviewed source; no DNS or mail change is required for this candidate |

## Presentation losses and future extension boundary

The [two-domain audit](mathgraph_full_product_audit_2026-10-11.md#12-two-domain-extension-test-and-protected-future)
records source contracts, authority, assumptions, exact scope, replay and all
status axes separately. Object projections omit some record attribution,
publisher, evidence-run, normalization and separator fields, and omit capability
opaque extensions and full policy/receipt bodies. Source pins provide recovery
locators, not lossless round trips or continued availability. Missing projected
fields display UNKNOWN. Original sources remain necessary for full interpretation.

Current noninterference tests cover record 001 with/without the finite adapter,
not arbitrary future adapters. Relations are explicit and same-source; no
arbitrary federated edges are admitted. Map extensions may carry explicitly
noncritical opaque data, but critical/unsupported semantics fail closed.
Authority NONE persists through map export/read and cannot become evidence.

Brains, Maps, capabilities, certified Paths, living papers, transport, agent
exchange, federation, compounding, requalification and network sharing each
have a present seam and a separate next-profile acceptance obligation in that
audit. No general future compatibility is established by the present two cases.

## Deliberate omissions

The [omission table](mathgraph_full_product_audit_2026-10-11.md#13-deliberately-omitted-abstractions)
explains why V2 adds no universal ontology, inferred equivalence/support,
universal badge, general composition/CFC/autonomous growth, accounts/database/
editor/marketplace, hosted proof execution/arbitrary imports/MCP, new trust root
or heavy graph framework. Versioned artifacts, explicit adapters and independent
consumers preserve a route for later additions without granting those additions
unearned authority now.
