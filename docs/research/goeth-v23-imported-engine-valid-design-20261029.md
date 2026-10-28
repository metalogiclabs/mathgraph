# GOETH V23 — two imported forks, authenticated Engine-VALID arrival-order probe

Date: 2026-10-29 (Pacific/Auckland). Research-only; draft/unmerged.

## Question and falsifier

V22 warranted only speculative pending-witness supersession: both cold unknown-head Engine V4 replies were `SYNCING`. Does an *independently source-qualified pair of already imported and locally executable forks* yield the stronger Engine `VALID` responses, and what happens if an older authenticated request reaches the RPC test boundary before a newer conflicting request, but is delayed before native Geth's forkchoice handler?

The proposed *external arrival-order authority rule* is: B supersedes A when B is received later. This is **not** a rule proven to be part of the Engine API specification. The test explicitly contrasts that proposed rule with Geth's actual execution-time forkchoice behavior; a counterexample does not establish a production Geth bug. JWT authentication does not assign independent consensus-controller precedence.

## Exact schedule

1. Produce distinct A/B chains (same genesis) with exact hash-linked head/finalized pairs; import **both** full chains into a fresh native Geth target, verify both head/finalized blocks and state are locally available, and verify canonical finalized pointer starts nil. No speculative pending-witness adapter handles the requests.
2. Independent serial positive: authenticated Engine V4 FCU to A yields `VALID` and exact canonical head/final A; subsequently B yields `VALID` and exact head/final B. If either does not, classify `UNKNOWN/setup` and do **not** call the overlap an Engine-VALID race.
3. In a second fresh target, use the **unmodified** `ConsensusAPI.ForkchoiceUpdatedV4` through two distinct JWT-authenticated HTTP RPC clients. A test-only wrapper pauses only the first A request *before delegation* to the native method; an observed `entered` barrier establishes A arrived at the wrapper first.
4. B arrives after A, delegates normally, returns exactly Engine `VALID`, and installs the exact B canonical head/final pair. Only then release A. Record A's exact response and both canonical pointers.
5. Named obstruction if the delayed A itself returns `VALID` and restores its older conflicting A canonical head/final pair: `MG_BAL_V23_RED_OLDER_A_REPLACED_B_AFTER_ENGINE_VALID`. This violates the proposed external arrival-order rule but **not necessarily Geth's actual contract**. A refusal or no stale change preserving B receives a *bounded* positive; any compile/setup/status ambiguity is `UNKNOWN`.

## Comparison and controls

- V23 is a direct source-native Geth Engine `VALID` exercise, not a V13/V21 speculative adapter test. The only shim is the before-delegate barrier, which does not forge or change the Engine response or canonical chain updates.
- Retain V22's independent two-remote-fork `SYNCING` protected control, V20 remote crossfork 3-arm control, V20 serial invalidation and V17–V19 controls. The existing V21 generation-guard overlay is only applied to those historical fork-only controls, and **cannot** justify a claim about the native imported-head path.
- Pin original Geth source commit, official upstream merge and exact source tree; separately record the V23 Go test blob, test-only wrapper, workflow Git tree, Go compiler, raw logs and artifact SHA256.
- No Geth production file, CL, MathGraph Check owner policy, release grant, or deployment is modified. This study cannot establish real controller identity, legitimate FCU ordering, multi-instance policy, import/restart parity after the observed result, or commercial superiority.

## Precommitted classification

- `NAMED_OBSTRUCTION` only with two independently hash-linked imported forks, 2 authenticated `VALID` replies, ordered A-before-B wrapper entry, B installed first and A restored afterward, and independent positive controls.
- `BOUNDED_POSITIVE` only when the same schedule preserves B and all setup/controls pass.
- `UNKNOWN` for invalid imports, non-`VALID` B, absence of ordered markers, missing top-level controls, compilation failure, timeout, or any other branch.

This test probes a missing *external controller-authority rule*. Even a reproducible negative must not be promoted to a Geth consensus defect or a release decision without that declared rule and source-controlled proof.

## Protected repeat after first native result

After preserving the first qualifying native RED or positive as its own immutable GitHub Actions artifact, rerun the **identical V23 Go test blob** and all seven controls with `go test -count=3`. Require exactly three top-level passes per control, three serial A and B `VALID` markers, three ordered A-before-B/barrier markers, and either exactly three V23 expected RED failures with exact marker or three bounded positives. Any partial, mixed, or unrelated result remains `UNKNOWN`. The protected workflow also records its own GitHub overlay tree and workflow blob; GitHub artifact ZIP digests are checked as post-upload metadata, not manufactured by the runner.
