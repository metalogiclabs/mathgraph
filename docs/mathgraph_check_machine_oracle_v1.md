# MathGraph Check: no-human-label machine oracle V1

## Why this experiment exists

MathGraph Check v0 compares **explicitly supplied** protected source/formal
contract dimensions, but cannot automatically establish what natural-language
statements mean. Human-labelled real-paper tests are valuable, but an initial
fully automatic test is possible if we deliberately narrow the mathematical
language and generate true/false labels from an independent verifier.

This experiment does **not** use external human annotations, AI judges, model
API calls, or production credentials. It is a bounded finite-semantics test,
not a Palomar statement-alignment substitute or accuracy benchmark on prose.

## Exact boundaries

- A tiny typed grammar covers variables, Boolean constants, negation,
  conjunction, disjunction, XOR, implication and biconditional, with 1–5
  Boolean variables, depth at most 20 and at most 120 nodes.
- The inference module evaluates every possible Boolean assignment and
  compiles a **finite-domain truth signature** into the pre-existing v0
  protected-contract comparator. It returns either an explicit minimal
  counterexample, a finite-domain match, or UNKNOWN for unsupported syntax.
- Unknown source-to-natural-language interpretation, infinite-domain
  generalization and kernel qualification per arbitrary incoming query remain
  separate UNKNOWN states. No green verification badge is produced.
- An independent benchmark oracle uses whole-domain integer bitsets rather
  than the scalar recursive evaluator in the runtime. It derives the expected
  labels without querying MathGraph for those labels.
- A separate pinned Lean 4.35.0-rc2 CI job checks 132 predeclared generated
  finite propositions with by decide, and where applicable explicit
  counterexample witness theorems. Its output is a kernel-checked bounded
  oracle, not a certificate about a human-authored mathematical statement.

## Reproduce

    python -m unittest discover -s tests -p 'test_finite_logic.py' -v
    python research/mathgraph_check_machine_oracle_v1.py --out evidence/mg-machine-oracle

The generator uses the fixed seed 0x4D475632 and produces 420 cases:
195 equivalent pairs, 193 semantically different pairs, and 32 intentionally
unsupported formulas. Four fixed adversarial cases include vacuous implications,
De Morgan equivalence, and impossible assumptions. Their outcomes are checked
against the independent bitset oracle, not accepted on declaration.
Only the declared Bool cubed domain is judged.

The evidence/mg-machine-oracle directory contains a full generated corpus,
case-level classifications, the frozen manifest/summary with SHA256, and the
Lean source to replay separate qualification. CI publishes all artifacts
and records whether the Lean checker passed.

## Acceptance criteria

- No missed finite counterexample or false alarm on generated equivalent
  pairs according to the independent bitset oracle.
- Every reported witness agrees with the reference assignment and Boolean
  outcomes.
- Every unsupported grammar returns typed UNKNOWN without a false claim.
- Every response has truth_promotion=false and NOT_ISSUED badge.
- All 132 generated Lean propositions and counterexample witnesses check
  under the exact pinned Lean toolchain.
- Exact corpus SHA and fixed seed permit cold re-execution.

## What cannot be concluded

- Zero errors on 420 generated Bool cubed cases does not imply any general
  ability to interpret informal mathematical prose or arbitrary Lean.
- The benchmark is machine-generated from a declared DSL, not a naturally
  sampled held-out distribution of real mathematical articles.
- There is **no fair accuracy or cost comparison with Palomar**. Such a
  comparison must include full extraction/review costs and independent
  source-to-statement ground truth over externally sourced, untouched examples.
- Lean decide on bounded Bool statements does not settle infinite-domain
  theorem validity or a physical/scientific model.

## Next gate after passing

Obtain independently grounded original-text/Lean pairs or a mechanically
specified source corpus with audited original meanings, and compare
error detection on the same untouched problems against the published Palomar
statement-alignment rubric at equal total time and inference budget.
