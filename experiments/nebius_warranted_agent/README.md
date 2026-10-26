# MathGraph Autopilot — The agent that proves it's finished

**Status: CANDIDATE / offline bounded demonstration verified locally. NOT a completed Nebius hackathon submission.**

MathGraph Autopilot has a planner/repair-proposal interface (NVIDIA Nemotron on Nebius Token Factory in live mode) and a separate bounded local evidence-acquisition/qualification component. It proposes a repair, executes declared tests independently, invalidates old test evidence after code changes, and withholds completion until a fresh receipt is bound to the precise tested file bytes.

## 2026-10-26 source-native transfer and model adapter — current verification

**WARRANTED (bounded offline):** [GitHub Actions run #40252245020](https://github.com/metalogiclabs/mathgraph/actions/runs/40252245020), branch commit `2184e0cf0e636b0f87ea13e89eedc6f2989affb7`, **55/55 tests passed**, [seven-file retained artifact #12620369151](https://github.com/metalogiclabs/mathgraph/actions/runs/40252245020/artifacts/12620369151), ZIP SHA-256 `9e92d8822cafd46caad8ce2d8baddd2cd5a9dd61e64be2b0d993dc352488cfe3`. This is distinct from genuine model inference.

The `upstream_encoding_transfer.py` experiment checks out the actual Pallets `itsdangerous` repository at **`672971d66a2ef9f85151e53283113f33d642dabd`**, verifies the Git blob hashes of its native encoding source and test file, then deliberately introduces three **synthetic defects in isolated copies**. Every modified candidate passes the original upstream encoding tests. The independent evaluator compares the real source-native implementation against Python's standard-library URL-safe unpadded Base64 oracle over 1,026 frozen byte inputs. Exact minimum-cost selection finds two test inputs (`00` and `f80000`, hex; synthetic cost 6), which distinguish all three injected mutations. The newly acquired native tests expose the defect, invalidate stale receipts, and admit the scripted correction only after fresh native test execution. **No defect is alleged in upstream Pallets.**

The `upstream_nebius_agent.py` adapter now supports constrained Nemotron-generated repair proposals for this same pinned repository, preserving exact function boundaries and running source-native tests outside the model. Its **scripted** proposals are verified in CI; authenticated real Nebius execution remains **UNKNOWN**. The CI has a manual `workflow_dispatch` input `run_live_nebius` and requires the privately configured GitHub Actions secret `NEBIUS_API_KEY`. It is off by default; every ordinary PR CI run skips the live step. Do not interpret mocked requests or offline scripted proposals as provider evidence.

To reproduce without external model credentials: run the repository's **Nebius Autopilot Bounded Verification** workflow or locally check out the exact Pallets upstream commit and execute:

```sh
python -m unittest -v test_autopilot test_cockpit test_separating_experiments test_separating_cockpit test_upstream_encoding_transfer test_upstream_transfer_cockpit test_upstream_nebius_agent
python upstream_encoding_transfer.py --upstream-checkout ../../upstream_itsdangerous --report upstream-transfer-report.json
python upstream_transfer_cockpit.py upstream-transfer-report.json --output upstream-transfer-cockpit.html
python upstream_nebius_agent.py --upstream-checkout ../../upstream_itsdangerous --provider scripted --report upstream-agent-report.json
```

**Unresolved competition conditions:** authenticated Nemotron inference receipt, genuine model-generated repair, independently frozen holdout/generalization beyond preselected mutations, publicly accessible functional demo, public YouTube video, and Devpost submission. The minimum-cost claim is exact only for the declared finite grammar and synthetic price function. The local Python/test runner is not a hardened sandbox for arbitrary third-party code.

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

## Pinned real-project transfer — independently tested

The same mechanism now runs against actual [Pallets itsdangerous](https://github.com/pallets/itsdangerous/tree/672971d66a2ef9f85151e53283113f33d642dabd) source and its original `tests/test_itsdangerous/test_encoding.py` at immutable upstream commit `672971d66a2ef9f85151e53283113f33d642dabd`. Git blob hashes of `src/itsdangerous/encoding.py` and native tests are checked before executing. Upstream code is not altered; three **explicitly injected synthetic faults** are tested in isolated copies, and all three pass the unmodified original encoding suite. **This is not an upstream bug report.**

An independently declared URL-safe unpadded Base64 oracle is compared with native upstream execution across **1,026 frozen byte inputs**. A finite exact-cover dynamic program selects **two minimum-cost separating tests**, with a source-distinct exhaustive one/two-test comparison agreeing on synthetic cost **6**. The selected inputs, in hex, are `00` and `f80000`. After the first new test is admitted, the old native-suite receipt is invalidated; the defective candidate fails, a scripted repair is tested on the exact source and test bytes, and qualification is restored. This demonstrates transfer of evidence-acquisition **to real source-native tests**, not discovery of an organic upstream defect.

A **source-native Nebius coding-agent adapter** lives in `upstream_nebius_agent.py`, protected by an AST-constrained single-function patch policy. Its scripted two-attempt repair loop passes CI. The `--provider nebius` mode is implemented but **has not run against a real Nebius API key**. No hosted model or public deployment is claimed.

From the experiment directory, after obtaining the independent upstream checkout at the exact commit and installing `pytest==8.4.2`:

```sh
python -m unittest -v test_upstream_encoding_transfer test_upstream_nebius_agent test_upstream_transfer_cockpit
python upstream_encoding_transfer.py --upstream-checkout /path/to/itsdangerous --report upstream-transfer-report.json
python upstream_transfer_cockpit.py upstream-transfer-report.json --output upstream-transfer-cockpit.html
python upstream_nebius_agent.py --upstream-checkout /path/to/itsdangerous --provider scripted --report upstream-agent-report.json
```

The authentic model mode uses `NEBIUS_API_KEY` from a private environment or a properly configured GitHub Actions secret, **never a chat message or committed file**. If using workflow dispatch from GitHub, confirm that the workflow is registered/enabled on the repository's default branch first; a draft-PR-only workflow may not be dispatchable by the GitHub UI.

**Evidence:** [successful independent Actions run #40252245020](https://github.com/metalogiclabs/mathgraph/actions/runs/40252245020), exact qualified commit `2184e0cf0e636b0f87ea13e89eedc6f2989affb7`, **55/55 tests**, and [seven-file retained artifact #12620369151](https://github.com/metalogiclabs/mathgraph/actions/runs/40252245020/artifacts/12620369151) (ZIP SHA-256 `9e92d8822cafd46caad8ce2d8baddd2cd5a9dd61e64be2b0d993dc352488cfe3`). The redundant `upstream_guarded_agent.py` candidate and its test were removed in favor of the existing independently tested `upstream_nebius_agent.py`, preserving one repair implementation.

**UNKNOWN:** Actual NVIDIA inference provenance, true model autonomy, general-repository repair, original real-world bug discovery, comparison against optimized property-based testing, hosted functional app, public YouTube video and Devpost submission.

## Exact-source real-project transfer and guarded Nemotron repair

The [independent Actions run #40251263700](https://github.com/metalogiclabs/mathgraph/actions/runs/40251263700) qualified source-native offline transfer against immutable `pallets/itsdangerous@672971d66a2ef9f85151e53283113f33d642dabd`: 41/41 tests, three deliberately injected faults invisible to the existing encoding tests, a two-test exact minimum basis over 1,026 finite inputs (declared synthetic cost 6), and real pytest plus receipt withdrawal. [Artifact 12620921422](https://github.com/metalogiclabs/mathgraph/actions/runs/40251263700/artifacts/12620921422), archive SHA256 `9997393a9c4bff0a63803e8d20585cce428522886906ed1772b2b23ff3cf1e0a`.

**New CANDIDATE:** `upstream_nebius_agent.py` accepts restricted one-function patches from NVIDIA Nemotron via Nebius Token Factory. The independently selected separating tests gate completion; malformed or unsafe proposals are refused, and source/test changes revoke older receipts. Scripted mode is an offline controlled baseline, not a genuine model call.

From the experiment directory, with a separately checked out and source-pinned upstream repository:

```sh
python -m unittest -v test_upstream_nebius_agent test_upstream_encoding_transfer
python upstream_nebius_agent.py --provider scripted --upstream-checkout ../../upstream_itsdangerous --report upstream-agent-report.json
# Live: configure NEBIUS_API_KEY privately; never publish tokens.
python upstream_nebius_agent.py --provider nebius --model nvidia/nemotron-3-super-120b-a12b --upstream-checkout ../../upstream_itsdangerous --report upstream-live-nebius-report.json
```

GitHub Actions provides an optional manual workflow-dispatch route using a private `NEBIUS_API_KEY` secret; ordinary pull-request checks must never spend inference credits.

**Explicit limits:** constructed mutations and oracle, not a discovered upstream bug; no verified real Nebius response or general-repository autonomy, no public live judge build, and no competition submission yet. Preserve signed-source and retained CI artifacts as authority, not the prose description.
## Actual scope and research lineage

| Component | Epistemic state | Authority |
|---|---|---|
| Earlier finite `evidence_gate.py` sketch | SUPERSEDED | No independent test runner |
| Autopilot deterministic repair/test loop | REUSABLE, bounded | Local unittest + committed code; check CI |
| Tamper, stale-receipt and UNKNOWN scenarios | REUSABLE, bounded | Adversarial regression tests |
| Finite missing-experiment acquisition | REUSABLE, bounded | CI #40151184773; exact 195-case grammar and independent exact minimum |\n| Pinned real-project native-test transfer | REUSABLE, bounded | CI #40252245020; 1,026-input byte grammar, 55/55 tests, three injected faults |\n| Nebius/NVIDIA live API integration | CANDIDATE, untested with credentials | Source adapter only |
| General-repository repair capability | UNKNOWN | Not implemented |
| Real third-party externally hosted demo | UNKNOWN | Not deployed |
| Tavily evidence-retrieval integration | UNKNOWN | Not implemented; never claim bonus eligibility |

The objective is *an agent that determines which evidence its proposed action still requires and reacquires it*. It is intentionally narrower than the full MathGraph research program. Earlier independent warrant-resolution work can be found in `mathgraph_check/warrant_resolution.py` and `mathgraph_check/living_warrants.py` elsewhere in this repository; this experiment reuses its **epistemic separation**, not its proof or formal authority.

## Hackathon submission readiness

The event requires a genuine Nebius inference call or Nebius compute execution plus an NVIDIA open model, significant new work after 26 August 2026 for an existing project, public source and license, a working accessible test build, and a public YouTube demonstration shorter than three minutes. The **current candidate is not ready to submit** because authentic Token Factory inference, a publicly accessible functional test build and video evidence have not yet been completed. See [official rules](https://nebiusglobalaihackathon.devpost.com/rules) and [organizer judging guidance](https://nebiusglobalaihackathon.devpost.com/updates/46204-here-s-how-judging-works).

**Demo video hook:** The agent confidently returns a repair. A green receipt appears. An innocent-looking post-test edit invalidates the receipt. MathGraph refuses completion, reruns precisely the missing check, and only then authorizes *test-qualified* completion.