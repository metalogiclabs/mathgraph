# PROSPECTIVE HOLDOUT COHORT — source-only Qwen C→Rust translation

The target bodies of BOTH named Rust files were not opened before this commit.
This immutable preregistration fixes both cases, the input populations,
source-authored contracts, and the success/failure taxonomy. Selection used
only original C ACSL source and target path-existence metadata.

Upstream: ZoneOut12/C2VerifiableRust@6c8b35b5dd8e94473b713b7edcf4bf4142f214e3,
whose README states transpiled_rust is Qwen3-235B-A22B generated.

Case A / UNSORTED_RECURSIVE_SEARCH:
- C: data/tutorial_wp/ex-3-search-answer.c
- Git blob: 72d7eafa47c1e4914101ee1a088ffd15688e6369
- Holdout target path: transpiled_rust/tutorial_wp/ex-3-search-answer.rs
- Original returns matching unsigned index when present; UINT_MAX (4294967295
  on the pinned Linux uint32 reference) when absent; empty input returns UINT_MAX.
- Input preserved and function terminates.
- Every integer array of length 0..4 over [-2,-1,0,1,2], every query in
  [-3,-2,-1,0,1,2,3]: 5,467 valid-domain cases.

Case B / SORTED_BINARY_SEARCH:
- C: data/tutorial_wp/ex-3-binary-search-answer.c
- Git blob: b4f00cac89395f618671bcd73f5b2828e4df3858
- Holdout target path: transpiled_rust/tutorial_wp/ex-3-binary-search-answer.rs
- A match permits any index carrying the queried value; absence returns -1
  (not len); empty input returns -1; input preserved; sorted precondition.
- Every sorted integer array length 0..5 over [-2,-1,0,1,2], seven query
  values as above: 1,764 valid-domain cases.

Total: exactly 7,231 prespecified cases. An independently compiled C reference
must conform to source-authorized result sets before target evaluation.
Unchanged Qwen target must compile as-is for a runtime fidelity verdict.
Non-semantic runners/harnesses may be added separately but target function
bodies must not be repaired or edited. A missing build/test harness alone must
not become an alleged translation bug. Native Verus evidence, if available,
is separately scoped from runtime correspondence.

Outcomes per case:
WARRANTED_BOUNDED_MATCH, FINITE_COUNTEREXAMPLE (native valid-input mismatch),
UNKNOWN_NOT_EXECUTABLE (unchanged target cannot be executed),
REJECTED_SOURCE_BASELINE, or UNKNOWN_UNPROVEN.
No representative case may be dropped after target unblinding.
Strong conventional source-aware baseline gets the same C contract, full
test corpus, target, compiler and costs; report ties honestly.
Preserve all positive, negative, unknown and failed CI lineages.
