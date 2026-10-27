# Prospective source-only C-to-Qwen-Rust binary-search audit

## Binding chronology
This is committed BEFORE any generated Rust file content has been inspected.
Selected using only the ACSL C source, repository README (Qwen3-235B-A22B
pre-translated outputs), and path-existence metadata.

Source repository: ZoneOut12/C2VerifiableRust
Pinned revision: 6c8b35b5dd8e94473b713b7edcf4bf4142f214e3
Authoritative C: data/tutorial_wp/ex-4-binary-search-answer.c
Git blob SHA: c31d685b159f072d75212aa48ba98e1e19a0f207
Heldout Qwen target (path existence only):
transpiled_rust/tutorial_wp/ex-4-binary-search-answer.rs

## Independent source-authored behavioral requirements
For valid nondecreasing arrays:
- If key occurs, output must be an index 0 <= r < len with arr[r] == key.
- If key is absent, output MUST be len, not -1.
- For an empty array, len == 0, so return 0.
- Duplicate keys may return any matching index.
- Input array may not be mutated (ACSL assigns nothing).
- Outside-contract unsorted/invalid-pointer inputs are NOT scored.

## Frozen data and protocol
Enumerate every nondecreasing array of length 0..5 from integer values
[-2,-1,0,1,2] and query keys [-3,-2,-1,0,1,2,3].
This is exactly 1764 distinct input pairs, fixed before target inspection.
Build and run original C as source-side reference and check its outputs
against this independent specification.
Compile and run Qwen Rust UNMODIFIED if possible, with no material repair.
Check exact same inputs. Retain first/minimal counterexample with exact bytes.

If target cannot compile or execute without fixes, call it
UNKNOWN_NOT_EXECUTABLE, not a semantic bug.
A green Verus run by itself is not a C-to-Rust refinement proof.

## Conventional comparator and verdicts
Equally informed baseline gets identical original source, target, corpus,
compiler and runtime restrictions. A competent source-aware black-box
comparator directly checks returned values against C and the source contract.
Report BASELINE_TIE when it reaches the same decision. Do not invent
economic benefit, superior error detection, or unintended defect.

Verdicts: WARRANTED_BOUNDED_MATCH (1764/1764 source and target agree),
FINITE_COUNTEREXAMPLE (valid-domain target mismatch with source-bound evidence),
UNKNOWN_NOT_EXECUTABLE (no unchanged runnable target),
REJECTED_SOURCE_BASELINE (C/oracle mismatch), UNKNOWN_UNPROVEN (other).
Positive tests are bounded, not universal equivalence claims.
