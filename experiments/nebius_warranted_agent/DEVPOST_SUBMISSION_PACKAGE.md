# Nebius × NVIDIA submission package — MathGraph Autopilot

**As of 26 October 2026: AUTHENTICATED MODEL REPAIR VERIFIED, PUBLIC JUDGE DEMO LIVE, AND STANDALONE LICENSED SOURCE STAGED; SUBMISSION NOT YET ENTERED.** Public YouTube upload, independent dedicated repository with a default-branch LICENSE, and Devpost submission remain outstanding. The evidence supports only the declared pinned source-native test boundary.

## Final distribution and hosted demonstration

- Public, anonymously accessible interactive demo: **https://mathgraph-autopilot-nebius-demo.metalogiclabs-check.workers.dev/**. The page clearly states that browser interactions are an offline replay, not live model execution.
- An independent GitHub Actions runner retrieved the public page anonymously with HTTP 200 and checked for the authenticated run reference: [standalone CI #40262381087](https://github.com/metalogiclabs/mathgraph/actions/runs/40262381087), 26/26 package tests + public web smoke. Source commit `f4b5c266ddab29ca18c756ad8d2a8b76e7651186`.
- Scoped MIT-licensed standalone source staging branch: [submission/nebius-autopilot-20261026](https://github.com/metalogiclabs/mathgraph/tree/submission/nebius-autopilot-20261026); [CI source ZIP artifact #12624757490](https://github.com/metalogiclabs/mathgraph/actions/runs/40262381087/artifacts/12624757490), ZIP archive SHA-256 `d665b6b8e9d16870646d965762db8395e05673b09189a78644a806c4cbc2e238`. **This is not a separate repository** and may not satisfy the requirement that the root license is detectable on the repository's default branch. Do not claim that prerequisite is met until the standalone files are published in a new repository whose default branch contains the LICENSE.
- Authenticated NVIDIA Nemotron source-bound repaired task: [Actions #40255882641](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641), [source-linked report artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641/artifacts/12621789949).
- A **1:43 captioned video cut** and voiceover script have been generated locally but **not uploaded to public YouTube**, so the video rule remains open. The browser interactions are marked OFFLINE, and the separate genuine inference evidence is called out in the recording.

## Suggested title

MathGraph Autopilot — The Agent That Knows When It Isn't Finished

## Track

Coding and Agentic Engineering

## Short pitch

AI coding agents can pass every existing test and still ship a defective change. MathGraph Autopilot identifies when the available tests cannot distinguish correct code from a plausible defect, constructs the cheapest missing separating experiments within a finite grammar, and withholds permission to finish until it has acquired and checked the evidence.

## Full description — evidence qualified at present

MathGraph Autopilot connects agent-generated repair proposals to an independent test-and-evidence gate. Rather than treating a successful test command as blanket authorization, it binds results to exact source and test bytes, distinguishes UNKNOWN from REJECTED, and revokes stale receipts whenever the candidate changes.

The current independent demonstration works against a publicly pinned Pallets `itsdangerous` source and its genuine native Python encoding tests. We deliberately inject three synthetic defects into isolated copies. All three pass the original upstream encoding suite. MathGraph then searches 1,026 finite binary observations and selects a provably minimum-cost two-test separating basis (under a declared synthetic cost function). Executing those new native tests exposes the defect; a scripted control and, subsequently, a genuine NVIDIA-model-generated repair each reacquired a passing source-bound receipt against the declared tests.

An AST-constrained agent used the authentic NVIDIA Nemotron 3 Super model through Nebius Token Factory. On [independent source-pinned Actions run #40255882641](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641), it generated one admitted repair proposal, passed original upstream and acquired separating tests, demonstrated post-test receipt withdrawal, then reacquired valid tests. **This is one successful injected-fault repair, not evidence of general-repository coding accuracy.**

The product addresses AI-assisted software repair, CI reliability and release authorization. Its differentiated capability is not another layer of prompting: it turns insufficient evidence into a concrete missing test, acquires that evidence, and retracts outdated authorization when source or tests change.

## Technical details

- Evidence model: Warranted / Rejected / Unknown, always scoped to named tests and exact file bytes
- Agent proposal: source-validated, single-function AST whitelist, no arbitrary generated shell execution
- Test acquisition: finite exact-cover/dynamic-programming selection with independent brute-force cost check
- Protected source: `pallets/itsdangerous@672971d66a2ef9f85151e53283113f33d642dabd`; upstream source and test Git blob checks
- Independent oracle: Python standard-library URL-safe, unpadded Base64 contract
- Injected faults: standard alphabet, retained padding, dropped trailing-zero bytes
- Finite selection: 1,026 inputs, two witnesses `00` and `f80000` (hex), synthetic minimum cost 6
- Independent GitHub Actions evidence: [run 40252245020](https://github.com/metalogiclabs/mathgraph/actions/runs/40252245020), 55/55 tests; [retained artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/40252245020/artifacts/12620369151)
- Browser-only interactive review: `website/public/autopilot/index.html`; this does not independently run the Python source or invoke a model
- Authentic qualification: [Actions 40255882641](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641), one Nemotron response, valid code proposal and source-native test receipt; [credential-free evidence artifact 12621789949](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641/artifacts/12621789949), ZIP SHA256 `2d5fb2f3b77a4a9e5947b8d51812762a8eb9ff6fa592c00f1debf9957e4c8109`. Earlier missing-key [Actions 40253221809](https://github.com/metalogiclabs/mathgraph/actions/runs/40253221809) preserved as superseded historical obstruction.

## What is new within the hackathon period

The source-bound Autopilot experiment, finite separating-test generator, source-native upstream transfer, restricted NVIDIA-model adapter, independent CI and evidence cockpit were developed after the start of the competition. This work is distinct from pre-existing MathGraph research. Retain exact commits and PR history as evidence.

## Remaining steps before submitting

- [x] Private `NEBIUS_API_KEY` configured in GitHub Actions; credential not printed.
- [x] Authentic Nebius/NVIDIA Nemotron call with request identity, response hash and test receipt retained in CI artifact.
- [x] Model-generated proposal passed the exact declared source-native and acquired separating tests; post-test alteration correctly withdrew the receipt.
- [x] Publish an anonymously accessible static interactive demo URL; preserve availability through 15 December 2026
- [ ] Upload the locally generated 1:43 captioned demo video to public YouTube (ideally with human narration), then add the exact URL
- [ ] Publish the already prepared MIT-licensed standalone distribution to a **separate public repository with LICENSE visible on its default branch**. The parent `metalogiclabs/mathgraph` remains project-wide unlicensed; do not alter unrelated research rights.
- [ ] Add feedback on Nebius/NVIDIA technology in the submission
- [ ] Register and submit on Devpost before **30 October 2026 at 10:00 am Pacific Time** (31 October 2026 at 6:00 am NZDT)

## Video structure — 2 minutes 40 seconds maximum

00:00–00:15 — The problem: a green test does not entail a correct repair.

00:15–00:40 — A real, pinned open-source codebase with deliberately injected mutations; existing native tests pass.

00:40–01:10 — MathGraph discovers two minimal-cost missing tests and invalidates the old receipt.

01:10–01:35 — The expanded tests fail, with exact counterexample bytes on screen.

01:35–02:05 — Show the **actual authenticated Nebius run #40255882641**, request/model provenance and source-bound native repair test receipts.

02:05–02:25 — Modify the tested code post-receipt; demonstrate withdrawal, fresh evidence acquisition and bounded requalification.

02:25–02:40 — Source commits, GitHub Actions results, honest scope and final product framing.

The browser replay remains explicitly OFFLINE; only the separately linked source-pinned GitHub Actions run is a real Nebius model execution. Do not splice scripted-browser visuals into the recording as if they were a live model run.

## Current source links

- [Research draft PR #203](https://github.com/metalogiclabs/mathgraph/pull/203)
- [Verified pinned upstream transfer](https://github.com/metalogiclabs/mathgraph/actions/runs/40252245020)
- [Authenticated Nemotron repair](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641)
- [Official competition rules](https://nebiusglobalaihackathon.devpost.com/rules)
