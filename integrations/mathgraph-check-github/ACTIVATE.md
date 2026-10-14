# MathGraph Check — GitHub App activation

## Immediate App-identity gate — GitHub Actions, no external hosting

The owner explicitly excluded **Render** as a deployment destination. Do not create a service, change billing, install secrets or select a workspace there. The static [mathgraph.org](https://mathgraph.org/) site and its Vercel account are likewise **not needed** to qualify the first registered-App Check.

**Already qualified on the real GitHub Checks API:** [native neutral check #115639910465](https://github.com/metalogiclabs/go-ethereum/runs/115639910465) at precisely `metalogiclabs/go-ethereum` PR #19 head `a04aa77aaebd81d11274560e8d24d90c6f417589`, produced by [Actions run #38498578840](https://github.com/metalogiclabs/go-ethereum/actions/runs/38498578840). GitHub records its publisher as `github-actions`, **not** registered MathGraph App `5308912`.

**Next cheapest actual identity check:** use the existing [registered-App publisher workflow](../../.github/workflows/mathgraph-check-app-publisher-v0.yml) and [APP_NATIVE_ACTIVATION.md](APP_NATIVE_ACTIVATION.md). This workflow runs entirely in **GitHub Actions**, using a short-lived repository-scoped token issued for the **registered GitHub App**; it checks GitHub's returned `app.id=5308912` and the exact PR SHA. No independent HTTPS service, webhook receiver or other hosting account is required **for this first App-identity test**.

The [exact missing-secret CI #38503497554](https://github.com/metalogiclabs/mathgraph/actions/runs/38503497554) failed closed: local adversarial tests ran, but no App token or App-native Check Run was issued. The owner must first rotate the App private key previously uploaded to chat, store the **fresh** PEM as the GitHub Actions repository secret `MATHGRAPH_CHECK_APP_PRIVATE_KEY` directly in [GitHub repository Actions secrets](https://github.com/metalogiclabs/mathgraph/settings/secrets/actions), and confirm installation on `metalogiclabs/go-ethereum` with Checks write, Pull requests read and Actions read. Never paste or transfer a private key through chat, commits, logs or PR comments. Then rerun the existing App-publisher job; accept only a real neutral exact-head Check whose GitHub-reported App ID matches `5308912`.

**Different later gate:** automatic real signed `pull_request` webhook-to-check delivery needs an approved long-running HTTPS worker, fresh `GITHUB_WEBHOOK_SECRET`, and its own identity, stale-SHA, replay and restart tests. Hosting for that future gate is **not selected**. An App-identity Check created through Actions does **not** count as a successful webhook delivery.

## Current boundary

The shadow pilot runs real source-pinned public PR queries. The webhook's HTTP-to-Check-Run path has passed **mocked GitHub API** integration tests. This is **not** an installed or hosted app. It must not be presented as active until a signed real GitHub webhook produces a neutral Check Run on its exact PR head.

## 1. GitHub App registered (owner-provided settings, 14 October 2026)

The owner provided the following **public identifiers** from GitHub App settings:

- Owner: `metalogiclabs`
- App ID: `5308912`
- Client ID (recommended JWT issuer): `Iv23lioiUs5KfHD7mkkw`
- Manage: [GitHub organization App settings](https://github.com/organizations/metalogiclabs/settings/apps)

The current worker accepts `GITHUB_APP_CLIENT_ID` and falls back to `GITHUB_APP_ID`. This registration has not yet been independently authenticated with GitHub's `GET /app` JWT API. Do not put a private key or webhook secret into the repository, CI artifacts, chat messages or PR comments.

Before activation, confirm repository permissions **Pull requests: read**, **Actions: read**, **Checks: write**, event **pull_request**, and no contents write or merge authority. Keep the webhook inactive until a verified hosted HTTPS callback is ready.

## 2. Install only on a controlled repository

In the GitHub App settings, select **Install App → Metalogic Labs → Only select repositories → `metalogiclabs/go-ethereum`**.

An installation with its webhook disabled is a setup step, not a functioning integration. Do not publish a public installation link, enable required checks, or describe this as continuous repo verification yet.

## 3. Optional future webhook service (separate approval and host)

The existing `webhook.mjs` requires a dedicated persistent Node 22+ process, not a static website or a terminating serverless request. **Do not deploy it until a non-Render provider has been approved.** That future service would need a stable HTTPS webhook URL ending in `/github/webhook` and the following environment variables:

- `GITHUB_APP_CLIENT_ID` — public Client ID (preferred JWT issuer; `GITHUB_APP_ID` remains a valid fallback)
- `GITHUB_APP_PRIVATE_KEY` — **private** GitHub-generated PEM (environment secret)
- `GITHUB_WEBHOOK_SECRET` — **private** random webhook signing secret
- `MATHGRAPH_ALLOWED_REPOS=metalogiclabs/go-ethereum`
- `PORT` — listener port

Run `node integrations/mathgraph-check-github/webhook.mjs`. Health endpoint: `GET /health`. Restrict network exposure to your TLS reverse proxy; never expose debugging routes, installation tokens or secret material. Configure GitHub to use the same signing secret as the worker; then enable only the **pull_request** webhook.

The public MathGraph website is a separate static deployment and must not be repurposed to host the webhook worker. A separate authorized worker deployment and explicit secret setup are still required; GitHub App registration is not deployment.

## 4. Later signed-webhook end-to-end gate

After a separate hosting decision, create or update a PR **in the installed repository**. Verify all of these before calling the **webhook service** active (the earlier Actions App-identity gate does not establish this):

- GitHub webhook delivery status is successful, signed with the configured secret.
- The App authenticates using its installation token and inspects the actual PR head SHA.
- A native `MathGraph Check / evidence scope` Check Run appears on that exact SHA with **neutral** conclusion, source-grounded evidence and explicit `ADVISORY_ONLY`.
- A later PR SHA update is rechecked; stale deliveries do not create checks.
- Duplicate delivery does not produce conflicting findings; investigate duplicates across worker restarts (in-memory dedup is not persistent).
- The app cannot push code, approve PRs, merge, or modify repository settings.

Do not enable required-status policy: GitHub regards a neutral check as sufficient for some branch protection configurations. `UNKNOWN` is not verification success.

## 5. Next before external installations

Add durable delivery queue/idempotency, bounded retries and rate-limit handling, private-repo/data retention policy, deployment observability and failure alarms, and outside-owner end-to-end qualification. Only then consider making this org-only app public.

## Existing evidence

- [Pilot PR #167](https://github.com/metalogiclabs/mathgraph/pull/167)
- [Original source-bound shadow run #38491853576](https://github.com/metalogiclabs/mathgraph/actions/runs/38491853576)
- The current branch's CI exercises signed local HTTP delivery against mocked GitHub check-run endpoints and separately reads two actual PRs through the GitHub API.

**Status:** App registration was reported by the owner; the first App-authored Check has not passed. GitHub Actions is the current identity-check path. A later external HTTPS endpoint remains unselected and is not completed by pushing these files.
