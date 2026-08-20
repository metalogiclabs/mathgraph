# Daniel V4 — relational law synthesis

V3 still supplied `RefinePartition(parent, conflicts)` as the developmental operation. V4 removes that primitive.

The frozen meta-language contains only generic binary-relation objects and operations:

```text
E   current observational equivalence
O   verifier obstruction relation
I   identity relation
U   universal relation

converse(R)
R ∩ S
R ∪ S
R \ S
```

The acquisition protocol was committed before implementation at commit:

```text
71b9ba081c69d5908d79b5005d0e40943c49737b
```

It freezes 129 exhaustive acquisition cases and 13,817 held-out cases with different world sizes, parent geometries, and output arities.

Program synthesis enumerates DSL terms by size, quotients them by acquisition semantics, and asks only which relation equals the verifier-required repair relation on every acquisition case.

Run:

```bash
python reproductions/daniel_relational_law_synthesis_v4/reproduce.py
```

## Claim boundary

A PASS means that a reusable representation-changing law program was synthesized from generic relation operations and transferred unchanged to held-out worlds. It does **not** mean that relational algebra, set difference, search, or minimization was invented.

The key adversarial question is whether synthesizing a short law such as `E \ O` is materially different from having supplied partition refinement extensionally. That interpretation should remain open even if the executable gates pass.
