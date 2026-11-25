# Prospective integer-preservation transfer: completed, no demonstrated detection advantage
26 November 2026 (New Zealand).

## Result and verification boundary

The method was frozen before selected implementation bodies were inspected or executed. It ran unchanged against all three Python implementations named in the external CBOR registry. On this finite workload, its defect-detection outcome ties an equally informed ordinary Hypothesis test. No real defect was found.

| Published distribution | Candidate probes | Hypothesis probes | Real value discrepancies, either arm | Independent scalar labels |
|---|---:|---:|---:|---:|
| cbor2 6.3.0 | 5,000 / 5,000 agree | 5,000 / 5,000 agree | 0 | 16 / 16 agree |
| Flynn 1.0.0b2 | 5,000 / 5,000 agree | 5,000 / 5,000 agree | 0 | 16 / 16 agree |
| Flunn 1.0.0 | 5,000 / 5,000 agree | 5,000 / 5,000 agree | 0 | 16 / 16 agree |

All selected targets installed and passed the frozen API admission controls. No target, API adapter, generator, property, budget or expected value was changed after source exposure. All original package source hashes remained stable.

Flynn and Flunn share fork lineage, so these are three distributions in two implementation families, not three independent source families. Seeds share fixed boundary prefixes; 30,000 calls are not 30,000 independent discoveries. The 48 external checks reuse 16 published vectors across three distributions.

**WARRANTED / REUSABLE within this boundary:** a fixed automatic constructor can exercise a supplied numeric-preservation contract on fresh implementations without per-target source repairs, with exact artifacts, ordinary-baseline comparison and fresh native replay.

**Comparative finding: TIE on observed discrepancy detection.** Both methods detected the separate synthetic float-intermediate control on their first native probe for each distribution. Those six outcomes validate apparatus sensitivity to the already exposed class; they are not real upstream defects or new discoveries.

**UNKNOWN:** false-negative rate on real defects, broad false-positive rate, autonomous semantic-requirement acquisition, genuine blind discovery, economic advantage and commercial demand. No independent human evaluator or exclusion of model-training exposure is established. The 16 public integer-vector cases were not used as expected-value inputs to the detector; this is a prospective source-transfer experiment, not the externally blinded L4YAML trial in #288.

## Frozen method, external targets and labels

[Method freeze 700bb8ad8c0809a370553d241fc9c3503b412aeb](https://github.com/metalogiclabs/mathgraph/commit/700bb8ad8c0809a370553d241fc9c3503b412aeb) includes every constructor, ordinary baseline, selection rule, evaluator, nine apparatus tests and PROTOCOL.md before selected implementation execution.

[Native qualification 45721842847](https://github.com/metalogiclabs/mathgraph/actions/runs/45721842847) completed both jobs:
1. Validate apparatus, resolve the externally curated registry, freeze versions/release hashes and upload selection receipts.
2. Verify the unchanged method, install the exact selected distributions, execute both arms, seal predictions, then evaluate independently authored expected values.

Target pool authority: [CBOR implementation registry, Python section](https://cbor.io/impls.html). The selector takes all three named Python entries and checks the observed section shape. The API names and registry were exposed during construction; target implementation bodies, defect histories and outputs were not. Selection is reproducible external-registry coverage; the rule and adapters are investigator-authored. Published versions and exact archives, rather than repository HEADs, identify the executed source.

The supplied mathematical requirement comes from [RFC 8949 section 3.1](https://www.rfc-editor.org/rfc/rfc8949.html#section-3.1): core unsigned and negative integer values, including their use inside definite arrays and integer-key maps. This is not automatic extraction of a new requirement.

Independent labels: [cbor/test-vectors at aba89b653e484bc8573c22f3ff35641d79dfd8c1](https://github.com/cbor/test-vectors/tree/aba89b653e484bc8573c22f3ff35641d79dfd8c1), appendix_a.json SHA-256 80e78dc2f53cfdc9836094791d09e84c6818edf380f7cdd4be26a5c2dc4e9f3a. The preparation stage exports only encoded scalar-integer inputs to the probes. The expected fields are consumed by the separate evaluator after predictions are sealed at SHA-256 b161ce8c9e0e466b17f0c4a364eff3e026d809b62e191d068601ae608a5431bf.

The independent labels agree with the frozen reference on all 16 admitted vectors. Native outputs agree with all 48 executions; there are zero alarms and zero refusals in that labelled cohort. This gives no empirical estimate of sensitivity to real defects.

Exact target input archives, authorized by the frozen PyPI release metadata:
- cbor2 6.3.0: 4f160b662059cc30ced4436fca332f4c27d0259698a5bde8373c9c6f829aabdf.
- Flynn 1.0.0b2: bb0004e3f6924b3148e3b537988356875c669fb502696fb2f5e366d7297b02d2.
- Flunn 1.0.0: 07678da9b286415b3e8c79d7b75c48bbc30b95d2255589d2482b1b9f0dee44c3.

Hypothesis 6.170.17 received the same full integer range, the same container shapes, the same boundary set, and the known 2^53+1 example. Five fixed seeds were used, alternating arm order. Failures could shrink and every actual call was charged. The candidate uses a conventional fixed-boundary/random loop; no special MathGraph kernel operation is invoked.

## Measured effort and limits

Median seconds for a fresh process, including package import, engine setup and output:

| Distribution | Fixed constructor | Informed Hypothesis |
|---|---:|---:|
| cbor2 | 0.101756 | 0.856893 |
| Flynn | 0.110094 | 0.872142 |
| Flunn | 0.110885 | 0.880423 |

These are measurements of different generators with matched nominal call budgets. They do not establish an economic advantage or equivalent search coverage. Across five seeds the fixed constructor exercised 2,496 distinct encoded inputs per distribution, versus Hypothesis's 3,935. Hypothesis includes general generation and failure-shrinking machinery. A competent ordinary fixed test loop can run the candidate corpus directly; this experiment does not show a unique MathGraph-specific speed mechanism.

Shared metadata preparation: 0.506 seconds. Common Hypothesis/dependency installation: 3.175 seconds. Target installations: cbor2 0.684 seconds, Flynn 2.633 seconds, Flunn 2.428 seconds. Whole native runner: 24.888 seconds, including dependency acquisition, original/control lanes, source copies and prediction sealing; it excludes CI provisioning, later evaluation and the investigator's construction work.

Original hosted execution made 30,306 actual target-decoder calls: 30,000 original probes, six synthetic-control probes, 252 admission calls and 48 external-vector calls. These roles are preserved separately. Human/LLM protocol construction, requirement acquisition and monetary costs were not fully measured, so full economic advantage remains UNKNOWN.

## Independent audit and native replay

Both provider archives were independently downloaded and matched their upload SHA-256 digests; ZIP integrity passed. All 118 native manifest entries passed. The exact frozen method hashes match the committed local source. Installed archive hashes match the selection metadata, installed module/native-extension bytes match the source snapshots, and prediction/label hashes agree.

A separately authored post-result auditor does not import the frozen constructor, reference reader or judge. It reconstructs mathematical expectations directly from raw CBOR bytes using integer byte operations, checks all 30,000 original observations and six injected observations, and independently checks all 48 external labels.

It then imports the actual preserved implementation bytes into fresh processes on another host (Python 3.12.14 versus hosted 3.12.16) and repeats all original cases plus the external vectors. Native replay: **10,016 / 10,016 per distribution; 30,048 / 30,048 total**. These are verification repeats of existing inputs, not extra discoveries or a change to the frozen comparative budget.

The auditor is saved at experiments/evidence-audits/precision_transfer_20261126.py. With the evidence bundle extracted, run it with --root pointing to the bundle directory. It verifies observations, source identities and fresh native executions. This is separate-process/implementation verification within the same authored investigation, not external peer review.

Raw artifacts:
- [Source freeze](https://github.com/metalogiclabs/mathgraph/actions/runs/45721842847/artifacts/15072098554): SHA-256 ef7bd33e0517800f9dc54914f4b0b44cab27e31c2375777faf27ee04a7dfb836.
- [Native observations and costs](https://github.com/metalogiclabs/mathgraph/actions/runs/45721842847/artifacts/15071923349): SHA-256 7185c8edb8003ddb52f9ea14d9d70af782056cb368e9ae302cc0c9c92d8aff7f.

## Residual and reuse

The narrow automation transfers. This trial provides no new upstream defect and no defect-finding advantage over the informed property-testing comparator. Stop at the frozen budget; do not switch targets until a positive result appears.

The remaining product residual is obtaining the right independently warranted contract and applicability boundary with less total work than ordinary engineering, then showing benefit on an externally labelled corpus containing real positive defects. A next experiment must freeze that positive/negative corpus and the complete acquisition cost budget before source exposure. More clean integer loops alone will not resolve this residual.

The prior OpenC3 calibration remains warranted separately. Existing L4YAML blind-transfer PR #288 remains NOT_RUN. No production branch, upstream source, issue, PR, email or outreach was changed or submitted by this trial.
