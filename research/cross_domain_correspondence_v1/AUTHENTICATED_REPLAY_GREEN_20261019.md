# Cross-domain authenticated historical replay — CI GREEN

Status: **WARRANTED_BOUNDED_AUTHENTICATED_HISTORICAL_REPLAY**; native source-change requalification **UNKNOWN**.

Frozen protocol commit: `9c8b427c679398fd80ea56d9a91a1627b2e96b6d` (verified unchanged using independently checked-out SHA).
Implementation commit: `52f705440c99f7c12e760f796cd56ff9fd76675a`.

**Successful job and archive**
- https://github.com/metalogiclabs/mathgraph/actions/runs/39192207386
- https://github.com/metalogiclabs/mathgraph/actions/runs/39192207386/artifacts/12160585927
- Archive digest: `sha256:872001d926a39b65447db55dce4a7328c28ac7a762f73d71198a0c327b765ae2`.

**Direct observations from completed job:** archived PKC and YAML artifacts downloaded, SHA256 matched GitHub artifact digests, frozen protocol compared with independent checkout, historical PKC verification script completed, updated L4YAML independent verifier completed, cross-domain receipt evaluator completed, and receipt artifact uploaded. All job steps succeeded.

PKC original: `e0deb453e05ffa63297d9704ceb47d0855193824`, artifact `12155725060`, `sha256:8546dfc16783f8243329883e12b7a11f49b6d0c7a3634aaa5293e6c32613cbc6`.
L4YAML original: `fdef03caf19e8862792034793da11020b39d6110`, artifact `12156807544`, `sha256:dbe762c882a78e6e49889a7b81d4cd211e6e52dbc17f506fac420bce4e7f298b`.
L4YAML evaluator source was upgraded to previously qualified verifier source `e48f094fa400c77ab07404645f6e12cfba7ebf45` due to earlier version not supporting `--upstream-sha`; underlying original native source SHA and original logs remained pinned.

**Measured:** protocol applied to both independently verified historical receipts and four selective withdrawal scenarios succeeded. Historical outcomes included P1 warranted only for declaration validity, P2 rejected for statement correspondence, P3 unknown, Y1 unknown, Y2 rejected for typed interchange collision, Y3 unknown. The evaluator's withdrawn authorities changed exactly the dependent verdict set.

**Not established:** fresh upstream native source execution under mutation, M5 source restoration and verifier replay, positive repaired L4YAML, a semantic relation-discovery engine, full native comparator, or general law. Do not call these warranted or reuse this receipt as proof of source-change requalification.

The next decisive experiment is a native source mutation and fresh native verifier replay in one source domain; reuse the same frozen protocol and verify that only the corresponding authority-dependent claims lose warrant.
