# SorryDB v4.4.18 — Reviewer Patch Note and Exact Replay Checklist

This note converts the v4.4.17 upstream patch evidence bundle into a reviewer-facing patch note.

Target repository: siddhartha-gadgil/MetaExamples
Pinned commit: edbb75e784db19846a1c19841e182b797afc18bb
Target file: MetaExamples/Fiddle.lean

Patch candidates: 2

## upstream-patch-001: eg1_line97_nat_le_add_right

Summary: Replace the eg₁ sorry with exact Nat.le_add_right n 1.

Target:
- repo: siddhartha-gadgil/MetaExamples
- commit: edbb75e784db19846a1c19841e182b797afc18bb
- file: MetaExamples/Fiddle.lean
- line span: 

Source snippet:

  · extract_goal using eg₁
    sorry

Replacement snippet:

  · extract_goal using eg₁
    exact Nat.le_add_right n 1

Evidence certificates:

- sorrydb-v4-3-2-metaexamples-fiddle-line97-eg1
- sorrydb-v4-3-4-emitted-metaexamples-fiddle-line97-eg1

Review requirement:

- apply only if the source snippet matches exactly
- rerun Lean in the recipient checkout
- accept only if the recipient checkout verifies


## upstream-patch-002: eg1_line97_nat_le_add_right

Summary: Replace the eg₁ sorry with exact Nat.le_add_right n 1.

Target:
- repo: siddhartha-gadgil/MetaExamples
- commit: edbb75e784db19846a1c19841e182b797afc18bb
- file: MetaExamples/Fiddle.lean
- line span: 

Source snippet:

  · extract_goal using eg₂
    sorry

Replacement snippet:

  · extract_goal using eg₂
    exact Nat.succ_le_succ (Nat.le_add_right n 1)

Evidence certificates:

- sorrydb-v4-3-2-metaexamples-fiddle-line99-eg2
- sorrydb-v4-3-4-emitted-metaexamples-fiddle-line99-eg2

Review requirement:

- apply only if the source snippet matches exactly
- rerun Lean in the recipient checkout
- accept only if the recipient checkout verifies


## Exact replay checklist

1. Clone the target repository.
2. Checkout the pinned commit.
3. Hydrate the Lean cache if needed.
4. Run the baseline Lean check before applying patches.
5. Apply only exact-source replacements.
6. Run the patched Lean check.
7. Accept only if the recipient checkout verifies.

## Replay commands

- git clone https://github.com/siddhartha-gadgil/MetaExamples.git MetaExamples-sorrydb-v4418-review
- cd MetaExamples-sorrydb-v4418-review
- git checkout edbb75e784db19846a1c19841e182b797afc18bb
- lake exe cache get
- lake env lean MetaExamples/Fiddle.lean
- apply the two exact-source replacements from the patch note
- lake env lean MetaExamples/Fiddle.lean

## Bounded claim

- v4.4.18 turns the v4.4.17 upstream patch evidence bundle into a reviewer-facing patch note and exact replay checklist.
- the note contains two exact-source patch candidates backed by four accepted replay certificates from v4.4.11.
- the checklist describes how a reviewer can independently replay the candidate patches.

## Does not claim

- new proof discovery
- new Lean replay
- new accepted patches beyond v4.4.11 evidence
- general SorryDB mining
- arbitrary proof repair
- upstream acceptance
- semantic portability beyond exact-source replay or verified adapters
- authority to modify the upstream repository
