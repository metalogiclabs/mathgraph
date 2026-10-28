# GOETH V24 — Synthetic owner-epoch envelope (NOT a production security boundary)

**Status: CANDIDATE, research-only; no real owner key or release permission.**
Base: PR #216 exact commit `5d0a0fbcd60b306d1386c28890e544f5b56f46c1`; Geth source `be33043dc27407a62471bfde1d50b6f99bfc9e6b` and upstream `3a6c2e3b35ef8caa3d39dcbea3fe9f09099cca8c`, merged tree `a61594923136563d50964d7aa96a44c778bf9441`.

The actual [Engine API common specification](https://github.com/ethereum/execution-apis/blob/3284ee80c3da3e516c53782dde75157cccf1ebdc/src/engine/common.md) has a mandatory receive-order rule for forkchoice updates; it *also* says many-to-one CL-to-EL simultaneous head control is undefined. The V23 test inserted its own pre-handler delay, and therefore did not show a production Geth violation. Keep that original bounded observation and its three repeated RED receipts distinct from any spec-conformance claim.

## Decisive small experiment

Use an independently signed (Ed25519) synthetic grant, domain-separated and bound to experiment scope, local genesis, monotonic epoch and exact head/finalized hashes. A test-only in-process gateway forwards the accepted grant through the **actual authenticated native Engine V4 RPC**. It does not change Geth's native handler or API.

Four actual native Go root tests:
1. **Unfenced negative control**: the valid, older epoch 1 request pauses before the gateway check, then newer epoch 2 returns native Engine VALID. Releasing epoch 1 without a fence rewrites canonical finality back to A.
2. **Fenced positive**: same schedule; one mutex protects epoch check → native execution → state advance. B remains canonical and stale A is rejected *before* native execution.
3. **Forgery/replay/liveness**: bad signature, wrong scope, tampered head, stale epoch and same-epoch duplicate all reject; genuine later epoch 3 still progresses.
4. **Bypass falsifier**: native `engine_forkchoiceUpdatedV4` remains directly reachable with the existing JWT and can overwrite B without the optional gateway. Expected outcome must be recorded as **NO PRODUCTION SECURITY BOUNDARY**.

Run historical native serial Engine VALID, V22 two-remote-fork pending gate, V20 three-arm crossfork, serial invalid, V17 malformed, V18 ancestry, V19 predicate in the same pinned Geth runner. The new Go source is expected to match Git blob `c322610f171a079b9f6877a55c282ee00bb76bde`; a mismatch, compilation error, skipped control or missing marker is **UNKNOWN**, not success.

**Claim boundary:** This can at most warrant `BOUNDED_TEST_GATEWAY_EPOCH_SUPERSESSION`. The signed private key is a deterministic fixture in test code, not a real owner. A synthetic grant authorizes nothing. The optional gateway is bypassable and not production-ready. Durable epoch state, process crash/restart, multiple gateway instances, single controller Engine receive-order compliance, external owner policy and commercial advantage stay UNKNOWN. Never merge/deploy this as an Engine security fix.
## Test-source-frozen protected repeat (preregistered before retry)

Initial native execution: [Actions #40768239077](https://github.com/metalogiclabs/mathgraph/actions/runs/40768239077), source `063cc9f2a6ffffa36ae42a7ad705e88e44cf3ea7`, all four new V24 Go roots and seven inherited controls passed, including the bypass witness. Artifact `12852400496`, GitHub-reported ZIP SHA256 `f95c6030348fb54eafea8dab50116f286d421d24961c63d5451f499c45cc919d` (not independently rehashed).

Freeze test Git blob `c322610f171a079b9f6877a55c282ee00bb76bde`. A separate repeat workflow now runs `go test -count=3`, requiring exactly **33 root PASSes** (4 new x3 and 7 controls x3), exactly three of each V24 positive, negative and bypass markers, and three each of V23 serial fork 0 and fork 1 VALID markers. Any compilation/setup/mixed count result stays UNKNOWN. Direct native RPC bypass remains a mandatory and expected *negative*, so even a fully green replay cannot warrant production mediation.
