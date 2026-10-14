# MathGraph Check — GitHub App activation

## Current boundary

The shadow pilot runs real source-pinned public PR queries. The webhook's HTTP-to-Check-Run path has passed **mocked GitHub API** integration tests. This is **not** an installed or hosted app. It must not be presented as active until a signed real GitHub webhook produces a neutral Check Run on its exact PR head.

## 1. Register under Metalogic Labs

[Open GitHub's prefilled MathGraph Check registration](https://github.com/organizations/metalogiclabs/settings/apps/new?name=MathGraph%20Check&description=Evidence-backed%20PR%20triage%2C%20exact%20source%20scope%20and%20explicit%20unknowns.%20Advisory%20only.&url=https%3A%2F%2Fmathgraph.org%2F&public=false&webhook_active=false&checks=write&pull_requests=read&actions=read&request_oauth_on_install=false&events%5B%5D=pull_request)

Preselected: **MathGraph Check**, homepage `https://mathgraph.org/`, owner `metalogiclabs`, organization-only (private), **Pull requests: read**, **Actions: read**, **Checks: write**, event **pull_request**. Metadata read is implicit. No repository contents write, Issues write, OAuth user token, or merge authority.

**Keep the webhook INACTIVE at registration.** We do not have an authorized public endpoint on the current MathGraph production hosting account. Do not use an invented webhook URL. If GitHub offers different options than preselected, verify these permissions manually.

Only a person with organization authorization can register the app. Record its **public App ID and app slug**; do not put private keys or webhook secrets in a chat, commit, issue or check output.

## 2. Install only on a controlled repository

In the GitHub App settings, select **Install App → Metalogic Labs → Only select repositories → `metalogiclabs/go-ethereum`**.

An installation with its webhook disabled is a setup step, not a functioning integration. Do not publish a public installation link, enable required checks, or describe this as continuous repo verification yet.

## 3. Deploy the existing worker behind authenticated HTTPS

The existing `webhook.mjs` requires a dedicated persistent Node 22+ process, not a static website and not a terminating serverless request. Deploy it with a stable HTTPS webhook URL ending in `/github/webhook` and environment variables:

- `GITHUB_APP_ID` — public numerical App ID
- `GITHUB_APP_PRIVATE_KEY` — **private** GitHub-generated PEM (environment secret)
- `GITHUB_WEBHOOK_SECRET` — **private** random webhook signing secret
- `MATHGRAPH_ALLOWED_REPOS=metalogiclabs/go-ethereum`
- `PORT` — listener port

Run `node integrations/mathgraph-check-github/webhook.mjs`. Health endpoint: `GET /health`. Restrict network exposure to your TLS reverse proxy; never expose debugging routes, installation tokens or secret material. Configure GitHub to use the same signing secret as the worker; then enable only the **pull_request** webhook.

The Vercel connector's `over-market` scope returned HTTP 403 during activation preparation, so there was no authorized deployment to `mathgraph.org`.

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
