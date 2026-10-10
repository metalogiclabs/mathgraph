# MathGraph P0 Authority Report — Resolve Record 002

Authority was reconciled on 2026-10-10T19:57:15Z (2026-10-11 NZDT). This report fixes the release and evidence identities used by the P0 branch. It does not itself promote a mathematical claim.

## Release authority and rollback

The production release authority is Vercel deployment `dpl_CWUMpTovnYsFhsks2RDaaVqLT62k`, serving commit `93850c7d66740699e8ad52452d1fe9bd38a4fc51`. Vercel control-plane inspection reported:

- project: `mathgraph` in the `over-market` context;
- target: `production`;
- state: `READY`;
- deployment URL: `https://mathgraph-r4vtjq3pr-over-market.vercel.app`;
- production alias: `https://mathgraph-over-market.vercel.app`;
- created: `2026-10-10T08:57:00Z` (`2026-10-10 21:57:00 NZDT`).

Commit `93850c7d66740699e8ad52452d1fe9bd38a4fc51` is both the P0 integration base and the rollback point. P0 staging does not change the production deployment, domain, DNS, nameserver, registrar, or mail configuration.

The deployment evidence classes must not be conflated:

- The Vercel control plane identifies `dpl_CWUMpTovnYsFhsks2RDaaVqLT62k` as the ready production deployment and lists its production alias. The release authority associates that deployment with commit `93850c7d66740699e8ad52452d1fe9bd38a4fc51`.
- GitHub deployment record `6978573287` is separate metadata for commit `93850c7d66740699e8ad52452d1fe9bd38a4fc51`. It records environment `Preview`, successful status `19560189512`, and preview URL `https://mathgraph-pcpcnw2g1-over-market.vercel.app` at `2026-10-10T08:56:10Z`. It is not the production deployment record and is not evidence that the GitHub environment named `Preview` is production.

## Repository and pull-request state

The GitHub states observed during reconciliation were:

| Authority | State | Exact head | Base / qualification |
| --- | --- | --- | --- |
| `main` | branch head | `9ad69aa966ad4e07539a80d66d08a89948247a64` | GitHub `refs/heads/main` |
| PR #153, `website/mathgraph-brand-assets` | open draft; merge state `CLEAN` | `b6e4094a925af0435da92ed88cf512b466052079` | base `main`; website and evidence-integrity checks succeeded; Vercel status succeeded |
| PR #154, `codex/mathgraph-agent-interface` | open draft; merge state `CLEAN` | `93850c7d66740699e8ad52452d1fe9bd38a4fc51` | stacked on `website/mathgraph-brand-assets`; website and evidence-integrity checks succeeded; Vercel status succeeded |
| PR #151, `mathgraph-check-living-warrants-v1` | open draft; merge state `UNSTABLE` | `040456fc8862c79c8b384ce63846628274b678be` | base `mathgraph-check-standalone-public-v1`; authoritative `qualify-and-publish` check succeeded; its separate Vercel status failed |

PR #151 is consumed as a qualified source lineage, not merged as a release branch. Its unrelated Vercel failure does not replace or negate the successful source-qualification run, but the PR remains open, draft, and `UNSTABLE` and must not be represented as a generally green release candidate.

## Resolve producer and consumer authority

The producer authority is MathGraph commit `040456fc8862c79c8b384ce63846628274b678be` on `mathgraph-check-living-warrants-v1`.

- Workflow: `MathGraph Check — Living Warrant Evidence V1`
- Job/check: `qualify-and-publish`
- Actions run: `38025044631`
- Event: `push`
- Result: `completed` / `success`
- Run interval: `2026-10-10T04:43:16Z` to `2026-10-10T04:43:29Z`
- Run URL: `https://github.com/metalogiclabs/mathgraph/actions/runs/38025044631`

The implementation-independent replay authority is RealityGraph commit `9b3189a64825e2cb6ebc7b5c17f5f193bdf5cfe3` in `heathsanchez/realitygraph`, on branch `realitygraph-mathgraph-warrant-consumer-v1`.

- Commit subject: `Run independent source-pinned cross-repository warrant replay with strict negative gates`
- Workflow: `RealityGraph — Independent MathGraph Warrant Replay`
- Actions run: `38025236380`
- Event: `push`
- Result: `completed` / `success`
- Run interval: `2026-10-10T04:46:37Z` to `2026-10-10T04:46:45Z`
- Run URL: `https://github.com/heathsanchez/realitygraph/actions/runs/38025236380`

The RealityGraph replay is implementation-independent, but it remains under the same owner and is not evidence of independently owned external adoption.

## Immutable snapshot identity

The imported public snapshot is `evidence/living_warrant_openai_jpl_20261010.json`:

- snapshot ID: `mg-living-warrant-openai-jpl-20261010`;
- schema: `mathgraph.living-warrant-snapshot.v1`;
- exact byte length: `5290`;
- transport SHA-256: `0a850b112cce200f2fa97f0d861db712f3752712a6326e62f4c0d56996a95d87`;
- canonical payload SHA-256 (`snapshot_sha256`): `b95297a081d513fb0ec145a776cc997eaed18109d6b2af39fa8e61f6d637af41`.

Source pins contained by the snapshot are:

- OpenAI repository commit: `fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb`;
- OpenAI `history.md` Git blob SHA-1: `693874f398905b1bc59e01b898b223ae9956bfc2`;
- OpenAI `history.md` byte SHA-256: `41c2a2d470014b3628695c7aabf5fd0c93f6f687621fca172062f22b59ed6a1e`;
- JPL record ID: `mg-l4yaml-source-check-20261010`;
- JPL record SHA-256: `f0d092974d5d710fe9e17fb6759a894f2c28f2d3f5456439c071bd0a71c8d3cb`.

Local identity checks against `040456fc:evidence/living_warrant_openai_jpl_20261010.json` returned `5290` bytes for each copy, the same transport digest for each copy, `cmp` exit `0`, and no diff across the final four imported files. The imported snapshot is therefore byte-for-byte the qualified producer snapshot.

## Qualification boundary

This authority is a frozen, source-bound publication-change demonstration. Its runtime status is `IMMUTABLE_HISTORICAL_SNAPSHOT_NOT_CONTINUOUSLY_MONITORED`.

The publisher notice authenticates only the pinned notice that three original OpenAI arguments were withdrawn. It does not authenticate the truth or falsity of the underlying mathematics. The three documentary support paths change from `SOURCE_DOCUMENTED` to `STALE`; all three corresponding mathematical theorem statuses remain `UNKNOWN`. The JPL finite-parser claim remains unchanged at `WARRANTED_BOUNDED`, limited to the independently qualified 48-case record. No new proof, refutation, live monitoring, or arbitrary natural-language verification is claimed.

The release is static and read-only. It accepts no arbitrary claims, URLs, repositories, proof code, or mutations, and it exposes no execution endpoint. Unknown schemas, relations, versions, source pins, and semantic transports must be rejected or resolved as typed `UNKNOWN`.

Transport and content hashes detect substitution relative to trusted expected digests; they do not authenticate a publisher by themselves. Git commit pins are provenance references governed by a separate repository/key trust policy. Neither hashes nor commit identity convert documentary evidence, finite-search results, or an external replay into a verified theorem.

## P0 integration order

The release stack and source import order are:

1. GitHub `main` at `9ad69aa966ad4e07539a80d66d08a89948247a64`.
2. Branding PR #153 at `b6e4094a925af0435da92ed88cf512b466052079`, stacked on `main`.
3. Agent-interoperability PR #154 and deployed rollback point at `93850c7d66740699e8ad52452d1fe9bd38a4fc51`, stacked on #153.
4. P0 design commit `7c973b7073d5dba4c2f3ddacd80dd8b45666c22c` on the branch created from `93850c7d66740699e8ad52452d1fe9bd38a4fc51`.
5. The ten qualified PR #151 source commits, cherry-picked in order without conflicts:

| Source commit | P0 commit | Subject |
| --- | --- | --- |
| `b99cdc16bded941cf7b82f6769f3ce5aa8a4ea63` | `a6a823db7c39cf9f2047f225c83315e0599a5a4e` | Add typed dependency-local source warrant reclosure with OpenAI withdrawal and JPL control |
| `85dfe64895b0093d12080a96ae7e6ddfbcd54f97` | `94bb663592332cbfb2f3fd85b5d8ce0001b1009e` | Protect typed warrant reclosure, real withdrawn source, unaffected JPL evidence and negative controls |
| `fb60f7ac784f0d58d7bf6c170b502b6c6ba78e7b` | `2ab90ad807365704bcadfcad871e039e2107acd8` | Qualify pinned OpenAI withdrawal and JPL evidence with strict graph tests and preview artifact |
| `7f27a59d2e66a202b04884c57369047cc9b91cf5` | `ce8fc5c7bc3439d1dc392f422708911669b802bf` | Publish exact-source qualified living-warrant snapshot for independent consumers |
| `c3e722b69c376119fdf8e3cf11c66a3c9475a619` | `10af21c3c109524f70fdeda2255789f17a6e7b28` | Require exact published manifest to match independently regenerated source-bound snapshot |
| `f10b06f10b3a670b587124909c014aab59807499` | `a9fc0d1a001193f80fac45b9544115a882549058` | Expose minimal typed claim/evidence graph so external consumers can recompute reclosure |
| `41f408b82a9163b45c2b7f85c00e093bc23e2148` | `c4c5648652803be50936baeee960bbac928f672d` | Canonicalize warrant graph edge arrays across JSON transport |
| `d2a832c4238b4c15c29bb4cfdb656a5c7f78416f` | `63f2bed24754175bf1e34a73c8ec96815ad3025d` | Publish derivation-complete immutable graph for independent replay |
| `589ff15f4daa235b12bbe1929cbd470a421eb47f` | `b3ae8227b7ecb950114be132c6595e9f02e8a6ed` | Pin full derivation payload and refuse publication drift |
| `040456fc8862c79c8b384ce63846628274b678be` | `62e26e551c849180750845f4124c979f2245dbc6` | Repair strict publication gate closing quote; preserve exact pinned manifest |

Record 001 is not modified by this import.

## Verification performed

The required source-independent verification was:

```text
python -m pytest tests/test_mathgraph_living_warrants_v1.py -k 'not RealSourceTests' -q
..........                                                               [100%]
10 passed, 6 deselected in 0.10s
```

The six deselected tests are the fixture-bound `RealSourceTests`: exact OpenAI source hash/three-withdrawal parsing, mutated-source refusal, JPL receipt pin and finite-case scope, exact-source end-to-end graph construction, snapshot/HTML round-trip, and forged qualified-JPL rejection. They were not rerun locally because this source-independent check intentionally excludes the pinned external OpenAI history and qualified JPL receipt fixtures. Their producer qualification authority is successful Actions run `38025044631`; the independent consumer authority is successful Actions run `38025236380`.
