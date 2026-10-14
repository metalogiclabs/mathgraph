# Cloudflare Workers + Queues — MathGraph Check pilot

Source authority: existing draft MathGraph PR #167. The reusable advisory analyzer lives in the shared `analysis.mjs`; Cloudflare's Worker does not interpret arbitrary source intent or execute PR code.

## Architecture and security

A GitHub App `pull_request` webhook hits the Cloudflare Worker path `/github/webhook`. The Worker checks the raw-body HMAC SHA-256, installation ID, exact PR SHA, and an explicit allowlist of only `metalogiclabs/go-ethereum` whose PR head is also in that owned repository. It acknowledges **after** Cloudflare Queue accepts a minimal descriptor; invalid signatures get HTTP 401 and never enter the queue. The consumer fetches the live PR, GitHub Actions and exact-source Check Runs, uses the original MathGraph `analyze` and `checkOutput` functions, rechecks the PR head and publishes only a `neutral`, `ADVISORY_ONLY` Check attributed to App 5308912.

Single-message queue consumer (`max_batch_size=1`, `max_concurrency=1`) and existing exact-SHA, external-ID reconciliation reduce duplicate writes. Transient failures are retried up to 3 times and then placed on the dead-letter queue. This is not exactly-once consensus across deployment races, not whole-repository exhaustive verification and not source-to-intent semantic equivalence.

## Freshness and webhook event qualification (14 October 2026)

The exact commit SHA is immutable, but the **current exact-head CI evidence
can change without changing the commit**. A previously published neutral
Check must not be silently reused as current advice when a workflow later
fails or succeeds. The original Check ID and `external_id` are retained:

- Signed `pull_request` events are confined to installed, first-party
  `metalogiclabs/go-ethereum` PR heads.
- A signed `workflow_run.completed` event is accepted **only** when the
  original GitHub payload names exactly one source-matching first-party PR
  and its head SHA equals the completed workflow's head SHA.
- The queued method re-reads the live PR and exact-source CI, compares
  the desired neutral output with the existing App-authored Check, and
  returns `EXISTING` only for identical evidence. Otherwise it
  `PATCH`-updates the original Check ID and independently reads it back.
  An updated Check does **not** become a new check or a correctness proof.
- A stale head, failed patch, wrong App identity, inconsistent Check
  inventory or invalid signature receives no unwarranted status; failed
  processing retries, rather than prematurely ACKing.

[Source-exact GitHub Actions #38508815714](https://github.com/metalogiclabs/mathgraph/actions/runs/38508815714)
qualified **21/21** mock source/permission/negative tests,
Wrangler's real bundle dry run, and live local Workerd `/health` 200
and unconfigured `/ready` 503. The old `REPO is not defined` runtime
regression was fixed earlier in the shared source loader and separately
requalified by the actual registered-App publisher.

[Authenticated registered-App publisher run #38508654185](https://github.com/metalogiclabs/mathgraph/actions/runs/38508654185)
confirmed the real App's **configured webhook subscriptions**:
`pull_request=true`, `workflow_run=false`. Consequently
automatic CI-completion updates are **NOT LIVE**. App settings must
subscribe to `workflow_run` (already authorized by Actions read)
before this route can receive such signed events. Webhook delivery,
running Cloudflare queues and external reporter adoption remain
unobserved regardless of source/test success.

**No deployment occurred:** the separate Cloudflare provisioning job is
gated by an explicit owner-controlled approval variable and account-scoped
encrypted credentials. Deploying or altering a GitHub App webhook URL is
not part of this source qualification, and Render is excluded by owner
instruction.

## Account configuration, not in chat

[Cloudflare Workers dashboard](https://dash.cloudflare.com/) → select the Cloudflare account to own the pilot. The existing GitHub Actions secret `MATHGRAPH_CHECK_APP_PRIVATE_KEY` contains the correct *rotated* App credential. In **metalogiclabs/mathgraph** GitHub repository [Actions secrets](https://github.com/metalogiclabs/mathgraph/settings/secrets/actions), additionally set:

- `CLOUDFLARE_ACCOUNT_ID`: account ID for the intended Cloudflare workspace (you needn't paste it into chat).
- `CLOUDFLARE_API_TOKEN`: custom account-scoped API token allowing Workers Scripts Edit and Queues Edit. Restrict the token to the intended account only.
- `MATHGRAPH_CHECK_WEBHOOK_SECRET`: a new random secret that will be configured identically inside GitHub App Webhook settings. **Do not send it in chat.**

Set repository [Actions variable](https://github.com/metalogiclabs/mathgraph/settings/variables/actions) `MATHGRAPH_CF_DEPLOY_APPROVED=true` only when the Cloudflare account/token are the intended ones and you authorize deploying this isolated service. Until then, the `Cloudflare approved deployment pilot` job is **skipped**, not deployed. On the next source push to the pilot branch the approved deployment job will provision the two specific queues, deploy Worker `mathgraph-check-webhook-pilot`, and push the already-rotated App PEM and webhook signing secret to Cloudflare's encrypted Worker secrets. No values are copied into Git commits, CI artifacts or command arguments.

If you also approve automatically configuring the registered GitHub App webhook URL **after** Cloudflare `/ready` is verified, set Actions variable `MATHGRAPH_CF_HOOK_ACTIVATE_APPROVED=true`. The deployment's guarded activation reads the actual Cloudflare workers.dev subdomain, verifies App `5308912`, checks its `pull_request` subscription, and writes an HTTPS-only webhook URL with the matching signature secret. It refuses to replace a different existing webhook URL unless you explicitly set `MATHGRAPH_CF_HOOK_REPLACE_APPROVED=true`. Do not approve replacement unless you reviewed the current App webhook URL.

Updating the GitHub App webhook configuration does not prove the webhook is active or that GitHub delivered an event. Only a real signed `pull_request` payload that produces a new native `neutral` Check Run at its exact SHA closes that final gate.

The dedicated Worker is separate from the MathGraph.org website and its Vercel hosting. It is not hosted on Render.

## Live acceptance after deployment

Use the actual Cloudflare-generated `https://<worker>.<account>.workers.dev` URL. GET `/health` is only process liveness; GET `/ready` returns HTTP 200 **only** when the queue binding, correct App ID/Client ID, a parseable RSA App private key, and webhook secret are configured. A non-ready Worker must not receive live GitHub events.

In GitHub's existing [MathGraph Check App settings](https://github.com/organizations/metalogiclabs/settings/apps), set the webhook target to that exact HTTPS URL with `/github/webhook`, configure the identical signing secret and subscribe to `pull_request` (App ID 5308912). Keep it installed on only `metalogiclabs/go-ethereum` for the pilot. Trigger a controlled PR update inside the owned fork and independently inspect: authenticated delivery result HTTP 202, queued event consumption, native `MathGraph Check / evidence scope` on exact new head under `app.id=5308912`, neutral conclusion, no duplicate after redelivery, stale-commit and invalid-signature negatives.

Live webhook delivery is **UNKNOWN** until those observations exist. The dry-run and mocked integration tests are not deployments.

## Source qualification

`node --test integrations/mathgraph-check-github/cloudflare/*.test.mjs`

`npx wrangler@4.129.1 deploy --dry-run --config integrations/mathgraph-check-github/cloudflare/wrangler.toml`

These exercises need no Cloudflare credentials. Cloudflare's Worker Free tier has a queue operation allowance, but queue message retention and Worker CPU limits are bounded. This deployment is a controlled evaluation, not a production SLA.

## Activation checkpoint — 14 October 2026

The operator has confirmed configuring the GitHub repository approval variables and secrets. Deployment is still evidence-gated: the Cloudflare deployment workflow must authenticate to the correct account, verify queues and Worker readiness, and inspect the existing GitHub App webhook URL before modifying it. A commit to this reviewed pilot document initiates that already-approved workflow. Do not treat workflow commencement as live webhook qualification; require the actual GitHub delivery and an App-owned check on the exact source SHA.
