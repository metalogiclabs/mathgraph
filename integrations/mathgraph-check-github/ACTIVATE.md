## Direct Render deployment of the qualified pilot branch

[Open the exact MathGraph Check branch in Render's deploy flow](https://render.com/deploy?repo=https://github.com/metalogiclabs/mathgraph/tree/mathgraph-check-github-app-shadow-v0). Render's official deployment URL syntax pins the *repository branch*, so it uses this branch's `render.yaml` instead of the public MathGraph site's `main`.

The no-cost pilot Blueprint creates one isolated Docker web service; the Render Dashboard must obtain the account owner's approval and prompt for `GITHUB_APP_PRIVATE_KEY` and `GITHUB_WEBHOOK_SECRET`. **Do not reuse the PEM uploaded to chat for public operation: rotate it within the existing GitHub App first.** Never supply these values through issues, Actions logs, Git commits, chat, or public status pages.

On successful Render deployment, the actual generated `https://<service>.onrender.com/github/webhook` URL must be configured in the already registered GitHub App settings. Do not assume any hostname until Render issues it. Free services may sleep and fail GitHub's webhook timeout when cold; treat Free as a best-effort pilot, not continuous production uptime. The *first real signed webhook and the Check Run's `app.id=5308912`* are still the decisive unqualified boundary.

**Latest protected source qualification:** [CI #38499648822](https://github.com/metalogiclabs/mathgraph/actions/runs/38499648822) SUCCESS at `f86ad7dc4aa06b45041ac511ba2a8b4d29b7515c`. The integration test now exercises both different delivery IDs and a restarted worker; the worker consults the exact source SHA and App ID in GitHub's existing Check Runs before issuing another write. This provides bounded deduplication, not a durable queue or cross-instance exactly-once guarantee.

# MathGraph Check — GitHub App activation

## Updated activation path — no Vercel dependency

The static [mathgraph.org](https://mathgraph.org/) website and its Vercel permissions have **nothing to do with** the GitHub App's operational authorization. Do not attempt to change Vercel team access or website deployment to activate this checker.

**Already qualified on the real GitHub Checks API:** [native neutral check #115639910465](https://github.com/metalogiclabs/go-ethereum/runs/115639910465) at exactly `metalogiclabs/go-ethereum` PR #19 head `a04aa77aaebd81d11274560e8d24d90c6f417589`, produced by [Actions pilot run #38498578840](https://github.com/metalogiclabs/go-ethereum/actions/runs/38498578840). It uses the unchanged MathGraph Check analyzer, but GitHub records its publisher as `github-actions`, **not** App `5308912`. This qualification does not prove the App is installed or that its webhook is live.

The remaining task is strictly to run the **existing webhook worker under the registered App identity** on an isolated HTTPS service. A no-secret [Render Blueprint](../../render.yaml) has been added at the repo root; use an authorized Render connection and select branch `mathgraph-check-github-app-shadow-v0`. It builds the already qualified Docker image, permits only `metalogiclabs/go-ethereum` and prompts for both secrets without storing them in Git. The Free pilot plan sleeps after inactivity: warm `/health` before testing GitHub delivery; use an always-on plan for any continuous service-level claim.

Before enabling the webhook, generate a fresh private key from the existing App's GitHub settings, then provide the PEM and a new webhook secret **directly to the hosting provider's secure environment-variable interface**, not a chat or Git commit. Configure the same signing secret and the actual assigned HTTPS `/github/webhook` URL in GitHub App settings. App installation, correct Checks/Pull Requests/Actions permissions and a real delivery-to-native-check assertion remain unqualified until separately observed.

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

## 3. Deploy the existing worker behind authenticated HTTPS

The existing `webhook.mjs` requires a dedicated persistent Node 22+ process, not a static website and not a terminating serverless request. Deploy it with a stable HTTPS webhook URL ending in `/github/webhook` and environment variables:

- `GITHUB_APP_CLIENT_ID` — public Client ID (preferred JWT issuer; `GITHUB_APP_ID` remains a valid fallback)
- `GITHUB_APP_PRIVATE_KEY` — **private** GitHub-generated PEM (environment secret)
- `GITHUB_WEBHOOK_SECRET` — **private** random webhook signing secret
- `MATHGRAPH_ALLOWED_REPOS=metalogiclabs/go-ethereum`
- `PORT` — listener port

Run `node integrations/mathgraph-check-github/webhook.mjs`. Health endpoint: `GET /health`. Restrict network exposure to your TLS reverse proxy; never expose debugging routes, installation tokens or secret material. Configure GitHub to use the same signing secret as the worker; then enable only the **pull_request** webhook.

The public MathGraph website is a separate static deployment and must not be repurposed to host the webhook worker. A separate authorized worker deployment and explicit secret setup are still required; GitHub App registration is not deployment.

## 4. First live end-to-end gate

Create or update a PR **in the installed repository**. Verify all of these before calling the app active:

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

**Status:** registration and authorized HTTPS endpoint are external controls; neither is completed by pushing these files.
