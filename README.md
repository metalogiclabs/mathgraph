# MathGraph Autopilot
### The AI engineer that knows when it isn't finished

**Hackathon track:** Nebius × NVIDIA Global AI Hackathon — Coding and Agentic Engineering.

An agent's tests can all pass while critical behavior remains unchecked. MathGraph Autopilot constructs an exact minimum-cost separating test set within a declared finite grammar, checks it on pinned source, and only authorizes completion after independent test evidence is bound to the current source and test bytes.

**Verified real-model demonstration:** [GitHub Actions #40255882641](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641) ran one genuine **NVIDIA Nemotron 3 Super 120B** inference through **Nebius Token Factory** and qualified its one-function repair against independently executed native tests and the acquired separating tests. This is one *bounded* successful repair of a deliberately injected fault, not proof of arbitrary code correctness. [Credential-free source-linked evidence artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641/artifacts/12621789949).

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
