# MathGraph Check — source-head read-window stability, V0

Date: 29 October 2026. Research branch only, no product deployment.

## Decisive negative and bounded correction

`githubSnapshot` originally read the PR source once, then fetched the old
head's check-runs. A PR advancing from head B to head C during those API
reads could yield an `OBSERVED` report for B after C became current. A change
to the PR base during the same window was likewise not detected.

The three test-first cases at `source-head-stability-v0.test.mjs` failed
before the change (3/3 RED): missing expected rejection for head/base changes,
and a stable source read only once rather than twice. The minimal correction
re-reads the authenticated PR base/head after check-run capture and rejects
if either has moved or repository identity changed. Both moving-source cases
and the stable positive control subsequently passed locally (3/3 GREEN).

The source-specific claim is **WARRANTED_BOUNDED for a single scheduled
mid-read PR-source change**, conditional on trustworthy GitHub API responses.
It is **not** an atomic snapshot, a complete solution to concurrent new
check-run attempts, a proof of user's functional intent, or a source-B
requalification attestation. If a PR changes after the final read, this
bounded test does not guarantee the later current head. Caller-provided
custom fetchers are a test seam, not independent production authority.

## Preserved outstanding result

At exact head B, a fresh qualified `auditIntent` receipt can be `OBSERVED`;
the `compareSnapshots` facade still conservatively reports `UNKNOWN` when
moving A→B because it has no independently authenticated requalification
witness. Do not set the raw `monitor` helper's unauthenticated boolean from
caller input. The earlier future-transition [test branch](https://github.com/metalogiclabs/mathgraph/tree/research/mathgraph-check-future-transition-20261029)
and its 129-test run remain valid predecessor evidence.

## Reproduce

Execute all `integrations/mathgraph-check-github/*.test.mjs` individually with
Node, or use the branch-specific Actions workflow. Local full replay after
the change was 132/132 across 18 files, zero failures; this does not replace
independent CI qualification.

[ROS seven-gate ledger](https://app.notion.com/p/4083e523d7ab81f78ea3f212da9b8509).
