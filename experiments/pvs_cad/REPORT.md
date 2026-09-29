# pvs_cad semantic-boundary audit

Pinned upstream: `j-tanner-slagel/pvs_cad@8750362e99c2ba0e9a0307dcaa39b9766c562feb`.

Objective: independently attack the reflection/specification boundary named by the author: whether the verified `decide5 ↔ fsem` result is connected to the PVS formula the user intended.

This branch does not modify upstream and does not open a PR.

The audit suite covers ordinary controls, zero/degenerate polynomials, repeated roots, strict boundaries, user definitions, quantifier alternation/renaming, variable-dependent division as an out-of-fragment canary, and shared non-polynomial terms for `(cad *)` abstraction.

Epistemic rule: a green run warrants only the tested boundary families. It is not evidence that every possible PVS surface form is covered. A red run is inspected and minimized before being classified as a semantic failure.
