# Semantic assurance comparator — retrospective calibration

## Question and boundaries

Can independent, requirement-specific evidence distinguish real historical faults that structural acceptance and conventional quality gates do not? These five public merged cases are known to the investigator. This is **not** blind discovery, autonomous MathGraph Check, or evidence of superiority over Sonar. MathGraph Check #285 retains fixed L4YAML profiles; #288 preregisters a genuinely blind follow-up. Do not substitute these cases for that follow-up.

Freeze the following source identities and requirements before further comparative execution. For each arm execute the same pre-repair tests, a direct independently specified oracle with compatibility/refusal controls, and an actual supported static-analysis configuration. Record raw statuses, exact source/tool versions, oracle and test hashes, costs and all findings. For a historical defect the static-analysis outcome is UNKNOWN until reviewed actual findings establish detection or no relevant finding. An unrelated warning or a green quality gate does not settle the requirement. Unsupported languages and infrastructure failures are UNKNOWN. An equally informed direct oracle is a required comparator, not a disadvantaged straw man. Any later reusable MathGraph implementation must improve cost, automation, scope transfer, or evidence integrity over that direct oracle. Holdout selection and independent labels must be external to the investigator and frozen before evaluation.

| Case | Before | After (upstream merge) | Obligation |
|---|---|---|---|
| [OpenC3 #4433](https://github.com/OpenC3/cosmos/pull/4433) | 791b3492ed8d6a7f39bd240837fc601ac491278e | 774c3ad3109f7caa7875ba420b632bf4b8296e32 | exact signed/unsigned integer identity, scalar and arrays |
| [ONNX #8791](https://github.com/onnx/onnx/pull/8791) | 290eaba8185c0ed1ba6abda16f6f16d562a42da5 | 366620ca097ed2dff8f76b50f264dd592d9edc9b | Hardmax 12→13 output equivalence with independent v12 oracle; structural checker separate |
| [Nyx #615](https://github.com/nyx-space/nyx/pull/615) | 09ab47dd4233ad3b80efc64479bf5339739b5570 | 71e31c137bfe2fea641a21455febb84c936fc409 | selected reference-frame identity, mixed-frame rejection, homogeneous physical round trip |
| [L4YAML #290](https://github.com/nasa-jpl/L4YAML/pull/290) | 218b41c974027f7433e6b0c369789a38e50b3740 | 171aa7a34917ce318f13a3c79f71fe675ad1cfbe | embedded-NUL byte identity across native C/Python boundary |
| [OpenMDAO #3848](https://github.com/OpenMDAO/OpenMDAO/pull/3848) | 64175aa55fb541355b2fb279a6bcfde01e17a878 | a3209e27dddbfe4eaaeba580163294f042097b04 | negative source indices equivalent to positive indices; assembled derivative and independent analytic oracle |

## First completed local result (2026-11-26 NZ)

Python accessor source blobs verified against both upstream Git identities, before 97c3f9bd2401532bd2bc11db5af54e0dd8a560b4 and after a541c9c574994fa41e4d9681fffb00ab3fae5278. The exact AST is executed except an unused ConfigParser import; no production body changed. No native JSON or packet test claimed from this isolated run. A deterministic seeded boundary/random cohort is selected for sensitivity, not a representative sample or blind holdout.

| Family | Total | Structural before | Exact before | Structural after | Exact after |
|---|---:|---:|---:|---:|---:|
| Precision probes | 422 | 422 | 0 | 422 | 422 |
| Exact controls | 53 | 53 | 53 | 53 | 53 |
| Compatibility controls | 32 | 32 | 32 | 32 | 32 |
| Rejection controls | 12 | 12 | 12 | 12 | 12 |
| Total | 519 | 519 | 97 | 519 | 519 |

Structural means declared integer return type and array length or expected error, not an existing test suite or a Sonar finding. All 97 controls agree on both arms. Precision-probe rows are dependent representations, not 422 independent bugs. Local probe SHA256 628cacc8674dadd89f4d9fc8a58885d1ddb8d536156facc5422e75b53cdadda8; full local JSON SHA256 95d67a7401e3fc66899f0f8ca4841d716b89603c48db037fec3be9097b1c34a8. Original source SHA256 81ecc06abd74d2ad81b215c8deae578bb504ba99b880ae5824c9418c89edd414; repaired dfaec2285267e158728dc05145baa7a1b5a8ed5ac22763f28fb24d0e64b85ee0.

Previous independent native baseline run [45333931446](https://github.com/metalogiclabs/mathgraph/actions/runs/45333931446) succeeded on a different pinned revision with the same accessor blob. Preserve its native evidence separately. New exact-pair native test replay and SonarQube Community Build scan are pending; SonarCloud, Sonar commercial editions, AI agents, and general tool comparisons are explicitly outside this initial scan. No superiority claim. Remaining four arms are CANDIDATE / NOT_RUN for this comparative experiment despite historical merged PR evidence.

## Hosted gate
The isolated workflow fetches exact revisions, validates blob hashes, replays the standalone probe, compares the two original accessor test modules against both source trees, then compares the merged versions of those tests against both. The static job scans each entire public Python package with the same server/default profile, captures analyzer versions, image digests, raw scans and issue pages, and captures the quality gate separately (first-analysis new-code gate is not a claim of precision). No cloud credentials or production changes. Scanner tag is resolved to a digest at execution and retained; future reproduction should use that digest. No comparative verdict until raw results are independently reviewed. All work remains on an isolated branch.
