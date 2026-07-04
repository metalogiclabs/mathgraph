# SorryDB v4.3.1 Accepted Patch Replay Ledger

v4.3.1 records the first successful controlled SorryDB proof-repair contacts after v4.3.0 landed the patch replay portal.

## Accepted replay 1

Target source snippet:

    · extract_goal using eg₁
      sorry

Patch snippet:

    · extract_goal using eg₁
      exact Nat.le_add_right n 1

Observed manifest verdict:

    baseline_verdict=BASELINE_PASSED
    patch_apply_verdict=PATCH_APPLIED
    patch_verdict=PATCH_ACCEPTED
    verdict=PATCH_ACCEPTED

Restore check:

    line 97 restored to sorry after replay

## Accepted replay 2

Target source snippet:

    · extract_goal using eg₂
      sorry

Patch snippet:

    · extract_goal using eg₂
      exact Nat.succ_le_succ (Nat.le_add_right n 1)

Observed manifest verdict:

    baseline_verdict=BASELINE_PASSED
    patch_apply_verdict=PATCH_APPLIED
    patch_verdict=PATCH_ACCEPTED
    verdict=PATCH_ACCEPTED

Restore check:

    line 99 restored to sorry after replay

## Earlier target-state obstructions

Two attempted theorem-level patches were correctly rejected before replay because the expected source snippets were not present in the actual file:

    OBSTRUCTED_PATCH_TARGET_MISSING

The file inspection showed:

    theorem eg₁ (n : ℕ) : n ≤ n + 1 := by exact Nat.le_add_right n 1

and no standalone eg₂ theorem line in the source file.

This matters because Lean stdout printed theorem text that was not reliable as exact source state. The source file itself became the trust boundary.

## Bounded claim

v4.3.1 claims:

- baseline-passing source was confirmed before patch replay
- one explicit text replacement was applied at a time
- Lean accepted each patched file
- original source was restored after each replay
- two local sorry replacements were accepted by Lean

v4.3.1 does not claim:

- general proof repair
- declaration retrieval success
- multi-file patching
- repository-wide sorry elimination
- upstream submission
- automation over arbitrary SorryDB entries

## New Lawbook entry

Given:
  baseline-passing cached Lean project
  exact source snippet occurs once
  explicit candidate replacement
  controlled replay runner

Then:
  Lean returncode 0 after replacement is a PATCH_ACCEPTED certificate
  file restoration preserves source state after replay

## Next frontier

Promote accepted replay artifacts into reusable patch certificates:

- source_snippet
- patch_snippet
- target file
- baseline command
- patch command
- Lean return code
- stdout/stderr tails
- restore proof
- verdict

Then batch over exact-source snippets only.
