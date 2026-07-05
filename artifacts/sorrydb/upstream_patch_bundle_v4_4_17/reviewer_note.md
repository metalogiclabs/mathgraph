# SorryDB v4.4.17 — Upstream Patch Evidence Bundle

Target repository: siddhartha-gadgil/MetaExamples
Pinned commit: edbb75e784db19846a1c19841e182b797afc18bb
Target file: MetaExamples/Fiddle.lean

This bundle contains 2 exact-source patch candidates.

## Candidate 1

Replace the eg₁ sorry with exact Nat.le_add_right n 1.

Source snippet:

  · extract_goal using eg₁
    sorry

Replacement snippet:

  · extract_goal using eg₁
    exact Nat.le_add_right n 1

Evidence certificates:

- sorrydb-v4-3-2-metaexamples-fiddle-line97-eg1
- sorrydb-v4-3-4-emitted-metaexamples-fiddle-line97-eg1

## Candidate 2

Replace the eg₁ sorry with exact Nat.le_add_right n 1.

Source snippet:

  · extract_goal using eg₂
    sorry

Replacement snippet:

  · extract_goal using eg₂
    exact Nat.succ_le_succ (Nat.le_add_right n 1)

Evidence certificates:

- sorrydb-v4-3-2-metaexamples-fiddle-line99-eg2
- sorrydb-v4-3-4-emitted-metaexamples-fiddle-line99-eg2

## Bounded claim

- v4.4.17 packages the two deduplicated accepted repair seeds into an upstream-facing exact-source patch evidence bundle.
- each patch candidate includes source snippet, replacement snippet, target repo, pinned commit, file path, certificate ids, and accepted replay evidence.
- the bundle is evidence for review and replay, not an upstream acceptance claim.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- general SorryDB mining
- arbitrary proof repair
- upstream acceptance
- semantic portability beyond exact-source replay or verified adapters
- authority to modify the upstream repository

## Replay checklist

- checkout the target repository at the pinned commit
- apply each replacement only to the exact matching source snippet
- run Lean in the recipient checkout
- accept only if the recipient checkout verifies
