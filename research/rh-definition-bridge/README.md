# RH semantic-definition bridge (reproducible evidence)

**Goal:** audit the meaning of Mathlib's RH definition without assuming RH itself.

## Exact frozen boundary

- Claimed proof uses Lean 4.33.1, Mathlib SHA `0df444a360eaa60ab8c11dca51a86af692955474`.
- The independent source-level specification defines the classical zeta function by the Dirichlet series for Re(s)>1 and analyticity away from 1, without mentioning Mathlib's \`riemannZeta\`.
- Lean theorem: \`RHBridge.independentRHIffMathlib : IndependentRH ↔ RiemannHypothesis\`.
- Source: \`RHIndependent.lean\`.
- Lean CI: https://github.com/metalogiclabs/mathgraph/actions/runs/44787307004 (success).
- Independent external \`con-ron\` verified-mode checker: https://github.com/metalogiclabs/mathgraph/actions/runs/44787599256 (success, 53,456 declarations accepted).
- External checker SHA: \`de06320fcdce1ee999bb7a751725e5840d54c3fe\`.
- Exporter SHA: \`15f6055e299ad5b89345e533cc2192f4cc00f659\`.

## Exact statement audit

\`IsClassicalZeta(f)\` requires \`AnalyticOnNhd ℂ f ({1}ᶜ)\` and agreement with \`∑' n, 1/(n+1)^s\` for \`Re(s)>1\`.

\`IndependentRH\` requires every nontrivial zero of **any** such continuation to lie on the real-part-1/2 line. The class is nonvacuous: \`mathlibZetaFits\` proves \`IsClassicalZeta riemannZeta\`. The identity theorem yields \`zetaUnique\` off the pole.

## Meaning of the checks

Lean checks the equivalence proof; con-ron separately checks its exported type/proof dependency closure. Both are only claims relative to their formalized definitions, trusted axioms, exporter completeness, and checker validity. They do **not** verify the massive announced proof of RH.

Lean \`#print axioms\` may under-report imported-inductive axioms in affected releases ([lean4#15226](https://github.com/leanprover/lean4/issues/15226)), so \`audit_axioms.py\` additionally enumerates explicit axiom records in the con-ron-checked NDJSON export. It is a separate cross-check, but still trusts the exporter's dependency-closure construction.

**Next residual:** independently certify the axiom-dependency boundary, then audit the claimant's complete main theorem, not merely its definition.
