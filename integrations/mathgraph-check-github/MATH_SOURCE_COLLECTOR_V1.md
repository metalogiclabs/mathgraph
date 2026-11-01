# MathGraph Check: read-only mathematical evidence collector V1

This is the server-side integration of the three experimental components:

1. `math-source-github-host-v1.mjs`: authenticated GitHub PR/head, workflow/job/attempt, artifact metadata and independent human review declaration.
2. `math-source-evidence-fetch-v1.mjs`: fixed-path, read-only, bounded GitHub artifact and original third-party source downloads.
3. `math-source-evidence-bytes-v1.mjs`: exact ZIP digest and contents; exact original Lean source and informal/formal statement hashes.

`math-source-evidence-collector-v1.mjs` correlates all three and **repeats the GitHub host readback after downloading**. It returns only `EVIDENCE_BYTES_CORRELATED` (with a separately labeled human review attestation, if any) or `UNKNOWN`.

## Authorization boundary

- Server operator supplies an installation-scoped GitHub token through `MATHGRAPH_GITHUB_APP_TOKEN`. The token is used **only for `api.github.com` calls to the configured MathGraph repository**; it is not sent to GitHub's artifact CDN or the third-party ProofNet source host.
- App installation permissions required for this **read-only** observer: repository **Contents: read**, **Actions: read**, and **Pull requests: read**. It does not require Checks: write, Issues: write, Contents: write, or Actions: write.
- The operator—not a PR—chooses `repository`, `pr`, `runId` and the independent `trusted` configuration. The workflow hash must come from separately audited workflow source; the approved-reviewer IDs must be selected by the repository owner.
- The downloader accepts a single GitHub API redirect to an HTTPS GitHub Actions / Azure Blob artifact host, with no Authorization on the second hop, no second redirect, and a 2 MiB ZIP limit. Fixed upstream URLs use `raw.githubusercontent.com` at the exact immutable `ProofNet-Verified` Git SHA and have no credentials.
- Every transport or trust failure returns a neutral `UNKNOWN` from the collector. The CLI never prints token values, raw proof/source text, or untrusted API response bodies.

## Standalone read-only operator job

An administrator supplies a private JSON file (outside the checkout and never committed) containing exactly the following fields:

```text
repository:                 "metalogiclabs/mathgraph"
pr:                         numeric PR number
runId:                      numeric completed workflow run ID
trusted.repository:         same repository
trusted.pr:                 same PR
trusted.headSha:            exact current 40-character PR head SHA
trusted.workflowPath:       ".github/workflows/mathgraph-check-proofnet-artin-replay-v1.yml"
trusted.workflowSha256:     SHA-256 of separately audited workflow bytes
trusted.workflowId:         GitHub numeric workflow ID
trusted.jobName:            "pinned-artin-replay"
trusted.artifactName:       "mathgraph-proofnet-artin-evidence"
trusted.sourceSha256:       a9ea15e08b984edb0690348b953a11bf0a1c2cd2541131323c26c243f21ee7fc
trusted.claimSha256:        a908ad4a14106793dec67703b4051fd3587be202fcd94c5778981cab409051a0
trusted.formalSha256:       dc80af468161394ffc1415b4e1ff0585b6859dc80198abb6d2c7d4439888262b
trusted.environmentSha256: separately audited environment identifier (currently *not* resolved-Lake-proven)
trusted.approvedReviewerIds: array of independent GitHub human user IDs, possibly empty
```

Then run with a short-lived installation token already provisioned by the app's privileged credential broker:

```sh
MATHGRAPH_GITHUB_APP_TOKEN=... \
node integrations/mathgraph-check-github/run-math-source-evidence-collector-v1.mjs /path/to/private-admin-trust.json
```

The process prints only sanitized JSON and returns exit code `0` for correlated evidence, `2` for `UNKNOWN` or invalid/missing operator configuration. **A correlated result is not approval of a PR or proof of semantic equivalence.** Do not pass this output as a qualified `mathgraph.intent-probes.v1` receipt.

## Tests and genuine evidence

```sh
node --test integrations/mathgraph-check-github/*.test.mjs
```

The test suite constructs real ZIP bytes, executes the actual host validation against complete controlled GitHub API fixtures, challenges redirection and streaming limits, and exercises changed PR heads, reruns, artifact digests, source bytes, and review declarations. The positive original-source test uses a checked-out, SHA-verified copy of ProofNet-Verified, supplied via `MATHGRAPH_PROOFNET_FIXTURE_DIR` in GitHub CI; no bulky benchmark data is committed here. Existing true native Lean 4.28 replay evidence remains at [run #41346277520](https://github.com/metalogiclabs/mathgraph/actions/runs/41346277520), with separately verified ZIP digest `sha256:74a7838a82728a8326c15b1115992ac1519bf117d608ab497c92df3c07e2bd09` (artifact retention is limited).

## Gates still open

1. Record and bind the resolved `lake-manifest.json` dependency closure and actual Lean executable versions into a replay artifact that the collector verifies.
2. Obtain an independent qualified mathematician's exact-statement source-to-formal review on a specific PR head. Ordinary `APPROVED` is insufficient; even structured review is an attestation, not an automatic theorem equivalence proof.
3. Perform an owner-approved GitHub App installation/pilot in the target repository, wiring short-lived token minting and events to this *separate* read-only observer, without reusing the existing go-ethereum writer worker.
4. Only after those gates and security review consider contract-bound `intent-probes` receipts and a protected-workflow policy. Every current result remains `ADVISORY_ONLY`, `conclusion=neutral`, `intent_verification=NOT_ESTABLISHED` and `receipt_qualification=NOT_YET_CONTRACT_BOUND`.
