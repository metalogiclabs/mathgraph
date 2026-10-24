# MathGraph Check — independent L4YAML before-and-after audit

**Date:** 2026-10-25 (NZDT)  
**Status:** WARRANTED within the exact, bounded native replay described below; **not** a YAML-wide correctness proof.  
**Prepared for:** Nicolas F. Rouquette, as independent technical evidence from Heath Sanchez / Metalogic Labs; no JPL endorsement implied.

## Exact revision and scope

- **Before:** `nasa-jpl/L4YAML@82cdb78e8909f25d9079d9bb05ed7c6f508ee95c`.
- **After:** `nasa-jpl/L4YAML@a2a542569a92566ad8a320247dd7cb00eed0634b` (integration branch snapshot following merged scanner PR #89 and proof PRs #93–96).
- **Historical causal bridge:** independent [CI 40122149895](https://github.com/metalogiclabs/mathgraph/actions/runs/40122149895) compared the before SHA against early PR #89 SHA `364a80d4f6790175e06e29c59708da3b50c20049`.
- **Current native replay:** [CI 40134000893](https://github.com/metalogiclabs/mathgraph/actions/runs/40134000893), Metalogic-owned workflow at `744a878b668d1c0dcf31ae254bd04802fcac1aea`; **completed/success**, with 88/88 checker tests and two untouched upstream builds of 57 jobs each.
- A repository comparison from merged integration commit `550233c43a70ccc768b2e80590d2767db8af2428` to the frozen after SHA shows no modified scanner/parser/spec/schema/output implementation files; intervening edits concern proofs, guards and documentation.

## Behavioral findings (bounded finite witnesses)

| Independent native observation | Before | After | Classification |
|---|---:|---:|---|
| Source-derived flow-glued scanner cases | 11 accepted | **11 refused** | Targeted scanner tightening, bounded |
| Unaffected flow acceptance controls | 8 accepted | **8 accepted** | Preserve legitimate inputs |
| Legacy/indexed native disagreement on flow cases | 0 | **0** | Cross-path agreement only |
| Selected ordinary Core YAML values | 352/352 agree | **352/352 agree** | Independent bounded differential |
| Acyclic repeated-anchor variations | 105/180 disagree | **105/180 disagree** | One related nested-shadowing family |
| Typed scalar-style controls | 8/8 agree | **8/8 agree** | `parseTyped` only |

The 19 scanner cases are frozen from upstream PR #89's guard examples. Eleven are glued-colon forms such as `{a:[1]}`, `{a:{b: c}}` and `{? a :[1]}`; eight preserve JSON-like adjacent keys or explicit separation. The external YAML implementations differ on 11 inputs in the historical replay and are **not** promoted to specification authority.

## Interpretation and outstanding residuals

The scanner comparison tests a narrow behavioral change, not full YAML 1.2.2 conformance or a general grammar proof. Source identity and complete verifier receipts are necessary to warrant each observation. Do not infer release or deployment authority.

The current-source replay confirms 105 mismatches among 180 acyclic repeated-anchor cases (seven related nested-shadowing families, not 105 bugs), while 352 ordinary controls and eight typed controls agree. The simplest illustrative witness is `[&x [&x 1], *x]`: normative latest-preceding-anchor interpretation expects `[[1],1]`, while the native paths produce `[[1],[1]]`. This is distinct from, though related to, the already-known self-descendant anchor-commit timing difference documented in L4YAML's serialization proofs. Neither issue is repaired by the targeted scanner change.

The typed checks do **not** close the separate `ToYaml`/dump/interoperability question still tracked by L4YAML issue #6. Main-line and integration-branch releases remain separate authorities.

## Qualification and links

**Current replay:** [CI 40134000893](https://github.com/metalogiclabs/mathgraph/actions/runs/40134000893) completed/success. The independent verifier returned `BOUNDED_TARGETED_SCANNER_CHANGE_OBSERVED`, `BOUNDED_DIFFERENTIAL_OBSERVED` and `BOUNDED_TYPED_SCHEMA_AGREEMENT`. It checked exact input membership, native Boolean types, immutable upstream SHAs, Lean 4.35.0, source-file hashes, the 11/8 transition and unchanged 427/532 total value agreements. The two external parsers disagreed on 11 flow cases; this remains an explicit interpretation limit. All decisions remain `NOT_AUTHORIZED`, with no mathematical terminal-form proof.

**Retained artifact:** [12576421270](https://github.com/metalogiclabs/mathgraph/actions/runs/40134000893/artifacts/12576421270), ZIP `sha256:2140e175b7bf5c37f5263adbb71f4102e110aa020a8267f9b410d45bdfe6b614`. Independently downloaded ZIP digest matches GitHub's recorded digest. It includes the exact per-case native JSONL, source/verifier identities, both 532-case reports, the eight typed controls and the 19-case transition report.

- [MathGraph Check draft PR #202](https://github.com/metalogiclabs/mathgraph/pull/202)
- [Scanner PR #89 (merged to integration)](https://github.com/nasa-jpl/L4YAML/pull/89)
- [Previously qualified value/typed-source CI 40122150103](https://github.com/metalogiclabs/mathgraph/actions/runs/40122150103)
- [Existing MathGraph Research OS checkpoint](https://app.notion.com/p/3f53e523d7ab8111994eee79ec34178a)

**Proposed ongoing use:** a read-only, independent MathGraph Check receipt on consequential L4YAML source revisions, leaving Nicolas's proof-development workflow and upstream repository unchanged unless invited.
