# Source-only prospective Qwen C-to-Rust sentinels V2
This protocol, immutable data corpus and outcome rules were committed BEFORE
opening the two generated Rust targets. Selection used source C and target
path-existence metadata only. The earlier distinct len-sentinel case passed.

Upstream: ZoneOut12/C2VerifiableRust commit
6c8b35b5dd8e94473b713b7edcf4bf4142f214e3

Case A source: data/tutorial_wp/ex-3-binary-search-answer.c
Git blob b4f00cac89395f618671bcd73f5b2828e4df3858
Heldout target path: transpiled_rust/tutorial_wp/ex-3-binary-search-answer.rs

Case B source: data/tutorial_wp/ex-3-search-answer.c
Git blob 72d7eafa47c1e4914101ee1a088ffd15688e6369
Heldout target path: transpiled_rust/tutorial_wp/ex-3-search-answer.rs

Predeclared independent requirements:
A: Valid nondecreasing arrays, matching key returns any matching index;
absent key returns EXACTLY -1. Empty returns -1. Do not mutate input.
B: Valid arrays need NOT be sorted; matching key returns any matching index;
absent key returns EXACTLY UINT_MAX = 4294967295 on the native C ABI.
Empty returns UINT_MAX. Do not mutate input. Source declares termination.
Duplicates never require the first or last match.

Fixed corpus: A: all sorted arrays length 0..5 over [-2,-1,0,1,2] with
keys [-3,-2,-1,0,1,2,3] = 1764. B: all arrays (even unsorted)
length 0..4 over same values and keys = 5467. Total 7231.

Compile original C on Linux and check the source contract. Run the
unchanged generated Rust code with nonsemantic input/output harness only.
Retain output and array immutability for each input. No repairs to target
algorithm or assumptions may be introduced. If a genuinely unmodified
target cannot compile, report UNKNOWN_NOT_EXECUTABLE; do not claim defect.
Reproduce exact input and bytes of any witnessed wrong output.

Matched baseline independently checks the exact same source, executable
outputs and frozen corpus, with no calls to MathGraph oracle code.
Equal detection is BASELINE_TIE. Measure no unobserved economic advantage.

Per-case outcomes: WARRANTED_BOUNDED_MATCH / FINITE_COUNTEREXAMPLE /
UNKNOWN_NOT_EXECUTABLE / REJECTED_SOURCE_BASELINE / UNKNOWN_UNPROVEN.
A successful bounded run is not universal refinement, and no claim of
Microsoft adoption or automated discovery advantage is authorized.
