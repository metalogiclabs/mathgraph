# GitHub App-authorized first Check Run: no hosting dependency

This isolated acceptance gate lives on the existing MathGraph draft PR #167 branch. It is not a deployment and it does not alter mathgraph.org, Vercel, Render or an upstream Ethereum repository.

The official GitHub action actions/create-github-app-token (v3, pinned commit) creates a short-lived token with only Checks write, Pull requests read and Actions read for the Metalogic go-ethereum fork. The workflow's built-in GITHUB_TOKEN has only Contents read; it cannot silently substitute for the registered App.

The MathGraph engine checks PR #19 at exact SHA a04aa77aaebd81d11274560e8d24d90c6f417589, with source-declared concurrent_fcu and remote_conflicting_fcu both UNKNOWN. It creates only a neutral and advisory-only native Check. It reads the Check back from GitHub and demands app.id 5308912. The shared external ID allows later webhook processing to recognize this same exact-SHA record. Wrong author, wrong SHA, missing evidence, incomplete check enumeration or stale PR state reject without a positive qualification.

## Single required account setup

Generate a fresh private key in the already registered MathGraph Check GitHub App settings, replacing the one previously uploaded to chat before live/public use. In metalogiclabs/mathgraph GitHub Settings, under Secrets and variables -> Actions, add repository secret MATHGRAPH_CHECK_APP_PRIVATE_KEY containing that newly generated PEM.

Correct secret settings page: https://github.com/metalogiclabs/mathgraph/settings/secrets/actions

Never paste the secret into this chat, GitHub code, a PR, a GitHub Actions input, a log or a generated artifact.

Confirm the App is installed under metalogiclabs, with access to go-ethereum, and has Pull requests read, Actions read, Checks write. If these permissions changed after installation, GitHub requires approval of the updated App installation.

The workflow file mathgraph-check-app-publisher-v0.yml triggers on a push to the protected pilot branch. It has a prior Actions run that can be rerun once the secret is saved. If the key is missing, the run prints NOT_CONFIGURED and only the unit tests qualify. A missing App installation or a permission mismatch fails the action; no alternate token or App is used.

## Qualification contract

Live acceptance requires an actual GitHub Check Runs API response at the precise PR head with name MathGraph Check / evidence scope, app.id 5308912, conclusion neutral and exact external ID. Readback must independently confirm the same tuple. Success under the github-actions App ID 15368 is explicitly insufficient.

This one-time GitHub Actions path does not receive future PR webhooks on arbitrary repositories. Automatic all-repository operation still needs separately qualified webhook ingress, rate controls and a retry queue. Cloudflare Workers and Queues are candidates for that later operational gate, without replacing the existing verifier.
