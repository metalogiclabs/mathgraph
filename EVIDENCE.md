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

## Public demonstration deployment

- Static, interactive, read-only browser replay: [MathGraph Autopilot demo](https://mathgraph-autopilot-nebius-demo.metalogiclabs-check.workers.dev/)
- Cloudflare Worker: `mathgraph-autopilot-nebius-demo` under the existing `metalogiclabs-check.workers.dev` subdomain
- Cloudflare API confirmed route enabled and Worker deployment `f6e046a2-f134-41ad-8cb5-81f3f45ec768` serving version `1be57e3e-2bb3-439a-b251-6ec51123491f` at 100% traffic
- Independent Cloudflare Browser Rendering API returned HTTP 200 and HTML containing the Autopilot title and interactive controls
- This is deliberately not live code execution or a second NVIDIA inference call. The real model execution is the source-pinned GitHub Actions run above.

## Caveats

The live model's proposal was tested only against the declared original native tests and two newly acquired separating tests for a deliberately injected defect. A passing source-native receipt is not a theorem of software correctness. The solver's finite minimum is relative to the predeclared hypothesis grammar and synthetic cost. Source codes are not originally Pallets defects. Do not attribute the browser replay to actual live inference.
