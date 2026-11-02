# MathGraph Check owned-fork PR pilot implementation plan

> Implement inline with superpowers:executing-plans; independently review the completed branch before release.

**Goal:** a maintainer requests a source-pinned investigation on an eligible PR without operator intervention.

**Architecture:** reuse the registered GitHub App, trusted hosted dispatch and isolated Lean investigator. Trusted repository capability settings select permitted modules and commands; PR contents never select credentials or executable host commands. Keep model inference separate from native evidence.

**Spec:** Research OS Check investigator readiness audit, 2026-11-03. Public technical scope only; private collaboration context remains outside GitHub.

**Constraints:** owned public forks only during qualification; explicit check/fix; no automatic merge; exact repository/PR/base/head binding; no credentials or network in native execution; immutable generated tests; finite claims/UNKNOWN; source-fresh publication; bounded model calls and compute.

**Review focus:** spoofed maintainer command; changed head before publication; duplicate dispatch causing spending; original failure mislabelled a regression; source mutation of tests or trusted settings.

## Tasks

1. Read App permissions/installations before transport decisions. Record actual coverage, not inferred availability.
2. Add test-first trusted PR intake/configuration, dynamic base/head source binding and explicit command modes. Unsupported files/contexts return UNKNOWN. Replay generated probes across base/head with trusted source/guard identities.
3. Connect authenticated requests to source-repository progress/Check publication; preserve same-head idempotency and stale-head withdrawal. Separate repair request from investigation and freeze prior probes.
4. Reuse no-secret native jobs and model client in the trusted hosted workflow. Bound retries/time/spend and preserve failed attempts. Add reviewable optional draft repair; never merge.
5. Qualify owned-fork command/check/fix/stale/recheck, clean and failure controls using actual GitHub events and registered App identity. Retain artifacts and source pins.
6. Reconcile evidence and write installation/operator instructions. Release only the exact reviewed, tested scope; external install remains a distinct gate until exercised by another operator.

For each component: write failing contract tests, observe failure, implement, rerun focused suite, then broad integration suite. End with fresh independent branch review and fix consequential findings with regression tests.
