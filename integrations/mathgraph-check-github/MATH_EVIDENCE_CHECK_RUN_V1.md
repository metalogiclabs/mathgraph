# MathGraph Check — mathematical evidence GitHub App V1

**Technical status: opt-in integration candidate.** No third-party installation, webhook, human meaning review, or live Check Run has been performed. The native Lean replay and resolved environment are independently evidenced in GitHub Actions; the source-to-formal meaning review is still `UNKNOWN`.

## What a mathematical pull request gets

The new `math-evidence-check-run-v1.mjs` converts a successfully corroborated `ENVIRONMENT_AND_REPLAY_CORRELATED` observation into a **neutral** GitHub Check Run proposal, with separate statements for:

1. Original source and formal theorem pinned to an immutable source.
2. Proof execution and standard-axiom report replayed by Lean.
3. Resolved Lake/Mathlib dependency environment independently checked.
4. Exact-head human source-to-formal review either *attested* or `UNKNOWN`.
5. Mathematical equivalence and intent warrant always **NOT ESTABLISHED** by this automated system.

Neither an ordinary green CI status nor a self-authored review creates evidence authority. The Check Run always concludes `neutral`, never `success`, and carries no merge authority. On fresh changes, reruns, missing sources or unverifiable artifacts, requalify from scratch.

## Live opt-in installation (requires owner approval)

An operator can use the **existing registered MathGraph Check GitHub App** only if it has a fresh, repository-restricted installation token with:
- `Contents: read` to pin the workflow and repository head
- `Actions: read` to observe the run and download the artifact ZIP
- `Pull requests: read` for the exact-head human review
- `Checks: write` **only when the owner explicitly opts in to advisory Check Run publication**

The read-only collector does not require Checks:write. The current go-ethereum-specific writer worker must **not** be reused for Open Math Model repositories. A separate mathematical job with independent repository allowlisting, reviewer configuration, webhook identity verification (if events are used), and private operator trust manifests is required.

The **operator entry point** is `collectAndPublishMathEvidence`: it executes `collectMathSourceEvidenceWithEnvironment` itself, so no caller-supplied report can be substituted for authenticated GitHub observations. The pure renderer remains useful for unit tests and previewing an already authenticated observation, but **must not be exposed directly to untrusted clients**. The operator's source, theorem, workflow, environment and reviewer pins must be configured independently of the PR. Example:

```js
import {collectAndPublishMathEvidence} from './math-evidence-check-run-v1.mjs';

// input comes from an authenticated installation handler and private
// administrator trust configuration, NEVER from the PR body.
const preview = await collectAndPublishMathEvidence(adminInput);
// No network write; preview.mode === 'PREVIEW' only after full V2 correlation.

// Only after repository-owner opt-in and Checks:write provisioned:
const published = await collectAndPublishMathEvidence(adminInput,{
  publish: true,
});
// The renderer still posts only a neutral, exact-head advisory check.
```

In live mode the publisher re-reads the current PR head from GitHub and requires the same repository before posting a **neutral** Check Run. It checks the GitHub write response for the exact identity and expected neutral conclusion. The token stays out of output. A successful publication still does **not** automatically imply meaning equivalence or general correctness of the paper.


## One-command operator preview (no GitHub writes)

The read-only collector's administrative trust-file schema is documented in
[MATH_SOURCE_ENVIRONMENT_CORRELATION_V1.md](MATH_SOURCE_ENVIRONMENT_CORRELATION_V1.md).
Store the JSON outside the repository, owned by the operator and mode `0600`
(on Unix); never commit credentials or the administrator whitelist. The app
installation token is a short-lived separate environment variable:

```sh
MATHGRAPH_GITHUB_APP_TOKEN="$TOKEN" \
node integrations/mathgraph-check-github/run-math-evidence-check-v1.mjs \
  /private/mathgraph-admin-trust.json
```

This prints a **PREVIEW** of the neutral Check Run only after re-fetching
and correlating the authentic two-artifact V2 replay. It makes no GitHub write.
When the owner has explicitly authorized checks:write and a test installation
has been independently reviewed, **the only write opt-in is**:

```sh
MATHGRAPH_GITHUB_APP_TOKEN="$TOKEN" \
node integrations/mathgraph-check-github/run-math-evidence-check-v1.mjs \
  /private/mathgraph-admin-trust.json --publish
```

No webhook, bot, cron, account-discovery loop, automatic PR approval or
installation mutation is present. The CLI refuses extra JSON fields,
insecure file permissions, missing tokens, and unrecognized modes; the publish
path independently rereads the PR HEAD and only POSTs a neutral check.

## What is independently reproducible now

- Historical native Lean 4.28 replay with an axiom audit: [run #41346277520](https://github.com/metalogiclabs/mathgraph/actions/runs/41346277520).
- Native replay with resolved Lake/Mathlib dependency closure: [run #41356752114](https://github.com/metalogiclabs/mathgraph/actions/runs/41356752114).
- Environment SHA-256 (full resolved closure): `1a6ca48ac912d3f8900e4c4e4061d5c7b6921e92facca8bcd1a53c80fe7b2164`.
- Pinned original example: ProofNet-Verified `Artin_exercise_2_2_9` at commit `14879cb23e078d122adecd9578dd26a7304f753b`.
- The benchmark's natural-language/formal pair has not been freshly accepted by an independent mathematician here. It must not receive a semantic equivalence badge.

Run `node --test integrations/mathgraph-check-github/*.test.mjs`, or inspect this branch's read-only GitHub Actions gate for focused tests and an evidence/limitations summary.

## Current limits before offering an installation

- The positive publisher test exercises controlled GitHub API responses, not a real Check Run publish.
- No independent qualified mathematical review of the Artin translation has been obtained.
- No external repository's consent, data-processing agreement or App installation has been granted.
- The collector remains specialized to the pinned Artin example. General theorem onboarding and blind evaluation against strong semantic methods are not implemented; do not market broad automatic faithfulness detection.
- The new reporter observes qualified upstream results. It is not itself an independent proof kernel, an equivalence theorem, or a signed intent-probe receipt.

**Community contribution offer:** a small opt-in trial: one independently sourced theorem, three controlled changed-meaning statements, one independent mathematician's review, exact Lean replay, and a neutral reproducible GitHub Check. Compare accuracy against an equally informed baseline before making broader claims.
