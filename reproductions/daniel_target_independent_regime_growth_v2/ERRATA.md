# V2 audit errata — superseded by repair

An external adversarial audit identified two code-level presentation/control weaknesses in the first merged V2 implementation:

1. `unary_sham_preserves_base_partition()` was vacuous as written: under its `p[2] == q[2]` guard it compared the same truth-table entry to itself. The underlying mathematical claim is true, but that function did not independently test it.
2. The reported “ancestor ablation” was a replay of the same pure base-regime synthesis call, not an independent empirical intervention. For this exact finite model the counterfactual is mathematically valid, but it should be described and implemented as parent-regime reconstruction/replay rather than empirical ablation.

The subsequent repair replaces the sham check with explicit observation-partition comparison and explicit sham-regime synthesis, and replaces the ablation wording/control with reconstruction of the parent regime followed by the unchanged synthesis procedure.

This file is retained so the audit correction is part of the public provenance rather than silently erased.
