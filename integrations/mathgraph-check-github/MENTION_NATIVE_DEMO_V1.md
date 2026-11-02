# Mathematical mention pilot

`@MathGraph -check` tests whether a submitted proof establishes its original claim. `@MathGraph -fix` prepares a draft repair only after the original consumer and axiom audit pass. One App-authored comment progresses from acknowledgement to the result, with a compact source-bound receipt and review link. Only GitHub user 32909488 in metalogiclabs/mathgraph can invoke this pilot.

## Registered boundaries

| Adapter | Deliberate control | Repair |
|---|---|---|
| List reversal | Conclusion supplied as a hypothesis | A permitted native-checked Lean proof constructor |
| Artin exercise 2.2.9 | Commutative ambient group assumed instead of just commuting generators | Registered subgroup-closure proof under the original Group assumption |

The Artin formal target is byte-bound to marcusm117/ProofNet-Verified commit 14879cb23e078d122adecd9578dd26a7304f753b, data/archive/proofnet-verified-4.28/proofnet-1.lean, source SHA256 a9ea15e08b984edb0690348b953a11bf0a1c2cd2541131323c26c243f21ee7fc. Its declaration is compared with the adapter's target, allowing only whitespace normalization. The stronger CommGroup hypothesis is our controlled edit, not an upstream defect. The benchmark's gold proof is not read. The repair uses Mathlib's closureCommGroupOfComm lemma. Matching the published formal statement is not a machine certification of its English translation or mathematical novelty.

Both adapters accept only exact registered source forms. Multiple supported theorem paths in one PR are refused. No PR-supplied imports, scripts, verifier configuration or arbitrary tactics are executed. Repairs are verified against an unchanged original consumer; a compile alone cannot establish acceptance. Failed or incomplete evidence remains UNKNOWN.

## Execution and cost

Lean 4.28.0 release bytes are SHA256-pinned. Artin uses Mathlib revision 8f9d9cff6bd728b17a24e163c9402775d9e6a365 and its resolved Lake manifest. Dependencies are prepared by trusted workflow steps and mounted read-only into the secretless Docker sandbox. Native compilation runs as UID 65534 with no network, read-only root, no capabilities, bounded CPU, memory, PIDs and time. The Ubuntu image and apt packages are not reproducibly pinned; the built image ID is recorded.

The list repair permits/reports propext. The Artin repair permits/reports the standard axioms propext, Classical.choice and Quot.sound. Custom axioms, sorryAx and missing audits never qualify. Human review decides any merge.

Paid model proposals are permitted only inside the original conservative 20-owner-run window, at most 25 US cents reserved per call at configured rates. Incomplete or exhausted history closes the paid gate; native checks continue and may reuse registered proof constructors without calling a model. The Artin repair is registered and uses no model call. This is capability reuse, not autonomous invention of a new mathematical proof method. Native CI/build compute is additional.

## Identity and freshness

The existing MathGraph Check App is 5308912, client Iv23lioiUs5KfHD7mkkw, slug mathgraph-check. Repository secret MATHGRAPH_CHECK_APP_PRIVATE_KEY enables short-lived tokens restricted to mathgraph. The App requires Contents, Issues and Pull requests write permissions. No key is read back from Cloudflare or copied through logs. Actions credentials perform authenticated source/history reads; App credentials publish. When the App is unavailable, the workflow explicitly reports and uses the Actions identity. Historical comments are withdrawn using the credential of their actual author.

A changed head prevents repair publication; a change during publication withdraws the opened repair. Later source synchronization withdraws stale comments while retaining their old evidence. GitHub cannot atomically combine head validation and PR creation, so receipts always identify their exact revision. Reruns are refused and incomplete progress is settled without a model key.

## Qualification lineage

The list pilot's App identity and repair publication were qualified by runs 41390204192 and 41390275848 (draft repair PR 238). Run 41390373533 withdrew four prior observations, including three Actions-authored and one App-authored, with zero model calls. Earlier missing-installation runs 41385106398 and 41388840595 remain superseded setup evidence.

Published Artin host controls passed in run 41392433221: stronger candidate compiled, original consumer rejected it; the registered repair and original consumer passed with all three declared standard axioms. Earlier probes 41391360566 (cache setup), 41391723218 (CLI binding) and 41392026637 (unexpected compiler diagnostic) are preserved failed experiments. Live Docker/App qualification is a separate gate.

This is a two-adapter first-party pilot, not a generic mathematical repair system, general paper-to-proof certification, or a claim of customer advantage. The OpenAI/Kakeya and arbitrary-source cases remain unsupported. The separate deployed Cloudflare go-ethereum integration is unchanged.

Live Artin Docker/App qualification passed: [check run 41393077436](https://github.com/metalogiclabs/mathgraph/actions/runs/41393077436) classified the compiling stronger-assumption proof as CLAIM_NOT_ESTABLISHED against the published Group target. [Repair run 41393079197](https://github.com/metalogiclabs/mathgraph/actions/runs/41393079197) verified the registered repair against that target in the isolated Docker environment and automatically opened App-authored [draft PR 240](https://github.com/metalogiclabs/mathgraph/pull/240). Both used zero model calls. The original consumer passed with propext, Classical.choice and Quot.sound declared. Initial Artin receipts retained the legacy list-demo schema label; subsequent Artin receipts use the dedicated mathgraph.native-artin-demo.v1 schema and explicit case_id. The published source binding and native traces identify the tested target independently of that label.
