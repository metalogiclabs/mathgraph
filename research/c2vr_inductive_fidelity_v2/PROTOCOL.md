# Source-bound inductive contract fidelity — C2VR V2

This is a finite, independently replayable investigation of specification
**meaning**, not a generic C-to-Rust correctness claim.

## Pinned public input

- `ZoneOut12/C2VerifiableRust@6c8b35b5dd8e94473b713b7edcf4bf4142f214e3`
- `data/tutorial_wp/ex-2-gcd.c` SHA-256 `acd6ca718d61d14d709599d7961436ec136c13a94261d40f38911a190bc20d2d`
- `RQ3_result/Full_Fixed/ex-2-gcd.rs` SHA-256 `2536507f61a2fe83a1356c969093be18cd7aee4511c5155cf70753daa4506cab`
- Native Verus release requested: `0.2025.06.14.9b557d7`, executable SHA-256 `a3fe3b37b2ef1b68a6ef3b22490b4e628f442da423cb56fce6afc554e19c5c04`.

The benchmark's source C file defines `is_gcd` using an ACSL `inductive`
declaration with `gcd_zero` and `gcd_succ`. The published repaired Verus file
instead declares `is_gcd` as an uninterpreted spec function and exposes those
introduction rules using a proof function marked `#[verifier::external_body]`.
ACSL 1.14 section 2.6.3 defines inductive predicates by the **least** fixed
point. Verus documents `external_body` proof functions as an assumption/trusted
axiom; an uninterpreted spec function's meaning is not fixed by a body.

References:

- [ACSL reference manual, section 2.6.3](https://frama-c.com/download/acsl-1.14.pdf)
- [Verus assumptions and trusted components](https://verus-lang.github.io/verus/guide/tcb.html)
- [Verus specification and proof functions](https://verus-lang.github.io/verus/guide/spec_vs_proof.html)

## Frozen claim and falsifier

Claim under test: **the translated introduction axioms alone identify the
same inductive relation as the source least fixed point**.

For finite nonnegative domain `0..3`, the checker constructs the *least*
closure of the authentic two source introduction rules, explicitly setting
`a % 0 := a` only within the finite test to totalize the partial term. It
separately constructs the `is_gcd` interpretation true on every triple.
Both interpretations satisfy the two introduction rules. They disagree on
the predeclared tuple `(a,b,d)=(2,0,1)`: false in the least relation, true
in the total relation. This falsifies uniqueness under the finite model;
it does **not** imply the runtime Rust `gcd` implementation is wrong.

Native Verus verification of the unchanged published file (if successful)
has the status `VERUS_ACCEPTED_CONDITIONALLY_ON_EXTERNAL_BODY`, not a proof
that the source's least-fixed-point meaning has been preserved. If the
native run fails, that observation is retained without promotion.

## Independent comparator and challenges

The conventional comparator reads the same source and target bytes,
recognizes the inductive/uninterpreted distinction, and uses Python's
independent `math.gcd` implementation for the separating tuple. A tie is
expected: the experiment does not establish relative detection superiority
or lower cost. Real tests withdraw a changed/missing source or Rust target;
they refuse absent or forged native receipts and an executable that returns
success without emitting Verus's proof summary. Provenance guards bind
native log and tool bytes to the recorded claim. No source files from the
external repository are committed here.

## Authentic axiomatic positive control (bounded)

At the same upstream revision, `data/tutorial_wp/max_subarray-1.c`
(SHA-256 `ff66b503c6074877c5a764e521d7fbfa15901abfe6e1a70d71d7176a9e4a7e63`)
declares `axiomatic Sum_array` with a logic `sum` and named `empty` and
`range` axioms. The published repaired target
`RQ3_result/Full_Fixed/max_subarray-1.rs`
(SHA-256 `0f62e42e58ba8a0c1c95c4825cad3859123436fd0f99466a5d1eabb45eeec468`)
declares an uninterpreted `sum` with two explicitly trusted
`#[verifier::external_body]` proof functions named `empty` and `range`.
This is a positive control for the **kind of assumption being translated**:
the source is already axiomatic, unlike `is_gcd`'s inductive least relation.
The bounded verdict `MATCHED_AXIOMATIC_TRUST_KIND_BOUNDED` does **not**
warrant formula-by-formula equivalence, whole-program semantics, or
preservation of every contract. Native verification remains conditional
on explicit trust. An equally informed conventional comparator yields
`BASELINE_TIE`; no superiority claim follows.

## Reproduction

Checkout pinned upstream source; set `C2VR_SOURCE_ROOT` to its root. Then:

```sh
python3 -m unittest discover -s research/c2vr_inductive_fidelity_v2 -p 'test_*.py' -v
python3 research/c2vr_inductive_fidelity_v2/native.py "$C2VR_SOURCE_ROOT" "$C2VR_VERUS_BIN" "$EVIDENCE_ROOT"
python3 research/c2vr_inductive_fidelity_v2/checker.py "$C2VR_SOURCE_ROOT" --evidence "$EVIDENCE_ROOT" --output "$EVIDENCE_ROOT/MATHGRAPH_REPORT.json"
python3 research/c2vr_inductive_fidelity_v2/baseline.py "$C2VR_SOURCE_ROOT" --output "$EVIDENCE_ROOT/BASELINE_REPORT.json"
python3 research/c2vr_inductive_fidelity_v2/native.py "$C2VR_SOURCE_ROOT" "$C2VR_VERUS_BIN" "$EVIDENCE_ROOT/axiomatic" --case max_subarray
python3 research/c2vr_inductive_fidelity_v2/axiomatic_control.py "$C2VR_SOURCE_ROOT" --evidence "$EVIDENCE_ROOT/axiomatic" --tool "$C2VR_VERUS_BIN" --output "$EVIDENCE_ROOT/AXIOMATIC_REPORT.json"
python3 research/c2vr_inductive_fidelity_v2/baseline.py "$C2VR_SOURCE_ROOT" --case axiomatic --output "$EVIDENCE_ROOT/AXIOMATIC_BASELINE.json"
```

Continuous integration retains native exit/log, SHA-256 tool/inputs, both
reports, and test output. The broad generalization to human intent, whole
integer ACSL semantics, executable refinement, formal Verus soundness,
Microsoft FoSSE machinery, and deployment authority remains `UNKNOWN`.
