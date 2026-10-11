# MathGraph V2 — release authority checkpoint

Status: **UNRELEASED_CANDIDATE**. Observation date: 11 October 2026.
GitHub facts below were refreshed at approximately 10:24 UTC. Implementation
boundary: `7a43e7ff45eda96aee11c9efe056542f2498bbd8` on
`codex/mathgraph-v2-foundation`. This Task 7 document does not perform Task 8.
Its own documentation commit is identified by Git history; it is not an
already-qualified deployment identity.

## Production and research authority

| Authority | Exact observed identity | Boundary |
| --- | --- | --- |
| Remote main | [4edc77cb1a4ff3a345b5feffcf7f2b38d3fbab0c](https://github.com/metalogiclabs/mathgraph/commit/4edc77cb1a4ff3a345b5feffcf7f2b38d3fbab0c) | PR #156 merged foundation, not V2 |
| PR #156 | [MERGED](https://github.com/metalogiclabs/mathgraph/pull/156), 2026-10-11T03:59:39Z; final head `349764269756bc6c679ee99cc9147609980963d8` | Final head and merge have tree `a2efc76cb1b95b617e60173d01a85ecd7cdd65d7` |
| Production deployment | GitHub deployment `6990666088`, 2026-10-11T04:00:20Z, source `4edc77cb…`, status success | [Immutable deployment](https://mathgraph-38k5h85g9-over-market.vercel.app); deployment success adds no semantic authority |
| PR #157 | [OPEN, draft](https://github.com/metalogiclabs/mathgraph/pull/157), head `ba94d2827fbc0dc296ea3507ae034f00f9c58a5e` | Candidate consequence research; no merge/promotion or public protocol authority |
| V2 | Local accepted implementation through `7a43e7ff…` | Final source, draft PR, remote CI and protected preview PENDING |

The PR #156 final head has successful
[Check/public evidence](https://github.com/metalogiclabs/mathgraph/actions/runs/38104688120),
[Resolve](https://github.com/metalogiclabs/mathgraph/actions/runs/38104688116),
[website](https://github.com/metalogiclabs/mathgraph/actions/runs/38104688147), and
[protocol/capability](https://github.com/metalogiclabs/mathgraph/actions/runs/38104688145)
runs. No merge-commit Actions run was returned by the read-only query. Complete
tree parity is the reconciliation fact; no such run is implied. These are PR
#156 receipts, not V2 CI.

The [original audit](mathgraph_full_product_audit_2026-10-11.md) and
[modular candidate report](mathgraph_modular_contracts_release_candidate_2026-10-11.md)
retain their earlier stage observations. Their “draft” and “production untouched”
statements are historical. The correction here records the subsequent merge.

Read-only factual sources were `gh api repos/metalogiclabs/mathgraph/branches/main`,
`gh pr view 156/157`, production deployment listing/statuses, and `gh run list`
for the exact head and merge. Local `git show` checked tree identities. These
observations are timestamped snapshots, not continuous monitoring.

## Implementation ledger

| Label / scope | Exact commit | Implementation and coverage |
| --- | --- | --- |
| Plan | `6fc5890854fe9156969930ba523e6c13cb950316` | [Design](superpowers/specs/2026-10-11-mathgraph-v2-foundation-design.md), [plan](superpowers/plans/2026-10-11-mathgraph-v2-foundation.md) |
| T1 import | `0dfef4f754db486806beef3a72dfbf8d195a5fb4` | [Consumer](../conformance/import_v1/consumer.py), [tests](../conformance/import_v1/test_consumer.py), [result schema](../protocol/schemas/import-result-v1.schema.json) |
| T1 authority correction | `1204a1d267b6217c45c9b17f093cc3587450cf78` | Fixed processing/authority/replay fields and presentation/browser/reimport rejection |
| Qualification plan | `b5975f0ef9c26db4586d0f05aeab31dba3cfba50` | Two-domain, connected workflow and final-identity requirements |
| T2 projections | `9325ba3f0f3d12f45b9f177e5fb51d8d7dad58cc` | [Adapters/tests](../website/src/lib/object-projections.test.ts), [map/tests](../website/src/lib/knowledge-map.test.ts) |
| MIME/release plan | `eeaabfe6691312240051a66f07a079a63c64aef6` | Exact-path MIME and no-production-change requirements; planning, not deployed fix |
| T3 workbench | `3fcb4e74dad22bd02f00b6232584b18c2970a8d3` | [Recognition](../website/src/scripts/import-workbench.ts), [workflow browser test](../website/tests/import-workbench.browser.mjs) |
| T4 navigation/home | `ce5d19e8d2c685e6e6752e41c938a7b34647a1da` | [Home](../website/src/pages/index.astro), [navigation browser test](../website/tests/outcome-navigation.browser.mjs) |
| T5 explorer/map | `16e6b0782c9a2c7452f9dcd275f7b721a6f54443` | [Map component](../website/src/components/KnowledgeMap.astro), [detail](../website/src/components/ObjectDetail.astro), [browser test](../website/tests/knowledge-map.browser.mjs) |
| T5 history correction | `e1b13678c4680fee76e196c7e10b6f89506ac500` | Direct-fragment/reload/Back/Forward selection regression |
| T6 catalogues/docs | `a34e91523f34f9cddb4dcbd9586b47efbbfa4564` | [Catalogue](../website/src/components/CatalogueFilter.astro), [protocol](../website/src/pages/protocol.astro), [contracts](../website/tests/contracts.test.ts), [rendering](../website/tests/rendering.test.ts), MIME configs and social metadata |
| T6 source/layout correction | `7a43e7ff45eda96aee11c9efe056542f2498bbd8` | Source-derived social facts/mismatch control; container-responsive catalogue; [browser regression](../website/tests/catalogue-filter.browser.mjs) |

## Local observations and their limits

The controller's ignored Task 1–6 reports were read for this checkpoint. Their
results are prior local observations, not fresh Task 7 executions or remotely
retained CI receipts. Their executable tests are linked above.

| Boundary | Recorded local result |
| --- | --- |
| T1 final fix | 76 focused import tests; 107 combined import/protocol/Resolve tests and 72 subtests; schema/public byte parity |
| T2 | 10 focused projection tests; 132 website tests; all qualification components passed after loopback-permission retry |
| T3 | 135 website tests; full local qualify; two-route Chromium import workflow; 76 import tests |
| T4 | 151 website tests; full local qualify; import and responsive navigation browser suites |
| T5 final fix | 159 website tests; map fragment/history/browser matrix, Astro check and built check; earlier full qualify/80-link scan |
| T6 accepted head | Full local qualify rerun at `7a43e7ff…`: 163 tests (82 data, 19 contract, 62 rendering), 36 Astro routes, 37 HTML files, 53,218 client bytes, 83 links, both independent consumers; 390/901/1024 catalogue browser matrix |

Local browser details and transient capture locations are separated in the
[browser checkpoint](mathgraph_v2_browser_qualification_2026-10-11.md).
The original broad Python baseline failures remain historical; no claim of a
clean full-monorepo run is made. Local loopback/sandbox prerequisites were
retried with scoped permission, not skipped or relabelled as passing.

## Immutable identity and parity checkpoint

Task 7 reread these SHA-256 values at the accepted implementation boundary.
The first eight rows are historical artifacts, unchanged from production source.
The last row is the new T1 result, not replacement evidence.

| Object | SHA-256 |
| --- | --- |
| [Record 001 bytes](../website/public/evidence/mg-l4yaml-source-check-20261010/record.json) | `7b59ee76a39995f35a0feb0f4d91a3c6ab1234393143480c4f3e361a79fee703` |
| [Record 002 bytes](../website/public/evidence/mg-living-warrant-openai-jpl-20261010/record.json) | `0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87` |
| [Resolve bundle](../conformance/resolve_v1/fixtures/bundle.json) | `957080db79555f982fd3a314c263cf5177ef506969229e856897f0b19ccc1d62` |
| [Resolve policy](../conformance/resolve_v1/trust-policy.json) | `09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a` |
| [Resolve consumer](../conformance/resolve_v1/consumer.py) | `27a9be606040cc94a47c9b903dfc1cb24a86cbbc4e05ce71040c6c3d6e8d527b` |
| [TypeScript consumer](../website/public/examples/resolve-consumer-v1.ts) | `e7360df24b2fd0900c8ea88ccb1689163cec73a6c2e2347e4ab2b23b4d01bc2e` |
| [Finite contract](../conformance/capability_v1/fixtures/capability-contract.json) | `24e639b9181af313100504e0aa525536197d868810e6ffdb5093fd13501577a8` |
| [Capability registry](../protocol/registries/capabilities-v1.json) | `7ae45ef09ce492856234872c12adc6999667b14899a008baddc19687934b1358` |
| [Import result](../conformance/import_v1/fixtures/result.json) | `55ff4aa97dcc33deb2d319d41e4d91783492e7eff5c3048697f6a310cbcdab8b` |

Record content identities remain `f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb`
(001) and `b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41`
(002). Content and transport digests are distinct. Public schema mirrors and
the exact record fixture remain subject to byte-parity checks. Record 002 social
metadata is presentation outside these identities. Root/site MIME config changes
are explicit T6 changes, not historical evidence changes.

Hashes establish byte identity, not authenticity, truth, current applicability
or action permission. Final-head and preview download parity are PENDING in
Task 8, even where the historical bytes are unchanged at this checkpoint.

## Task 7 documentation verification

Fresh Task 7 checks on this documentation worktree passed: all 113 relative
Markdown links/anchors across the five edited documents, balanced fenced blocks,
nine recorded artifact hashes, byte-preservation of original audit sections 1–9
and the existing release-index entry, and `git diff --check`. The one original
header label was clarified to “Original audit baseline”; historical content was
otherwise retained and the current-state sections appended.

With the bundled Node 24 runtime, `npm test` from `website/` built 36 routes and
passed 163 tests (82 data, 62 rendering, 19 contracts). `npm run check:built`
reported 37 HTML pages, 53,218 client bytes and two 1200×630 social images;
`npm run check:resolver`, `npm run check:html` and the 83-link
`npm run check:links` scan passed. The link scan needed scoped loopback-server
permission. These checks validate local documentation/site consistency, not
external link availability, deployed HTTP headers or the Task 8 release.

Direct Git comparisons against production source preserved the historical
public evidence, original clients, source record/index data, Resolve/capability
conformance, capability registry and discovery manifest. Import schema/public,
record fixture/public and registry/public byte comparisons also passed. Task 7
changes only the five planned Markdown documents; its scratch checker/log/report
are ignored handoff files. No protocol, evidence, data, site source, deployment
or production setting was changed by this task.

## Final release identity — Task 8 has not run

| Required fact | Status |
| --- | --- |
| Final clean V2 source commit/tree | PENDING |
| V2 draft PR and exact final-head remote CI | PENDING |
| Immutable protected-preview deployment ID, URL and source association | PENDING |
| Deployment protection check | NOT_PERFORMED |
| Protected-preview browser matrix and retained screenshots | NOT_PERFORMED |
| Deployed MIME/digest/cache/console/network checks | NOT_PERFORMED |
| Measured production/preview transfer and loading comparison | NOT_PERFORMED |
| Final whole-branch architecture/security/claims review | PENDING |
| Exact final-head combined Python/site/publication gates | PENDING |
| Final browser/report documentation commit | PENDING |
| Reconciled Research OS checkpoint | NOT_PERFORMED |
| V2 production promotion, merge, DNS/alias change | NOT_PERFORMED |

Task 8 must bind one clean source commit to successful CI, immutable preview,
browser evidence and final review. Any subsequent source/content change repeats
the affected gates. A later documentation-only report commit must name the exact
deployment/source it describes and rerun document/link/CI checks. Research OS
is a synthesis surface, not evidence authority.

The immediate next action is Task 8 candidate qualification under the approved
[plan](superpowers/plans/2026-10-11-mathgraph-v2-foundation.md). After that evidence
is reconciled, any production merge/promotion or www-domain change remains a
separate authorized action. No such approval or action is implied here.
