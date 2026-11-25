# Native temporal monitor qualification — 26 November 2026

The temporal component is now qualified at an explicit finite boundary. The full NN requirement remains UNKNOWN. This follow-up does not change either locked investigator result or the original six-case tie.

[Successful complete hosted qualification](https://github.com/metalogiclabs/mathgraph/actions/runs/45708422870) ran the exact research source `6ddba1ddabd5103430e5afa11b0662d58d21f342`, tree `9c0160d99f84b9a1f6dcaf5a65bf57839849d0f2`. Kind 2 2.3.0, Z3 4.15.4 and Rust 1.85.0 were executed. The actual job logs and downloaded evidence archive were inspected.

| Verification boundary | Observed result |
|---|---|
| Pinned author sources and saved active clock | Verified; the two linked verification variants use a one-second base step. |
| Complete published Lustre export | Parses with Kind 2; existing unguarded-`pre` warnings retained. |
| Copied exported clock recurrence | Kind 2 k-induction proves mathematical time equals the step counter converted to real. |
| Native code generation | Kind 2 generated Rust for the scoped temporal component; Cargo release build succeeded. |
| Declared finite cohort | 411/411 traces, 204 ticks each; 83,844/83,844 output rows match the independent timestamped oracle. |
| Independent rebuild | Generated Rust rebuilt locally without source changes; all 83,844 rows agree with the hosted binary. |
| Unprojected Lustre boundary cross-check | Six traces / 1,224 rows at ticks 199, 200 and 201 agree with the compiled binary. |
| Evidence changes | Eight state snapshots agree with the conventional ledger; clock withdrawal removes the sampled-seconds conclusion while retaining native tick facts. |
| Invalid admission controls | Corrupted native certificate and substituted formal window both rejected. |
| Hypothetical changed clock/window | Three finite transfer countermodels retained; these are controls, not NASA defects. |

The source is `hbourbouh/lm_challenges` at `133447a8943721eaa1d16acf1ba5845b67a98df1`, file `FRET_CoCoSim/5_nn/CoCoSim/cocosim_output/nn_12B_with_contracts_PP/nn_12B_with_contracts_PP.KIND2.lus`, SHA-256 `8dbf83197dd057721e89fabe655dd7412421075fd32afad32e7bb377eefd8ace`. Source-level checks follow the top-level clock through the network call and contract import to the 200-step temporal operator and slope predicate. These structural checks do not prove that the complete NN satisfies the requirement.

Five temporal helper bodies are copied exactly into a new scalar-observation harness. To satisfy the compiler interface, the same integer range predicates are moved from Lustre `assert` statements into named contract assumptions; they are retained, not dropped. Both source forms are preserved. The harness exposes verdicts as outputs because the Kind 2 backend omits proof-only properties from generated executables. A separate clock miter retains the integer-to-real correspondence proof. The executable harness's own auxiliary proved property is clock nonnegativity, not the NN requirement.

The cohort contains constant traces at 0, -35 and 10, plus a single violation at every position 0–203 with value -36 or 11. It is complete for that declared cohort, not all possible real-valued traces. The independent oracle evaluates timestamped observation prefixes directly. All chosen arithmetic values are exactly representable at this scale; no unbounded machine-integer or floating-point soundness claim follows.

The window includes tick 200 and excludes tick 201 under the admitted one-second clock. A violation at 200 remains a historical failure after the window ends. A first violation at 201 does not violate this bounded requirement. Changing the claimed window to 201, or changing the hypothetical clock to half-second or two-second ticks, yields concrete mismatches. Those changes were controls; the author models were not modified.

With all required evidence, the experimental resolver warrants the finite sampled-seconds claim. Withdrawing the documentary clock receipt changes it to UNKNOWN/STALE; the native tick semantics and formal clock recurrence stay supported. Restoring the receipt restores the bounded conclusion. The direct conventional ledger matches all eight snapshots. Caller admission freshly checks source identities, native executions, certificates and the documentary interpretation before constructing receipts; the resolver does not authenticate evidence. No unique architectural or economic advantage is established.

Failed attempts constrain the result. The whole-network native interpretation attempt timed out after 30 seconds, so complete NN/dataset/differencing behavior is unqualified. No fresh MATLAB/Simulink build was performed. The original saved simulation stop remains 100 seconds. The first hosted attempt lacked an explicit solver path. The second proved the clock but encountered unsupported integer-to-real Rust generation: Kind 2 returned zero despite logging a backend error, and Cargo rejected the truncated Rust file. Backend logs and an actual successful binary build are now checked separately. An artifact upload initially omitted hidden build metadata; the final archive includes it. A local rebuild restored an empty `rsc/lus` directory required by the generated build script, without changing Rust source.

The complete hosted evidence artifact is `15065674003`, ZIP SHA-256 `7ebc1d28fe5c62c295426d9aca4ddef890bdf9344ee6d3dbe803ef254416a49c`; all 2,526 payload hashes and CRCs were independently verified. Hosted binary SHA-256: `c41bcf018429414600bde95214402d0820f0c1e4232673e24ae2ea8af24cefed`. Full finite certificate SHA-256: `a0eb605cccc3c71f68929503fbe628fdbbc5dbeb6cf0a1d85fdc5a0cb8d993b3`.

The reusable outcome is native qualification of a precisely scoped temporal transfer and its evidence dependencies. It is not general natural-language correspondence, continuous-time assurance, deployed-system correctness, or proof of the complete NN requirement. No new Lean kernel qualification is claimed.
