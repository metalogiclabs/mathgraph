# GOETH V20 authenticated remote cross-fork observation — preregistration

Date: 2026-10-28 (Pacific/Auckland)
Status: `CANDIDATE_TEST_PLAN`; run results are not presumed

## Why this experiment

Metatron/MathGraph Check PR #212 records two unresolved source-native GOETH
V19 obligations: `remote_conflicting_fcu` and `concurrent_fcu`. The prior
Geth V19 `TestBALV19CrossForkAdmissionPredicate` executed a direct header
ancestry helper and its separate V13/V17 Engine controls used a valid local
chain. None showed two *different* peer-served forks through the authenticated
Engine API. A green predicate is not a warranted remote Engine result.

## Options and ruling

1. Re-run the V19 direct predicate test: cheap but leaves the exact residual.
2. **Chosen:** run an additional **test-only overlay** at the original frozen
   Geth source revision through GitHub Actions. Produce independently
   header-retrievable A and B forks from one genesis, expose both through real
   encrypted Geth TCP peers, and send JWT-authenticated FCU V4 to a fresh
   cold Geth target. This isolates native observations without rewriting the
   protected Ethereum PR or claiming new owner permission.
3. Edit the Geth PR/production Engine implementation: inappropriate before
   a separating native test and a human release-policy decision.

## Immutable inputs

- Geth owned PR #19 head: `a04aa77aaebd81d11274560e8d24d90c6f417589`.
- Original Geth official pinned merge: `3a6c2e3b35ef8caa3d39dcbea3fe9f09099cca8c`,
  the same official parent merged by original V19 CI. Its resulting source
  tree must be logged. The overlay only adds the new `*_v20_test.go` file.
- Original historical V19 qualification: run `38202260024`, archived
  artifact `11725753900`; **not** evidence for these new observations.
- Native target: the existing `balV13PendingEngineAPI` test-only wrapper,
  `balV18ProveFinalizedAncestor`, `openBALEngineV11Node` and original Geth
  source-native JWT/peer harness. No new Go dependencies or production code.

## Frozen experimental arms

All three arms require both source nodes to have distinct fork heads, two
authenticated TCP peers, the exact requested head *and* final headers
**and the head's true parent header** successfully fetched by the cold target
from remote peers **before** an
authenticated Engine RPC, a rejected unsigned HTTP call, a canonical
finalized pointer still unset, and a cold head before the request.

1. `A_head_B_final`: announce A tip, B preceding finalized hash. The
   provisional pending authority must be empty, admissions zero.
2. `B_head_A_final`: reverse A/B. Same negative acceptance.
3. `A_head_A_final`: announce A tip and its actual preceding A ancestor.
   Positive control must issue a pending witness for the exact A final hash.
   If this cannot admit, either negative is vacuous and no promotion follows.

Both wrong-fork cases compare a head at height 260 to a proposed final at
height 259. Fetching the actual parent at height 259 closes the vacuous
"missing intermediate header" alternative: the candidate rejected final
must be demonstrably different from the separately available genuine parent.
The Engine response `SYNCING` is **not by itself** the oracle. The oracle
is the pending witness and admissions count at the tested boundary with
all three exact remote headers independently available. Record per-arm RPC
status, announced head/final/actual-parent hashes, witness hash, peer count
and cold-target precondition in logs. Network node IDs are not recorded.

## Falsifiers and epistemic boundary

- A cross-fork arm admits pending finality: `REJECTED` for the advertised
  native wrong-fork fail-closed property under that exact input, with the
  original result retained and no engine repair hidden.
- Any fork header cannot be fetched, peers cannot authenticate, the target
  is not cold, or valid same-fork positive cannot admit: `UNKNOWN` due
  inadequate separating observation, **even if both wrong-fork cases appear
  green**. No false promotion from a vacuous negative.
- If all arms satisfy exact native preconditions, mark at most
  `WARRANTED_BOUNDED_NATIVE_REMOTE_CROSS_FORK_REPLAY` under the pinned test
  overlay. This is a new synthetic two-fork test, **not** an independent
  consensus/CL node, a general Ethereum safety proof, or contemporary
  full remote/concurrent FCU authorization.
- `concurrent_fcu` remains `UNKNOWN`: no scheduler interference, blocked
  fetch, epoch supersession or durable stale-commit test is performed here.
- No GitHub App Check, protected-frame source grant, owner policy or merge
  permission changes. A new exact receipt must be reviewed and source-pinned
  separately before any MathGraph frame promotion.

## Verification boundary

GitHub Actions checks out original Geth commit, merges the same upstream
official pin, overlays the test-only file, runs the exact three arms with
the original V19 predicate control, retains full logs as a workflow artifact
and emits an explicit `V20_BOUNDARY` marker **only after** all required
native arm assertions pass. Test failures are evidence, not permission to
relax requirements. The workflow has `contents: read` and no deployment,
write token, issue, PR mutation or third-party contact step.
