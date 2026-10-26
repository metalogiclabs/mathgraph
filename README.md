# MathGraph Autopilot
### The AI engineer that knows when it isn't finished

**Hackathon track:** Nebius × NVIDIA Global AI Hackathon — Coding and Agentic Engineering.

An agent's tests can all pass while critical behavior remains unchecked. MathGraph Autopilot constructs an exact minimum-cost separating test set within a declared finite grammar, checks it on pinned source, and only authorizes completion after independent test evidence is bound to the current source and test bytes.

**Verified real-model demonstration:** [GitHub Actions #40255882641](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641) ran one genuine **NVIDIA Nemotron 3 Super 120B** inference through **Nebius Token Factory** and qualified its one-function repair against independently executed native tests and the acquired separating tests. This is one *bounded* successful repair of a deliberately injected fault, not proof of arbitrary code correctness. [Credential-free source-linked evidence artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641/artifacts/12621789949).

## New: authenticated Nemotron-selected merge evidence — three outcomes

**Live NVIDIA/Nebius qualification:** [Source-pinned one-shot GitHub Actions #40289255597](https://github.com/metalogiclabs/mathgraph/actions/runs/40289255597), executing exact tested standalone source `7bd3679543b5fd4d67bc4555cd45dcc13876e8e7`, offline-independent [54/54 qualification #40289131662](https://github.com/metalogiclabs/mathgraph/actions/runs/40289131662), with a separately pinned Pallets `itsdangerous@672971d66a2ef9f85151e53283113f33d642dabd` checkout. Authenticated **NVIDIA Nemotron 3 Super via Nebius Token Factory** selected one of several **source-derived, typed finite observation plans** for each review case. Its chosen plan could not change the native oracle, mutate arbitrary repositories, approve a merge or authorize release. MathGraph independently checked permitted observations, exact finite cost and source-native pytest receipts.

| Actual model-selected case | Selected evidence | Source-native final decision | Merge permission |
| --- | --- | --- | --- |
| Green original suite hides deliberately injected encoding fault | `00`, `f80000` (hex), cost 6 | **REJECTED**, expanded tests exit 1 | NONE |
| Correct reference change but original tests don't distinguish alternatives | `00`, `f80000` (hex), cost 6 | **WARRANTED_BOUNDED**, expanded tests exit 0; post-test edit withdraws, fresh test reacquires | REVIEW_ONLY_BOUNDED |
| Correct candidate with only three-byte inputs permitted | Model-selected typed **OBSTRUCTION**, missing `unstripped_padding` distinction | **UNKNOWN** | NONE |

Each decision was accepted on the **first authenticated model attempt**. [Retained credential-free evidence artifact #12635700459](https://github.com/metalogiclabs/mathgraph/actions/runs/40289255597/artifacts/12635700459), ZIP SHA256 `d437c7aaedb567849bd4a43c2edb052b54f8de1af9117a756a1209b8a8484f56`. [Full replay/evidence context](./LIVE_MODEL_MERGE_EVIDENCE_20261026.md).

**Boundary:** The finite plan menu and defective-candidate family are predeclared, and the model chooses a typed option; it did not synthesize arbitrary tests or analyze an unfamiliar pull request. The original independent [live model-generated *code repair*](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641) is a separate experiment. No GitHub merge occurs. Results are bounded to the declared source, test scope and permitted observation grammar.

## See the demonstration

**Public hosted judge demo:** https://mathgraph-autopilot-nebius-demo.metalogiclabs-check.workers.dev/ (read-only interactive replay, no login or Nebius billing required). Its public route is served by a dedicated Cloudflare Worker; no authentication secrets are deployed with the HTML.

Open **`index.html`** locally or host this directory on any static web host. The page is interactive but intentionally a **read-only OFFLINE replay**; it does not execute arbitrary Python or consume Nebius credits. The authenticated run is evidenced separately by the GitHub Actions link above.

## New: Permission-aware active observation lab

The public demo now contains a **live finite experiment compiler**, not merely a preset replay. Select which input lengths are legally or operationally permissible to observe. The browser independently computes the exact minimum synthetic-cost set of observations that distinguishes the three predeclared encoding fault hypotheses, or returns a **named obstruction** when no permitted observations can separate them. Clicking **Execute missing observations** evaluates the chosen cases locally and exposes defective behavior; changing observation permissions invalidates the displayed result.

[Open the public active observation lab](https://mathgraph-autopilot-nebius-demo.metalogiclabs-check.workers.dev/#observation-lab).

**Permission scope:** Only input lengths 1, 2 and 3 may be selected in this lab. Three empty/longer control inputs from the 1,026-input benchmark are deliberately excluded; some longer controls could also reveal defects if permitted. Every OBSTRUCTION verdict is conditional on this explicitly restricted observation grammar.

- All 1-, 2- and 3-byte observations permitted: `00` and `f80000` (hex), total synthetic cost 6.
- One-byte observations forbidden: `0000` and `f80000`, total cost 7.
- Only three-byte observations permitted: **OBSTRUCTION**, because the unstripped-padding mutant is observationally indistinguishable on this permitted subset.
- The original source-native external tests, Nebius provider response and GitHub Actions evidence are separate from this browser simulation. No arbitrary code or model is executed in the page.

This demonstrates **permission-aware active identification**, not a new universal scientific algorithm. As the fair comparison below establishes, an equally informed conventional mutation-testing selector can match the finite minimum, and any out-of-domain fault remains UNKNOWN.

## New: the evidence-seeking merge-review agent (three outcomes)

**[Try the interactive three-way merge lab](https://mathgraph-autopilot-nebius-demo.metalogiclabs-check.workers.dev/#merge-review-lab).** The interface replays a **genuine pinned-source native-test experiment** (not live Python execution in your browser and not a new Nebius inference). Unlike an ordinary all-green test badge, the report distinguishes the protected target relation from what those existing tests actually warrant:

| Source-native scenario | Original upstream suite | Evidence acquired | Bounded review outcome |
| --- | --- | --- | --- |
| Deliberately defective encoding change | Green | Minimum two separating tests reveal the defect | **REJECTED** (no merge) |
| Correct pinned reference implementation | Green | Same two tests pass; exact source/test receipt acquired | **WARRANTED_BOUNDED** (scoped review only) |
| Correct code, only three-byte probes permitted | Green | Padding behavior cannot be distinguished by any permitted probe | **UNKNOWN** with named obstruction (no merge) |

The native replay also edits the source **after testing**. Old evidence is invalidated; fresh source-native test execution is necessary before a previous review verdict can be reacquired. **Nothing is actually merged or submitted upstream.** All non-reference faults are deliberately injected, and the complete candidate/observation grammar is declared in advance. General new-code repair and blind tasks remain UNKNOWN.

**Independent evidence:** [41/41 tests and source-native replay, Actions #40286531693](https://github.com/metalogiclabs/mathgraph/actions/runs/40286531693). [Latest green UI/source qualification](https://github.com/metalogiclabs/mathgraph/actions/runs/40286783200). The source-linked `merge-decision-report.json` is retained among the standalone audit artifacts.

Reproduce on the separately checked out immutable Pallets source, after installing the pinned test dependency:

```sh
MATHGRAPH_PINNED_UPSTREAM=upstream_itsdangerous python -m unittest -v test_merge_decision_lab
python merge_decision_lab.py --upstream-checkout upstream_itsdangerous --report merge-decision-report.json
```

The previously authenticated [Nebius/NVIDIA Nemotron repair #40255882641](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641) is a **separate real model inference**. The three-way merge-review workflow is a source-native offline demonstration of what decisions independent evidence can justify, not another authenticated model run.

## Experimental typed evidence planner — do not claim success yet

The optional `model_observation_merge.py` adapter asks NVIDIA Nemotron to select an admissible **typed observation proposal** from predeclared source-native candidate probes. The deterministic exact solver independently checks coverage, cost, permitted channels and named obstructions; it alone controls native test execution and scoped merge-review permission. No generated shell or direct GitHub merge action is accepted.

**Offline adapter qualification:** [49/49 tests, Actions #40287890753](https://github.com/metalogiclabs/mathgraph/actions/runs/40287890753). **Authenticated model-planning attempts:** [#40288064254](https://github.com/metalogiclabs/mathgraph/actions/runs/40288064254) and [#40288288516](https://github.com/metalogiclabs/mathgraph/actions/runs/40288288516) all returned invalid or unsupported typed proposals for the three finite cases; the checker refused them, so **the new model-chosen observation-planning task is NOT verified**. This is a useful safe-failure demonstration, not autonomous evidence-planning success.

The existing [genuine one-function Nemotron repair](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641) is a separate successful injected-fault repair; the [three-way merge-review experiment](https://github.com/metalogiclabs/mathgraph/actions/runs/40286531693) is independently verified **offline**. Those distinct authorities must not be merged into a single invented success claim.

## Reproduce

Requirements: **Python 3.11+**, `git`, `pytest==8.4.2`. The external Pallets upstream repository is NOT included; source and tests are fetched from its public licensed repository at one exact commit and verified by original Git blobs.

```bash
python -m pip install -r requirements-dev.txt
git clone https://github.com/pallets/itsdangerous.git upstream_itsdangerous
git -C upstream_itsdangerous checkout 672971d66a2ef9f85151e53283113f33d642dabd
export MATHGRAPH_PINNED_UPSTREAM=upstream_itsdangerous
python -m unittest -v test_upstream_encoding_transfer test_upstream_transfer_cockpit test_upstream_nebius_agent
python upstream_encoding_transfer.py --upstream-checkout upstream_itsdangerous --report upstream-transfer-report.json
python upstream_transfer_cockpit.py upstream-transfer-report.json --output upstream-transfer-cockpit.html
python upstream_nebius_agent.py --provider scripted --upstream-checkout upstream_itsdangerous --report upstream-scripted-report.json
```

The scripted provider **does not call Nebius**. For authentic inference, configure the API key privately, then run:

```bash
export NEBIUS_API_KEY="<set privately; never commit or paste into tickets>"
python upstream_nebius_agent.py --provider nebius --model nvidia/nemotron-3-super-120b-a12b --upstream-checkout upstream_itsdangerous --max-attempts 2 --report upstream-nebius-report.json
```

**Security:** This agent executes only an AST-restricted single Python function in a controlled temporary workspace. Do not generalize it into a runner for arbitrary untrusted repositories. An AI model response is a proposal, never evidence; source-pinned test receipts and changed-byte withdrawal are authoritative only within the declared test suite.

## The real-project counterexample

The native `pallets/itsdangerous` encoding tests at `672971d66a2ef9f85151e53283113f33d642dabd` are checked against three **deliberately injected** defects in isolated workspaces, not defects in upstream Pallets. All three mutants pass the original native tests. A frozen **1,026-input** finite grammar admits an exact minimum synthetic-cost two-test basis (**`00`** and **`f80000`**, hexadecimal, cost **6**) that distinguishes them. Independent brute-force minimization agrees. Source/test changes automatically revoke older passing receipts.

## Measured difference: evidence-seeking versus other testing

In a source-pinned, frozen **constructed** encoding-fault family, MathGraph selected two minimum-cost tests that distinguish all three mutants. With the same two-test budget, deterministic uniform-random input selection achieved complete separation in **19 of 1,000 seeds (1.9%)**. Both a strong mutation-aware conventional greedy selector and MathGraph attained the **same synthetic cost of 6** when equally informed. A hand-selected three-boundary-test suite also worked at cost 8.

**What the result actually supports:** finite minimum separating evidence + source-bound authorization, **not** a superior test-selection algorithm over optimized mutation testing, not a runtime speed claim, and not general repair success. The held-out four-byte fault outside the declared input domain remains an explicit obstruction.

[Full frozen comparative report](./BENCHMARK_RESULTS_20261026.md) · [Pre-registered protocol](./BENCHMARK_PROTOCOL_20261026.md) · [Independent CI #40268881457](https://github.com/metalogiclabs/mathgraph/actions/runs/40268881457)

## Evidence and limits

- [Authenticated Nemotron run](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641) · [retained artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641/artifacts/12621789949)
- [Preceding independent code qualification](https://github.com/metalogiclabs/mathgraph/actions/runs/40255832893): **59/59** bounded tests.
- [Original research and causal lineage — draft PR #203](https://github.com/metalogiclabs/mathgraph/pull/203)
- [Research checkpoint](https://app.notion.com/p/3e43e523d7ab81a5bbc9e405e81aba6c)

**WARRANTED:** one authenticated repair within exact source/native test boundary, finite minimum separating evidence. **UNKNOWN:** blind real-world generalization, new organic upstream defect discovery, deployment authorization outside declared tests, and performance versus optimized property-based testing. The browser replay is not a hosted real-model execution.

## License and provenance

The **files in this standalone submission distribution** are licensed under the accompanying MIT `LICENSE`. No other MathGraph repository source files or branches are included in this license grant. This is NOT a license of the whole [metalogiclabs/mathgraph](https://github.com/metalogiclabs/mathgraph) research repository or its other branches. Pallets `itsdangerous` is independently owned and licensed under BSD-3-Clause; no upstream code is bundled in this distribution. See [Pallets license](https://github.com/pallets/itsdangerous/blob/672971d66a2ef9f85151e53283113f33d642dabd/LICENSE.txt).

Developed during the hackathon entry period as a product-specific implementation based on pre-existing MathGraph research. [Competition rules](https://nebiusglobalaihackathon.devpost.com/rules).
