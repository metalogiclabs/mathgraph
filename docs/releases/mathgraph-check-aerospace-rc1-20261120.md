# MathGraph Check — aerospace release candidate RC1 (2026-11-20)

**State: CANDIDATE — isolated source branch, no release/deployment approval.**
This is a reviewable **first-party L4YAML aerospace-tooling pilot**, not a general aerospace-safety assessment, external customer installation, or certification. Keep all production permissions, endpoints, policies and webhook routes unchanged.

## Source and operational reconciliation

- Original **source-frozen baseline**: [`b3ff95df9bed186bdd173ded5e9a563a5322c9ed`](https://github.com/metalogiclabs/mathgraph/commit/b3ff95df9bed186bdd173ded5e9a563a5322c9ed), the Git SHA named by the Cloudflare Worker version annotation. RC1 is a **new descendant**, not those identical bytes.
- Read-only Cloudflare account observation on 2026-11-20: script `mathgraph-check-webhook-pilot`, deployment `4b734632-204f-44fd-9f1d-7de538561c81`, version `93acd982-2661-4be0-9a83-b64a247d8d3a` at 100% (created 2026-11-04T12:28:06Z). Version annotation names `b3ff95df...`. An operator-supplied deployment annotation is **not** a byte-for-byte independent attestation of deployed code.
- The `main` repository-dispatch workflow `.github/workflows/check-pr-selfserve.yml` currently pins **an older exact controller** `28658f4232f6a0f0e5d86244edf5bf97936570f4`. This candidate does **not** re-pin that scheduler or claim its new code executes in production.
- The Worker imports `cloudflare/monitor-transition-v1.mjs` for its observational transition; the generic `check-resolve-monitor-v1.mjs` patched here is a **separate pure facade**. Do not call this patch a live Worker vulnerability repair without an actual route/use audit.
- Existing [pilot-v2 workflow](https://github.com/metalogiclabs/mathgraph/blob/b3ff95df9bed186bdd173ded5e9a563a5322c9ed/.github/workflows/check-pilot-v2.yml) is the template for independent CI qualification; its PR6/PR34/PR37 cases require exact source/context checks and are not unrestricted PR support.

## Deliberate small delta from the deployed-source baseline

1. **Fail-closed pure Monitor**: an in-band `next.independent_requalification` value can no longer turn a changed-dependency or changed-head result back into `OBSERVED`. Changed evidence requires a separately authenticated fresh readback. This is the narrow repair from [Check #266](https://github.com/metalogiclabs/mathgraph/pull/266), not a wholesale merge of that research branch.
2. **Adversarial controls**: forged requalification types, changed heads, missing dependency scope, affected/unaffected claims and BLOCKED failures are exercised by the native Node suite. An unchanged baseline module provides an intentional RED/bypass witness in the RC qualification workflow.
3. **Independent readback module (CI only)**: the source-pinned `fresh-ci-requalification-v1.mjs` checks actual GitHub PR/check-run identities without using report-supplied status. It yields **CI observations**, with `semantic_verification=NOT_ESTABLISHED` and `permission=ADVISORY_ONLY`; it is not wired into the live Worker or a semantic warrant.
4. **Read-only release qualification**: contract regression, native L4YAML finite checks, Worker *dry run*, browser QA and an explicit protected-delta allowlist. No deployment, model-key, App-token publishing, GitHub comments, or external-source mutation.

## Assurance model

The existing [capability contract](https://github.com/metalogiclabs/mathgraph/blob/main/docs/capability_contract_v1.md) and research [Boundary Warrant #261](https://github.com/metalogiclabs/mathgraph/pull/261) provide the planned carrier: **Subject, Obligation, Relation, Verification, Conclusion, Dependencies**. Do not import the entire research PR or mint a new source of authority.

The first aerospace-checking scope uses **operator-adopted, finite source-to-source obligations** on the owned L4YAML fork and native reference checks (Bash/Lean). Some historical source/repairs have authentic reproducible evidence. Owner-authorized NASA mission intention, generic FRET/MLTL-to-monitor semantic correspondence, arbitrary PR checking, operational safety and whole-repository correctness are **UNKNOWN** here.

## Qualification gates

- [ ] Exact source lineage and modified-path allowlist checked from baseline `b3ff95df...`.
- [ ] The baseline forged-flag bypass is reproduced as an intentional negative control; the new code rejects it.
- [ ] All Check Node tests, Python adapter tests and Worker Wrangler **dry-run** succeed at the exact RC head.
- [ ] Real owned-fork native checks for PR6 / PR34 / PR37 pass or are recorded as source-version-specific UNKNOWN (never silently green).
- [ ] Browser/report QA qualifies both selected repair reports and pilot page.
- [ ] Exact final-head run, artifacts and warnings are reviewed; no skipped/unsupported obligation is called a pass.
- [ ] Independent operator and actual requirements authority approve any expansion beyond the first-party test scope, separately from code CI.
- [ ] Deployment/merge requires a later **explicit** decision; this branch does not update the scheduler, Cloudflare version or App permissions.

Historical source-bound observations for orientation: [CI contract/native/browser](https://github.com/metalogiclabs/mathgraph/actions/runs/41776964010); [live Check](https://github.com/metalogiclabs/mathgraph/actions/runs/41777411050); [live Fix](https://github.com/metalogiclabs/mathgraph/actions/runs/41777739707); [live Recheck](https://github.com/metalogiclabs/mathgraph/actions/runs/41778309167); [pure Monitor guard](https://github.com/metalogiclabs/mathgraph/actions/runs/41742913643). These are **historical** and do not independently qualify RC1.

## Highest-leverage unresolved residual

After the source and trust gates, demonstrate **one independently authorized aerospace purpose-to-specification-to-native behavior correspondence**, preferably the already bounded Ogma/FRET comparison, followed by a genuinely prospective, matched-budget comparison with conventional expert review. Until then, commercial discovery lift and external mission-purpose adequacy remain **UNKNOWN**.
