# MathGraph Check — GitHub App shadow pilot V0

This release is a **candidate GitHub App worker** plus a read-only shadow experiment. It is not a registered, installed or deployed GitHub App. No upstream comments, code changes or merge action. No claim that an AI has independently checked arbitrary source-code correctness.

## Objective and trust boundary

The first test is whether a PR has **green CI at its exact head but explicitly declares a narrower verification boundary**. The extractor recognizes added source lines such as remote_conflicting_fcu=UNKNOWN, not generic English claims. It reports those lines as **author declarations**, not verified truth. All GitHub Check conclusions are neutral/advisory. Runs are filtered to exact SHA and most recent by name; diff or Actions pagination, missing permissions and unsupported evidence retain UNKNOWN. No PR code is executed.

Real control: metalogiclabs/go-ethereum PR #19, exact head a04aa77aaebd81d11274560e8d24d90c6f417589, source-declared remote_conflicting_fcu=UNKNOWN and concurrent_fcu=UNKNOWN, with green workflow 38202260024 checking narrower predicates. PR #16 has its own bounded, exact-head green CI. Neither is a universal safety proof.

## GitHub App registration / installation preparation

The first controlled GitHub installation is documented in [ACTIVATE.md](ACTIVATE.md), including GitHub's prefilled org registration link, minimum permissions and exact signed-webhook acceptance criteria. **App registration and hosting have not occurred yet.**

The added `webhook.integration.test.mjs` executes a real local HTTP webhook request, validates its signature and verifies the eventual neutral Check Run against **mock GitHub APIs**. This is deliberately separate from the existing shadow CLI, which reads actual public PRs without writing to GitHub.

## Commands

Node 22; no external dependencies:

    node --test integrations/mathgraph-check-github/test.mjs integrations/mathgraph-check-github/webhook.integration.test.mjs

Read-only shadow; produces JSON and Markdown (no GitHub writes):

    GH_PUBLIC_TOKEN=... node integrations/mathgraph-check-github/core.mjs \
      --repo metalogiclabs/go-ethereum --pr 19 --out /tmp/pr19.json

The isolated push workflow tests both real fork PRs and preserves source-bound reports as a downloadable artifact.

## To activate the app later

Register a GitHub App in an authorized Metalogic account and select only Pull requests: read, Actions: read, Checks: read/write (Metadata: read is implicit). Subscribe to pull_request webhook. Configure a hosted HTTPS URL ending in /github/webhook. Set GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY, GITHUB_WEBHOOK_SECRET, and a mandatory MATHGRAPH_ALLOWED_REPOS comma-separated list. Run the dedicated long-lived Node worker:

    node integrations/mathgraph-check-github/webhook.mjs

It validates HMAC SHA-256 signatures, obtains a short-lived installation token, reads permitted PR evidence, rechecks the exact SHA and writes a **neutral** check. It never commits, merges, comments or runs uploaded code. Webhook response is acknowledged before work, so deployment must support a persistent process. It has bounded in-memory same-source work serialization **and** durable GitHub Check Run reconciliation by exact source SHA, external ID and App ID. These protect against ordinary duplicate delivery and worker restarts, but **do not** provide an atomic cross-instance exactly-once guarantee. Add a durable queue, bounded retries and cancellation handling before outside-owner installations. Keep secrets out of repository files.

## Next decisive gate

Compare the PR #19 output with a baseline that only reports the diff and green CI. Measure whether a maintainer is helped to identify the genuinely missing authenticated cross-fork and concurrent FCU tests. This pilot cannot by itself establish third-party adoption, semantic correspondence or cost savings.
