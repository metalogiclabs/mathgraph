# MathGraph Autopilot — The agent that proves it's finished

**Status: CANDIDATE / offline bounded demonstration verified locally. NOT a completed Nebius hackathon submission.**

MathGraph Autopilot has a planner/repair-proposal interface (NVIDIA Nemotron on Nebius Token Factory in live mode) and a separate bounded local evidence-acquisition/qualification component. It proposes a repair, executes declared tests independently, invalidates old test evidence after code changes, and withholds completion until a fresh receipt is bound to the precise tested file bytes.

## Run locally (Python 3.11+; no pip dependencies)

From this directory:

```sh
python -m unittest -v test_autopilot
python autopilot.py --provider scripted --report /tmp/mathgraph-offline.json
python cockpit.py /tmp/mathgraph-offline.json --output /tmp/mathgraph-cockpit.html
```

Open `/tmp/mathgraph-cockpit.html` in a browser. This is **an explicitly scripted coding-model fixture**; tests, retries, receipt binding and qualification are actually executed. The fixture fails once before producing a valid repair. The verifier detects a post-test edit and requires reacquisition.

## Authentic NVIDIA Nemotron inference via Nebius Token Factory

Obtain a Token Factory API key via the Nebius Builder Program. Configure it through a local environment variable or private runtime secret, **not in source, public logs or an issue**:

```sh
export NEBIUS_API_KEY='<redacted token from your secret manager>'
python autopilot.py --provider nebius --model nvidia/nemotron-3-super-120b-a12b --report /tmp/mathgraph-live.json
python cockpit.py /tmp/mathgraph-live.json --output /tmp/mathgraph-live-cockpit.html
```

The live adapter uses `https://api.tokenfactory.nebius.com/v1/chat/completions` with an NVIDIA Nemotron model. Confirm the model ID in the live Token Factory catalog before running. A real provider response is required to claim Nebius compliance: the scripted mode is not a substitute.

Evidence captured in the JSON report includes model ID, response hash, request ID when supplied, candidate source-byte identity, exact test command, test output hash, return code, and post-test byte identity. It does not establish public third-party authenticity of a model response or reproduce full private API messages. No deployment is authorized, and passing this test suite makes only a **bounded test-scoped claim**, not a formal proof of all software correctness.

## End-to-end experiment and trust boundary

1. Verify that the starting buggy `clamp` implementation fails declared tests.
2. Ask the provider for a proposed new implementation, constrained to exactly one `calculator.py` function.
3. Revoke old evidence immediately whenever candidate bytes differ.
4. Execute the approved unit-test command in a temporary workspace (15-second timeout; sanitized process environment).
5. Compare before/after file-byte snapshots, outcome and return code. Only passing test evidence for exactly the current candidate bytes warrants the **declared tests**.
6. Attack the obtained warrant with an extra post-test edit. This correctly rejects the old receipt. Re-run the tests, regenerate the receipt, and check qualification again.

The bounded task validates the generated Python AST to allow only a single-return pure `clamp` function using `min` and `max`. **Do not broaden this to arbitrary repositories or execute unrestricted generated code without a real execution sandbox and stronger supply-chain controls.** The local test receipt is trusted only within the orchestrator that invokes the runner; it is not a cryptographically signed attestation. The included `evidence_gate.py` from the first research commit is a **SUPERSEDED** boolean-gate sketch, not the authority used in Autopilot.

## Evidence-seeking differentiator — independently verified offline

The finite `separating_experiments.py` module tests the precise weakness of the fixed-test baseline. Three explicitly predeclared defective clamp hypotheses (`cap10`, `cap11`, `floor0`) pass the four original tests. The independent order-comparison oracle spans a frozen **195-case** integer domain. The minimum-total-cost subset-DP selector, independently checked against brute-force alternatives, chooses **two** separating tests at declared synthetic cost **34**: `clamp(-1,-2,5) == -1` and `clamp(12,0,12) == 12`. The test file changes, so the earlier test receipt is invalidated; the new tests reject the deceptive implementation; a scripted repair is accepted only after fresh tests, with agreement on all 195 cases.

Reproduce:

```sh
python -m unittest -v test_autopilot test_cockpit test_separating_experiments test_separating_cockpit
python separating_experiments.py --report separating-report.json
python separating_cockpit.py separating-report.json --output separating-cockpit.html
```

**CI evidence:** [GitHub Actions run #40151184773](https://github.com/metalogiclabs/mathgraph/actions/runs/40151184773), 33/33 tests, exact branch head `2b59eb48b5b63ed31ff9c9aa5a202bef610cc6e7`, [retained four-file artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/40151184773/artifacts/12582549744), ZIP SHA-256 `b86d2e58cc7d1a8d41abe2c3e0a38ba7a2cb6f150322af39f7e3631cef2e0fa7`.

**Limits:** Both the version space and the finite test domain are constructed fixtures. The oracle is independently implemented but its contract is human-specified. The minimum is exact only within those constraints and the declared synthetic cost, not an optimization claim about wall-clock time. The repair remains scripted and no real Nebius/NVIDIA inference or unfamiliar GitHub repair is qualified. The original `evidence_gate.py` remains SUPERSEDED by the source-bound runner; no claim of general correctness or formal Lean proof.

## Actual scope and research lineage

| Component | Epistemic state | Authority |
|---|---|---|
| Earlier finite `evidence_gate.py` sketch | SUPERSEDED | No independent test runner |
| Autopilot deterministic repair/test loop | REUSABLE, bounded | Local unittest + committed code; check CI |
| Tamper, stale-receipt and UNKNOWN scenarios | REUSABLE, bounded | Adversarial regression tests |
| Finite missing-experiment acquisition | REUSABLE, bounded | CI #40151184773; exact 195-case grammar and independent exact minimum |\n| Nebius/NVIDIA live API integration | CANDIDATE, untested with credentials | Source adapter only |
| General-repository repair capability | UNKNOWN | Not implemented |
| Real third-party externally hosted demo | UNKNOWN | Not deployed |
| Tavily evidence-retrieval integration | UNKNOWN | Not implemented; never claim bonus eligibility |

The objective is *an agent that determines which evidence its proposed action still requires and reacquires it*. It is intentionally narrower than the full MathGraph research program. Earlier independent warrant-resolution work can be found in `mathgraph_check/warrant_resolution.py` and `mathgraph_check/living_warrants.py` elsewhere in this repository; this experiment reuses its **epistemic separation**, not its proof or formal authority.

## Hackathon submission readiness

The event requires a genuine Nebius inference call or Nebius compute execution plus an NVIDIA open model, significant new work after 26 August 2026 for an existing project, public source and license, a working accessible test build, and a public YouTube demonstration shorter than three minutes. The **current candidate is not ready to submit** because authentic Token Factory inference, a publicly accessible functional test build and video evidence have not yet been completed. See [official rules](https://nebiusglobalaihackathon.devpost.com/rules) and [organizer judging guidance](https://nebiusglobalaihackathon.devpost.com/updates/46204-here-s-how-judging-works).

**Demo video hook:** The agent confidently returns a repair. A green receipt appears. An innocent-looking post-test edit invalidates the receipt. MathGraph refuses completion, reruns precisely the missing check, and only then authorizes *test-qualified* completion.