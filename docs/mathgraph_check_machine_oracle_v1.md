# MathGraph Check: no-human-label finite oracle V1

## Objective

This executable benchmark stress-tests MathGraph Check on a deliberately
restricted Boolean claim language without human-labelled examples, AI judges,
paid inference, or outside users. It is **not** an informal-to-Lean translation
quality benchmark or a cost/accuracy comparison against Palomar's reviewer.

## Frozen scope

- Three Boolean variables p/q/r and eight exhaustive valuations for each claim.
- 420 generated pairs with seed 0x4D475632: 195 equivalent, 193 semantically
  different, 32 intentionally outside the typed fragment.
- Independently derived expected outcomes via an integer bitset oracle. The
  MathGraph runtime uses a separate scalar evaluator and routes the complete
  truth signatures through the existing MathGraph Check v0 comparator.
- Checks counterexample witnesses, false alarms, missed differences and
  out-of-grammar UNKNOWNs without elevating source fidelity or issuing badges.
- Includes vacuous-implication, De Morgan and hidden-vacuity negative controls.
- From the supported cases, a predeclared deterministic sample of 132 produces
  Lean theorems and counterexample witnesses. A separate CI job checks these
  under the pinned Lean v4.35.0-rc2.

The manually specified grammar is narrow: Bool constants, variables, negation,
AND, OR, XOR, implication and iff. The result cannot be extrapolated to arbitrary
Lean dependent types, source-to-informal statement correspondence, JPL L4YAML
parsers or PKC provenance/tape relations.

## Reproduction

    python -m unittest discover -s tests -p test_finite_logic.py -v
    PYTHONPATH=. python research/mathgraph_check_machine_oracle_v1.py --out evidence/mg-machine-oracle

The corpus identity is fixed to:
a8c05bda6e6bbfb15fdfe21bc8954fd9c5d790f8a31b2df04c8a3ef83b04b609

CI saves summary.json, corpus.json, results.json, MachineOracleV1.lean,
Lean toolchain identity and separate Lean qualification result. A local Python
PASS alone does not establish independent Lean verification. A qualified CI
PASS establishes only this scoped finite-domain claim.

## Separations that must not collapse

- Finite-domain equal signatures are not evidence that the original English
  mathematical statements are equivalent.
- A finite counterexample is valid for the encoded formulas and declared
  interpretations only, not for an unverified natural-language extraction.
- An unsupported syntax query returns typed UNKNOWN.
- A cached proof result does not certify a general theorem unless the native
  checker has independently replayed its exact source and assumptions.
- No zero-human synthetic benchmark can substitute for independent source
  interpretation on an unrestricted natural-language distribution.

## Nicolas Rouquette connection

This is a limited example of an independently exercised mathematical observer
and a second checker, a useful constituent of Nicolas's request to validate
the validator. His requested JPL L4YAML acceptance iff characterization and
PKC provenance/tape semantic seals involve real executable semantics and remain
separate obligations. The 420-case result cannot be described as fulfilling
those broader needs.

## Next decisive experiment

Use an independently specified parser/logic artifact with a separate executable
interpreter and checker, including deliberate semantic mutants, then qualify an
end-to-end source-to-formal preservation theorem. Compare any broad fidelity
claims against independent public source-alignment labels and the published
Palomar review baseline with total inference, machine and human work charged.
