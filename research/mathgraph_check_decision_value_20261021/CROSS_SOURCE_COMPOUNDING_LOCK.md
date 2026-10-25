# Cross-source capability compounding: prospective gate 2026-10-21

STATUS: CANDIDATE / NO PROSPECTIVE CLAIM BEFORE EXECUTION.

Frozen before reading either source:
- Source A: BurntSushi/toml, default branch exact head to be pinned before opening source.
- Source B: go-ini/ini, default branch exact head to be pinned before opening source.
- Both public Go packages; different file formats (TOML versus INI), not independent programming-language ecosystems.
- Candidate method: source-independent metamorphic *string round-trip preservation* after encoding, decoding and a second encode/decode, constructed from A's native public API. Retain the test schema / generators, adapt only API wiring to B.
- Source-independent inputs: empty, leading and trailing whitespace, dotted syntax, hash/comment characters, quotes, backslashes, Unicode, CR, LF, equal sign; use only representable strings. Avoid declaring parsing equivalence outside API contract.
- Baseline: competent stateless test author gets the same round-trip method, generator, source documentation and API knowledge, and can reuse executable templates. Same tooling and full time budget; baseline prefilled with equal information.
- Primary outcome: source B previously unseen, native package test: accepted candidate property checks and non-regression; all API wiring, baseline acquisition, source inspection, setup, compilation, test execution, failed/redo attempts, and verification cost charged.
- Causal intervention: remove acquired executable method/generator from B adapter and measure end-to-end cost of re-derivation; restore and cold restart.
- Null/negative gates: both arms tie, one format rejects a generated string by declared grammar, inability to freeze before source inspection, or B method simply restates an obvious test.
- The candidate does NOT have a recognized certified property transporter into B. Independent correctness depends on native package replay and explicit scope.
- NO AUTONOMOUS METHOD DISCOVERY: method is human specified. NO COMMERCIAL OR CROSS-DOMAIN WIN without net advantage against fully informed baseline.
- No external repository writes, no reviewer outreach, no deployment.
