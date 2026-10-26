# Devpost final copy — MathGraph Autopilot

**Submission status: DRAFT — do not claim submitted until Devpost confirms it.** The independent source repository URL and public YouTube URL must still be inserted and verified.

## Project name

MathGraph Autopilot — The Agent That Knows When It Isn't Finished

## Elevator pitch

A green test suite can still hide a broken AI-generated repair. MathGraph Autopilot asks what evidence is missing, acquires the cheapest separating tests it can justify within a finite hypothesis grammar, and refuses to call a coding task complete until independent results are bound to the exact source revision.

## Track

Coding and Agentic Engineering

## How it works

A coding model proposes a source change, but cannot authorize its own success. MathGraph inspects what the existing tests can and cannot distinguish, generates a minimum-cost separating test basis relative to a declared finite model, and executes the additional tests independently. It returns UNKNOWN when target evidence is missing, REJECTED when new tests expose a defect, and test-scoped WARRANTED only when the source and test files match a fresh passing receipt. Changes after testing automatically withdraw prior authorization.

We demonstrate on an exact pinned checkout of the open-source Python project Pallets `itsdangerous`. We deliberately inject three isolated encoding defects; **these are experimental faults, not defects in upstream Pallets**. All three pass its original native encoding tests. MathGraph independently evaluates 1,026 frozen byte inputs, finds two separating observations, and exposes the defects. Its exact minimum cost is independently cross-checked.

**Authentic Nebius/NVIDIA:** Through Nebius Token Factory, **NVIDIA Nemotron 3 Super 120B** generated a correct one-function repair for one injected fault. Its source proposal was constrained by an AST admission policy and independently passed the original native tests and newly acquired tests. Evidence withdrawal and fresh requalification were both reproduced in [GitHub Actions run #40255882641](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641); its credential-free artifact preserves provider request/response hashes and test receipts. This is one bounded source-native repair, not evidence of arbitrary-repository correctness.

## What makes the approach different?

Unlike a completion wrapper that trusts its current green CI result, Autopilot separates the model's proposed code, what the tests actually establish, and permission to call the job done. When evidence is insufficient, it turns that insufficiency into a concrete test-acquisition action and preserves the exact-source evidence lineage.

We evaluated the test-selection component against honest controls. In a preregistered **three-mutant finite benchmark**, MathGraph caught all three defects in two tests at synthetic cost 6. Uniform random two-case selection succeeded in only **19 of 1,000** frozen seeds. Importantly, a conventional mutation-aware weighted greedy algorithm with equal access to the mutant behavior **also caught all three at cost 6**. We do not claim a new mathematical optimum unavailable to established mutation testing. Our differentiator is source-bound warrant acquisition, selective refusal and automatic authority withdrawal, not outperforming an informed mutation test selector.

This is useful for teams adopting AI-generated code in CI, release engineering, critical configuration, compliance automation and software supply-chain workflows where false confidence can be more costly than a justified UNKNOWN.

## Technologies used

- Nebius Token Factory inference API
- NVIDIA Nemotron 3 Super 120B (`nvidia/nemotron-3-super-120b-a12b`)
- Python 3.11, standard-library AST, deterministic finite selection and native pytest
- GitHub Actions for pinned-source independent tests, artifacts and model invocation
- Cloudflare Workers for an anonymously accessible offline interactive evidence cockpit

## Working app and code

**Public interactive app (OFFLINE replay):** https://mathgraph-autopilot-nebius-demo.metalogiclabs-check.workers.dev/

**Authenticated Nebius demonstration and evidence:** https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641

**Independent benchmark results and limitations:** https://github.com/metalogiclabs/mathgraph/blob/submission/nebius-autopilot-20261026/BENCHMARK_RESULTS_20261026.md

**Public independently licensed project repository:** [INSERT NEW PUBLIC REPOSITORY URL ONCE CREATED — do not use the unlicensed parent repository]

**Public YouTube demonstration:** [INSERT ACTUAL PUBLISHED YOUTUBE URL]

## Significant new work since August 26

MathGraph research predates this competition. The **Autopilot** product-specific code-repair loop, independent test acquisition, exact-source warrant mechanism, Nebius/Nemotron adapter, authentic inference integration, finite baseline comparison, and accessible evidence cockpit were developed for this hackathon after the submission period began. See draft research PR #203 and source-linked GitHub Actions histories.

## Nebius/NVIDIA experience and feedback

Nebius Token Factory exposed an OpenAI-compatible endpoint that made it easy to integrate Nemotron with a standard-library Python client and a private GitHub Actions secret. The model ultimately produced a qualifying repair proposal, with request identity and response digest preserved separately from source-native tests.

Our first real attempts exposed concrete integration issues: an initially empty final response when reasoning used the output budget, malformed JSON output, and syntactically structured but semantically inadmissible generated code. The successful implementation uses a non-thinking output mode for short bounded repairs, grammar-guided JSON, strict function/source admission and previous verifier feedback. Clearer model-specific examples for `enable_thinking`, `guided_json`, truncation diagnostics and typed repair actions would shorten onboarding. We would use Nebius again for constrained, independently verified model proposals. See [the full engineering feedback record](./NEBIUS_NVIDIA_FEEDBACK.md).

## Scope and caveats

Only one live model-generated injected-fault repair was qualified. The observed minimum belongs to a constructed finite grammar and synthetic test price, not latency or financial cost. A deliberately withheld four-byte failure outside that grammar remains undetected. The hosted UI replays real evidence but does not call Nebius or execute untrusted source live. We make no claim of a novel underlying set-cover algorithm, a discovered upstream Pallets bug, general software verification, or demonstrated advantage on unseen repositories.

## Publication checklist

- [ ] Create a new **public** repository with `LICENSE` on its **default branch**, and upload the exact scoped MIT-licensed source distribution
- [ ] Publish the less-than-three-minute demo to public YouTube; verify anonymous playback
- [ ] Replace both placeholders above with actual public URLs, and check them while signed out
- [ ] Put Nebius Token Factory and NVIDIA Nemotron 3 Super in the Built With fields
- [ ] Enter the detailed technology feedback above
- [ ] Submit on Devpost before **Friday 30 Oct 2026 10am PDT / Saturday 31 Oct 2026 6am NZDT** and verify submission confirmation

**Judging boundaries:** The browser's interactive steps are explicitly an offline replay. The separate GitHub Actions run is the genuine Nebius source-native model result.
