# MathGraph Check: pinned math-source evidence bytes V1 (advisory)

This milestone extends the [independent GitHub host observation](MATH_SOURCE_GITHUB_HOST_V1.md) with byte inspection. It stays **read-only** and does not approve, install, comment, publish Check Runs, merge, or mint a trusted `mathgraph.intent-probes.v1` receipt.

## Scope

`math-source-evidence-bytes-v1.mjs` exports two pure verifiers:

| Function | Caller-supplied evidence | Proven fact | Important non-claim |
| --- | --- | --- | --- |
| `verifyPinnedArtinArtifactBytes` | downloaded GitHub Actions artifact ZIP and a **separately authenticated** `artifact.digest` from GitHub's artifacts API | SHA-256 over the **original ZIP bytes**; exactly two bounded JSON records; expected source/claim/theorem/gold proof hashes and axiom report | Does not execute Lean; JSON cannot certify its own workflow or human review |
| `verifyPinnedArtinUpstreamBytes` | source Lean file and archived JSONL fetched from the **exact pinned Git commit**, with that commit independently authenticated | original source bytes match pinned SHA-256; first original informal/formal statements are pinned and the formal statement is present in the source | Does not establish semantic equivalence between English and Lean |

The GitHub host in `math-source-github-host-v1.mjs` reports metadata-only replay observations, including an `artifact_digest`. Only a trusted server-side caller should pass that independently obtained digest into the ZIP verifier. Never accept a digest, repository, commit, review verdict, or source file URL from a PR body as authority. The byte verifier deliberately contains no token, HTTP client, installation lifecycle, or permission to write GitHub state.

The artifact parser allows only the two expected filenames (`artin-preflight.json`, `artin-axiom-audit.json`); rejects duplicate, missing, extra, path-traversing and symlink members; enforces compressed and uncompressed bounds; checks local and central ZIP headers, decompressed CRC-32, JSON schema/fields, proof provenance and classical Lean axiom allowlist. It does not extract any archive to a filesystem and rejects unknown ZIP64 layouts.

## Reproducible third-party Artin example

- Upstream: `marcusm117/ProofNet-Verified`, commit `14879cb23e078d122adecd9578dd26a7304f753b`.
- Source: `data/archive/proofnet-verified-4.28/proofnet-1.lean` (`sha256:a9ea15e08b984edb0690348b953a11bf0a1c2cd2541131323c26c243f21ee7fc`).
- First archived dataset row: `data/archive/proofnet-verified-4.28.jsonl`, theorem `Artin_exercise_2_2_9`.
- Informal claim hash: `sha256:a908ad4a14106793dec67703b4051fd3587be202fcd94c5778981cab409051a0`.
- Formal statement hash: `sha256:dc80af468161394ffc1415b4e1ff0585b6859dc80198abb6d2c7d4439888262b`.
- Pinned archived gold proof ZIP: `sha256:e1cf0e5eb34ca13067efb61365a1b8c534e140eb02518e5a7801dac1fce79445`; selected proof source: `sha256:84abeb60969d2c4a8aa3483806e2d71cb2d762e49fd855e7953770b5fbabbc0d`.
- Replay environment requested: Lean `leanprover/lean4:v4.28.0`, Mathlib `v4.28.0` (the resolved Lake dependency closure is **not** yet bound in a receipt).
- Independently successful replay: [Actions run 41346277520](https://github.com/metalogiclabs/mathgraph/actions/runs/41346277520); evidence artifact ID `13098749856`, SHA-256 of the GitHub artifact ZIP: `74a7838a82728a8326c15b1115992ac1519bf117d608ab497c92df3c07e2bd09` (artifacts may expire).

## Run the verification

The unit tests construct actual in-memory ZIP archives, including adversarial header/entry variants; no mock ZIP decoder is used:

```sh
node integrations/mathgraph-check-github/math-source-evidence-bytes-v1.test.mjs
```

For an optional end-to-end check after independently checking out the pinned upstream commit and downloading the artifact via authenticated GitHub Actions API:

```sh
MATHGRAPH_PROOFNET_FIXTURE_DIR=/path/to/verified-ProofNet-Verified \
MATHGRAPH_ARTIN_EVIDENCE_ZIP=/path/to/authenticated-artifact.zip \
node integrations/mathgraph-check-github/math-source-evidence-bytes-v1.test.mjs
```

For a trusted GitHub App backend integrating the pure functions:

```js
import {
  verifyPinnedArtinArtifactBytes,
  verifyPinnedArtinUpstreamBytes,
} from './math-source-evidence-bytes-v1.mjs';

// Observation must come from observeGitHubMathSource with its independently
// administered exact-head pins; don't accept a JSON object from the PR.
if (observation.replay.status !== 'PINNED_REPLAY_OBSERVED') {
  throw Error('GitHub replay metadata not independently established');
}
const artifact = verifyPinnedArtinArtifactBytes({
  zipBytes: downloadedArtifactZip,
  artifactDigest: observation.replay.artifact_digest,
});
const upstream = verifyPinnedArtinUpstreamBytes({
  observedCommit: independentlyAuthenticatedUpstreamCommit,
  sourceBytes: upstreamLeanFile,
  jsonlBytes: upstreamArchivedDataset,
});
// Correlated bytes and metadata are still ADVISORY_ONLY and NOT contract-bound.
```

The backend must authenticate all three fetches and correlate artifact ID/run attempt/head, repository, workflow and reviewer through the existing read-only host before using the returned facts. Artifact data alone never supplies authority. An explicit independent human mathematical review, a pinned Lake dependency closure, and the full `intent-probes` contract remain separate gates before any qualified receipt can exist. No live installation or community outreach occurs in this milestone.
