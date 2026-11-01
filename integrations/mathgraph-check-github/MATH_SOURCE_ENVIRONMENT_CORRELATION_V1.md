# MathGraph Check: same-run source, replay and Lake environment correlation V1

`collectMathSourceEvidenceWithEnvironment` is the read-only end-to-end observation entry for a pinned native Lean 4.28 Artin replay. It combines the earlier GitHub host and proof-evidence ZIP checks with **a second artifact from the same run** that supplies the actual Lake dependency closure.

## How it reaches a bounded outcome

1. Independently configured GitHub App bearer token authenticates PR/head, workflow SHA, completed run/attempt, successful required steps, original evidence artifact metadata and (if present) an allowlisted human review declaration.
2. It independently downloads, SHA-checks and parses the original two-file proof-evidence ZIP, and fetches the exact third-party source at its immutable Git SHA.
3. It reads the full same-run GitHub artifact list, requiring exactly one primary evidence artifact and one environment artifact on the same run/head/repository, with no expired/duplicate/missing records.
4. The environment ZIP is fetched through the fixed authenticated GitHub API artifact endpoint, then one uncredentialed bounded CDN redirect; its five files are strictly parsed. The environment SHA-256 is compared against an **out-of-band administrator pin**.
5. It repeats the entire PR/run/evidence observation and finally re-reads the artifact metadata. Head, attempt, review, artifact ID or digest changes withdraw the result to `UNKNOWN`.

The only positive status is `ENVIRONMENT_AND_REPLAY_CORRELATED`; it is not proof that English and Lean express equivalent mathematics. The existing exact-head independent human declaration, if any, is reported only as **review attestation**. All output remains `ADVISORY_ONLY`, `conclusion=neutral`, `intent_verification=NOT_ESTABLISHED` and `receipt_qualification=NOT_YET_CONTRACT_BOUND`.

## Reproducible real replay evidence

Native replay: [GitHub Actions run #41356752114](https://github.com/metalogiclabs/mathgraph/actions/runs/41356752114), head `4c6bf5f9e09bdc370ccb84b1bb7a9551437c596b`, successful first attempt.

| Artifact | ID | Independent ZIP SHA-256 |
| --- | --- | --- |
| Source/proof/axiom evidence | `13103253610` | `21e145b8ecde54842c289c2bd03e64f82b74a0dc966dc023a81bf35e9a626998` |
| Resolved Lake environment | `13103218833` | `64fcc2dd5e6ca54846ed102af19398e0a90b3115bac71234bdba4378a971f544` |

The environment artifact independently replays through the strict verifier to:

- `manifest_sha256=097b38d896aaeca48efeda3d08f260a08d8b9539a3558af4e7333fba99b254f1`
- `environment_sha256=1a6ca48ac912d3f8900e4c4e4061d5c7b6921e92facca8bcd1a53c80fe7b2164`
- Nine full Git dependency revisions, including Mathlib `8f9d9cff6bd728b17a24e163c9402775d9e6a365` at the upstream `v4.28.0` tag.

Artifacts have 14-day retention and are not copied into this repository. Later observations require a fresh successful run and new trust pins.

## Read-only V2 GitHub App job

An administrator creates a private JSON trust manifest outside the PR, using the full same-run source/head/workflow/reviewer pins documented in `MATH_SOURCE_COLLECTOR_V1.md`, with:

- `trusted.workflowPath=.github/workflows/mathgraph-check-proofnet-artin-replay-v2.yml`
- `trusted.environmentSha256=1a6ca48ac912d3f8900e4c4e4061d5c7b6921e92facca8bcd1a53c80fe7b2164` for the referenced native run
- independently calculated `trusted.workflowSha256`, matching the exact live PR head's workflow contents; `trusted.workflowId` matching the GitHub Actions workflow ID
- `trusted.approvedReviewerIds=[]` until the owner appoints an independent mathematician (no reviewer has been approved for this pilot).

Then, with an independently obtained short-lived GitHub App installation token that has only Actions:read, Contents:read and Pull requests:read for the target repository:

```sh
MATHGRAPH_GITHUB_APP_TOKEN=... \
node integrations/mathgraph-check-github/run-math-source-environment-collector-v1.mjs \
  /path/to/private-v2-trust.json
```

The process prints sanitized JSON and exits `0` only for a fully correlated advisory observation; missing evidence, invalid token/scope, moved PR head or rerun produces `UNKNOWN` and nonzero exit. It never approves, comments, edits a Check Run, merges or deploys anything.

## Gates before a real Open Math Model opt-in pilot

1. Independent human mathematical source-to-formal review, expressly scoped to the original claim, formal statement, dependency identity and exact head, with reviewer selected by the target repository owner.
2. Security review and owner-approved installation of a **separate read-only GitHub App** or least-privileged App job. Do not reuse the existing go-ethereum Check Run writer worker.
3. Optional later signed/typed `intent-probes` integration, and independent revalidation on source/review/environment changes. No qualified receipts are minted here.

There has been **no live deployment or independent human review** of this mathematical example.
