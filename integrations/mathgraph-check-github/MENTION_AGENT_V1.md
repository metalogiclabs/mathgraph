# MathGraph mention pilot

A separate, opt-in service for `@MathGraph -check` on pull requests. It reads the PR title/body, up to 30 changed-file patches from an immutable base/head comparison, and exact-head Actions observations; makes one structured model request; and updates one comment with at most three candidate findings and a next step. The configured handle must match the actual GitHub App identity. GitHub App mentions do not install the App.

**Current boundary:** source-bound LLM advisory analysis. No Lean execution, proof verdict, qualified paper-to-theorem correspondence, or verified repair is performed by this service. `-fix` explicitly reports that the isolated repair executor is not connected and spends no model tokens. The existing mathematical source/environment collectors remain separate and unchanged. Repository contents, suggested commands and model text are never executed.

## Run

Requires Node 22 or newer, Linux `flock` (util-linux), and a persistent local POSIX filesystem supporting advisory locks. No npm dependencies.

```sh
node integrations/mathgraph-check-github/mention-server-v1.mjs /secure/mathgraph-policy.json
```

Inject these secrets through the host's secret manager, never through repository files, PR comments, command-line literals or logs:

- `OPENAI_API_KEY`: project-scoped API credential. The owning API account pays for inference.
- `MATHGRAPH_WEBHOOK_SECRET`: dedicated GitHub webhook signing secret.
- `MATHGRAPH_APP_PRIVATE_KEY`: dedicated App's RSA private key in PEM form.

Non-secret deployment settings:

- `MATHGRAPH_APP_ID`: registered App's numeric ID.
- `MATHGRAPH_APP_OWNER`: expected GitHub login owning that App.
- `MATHGRAPH_STATE_DIR`: absolute persistent directory, private to this service.
- `PORT`: defaults to 8080; terminate HTTPS at the host ingress.

Create a separate minimal-permission App for the pilot, subscribe to **Issue comments**, and set its webhook to `https://<service>/github/webhook`. Permissions: Contents read, Pull requests read, Actions read, Issues write. Install on only the operator's chosen demo repository. No merge, source-write or upstream installation permission is needed. Do not repurpose a differently scoped production App without reviewing that change.

The policy file is operator-controlled, outside the repository. Its fields are:

| Field | Meaning |
|---|---|
| `repositories` | Exact allowed `owner/repository` names |
| `userIds` | Explicit numeric GitHub user IDs allowed to initiate spend |
| `handle` | Actual mention login, e.g. `MathGraph` if available |
| `model` | Explicit supported model ID; choose and test against the API account |
| `inputCentsPerMillion` | Conservative current input token price, in integer US cents per million |
| `outputCentsPerMillion` | Conservative current output token price, including reasoning where billed |
| `maxOutputTokens` | Hard per-request output token maximum; e.g. 4096 |
| `maxInputBytes` | Maximum serialized source/observation input bytes; e.g. 40000 |
| `jobCapCents` | Maximum reserved inference cost per check; suggested demo ceiling 500 |
| `totalCapCents` | Total persistent inference reservation pool; suggested demo ceiling 5000 |

No model or price is assumed. Confirm model support for the Responses API and strict JSON schema before enabling. A deployment requires actual API access and billing/credit availability; local fixture tests do not establish them. Provider rates changing beyond configured bounds invalidate a dollar-cap estimate. Hosting, GitHub requests, storage and future proof-execution compute are outside the inference reservation.

## Spend and retry policy

One model request per accepted comment; no automatic paid retries or tools. Before calling the API, reserve a worst-case textual input-token allowance (`maxInputBytes + 8192`) and the configured maximum output tokens at operator-supplied rates. No image or tool inputs are accepted. Uncertain or failed requests retain their full reservation. A new comment is a new request and can consume another reservation; webhook redelivery is deduplicated by repository and comment ID.

An OS-managed `flock` serializes reservations and is released on process termination. One-cent exclusive reservation files and job directories persist across restart. All service instances must share the SAME state directory; do not deploy replicas with independent disks. Budget is lifetime for that directory, not daily or monthly. Never automatically clear it. The lock file may persist after a crash; it does not retain lock ownership. An interrupted partial reservation consumes capacity, not permission to exceed it.

Ingress stores accepted events before returning 202, then runs a sequential work queue in the same long-running process. On restart, pending inbox files are revisited. A claimed job with a saved result republishes that result without repeating inference. If inference completion is uncertain, recovery reports UNKNOWN and never retries the paid request. Recovery of an existing comment checks its App ownership and PR destination through GitHub. A crash between comment creation and saving its ID can leave an orphan progress comment; recovery posts a separate unresolved result. This is a small pilot, not a managed distributed queue.

## Evidence and user interface

Only standalone `@<handle> -check` or `@<handle> -fix` comments from approved human IDs qualify. Edited comments, bot comments, quoted commands, prose surrounding a command, and unapproved repositories/users are ignored. The webhook signature is checked before parsing. App identity and installation are independently read from GitHub, and a repository-scoped installation token is revoked after the job.

Model findings remain proposals even if they use confident language. The deterministic report always says proof was not replayed and meaning is unverified. Untrusted model Markdown, raw HTML and mentions are escaped. Both comparison SHAs are recorded. Only first-party branches in the configured repository are accepted. Final publication rechecks the live PR head; changed revisions withhold model findings. GitHub has no atomic compare-and-comment operation, so every result retains its explicit revision and cannot promise to stay current after publication.

The collected patches may omit surrounding definitions or be truncated. This limits analysis; a model comment cannot establish all mathematical dependencies or a global absence of defects. No findings is explicitly not proof of correctness. Missing source, model error, timeout or malformed output yields an unresolved result.

## Verification

```sh
node --test integrations/mathgraph-check-github/mention-agent-v1.test.mjs integrations/mathgraph-check-github/mention-server-v1.test.mjs
node --test integrations/mathgraph-check-github/*.test.mjs integrations/mathgraph-check-github/cloudflare/*.test.mjs
```

The HTTP test uses a real local server and signed GitHub-shaped fixture delivery. The model/GitHub transports are fixtures: no paid inference, real App posting, deployment, external mathematical finding, or proof repair is established by those tests.

Before public use, run one live opt-in check against a controlled demo PR with known claim, record its exact source, inspect model usage and the resulting public comment, then test one changed-head withdrawal. Verify costs and model quality before broader access.
