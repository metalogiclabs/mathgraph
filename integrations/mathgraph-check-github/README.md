# MathGraph Check — GitHub App shadow pilot V0

This release is a **candidate GitHub App worker**, a read-only shadow experiment, and a separate GitHub Actions App-token publisher qualification route. The registered App has already published one exact-head neutral Check; automatic signed-webhook delivery remains unqualified and undeployed. No upstream comments, code changes or merge action. No claim that an AI has independently checked arbitrary source-code correctness.

## Current qualified status (14 October 2026)

**Registered App gate CLOSED, automatic event delivery OPEN.**
[GitHub Actions #38505056995](https://github.com/metalogiclabs/mathgraph/actions/runs/38505056995)
qualified an independently read back *actual* neutral Check
[115663454933](https://github.com/metalogiclabs/go-ethereum/runs/115663454933)
on exact `metalogiclabs/go-ethereum#19@a04aa77aaebd81d11274560e8d24d90c6f417589`
with publisher `app.id=5308912`. A subsequent App-authenticated retry retained
**one** Check identity and revoked each short-lived installation token.

**Same-SHA mutable-evidence repair:**
[Cloudflare Worker dry-run qualification #38508815714](https://github.com/metalogiclabs/mathgraph/actions/runs/38508815714)
passed **21/21** original-source fixture/negative tests and ran the actual
local Cloudflare Workerd runtime, but **no Cloudflare deployment**.
On a source-stable PR head, the signed `pull_request.edited` and
`workflow_run.completed` inputs are independently narrowed to
source-validated descriptors. The consumer independently refreshes changed
CI facts, **PATCHes the original registered-App Check** rather than posting
a duplicate, and fails closed on stale heads, wrong publisher, denied update,
untrusted signatures and conflicting duplicate App identities.

**Current subscription observation:**
[registered App run #38508654185](https://github.com/metalogiclabs/mathgraph/actions/runs/38508654185)
read back `pull_request=true`, `workflow_run=false` from GitHub's
authenticated App metadata. The account owner must explicitly subscribe
to `workflow_run` to enable automatic CI-completion refresh; merely having
Actions-read permission does not show subscription. No live `workflow_run`
delivery has been observed. Real `pull_request` delivery is also unobserved.

Cloudflare is a **candidate non-Render** deployment only.
Deployment is disabled pending explicit account approval, scoped credentials
and repository variable `MATHGRAPH_CF_DEPLOY_APPROVED=true`; the activation
worker refuses webhook URL replacement without separate approval. Nothing
in this branch changes mathgraph.org, production GitHub App webhook settings
or third-party repository contents.

**Scientific boundary:** This is bounded secure event transport and scoped
PR decision support, not independent verification of all PR semantics or
autonomous self-improvement of the generator. `E2E_SYSTEM/L7=UNKNOWN`.

## Objective and trust boundary

The first test is whether a PR has **green CI at its exact head but explicitly declares a narrower verification boundary**. The extractor recognizes added source lines such as remote_conflicting_fcu=UNKNOWN, not generic English claims. It reports those lines as **author declarations**, not verified truth. All GitHub Check conclusions are neutral/advisory. Runs are filtered to exact SHA and most recent by name; diff or Actions pagination, missing permissions and unsupported evidence retain UNKNOWN. No PR code is executed.

Real control: metalogiclabs/go-ethereum PR #19, exact head a04aa77aaebd81d11274560e8d24d90c6f417589, source-declared remote_conflicting_fcu=UNKNOWN and concurrent_fcu=UNKNOWN, with green workflow 38202260024 checking narrower predicates. PR #16 has its own bounded, exact-head green CI. Neither is a universal safety proof.

## GitHub App registration / installation preparation

The minimal App-authorized first Check uses [APP_NATIVE_ACTIVATION.md](APP_NATIVE_ACTIVATION.md) and GitHub Actions **without hosting**; see [ACTIVATE.md](ACTIVATE.md) for separate, later signed-webhook requirements. **Historical preparation guidance, superseded:** registered App ID 5308912, private-key-backed Actions authentication, installation and one native App-authored Check have since been independently qualified (see current status above). The owner has explicitly excluded Render; do not deploy there.

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
