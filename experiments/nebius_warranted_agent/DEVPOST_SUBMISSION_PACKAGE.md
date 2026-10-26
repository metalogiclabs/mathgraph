# Nebius × NVIDIA submission package — MathGraph Autopilot

**As of 26 October 2026: NOT READY TO SUBMIT.** This is a copy-ready submission package **only after** authentic Nebius/NVIDIA inference and public deployment are independently checked. Never claim those checks passed merely because CI is green.

## Suggested title

MathGraph Autopilot — The Agent That Knows When It Isn't Finished

## Track

Coding and Agentic Engineering

## Short pitch

AI coding agents can pass every existing test and still ship a defective change. MathGraph Autopilot identifies when the available tests cannot distinguish correct code from a plausible defect, constructs the cheapest missing separating experiments within a finite grammar, and withholds permission to finish until it has acquired and checked the evidence.

## Full description — evidence qualified at present

MathGraph Autopilot connects agent-generated repair proposals to an independent test-and-evidence gate. Rather than treating a successful test command as blanket authorization, it binds results to exact source and test bytes, distinguishes UNKNOWN from REJECTED, and revokes stale receipts whenever the candidate changes.

The current independent demonstration works against a publicly pinned Pallets `itsdangerous` source and its genuine native Python encoding tests. We deliberately inject three synthetic defects into isolated copies. All three pass the original upstream encoding suite. MathGraph then searches 1,026 finite binary observations and selects a provably minimum-cost two-test separating basis (under a declared synthetic cost function). Executing those new native tests exposes the defect; running the tests again after a scripted repair produces a fresh source-bound qualification.

An AST-constrained model adapter can request a bounded repair from NVIDIA Nemotron on Nebius Token Factory, and reverify the result against the same independently generated test suite. **However, as of this draft no authenticated Nebius API request has been demonstrated. Do not imply that the adapter alone satisfies the platform requirement.**

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
- One-shot attempt: [Actions 40253221809](https://github.com/metalogiclabs/mathgraph/actions/runs/40253221809) recorded **NEBIUS_API_KEY_NOT_CONFIGURED** and did not attempt inference

## What is new within the hackathon period

The source-bound Autopilot experiment, finite separating-test generator, source-native upstream transfer, restricted NVIDIA-model adapter, independent CI and evidence cockpit were developed after the start of the competition. This work is distinct from pre-existing MathGraph research. Retain exact commits and PR history as evidence.

## Required live qualification before using this submission text

- [ ] Configure a private `NEBIUS_API_KEY` in the intended execution environment; never post the key to chat or commit it
- [ ] Execute an authentic NVIDIA Nemotron inference request through Nebius Token Factory and retain safe request/model identifiers, response hash and test receipt
- [ ] Confirm a model-generated proposal (not scripted) passed the source-native expanded tests; otherwise report its honest failure or UNKNOWN
- [ ] Publish a functional public demo URL that remains usable for judges through 15 December 2026
- [ ] Publish a public YouTube recording of the actual working app, under three minutes
- [ ] Provide a competition-specific open-source licensed repository, visibly licensed at its root. The parent `metalogiclabs/mathgraph` currently lacks a confirmed project-wide license; **do not add a blanket license covering unrelated research without an intentional rights decision**
- [ ] Add feedback on Nebius/NVIDIA technology in the submission
- [ ] Register and submit on Devpost before **30 October 2026 at 10:00 am Pacific Time** (31 October 2026 at 6:00 am NZDT)

## Video structure — 2 minutes 40 seconds maximum

00:00–00:15 — The problem: a green test does not entail a correct repair.

00:15–00:40 — A real, pinned open-source codebase with deliberately injected mutations; existing native tests pass.

00:40–01:10 — MathGraph discovers two minimal-cost missing tests and invalidates the old receipt.

01:10–01:35 — The expanded tests fail, with exact counterexample bytes on screen.

01:35–02:05 — **Only after authentic Nebius inference succeeds:** show the real Nemotron-generated proposal, request/model provenance and actual native repair test receipts.

02:05–02:25 — Modify the tested code post-receipt; demonstrate withdrawal, fresh evidence acquisition and bounded requalification.

02:25–02:40 — Source commits, GitHub Actions results, honest scope and final product framing.

If no authentic Nebius call is available, label this an offline research demonstration rather than recording simulated inference as live.

## Current source links

- [Research draft PR #203](https://github.com/metalogiclabs/mathgraph/pull/203)
- [Verified pinned upstream transfer](https://github.com/metalogiclabs/mathgraph/actions/runs/40252245020)
- [One-shot credential obstruction](https://github.com/metalogiclabs/mathgraph/actions/runs/40253221809)
- [Official competition rules](https://nebiusglobalaihackathon.devpost.com/rules)
