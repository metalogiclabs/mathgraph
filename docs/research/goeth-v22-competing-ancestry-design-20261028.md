# GOETH V22: overlapping competing ancestry-qualified peer forks (not Engine VALID)

Pre-registered 2026-10-28 after the independent V21 generation-fence
[RED #40660706170](https://github.com/metalogiclabs/mathgraph/actions/runs/40660706170)
and [GREEN #40661689124](https://github.com/metalogiclabs/mathgraph/actions/runs/40661689124).
The earlier experiment used a **newer invalid** zero-head FCU to supersede a
paused older FCU. V22 tests a stronger *positive-versus-positive* case:
two distinct, independently hash-linked, peer-served competing forks, each
proposed through a separate authenticated Engine V4 client.

## Falsifiable causal schedule

1. Two independent actual Geth TCP source peers serve different chains A and B
   from the same genesis. The target is cold. Both exact heads, each actual
   parent and each proposed finalized header must be retrievable from peers.
   The finalized proposals must be distinct genuine parent hashes; the head
   hashes must be distinct. Anonymous HTTP must return 401; two independent
   clients must use the target's genuine JWT Engine endpoint.
2. Authenticated FCU A, head A plus its exact finalized parent A, reaches the
   native V18 ancestry-qualified admission hook. A is held at a deterministic
   barrier *before* the speculative witness is written. Pending must be empty
   and admissions must be zero.
3. Authenticated FCU B, head B plus its exact finalized parent B, completes
   while A remains paused; B must receive Engine `SYNCING`, admit its **exact**
   finalized B hash as pending witness once, and leave canonical finalized
   state empty. This positive prevents vacuous all-rejection.
4. Release A, require its Engine response to complete `SYNCING`. If A
   reinstates its earlier finalized A pending hash with two admissions,
   observe `MG_BAL_V22_RED_OLDER_A_REPLACED_NEWER_B`. The desired invariant
   is pending B with one admission, two ancestry-qualified hook arrivals,
   no canonical finalized pointer, and
   `MG_BAL_V22_COMPETING_ANCESTRY_PASS`.

`SYNCING` is specifically **not** Engine `VALID`. The test establishes the
fork-only adapter's pending-witness ordering for two *ancestry-qualified*
unknown-head proposals, not consensus validity or import/restart parity.

## Test-first protocol

Run the exact new V22 Go test first against unpatched owned Geth
`be33043dc27407a62471bfde1d50b6f99bfc9e6b` with official upstream
merge input `3a6c2e3b35ef8caa3d39dcbea3fe9f09099cca8c` and pre-overlay
merged source tree `a61594923136563d50964d7aa96a44c778bf9441`.
The RED classifier demands actual nonzero Go test exit, both ordered markers,
the exact stale-A-over-B marker, and independent PASS for:

- V20 serial positive valid then invalid FCU;
- V20 full three-arm *remote cross-fork* JWT positive/negative probe;
- V17 malformed attributes;
- V18 ancestor predicate;
- V19 crossfork predicate.

Timeout, unavailable source, failed controls, missing V22 marker or arbitrary
Go failure is **UNKNOWN**, not expected RED. Preserve the unmodified source
and native logs in the artifact.

Only after actual RED, apply the exact byte-pinned V21 **test-only** adapter
patch `bal_pending_fcu_epoch_fence_v21.patch` with original adapter blob
`7c41562e93516b6f35792083c2c05bc6eca019d4`. Re-run the identical
V22 test and controls; require Go exit 0, exact V22 positive marker,
zero stale marker and all controls PASS. Preserve source/patch/test blobs.
Any green result is bounded to **one shared adapter instance** and these
two source-fork proposals under cold-head `SYNCING`.

## Residual authority

Actual Engine-`VALID` competing forkchoice processing; full native import
and restart state parity; multi-instance shared-blockchain coordination;
production Geth; independent CL consensus; and owner release authorization
remain **UNKNOWN**. No production change, merge or deployment is requested.
