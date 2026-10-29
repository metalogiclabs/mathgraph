# MathGraph Check — exact-head continuation boundary (private research)

Date: 29 October 2026. Status: **WARRANTED_BOUNDED for direct synthetic unit tests**; real customer intent and external source-native repair **UNKNOWN**.

The read-only product facade already distinguishes green CI, bounded probe observation, source freshness and independent authority. The full existing GitHub App/Cloudflare test surface was rerun locally: **122/122** across 16 files (direct Node invocation; the file-level `node --test` summary is not used to overcount recognized subtests). A new seven-test follow-on at `future-commutation-boundary-v0.test.mjs` exercises exact-head continuations with real `auditIntent`, `monitor` and `compareSnapshots` implementations, bringing the local aggregate to **129 tests**.

## Concrete findings

1. Old exact-head receipt A **does not** qualify source B. A real independent receipt for B becomes only bounded `OBSERVED` at the audit plane; no assertion of general intent proof follows.
2. The raw `monitor` helper conservatively treats source A→B as **UNKNOWN** even when a fresh independently qualified receipt for B exists. A separate, caller-supplied `independent_requalification=true` bit can make that pure helper display `OBSERVED`; the helper does not authenticate the bit itself.
3. The product's actual `compareSnapshots` authenticated-cycle facade *explicitly resets* that bit to `false` before calling `monitor`. A forged bit therefore **does not bypass this observed facade**. The unauthenticated raw-helper example is a **trust-boundary characterization, not a demonstrated live GitHub App exploit**.
4. The remaining implementation gap is a native, typed evidence-to-monitor requalification attestation owned by an independent checker rather than a naked boolean. There is no evidence that a source transition should be promoted automatically without that bridge.

## Reproduce and scope

From this repo branch, execute each `*.test.mjs` with `node` directly or run `mathgraph-check-future-transition-v0.yml`. All tests are synthetic local objects and mocked GitHub effects; none accesses live customer repositories, posts Checks, or grants production authority.

Do not infer G4 economic superiority, owner-conferred intent, real developer benefit or an independently anchored GOETH G6 monitor from this report. No production app deployment or external issue is part of this branch.

Cross-program ROS ledger: [Seven-gate execution](https://app.notion.com/p/4083e523d7ab81f78ea3f212da9b8509).
