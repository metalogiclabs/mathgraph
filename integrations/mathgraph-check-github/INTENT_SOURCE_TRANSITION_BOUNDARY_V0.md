# Exact-source intent transition V0 — research boundary

**Candidate product closure, not owner-intent proof.** Isolated research branch
`research/mathgraph-check-intent-source-transition-v0-20261029`.

## Why this experiment exists

`auditIntent` can qualify a pinned probe at B, while the existing pure `monitor`
cannot tell whether the B report and its `independent_requalification` boolean
were supplied by an untrusted caller. The authenticated `compareSnapshots`
facade correctly strips the boolean, leaving B `UNKNOWN` even after a real
separate audit. A new bridge must derive the bit internally, from the fresh B
source, host-supplied independent receipt authority and an unchanged intent
basis. It must not accept self-asserted report objects or `true` flags.

## Experiment and invariant

`qualifyIntentSourceTransition` does, in order:

1. Fetch real GitHub PR/check-run source using `githubSnapshot`, including the
   final head/base stability read already tested at commit `c55f7eb`.
2. Require that B's complete PR subject (repository, PR, base, head) matches
   the observed source. Reject a moving source, even if older checks are green.
3. Require **same owner-intent basis** across A→B: claim IDs and *statements*,
   required probe IDs and each probe's input/oracle hash. A changed requirement
   or oracle is `UNKNOWN` until independently owner-approved; this V0 does not
   invent that approval. Qualified verifier implementations may evolve.
4. Independently recompute old and new `auditIntent` from the contracts and
   receipts with authority supplied in a separate `trustedAuthorities` host
   parameter. No authority or requalification fields in the developer-controlled
   audit packets are honored.
5. Only if exact B CI checks and all independently qualified pinned B probes are
   `OBSERVED` can it derive a scoped requalification for `monitor`. A checked B
   counterexample remains `BLOCKED`; missing, forged, stale or unrelated
   evidence remains `UNKNOWN`.

## Red/green lineage

- Base gate: independent source-stability run
  [40832066205](https://github.com/metalogiclabs/mathgraph/actions/runs/40832066205)
  successfully completed **132/132 tests, 18/18 files**.
- New initial bridge tests failed meaningfully before implementation; after
  implementing the bridge, the first 11/11 scoped cases passed.
- Crucial follow-up negatives **2/2 RED**: fresh B receipts and host authority
  could still silently change a claim's statement or its oracle while retaining
  the same claim ID. Exact SHA and evidence authentication did not establish
  *intent continuity*. Conservatively pinning the unchanged basis made both
  and the other cases green.
- Requalifying authority is a separate trusted-host input, not a property of
  untrusted before/after packets; a forged in-band authority test passes green.
- Final full-suite and independent CI verdict: see the workflow run at the exact
  qualifying branch commit; do not promote from local assertions alone.

## What the V0 does **not** establish

- It does **not** authenticate the claimed host's independently supplied oracle,
  verifier and receipt authority. The host must actually derive these from
  non-developer-controlled artifacts, signature verification or trusted policy.
- It does **not** verify owner-authored intent or owner-approved *changes* to
  that intent basis. Conservative rejection of changed contracts is expected.
- It does **not** verify revocation, new post-read GitHub state or check-run
  reruns after the last read; the GitHub observation is not an atomic snapshot.
- It does **not** prove total correctness: `OBSERVED` describes only the frozen
  declared input/oracle probes. No merge authorization or autonomous repair.
- It does **not** establish better economics or held-out superiority over an
  equally informed, full-rechecking agent.

The next decisive product test must bind trusted external owner policy and
receipt revocation/freshness to a native check/audit workflow, with honest
equal-information full-recheck comparison. Until then Gate 1 is partial.
