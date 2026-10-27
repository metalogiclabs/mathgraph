# Source-only preregistered ACSL implication normalizer V1

On this branch, target paths are disclosed only as existence metadata.
The source-only analyzer and test policy are sealed BEFORE opening any
Qwen-translated Rust bytes. Input repository is exactly
ZoneOut12/C2VerifiableRust@6c8b35b5dd8e94473b713b7edcf4bf4142f214e3.

Five unreviewed Qwen targets: original C max, all-even, zero-even-indices,
index-initialized doubling, and conditional reset_1st. All original C
SHA/blobs are pinned in FROZEN_MANIFEST.json.

Predeclared source-only normalization:
- Conjunction of forall lower-bound and existential member ensures => MAX
- Complementary forall/even and exists/odd ACSL behavior => Boolean all even
- Forall implication with even-index antecedent => zero even positions
- Forall antecedent pre (a[k]==k) + forall post => double positions
- Old-state, aliasing and pointer-separation formulas => UNKNOWN

Explicitly do NOT infer that odd positions stay untouched from zero-even
postconditions without an assigns clause. Do NOT run invalid preconditions.
Predeclared finite domain for array cases: all arrays length 1..4 over
[-2,-1,0,1,2], 780 each. Index-initialized array cases: lengths 1..6,
six tests. Total recognized 2346. Generate precisely three short source-only
probes per recognized contract (12 total), plus one unsupported case.

After freezing packet and source-only CI independently:
- Build and execute untouched C and corresponding unmodified Rust where
  signatures can be adapted without semantic repairs.
- Keep actual C failure separate from failed Rust compilation or execution.
- Score finite contract violations, source→target discrepancies, and positive
  controls. A conventional reviewer independently implements all four rule
  families with same inputs. No superior accuracy or cost assumed.
- Run mutation/negative tests only on copied outcomes, never claim an authentic
  Qwen migration defect from synthetic data.

This template-limited syntactic extractor is NOT general ACSL semantics or
a formal universal C→Rust refinement theorem. Unknown remains unknown.
