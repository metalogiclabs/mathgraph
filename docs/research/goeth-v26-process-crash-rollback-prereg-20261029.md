# GOETH V26: real separate gateway OS process kill, source-native recovery, and journal tamper negatives

29 October 2026 NZDT — CANDIDATE until actual source-native CI. Test-only; no production code or real owner authorization.

## Precise provenance

Base MathGraph protected V25 source commit 968e59a1b02d830f10713d12b8f71da9e392b121. Frozen V25 test Git blob bc7646371638f57b117414394066acfab0811bb4 and repaired V25 journal gateway blob 3c6415c027e5c072a8affc12131da6626d46aeb6 are unchanged. Original owned Geth commit be33043dc27407a62471bfde1d50b6f99bfc9e6b plus upstream pinned commit 3a6c2e3b35ef8caa3d39dcbea3fe9f09099cca8c gives merged source tree a61594923136563d50964d7aa96a44c778bf9441. Go 1.27.3, Linux GitHub Actions, read-only permissions. New V26 test Git blob 342a61a52d1b98e19672e5c61a08319e2a5278e5.

## Preregistered five cases

1. **Real child OS SIGKILL, retained intent, separate-process recovery.** The Geth node runs in the parent Go test. A new gateway child receives a B-epoch2 synthetic signed grant, uses the inherited V25 fsync/atomic rename/directory fsync journal writer to publish PREPARED, and sends native JWT Engine V4. It must receive actual VALID and read both head and finalized hashes through authenticated eth_getBlockByNumber(latest/finalized). It then emits a source marker. The parent immediately SIGKILLs the child at that exact post-effect/pre-journal-completion boundary and proves the OS wait status is SIGKILL. A freshly launched different gateway child must reload PREPARED and refuse stale A epoch1 *and* prospective epoch3 while IN_DOUBT. A new read-only observation/reconciliation child must compare both native hashes and save RECONCILED_OBSERVED. Another fresh child refuses A epoch1; new signed epoch3 progresses to native VALID.
2. **Raw native Engine bypass negative.** After a genuine child SIGKILL and native B effect, the still-live parent's direct JWT Engine V4 sends A and changes canonical state. A new child must refuse journal-B reconciliation because observed native head/final no longer match and must keep IN_DOUBT. This demonstrates that the optional gateway is not complete mediation.
3. **Deleted-journal negative.** After SIGKILL with B canonical, explicitly delete the only trusted-history file. Reopening with no monotonic anchor treats old signed epoch1 A as fresh and changes native canonical B to A. This is a VULNERABILITY in the test-only journal design, not a passing tamper-resistance claim.
4. **Rolled-back-journal negative.** After crash/reconcile B epoch2, process signed epoch3 A and epoch4 B. Replace the journal with the older valid signed epoch2 snapshot. Separate gateway child then admits superseded signed epoch3 A and rewrites B. The rollback vulnerability must be observed, not treated as a false positive or fixed in this experiment.
5. **Malformed-journal rejection.** An invalid journal must fail closed in a separate child after the native B effect; native B remains canonical.

Native source independent controls: all 3 frozen V25 roots, all 4 V24 roots, V23 imported-head two-fork VALID, V22 two-remote-fork guarded control, V20 serial/three-arm remote, and V17/V18/V19. Any native compile/setup/control failure, incomplete SIGKILL, unreadable native finalized observation, or unexpected behavior is UNKNOWN. Historic V22 syncer nondeterminism must remain included; do not weaken to achieve green.

## Scope

Positive would warrant only a **gateway OS child-process SIGKILL** and restart against an otherwise still-running Geth server, plus fail-closed recovery under one *untampered* local journal. The signer is synthetic and deterministic. Negative deletion, rollback and raw native API bypass show no anti-rollback or full mediation security. Neither Geth OS restart or database re-import, multiple concurrent gateway writers, independent trusted monotonic anchor, real source owner credentials, complete policy enforcement, production Ethereum correctness nor commercial advantage is tested. No merge/deploy.

Next cheapest decisive test after the negative: an independently signed high-water epoch anchor held outside the mutable journal, explicit rollback/deletion refusal, and separate authority for the only native effect path.