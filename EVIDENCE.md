# Verification manifest

This manifest links exact external evidence. It is not a signed external attestation or a proof of general correctness.

| Role | Grounded authority |
| --- | --- |
| Authenticated Token Factory call | [GitHub Actions run 40255882641](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641) |
| Run source commit | `56315d382a5b439ffee9dc5a73320e25b2d1757c` (checked out explicitly in one-shot workflow) |
| One-shot workflow trigger | `b59f9f788f6fe14c60601f4ffaf623a4bc1e88c1` |
| Upstream source commit | `pallets/itsdangerous@672971d66a2ef9f85151e53283113f33d642dabd` |
| Model | `nvidia/nemotron-3-super-120b-a12b`, provider `nebius-token-factory` |
| Provider request ID | `474bcea32c45d24df22a5e657206685a` |
| API response SHA-256 | `8b43aaa9f1388ff98babbe1129dab553c08993e8598b44720157bb8df2a4b292` |
| Admitted repaired source SHA-256 | `c4da532733d3aaab18d3b98b53fc35f0e58eb4cf15957fb61f591d1384791f45` |
| Credential-free ZIP artifact | [12621789949](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641/artifacts/12621789949) |
| Artifact ZIP SHA-256 | `2d5fb2f3b77a4a9e5947b8d51812762a8eb9ff6fa592c00f1debf9957e4c8109` |
| Independent offline qualification | [59/59 tests, Actions 40255832893](https://github.com/metalogiclabs/mathgraph/actions/runs/40255832893) |
| Current research | [MathGraph draft PR 203](https://github.com/metalogiclabs/mathgraph/pull/203) |

## Frozen comparative benchmark (26 October 2026)

- **Prospective protocol:** [Frozen benchmark protocol](./BENCHMARK_PROTOCOL_20261026.md) committed at `4c9009cedf362a9e50ba8437614c75b330ecd8fb` before implementing the comparator.
- **Independent GitHub runner:** [Actions #40268881457](https://github.com/metalogiclabs/mathgraph/actions/runs/40268881457), 32/32 tests, pinned source commit `159c418f576c17a34dc8bdaedcc0a5636474589e`.
- **Source-linked evidence ZIP:** [Artifact #12627522966](https://github.com/metalogiclabs/mathgraph/actions/runs/40268881457/artifacts/12627522966), ZIP SHA-256 `384d6a8b2f784b80a4f8bf89d9704ad9239e7596f7b36e5a0a067971e90b39ed`.
- **Actual finite results:** MathGraph 2 tests, 3/3 detected, synthetic cost 6. Informed conventional mutation-aware greedy **ties cost 6** and 3/3. Fixed edge-case pair 2/3; supplemented third test 3/3 at cost 8. Uniform random 2-test selection fully separates 19/1,000 fixed seeds. Deterministic random rates at 4/8/16 tests are 60/151/314 of 1,000.
- **Known limitation:** input `ffffffff` (hex) activates a constructed, out-of-grammar mutation not detectable by the frozen finite experiment, disproving any universal correctness claim.
- See [complete experimental report](./BENCHMARK_RESULTS_20261026.md) for scope, sampling, price units and baselines. Do not describe this as advantage over informed, optimized mutation testing, unseen real-world defects, or arbitrary agent tasks.

## Public demonstration deployment

- Static, interactive, read-only browser replay: [MathGraph Autopilot demo](https://mathgraph-autopilot-nebius-demo.metalogiclabs-check.workers.dev/)
- Cloudflare Worker: `mathgraph-autopilot-nebius-demo` under the existing `metalogiclabs-check.workers.dev` subdomain
- Cloudflare API confirmed route enabled and Worker deployment `f6e046a2-f134-41ad-8cb5-81f3f45ec768` serving version `1be57e3e-2bb3-439a-b251-6ec51123491f` at 100% traffic
- Independent Cloudflare Browser Rendering API returned HTTP 200 and HTML containing the Autopilot title and interactive controls
- This is deliberately not live code execution or a second NVIDIA inference call. The real model execution is the source-pinned GitHub Actions run above.

## Permission-aware experiment compiler — native qualification

- The [public browser observation lab](https://mathgraph-autopilot-nebius-demo.metalogiclabs-check.workers.dev/#observation-lab) offers three observable channels (input byte lengths 1, 2 and 3), computes a finite minimum-cost separating test basis, and returns a named obstruction when the permitted grammar cannot distinguish a declared defect. **Three empty/longer inputs from the full 1,026 benchmark domain are excluded from this permission grammar; some are informative and would alter the obstruction if admitted.**
- Independent native-source [GitHub Actions #40277739469](https://github.com/metalogiclabs/mathgraph/actions/runs/40277739469) **35/35 regression tests GREEN** at commit `8f212d625701e23d4db3419c462ac1d37a5785c7`; [retained independent evidence artifact #12630763228](https://github.com/metalogiclabs/mathgraph/actions/runs/40277739469/artifacts/12630763228), archive SHA256 `a99feae84e77da519b117ad28f1487e07ef98d917b5d211fd176dfe59ef0e24d`.
- **Source-native conditional results:** All lengths 1,2,3: 1,023 eligible inputs, two separating tests `00` and `f80000`, synthetic minimum cost 6. Forbid length 1: 767 eligible inputs, witnesses `0000` and `f80000`, minimum cost 7. Permit only length 3: 256 eligible inputs, **OBSTRUCTION** with `unstripped_padding` observationally inseparable. Both finite minima were independently cross-checked by exhaustive small-basis comparison.
- **Adversarial source continuity:** The earlier [Actions #40277440823](https://github.com/metalogiclabs/mathgraph/actions/runs/40277440823) failed when the native checker erroneously assumed the excluded longer controls were uninformative. That false precondition was corrected, permission scope tightened explicitly, and the 35-test source-native suite requalified. This failure is a useful demonstration of why admissible observation scope must be declared and checked.
- **Authority boundary:** This finite JavaScript computation and source-native Python replay are *not* a live LLM request, a universal test oracle, or permission for uncontrolled deployment. A separate [authenticated Nebius/NVIDIA repair](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641) remains the model-execution evidence.

## Three-way evidence-seeking merge review (source-native; no actual merge)

**Qualified:** [GitHub Actions #40286531693](https://github.com/metalogiclabs/mathgraph/actions/runs/40286531693) GREEN **41/41 tests** on commit `641f2df3893d6fe6047aa2cb19b57436bc2fc6cf`. [Source/HTML requalification #40286783200](https://github.com/metalogiclabs/mathgraph/actions/runs/40286783200) GREEN. Both operate on the pinned Pallets `itsdangerous@672971d66a2ef9f85151e53283113f33d642dabd` reference and intentionally injected isolated faults.

The independent `merge_decision_lab.py` gate produces three source-and-test-bound paths:
- `defective_green_tests`: source-native original tests GREEN but stronger target UNKNOWN; acquire minimal separating tests; newly expanded suite fails → **REJECTED**, release permission NONE. Post-test source edit invalidates previous receipt.
- `correct_but_initially_unknown`: original suite GREEN yet target UNKNOWN; acquire same two tests, rerun on exactly the pinned source → **WARRANTED_BOUNDED**, scoped review only. Post-test source edit withdraws that authorization; rerun after restoring source bytes reacquires the receipt.
- `correct_but_observation_forbidden`: source-native original tests GREEN, but only 3-byte probes may be selected. The `unstripped_padding` rival remains unidentifiable within the declared grammar → **UNKNOWN**, named OBSTRUCTION, release permission NONE.

The original suite being green is *not* represented as general approval in any of these three cases. `WARRANTED_BOUNDED` means only the exact pinned test relation; **no GitHub PR was actually merged**. The source-native replay also does **not** call Nebius: genuine Nemotron inference belongs to [its separate authenticated qualified run #40255882641](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641).

The new browser [Merge Review Lab](https://mathgraph-autopilot-nebius-demo.metalogiclabs-check.workers.dev/#merge-review-lab) is a read-only interactive **replay** of those source-native results, not a general GitHub App. The new CI includes the structured `merge-decision-report.json` as a retained artifact so every displayed outcome can be reconciled with source/test SHA256 receipts.

## Caveats

The live model's proposal was tested only against the declared original native tests and two newly acquired separating tests for a deliberately injected defect. A passing source-native receipt is not a theorem of software correctness. The solver's finite minimum is relative to the predeclared hypothesis grammar and synthetic cost. Source codes are not originally Pallets defects. Do not attribute the browser replay to actual live inference.
