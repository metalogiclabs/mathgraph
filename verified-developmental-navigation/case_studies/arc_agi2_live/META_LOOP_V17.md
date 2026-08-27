# V17 meta-loop result

The guarded parser portal preserves the previously admitted V13 behavior: `d35bdbdc` remains an exact demonstration fit. It adds no held-out solve.

This establishes the operational distinction between **syntactic inclusion** and **semantic conservativity**. V16 contained the old parser states but changed downstream graph behavior and destroyed the old capability. V17 instead dispatches to the old semantics unchanged whenever the old representation is defined, and only invokes the extension outside that domain.

Current residual splits into two cases:

1. **Old representation undefined**: extend the observation/parser portal.
2. **Old representation defined but verifier fails**: keep the parser and refine relation/action policy.

The next deciding experiment should target case 2 on `d35bdbdc`: identify which symbolic composition edges are selected by the demonstrations before adding any further action family.
