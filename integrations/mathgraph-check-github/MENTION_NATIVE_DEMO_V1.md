# Mathematical mention pilot

`@MathGraph -check` tests whether a submitted proof establishes its original claim. `@MathGraph -fix` prepares a draft repair only after the original consumer and axiom audit pass. One App-authored comment progresses from acknowledgement to the result, with a compact source-bound receipt and review link. Only GitHub user 32909488 in metalogiclabs/mathgraph can invoke this pilot.

## Registered boundaries

| Adapter | Deliberate control | Repair |
|---|---|---|
| List reversal | Conclusion supplied as a hypothesis | A permitted native-checked Lean proof constructor |
| Artin exercise 2.2.9 | Commutative ambient group assumed instead of just commuting generators | Registered subgroup-closure proof under the original Group assumption |
| Four constructed group identities | A group tactic leaves natural powers unnormalized | At most two frozen tactic transformations, with independent original-target verification |

The Artin formal target is byte-bound to marcusm117/ProofNet-Verified commit 14879cb23e078d122adecd9578dd26a7304f753b, data/archive/proofnet-verified-4.28/proofnet-1.lean, source SHA256 a9ea15e08b984edb0690348b953a11bf0a1c2cd2541131323c26c243f21ee7fc. Its declaration is compared with the adapter's target, allowing only whitespace normalization. The stronger CommGroup hypothesis is our controlled edit, not an upstream defect. The benchmark's gold proof is not read. The repair uses Mathlib's closureCommGroupOfComm lemma. Matching the published formal statement is not a machine certification of its English translation or mathematical novelty.

Target statements are fixed in trusted registries. List and Artin accept exact registered source forms; the group adapter accepts only an explicit positive grammar for group/rfl and its qualified normalization tactics, under one of four exact frozen headers. Multiple supported theorem paths in one PR are refused. No PR-supplied imports, scripts, verifier configuration or arbitrary tactics are executed. Repairs are verified against an unchanged original consumer; a compile alone cannot establish acceptance. Failed or incomplete evidence remains UNKNOWN.

## Execution and cost

Lean 4.28.0 release bytes are SHA256-pinned. Artin and the group adapter use Mathlib revision 8f9d9cff6bd728b17a24e163c9402775d9e6a365 and its resolved Lake manifest. Dependencies are prepared by trusted workflow steps and mounted read-only into the secretless Docker sandbox. Native compilation runs as UID 65534 with no network, read-only root, no capabilities, bounded CPU, memory, PIDs and time. The Ubuntu image and apt packages are not reproducibly pinned; the built image ID is recorded.

The list repair permits/reports propext. The Artin repair permits/reports the standard axioms propext, Classical.choice and Quot.sound. Custom axioms, sorryAx and missing audits never qualify. Human review decides any merge.

Paid model proposals are permitted only inside the original conservative 20-owner-run window, at most 25 US cents reserved per call at configured rates. Incomplete or exhausted history closes the paid gate; native checks continue and may reuse registered proof constructors without calling a model. The Artin repair is registered and uses no model call. This is capability reuse, not autonomous invention of a new mathematical proof method. Native CI/build compute is additional.

## Identity and freshness

The existing MathGraph Check App is 5308912, client Iv23lioiUs5KfHD7mkkw, slug mathgraph-check. Repository secret MATHGRAPH_CHECK_APP_PRIVATE_KEY enables short-lived tokens restricted to mathgraph. The App requires Contents, Issues and Pull requests write permissions. No key is read back from Cloudflare or copied through logs. Actions credentials perform authenticated source/history reads; App credentials publish. When the App is unavailable, the workflow explicitly reports and uses the Actions identity. Historical comments are withdrawn using the credential of their actual author.

A changed head prevents repair publication; a change during publication withdraws the opened repair. Later source synchronization withdraws stale comments while retaining their old evidence. GitHub cannot atomically combine head validation and PR creation, so receipts always identify their exact revision. Reruns are refused and incomplete progress is settled without a model key.

## Qualification lineage

The list pilot's App identity and repair publication were qualified by runs 41390204192 and 41390275848 (draft repair PR 238). Run 41390373533 withdrew four prior observations, including three Actions-authored and one App-authored, with zero model calls. Earlier missing-installation runs 41385106398 and 41388840595 remain superseded setup evidence.

Published Artin host controls passed in run 41392433221: stronger candidate compiled, original consumer rejected it; the registered repair and original consumer passed with all three declared standard axioms. Earlier probes 41391360566 (cache setup), 41391723218 (CLI binding) and 41392026637 (unexpected compiler diagnostic) are preserved failed experiments. Live Docker/App qualification is a separate gate.

The current deployment is a three-adapter first-party pilot (list reversal, Artin generators, four frozen group identities), not a generic mathematical repair system, general paper-to-proof certification, or a claim of customer advantage. The OpenAI/Kakeya and arbitrary-source cases remain unsupported. The separate deployed Cloudflare go-ethereum integration is unchanged.

Live Artin Docker/App qualification passed: [check run 41393077436](https://github.com/metalogiclabs/mathgraph/actions/runs/41393077436) classified the compiling stronger-assumption proof as CLAIM_NOT_ESTABLISHED against the published Group target. [Repair run 41393079197](https://github.com/metalogiclabs/mathgraph/actions/runs/41393079197) verified the registered repair against that target in the isolated Docker environment and automatically opened App-authored [draft PR 240](https://github.com/metalogiclabs/mathgraph/pull/240). Both used zero model calls. The original consumer passed with propext, Classical.choice and Quot.sound declared. Initial Artin receipts retained the legacy list-demo schema label; subsequent Artin receipts use the dedicated mathgraph.native-artin-demo.v1 schema and explicit case_id. The published source binding and native traces identify the tested target independently of that label.

## Unregistered-case research follow-up

A separate branch-only study selected the next unused published template, Artin exercise 2.4.19 (a unique order-two element is central), before requesting model output. No reference proof or registered repair was supplied. This does not establish that the public theorem was unseen during model training. The live mention pilot still supports only the two registered adapters above.

[Prospective comparison 41401656441](https://github.com/metalogiclabs/mathgraph/actions/runs/41401656441) used three unique model requests, sharing the initial proposal between the unassisted and compiler-feedback arms. All drafts failed native verification; the recorded result remains NO_NATIVE_FEEDBACK_ADVANTAGE_SHOWN. Configured token rates estimate US$0.044795, not a billing receipt; 75 cents were conservatively reserved. No further model requests were made.

After inspecting that failure, a bounded generic transformation expanded natural powers before group simplification. [Post-hoc native run 41404903109](https://github.com/metalogiclabs/mathgraph/actions/runs/41404903109), source 11b974bd91de1a9b2c6fa66e3e5628f164ea8737, accepted the first transformed proof against the unchanged original consumer, with propext, Classical.choice and Quot.sound and no sorryAx. It used zero model calls and no registered theorem proof constructor. This improvement was designed after observing the failure and cannot replace the original prospective outcome or establish general superiority.

The artifact ZIP SHA256 is 3dd5005b59f7cdb903ad802b4ededc6c52c4020282f205141fd326120d745bab (artifact 13122887623); downloaded bytes were independently digest-checked. The frozen formal target SHA256 is e241d4c1753fd748054b544ce7969004c1f93e62ad58fd501c9b84cde2624f07. Accepted proof and full result are retained in fixtures/fresh-native-verified-v1.lean and fixtures/fresh-native-result-v1.json. The runner now confirms timed-out container removal before permitting another attempt. English-to-formal equivalence and performance on another prospective case remain unestablished.

## Frozen-method prospective transfer, ordinal 3

[Preregistration 4d0405e](https://github.com/metalogiclabs/mathgraph/commit/4d0405ef933626e791df488bd07afb5fe7015d94) selected the next unused published ordinal before reading its template. [Run 41408897632](https://github.com/metalogiclabs/mathgraph/actions/runs/41408897632), source 2e6473412017ecc119d9d1e4e588d8c5e189239d, tested Artin exercise 2.11.3: an even-order finite group contains an order-two element. The exact formal target was unchanged. Engine SHA256 9bf7a144d0a85bbacd154fcd7cc5c49f072feb251dbe58e654f4fb86cd2d4b92 matches the previously qualified method.

Outcome: SHARED_FIRST_PASSED_NO_TRANSFER_EVIDENCE. The initial model proof reused Mathlib's exists_prime_orderOf_dvd_card and passed both compilation and the original-type consumer, with propext, Classical.choice and Quot.sound. Both comparison arms therefore share one accepted proposal; no revision or frozen native repair variant ran. Exactly one API call was made (202 input, 707 output tokens); 25 US cents reserved, not a billing receipt. No reference proof was supplied. This is a new unregistered case accepted on the first proposal, not evidence of repair transfer or model superiority.

The full artifact evidence is retained under evidence/frozen-transfer-v1, including the accepted proof, native trace, raw comparison, budget ledger, frozen receipt and resolved Lake manifest. Artifact 13124975963 ZIP SHA256 1960f565a411d7a9ba36b41c211d394426731beb727356aa2d015a3f358bdb4f was downloaded and digest-checked. The completed raw comparison is saved before any native variant can run, and preregistration/protocol/source/target/engine bindings fail closed. Local suite: 260 passed, 9 skipped.

The live mention App remains the two-adapter pilot. Promotion of the generic repair is still unqualified: this case did not exercise its trigger. The smallest useful next experiment is a predeclared native transfer matrix of power/group identities plus ineligible and false controls, with no further model calls, before another paid theorem comparison. It would qualify tactic behavior within that boundary, not prospective theorem-level advantage.

## Frozen native tactic matrix

Twelve constructed controls were fixed in [preregistration f664a92](https://github.com/metalogiclabs/mathgraph/commit/f664a92c84446a2ac2da46eecef569a282f37c72) before native execution. [Run 41410152881](https://github.com/metalogiclabs/mathgraph/actions/runs/41410152881), source 504490990d84faa2808a337acae5c72d1778d1ab, completed with zero API calls and unchanged engine bytes. This is a finite mechanistic transfer test, not a prospective theorem benchmark or an LLM comparison.

Four originally failing proofs were repaired by the frozen natural-power expansion before group simplification: conjugation at powers 2, 3 and 4, plus nested conjugation at power 3. Every repaired original-type consumer passed with propext only. Three proofs already passed baseline, including both inverse-power identities predicted to require repair. The original predictions therefore matched 10/12 cases; expectations_met remains false. These two mismatches do not count as repair successes.

Both false group claims stayed unaccepted after two variants each. False, the unsupported nonlinear arithmetic draft, and the forbidden sorry draft also stayed unaccepted without any variant. No infrastructure failure was counted as a negative-control success. The runner now aborts on native resource/incomplete diagnostics, and writes separate immutable event records so later failures cannot truncate earlier evidence. Unit regressions for these review findings passed; the full local suite was 269 passed, 9 skipped, zero failures.

Artifact 13125755672 ZIP SHA256 0d167150bc0fc083099ec2785099222a462f40839793e782571c6e53fdbe69f6 was downloaded and digest-checked. Full result, frozen matrix, accepted proofs, resolved manifest, and immutable trace/evidence records (aggregated with original filenames and per-record hashes) are retained in evidence/native-transfer-matrix-v1.

WARRANTED_BOUNDED: this frozen tactic can repair the four tested constructed identities without strengthening the target. REUSABLE within this observed boundary; not a general mathematical repair guarantee. Full prediction accuracy was rejected (10/12), and prospective theorem-level repair advantage remains UNKNOWN after the earlier first-proposal tie. Live App support remains the two registered adapters. Next product gate: trusted input/target selection and source-fresh publication for this generic engine, followed by an end-to-end App qualification; this matrix alone does not authorize generic claims of deployed support.

## Live group mention qualification

WARRANTED_BOUNDED: [demo PR 242](https://github.com/metalogiclabs/mathgraph/pull/242) exercised the third adapter through actual owner comments. [Check 41412203591](https://github.com/metalogiclabs/mathgraph/actions/runs/41412203591) reported CLAIM_NOT_ESTABLISHED for by group on the conjugation-square target. [Fix 41412204856](https://github.com/metalogiclabs/mathgraph/actions/runs/41412204856) accepted the first frozen transformation, reverified the unchanged original consumer, and opened App-authored [draft repair PR 245](https://github.com/metalogiclabs/mathgraph/pull/245). The only source change is natural-power expansion before group simplification. Native proof audit: propext. Both runs used zero model calls. The downloaded verified source matches the repair's GitHub file exactly.

[Negative control PR 243](https://github.com/metalogiclabs/mathgraph/pull/243), run [41412279568](https://github.com/metalogiclabs/mathgraph/actions/runs/41412279568), submitted by rfl under the same frozen target. It retained CLAIM_NOT_ESTABLISHED, recorded zero eligible variants and opened no repair PR (independently queried by base branch). Changing that control's head from c71366fcbdf1d0047a2771b9ace7a499507da632 to c014911368596ded73c536e4e933eb8fc7f17a9a caused [withdrawal run 41413426259](https://github.com/metalogiclabs/mathgraph/actions/runs/41413426259) to withdraw the App's old card while preserving the previous evidence. Zero model calls. Publication-race closure retains its existing unit regression; this live test qualifies completed-card withdrawal.

Source 64cba8b569dede1fba266e0ec066e524a00c139c is pinned by main workflow bb0d0067dffcade8c9583580a7e435f6762b2bcf. [Implementation draft PR 244](https://github.com/metalogiclabs/mathgraph/pull/244) contains the adapter/controller changes. The explicit positive proof grammar rejects appended lemma, inductive and run_cmd commands; original dependencies, consumer failures and resource limits remain UNKNOWN. Each Candidate starts a fresh isolated directory, Consumer uses that attempt's output, and cleanup is confirmed. Repair receipts retain attempts and the winning method.

The three native artifacts were downloaded and digest-checked; full receipts, immutable traces, accepted proof, manifests, App cards before/after withdrawal, repair diff and provenance are retained under evidence/group-mention-live-v1. Full local suite: 279 passed, 9 skipped. The operational pilot now has three adapters, with group support limited to four exact target headers and the allowed proof grammar. Arbitrary mathematical claims and English-to-formal equivalence remain unsupported. Earlier negative comparisons and the 10/12 matrix predictions are not superseded by this product qualification.
