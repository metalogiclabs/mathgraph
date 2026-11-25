# OpenC3 COSMOS: numerical identity versus configured Sonar analysis
Date: 26 November 2026 (New Zealand).

## Warranted result

The original accessor changes exact integers through a floating-point intermediate. The pinned repaired accessor preserves all selected exact values. Neither of two tested SonarQube Community Build Python profiles reports that integer precision defect. This is a finite, known-defect retrospective calibration and configured analyzer non-detection result. It is not autonomous MathGraph discovery, a blinded benchmark, a measured advantage over property-based testing, or a claim about all Sonar products.

| Measurement | Original source | Repaired source |
|---|---:|---:|
| Independent exact-behavior cohort | 97/519 | 519/519 |
| Structural acceptance in that cohort | 519/519 | 519/519 |
| Original selected accessor tests | 25 passed | 25 passed |
| Expanded selected accessor tests | 32 methods run: 68 subtest failures, 4 errors | 32 passed |
| Sonar way core: 232 active Python rules | 11 issues; no precision-loss finding | 11 issues; no precision-loss finding |
| Sonar way comprehensive: 407 active Python rules | 844 issues; no precision-loss finding | 844 issues; no precision-loss finding |

The 422 selected precision probes are related representations of this defect, not 422 independently discovered bugs or an estimate of production failure frequency. The other 97 cases are exact-value, compatibility and invalid-input controls. Both revisions pass all 97 controls.

A concrete finite counterexample is the integer 9007199254740993: the original float intermediate maps it to 9007199254740992. The repaired integer path retains 9007199254740993. Correct return type and successful execution do not establish numerical identity.

## Exact sources and execution

Upstream [OpenC3 #4433](https://github.com/OpenC3/cosmos/pull/4433):
- Before commit: 791b3492ed8d6a7f39bd240837fc601ac491278e; accessor Git blob 97c3f9bd2401532bd2bc11db5af54e0dd8a560b4.
- After commit: 774c3ad3109f7caa7875ba420b632bf4b8296e32; accessor Git blob a541c9c574994fa41e4d9681fffb00ab3fae5278.
- Both retain sonar-project.properties blob 92c066210a5ac5967287a6f0fbb3699f13393ebe.
- Probe SHA-256: 628cacc8674dadd89f4d9fc8a58885d1ddb8d536156facc5422e75b53cdadda8.

[Native qualification and default-profile comparison](https://github.com/metalogiclabs/mathgraph/actions/runs/45709621108) ran harness a4c553af44073a1d432d62654c1b724646fb27f7. It uses the original OpenC3 package with its frozen dependency locks and actual test modules test_accessor.py and test_json_accessor.py. The isolated 519-case probe executes the real accessor AST with only its unused ConfigParser import removed; that isolation is not a claim to execute every JSON/packet path. The native tests independently exercise package integration. This is a selected accessor test cohort, not the entire COSMOS regression suite.

[Comprehensive-profile sensitivity comparison](https://github.com/metalogiclabs/mathgraph/actions/runs/45712111737) ran harness a682f29a4a2ea19f50d12bf47e12a2d384496509. This follow-up was frozen after exposure to the default result, before its own comparative execution. It is a separate sensitivity check, not a retrospectively enlarged preregistration.

The same immutable server and scanner images were used in both comparisons:
- SonarQube Community Build 26.11.0.134175: sonarqube@sha256:7b2296713a92b8ea0dd7a083a25faadc59376c9a1e6daf2744a89711c54ea1ba.
- SonarScanner CLI 8.5.0.16571: sonarsource/sonar-scanner-cli@sha256:8bb84373f00346f9a579adb7ccb2999f8cd050ab7167fa9ae08a16069de03c84.
- Python analyzer 5.32.0.37250, implementation build 68fad87bda6064b96dcc3971e287f04a1148432b.
- Both source revisions use the same chosen profile within each pair, Python 3.12 setting, source scope and upstream test configuration. Python analysis logs report 502/502 analyzed files, including configured tests. The source measure reports 273 production files.
- Actual active-rule snapshots, analyzer metadata, complete issue pages, scan logs, compute-engine success and quality-gate outputs are retained.

## Findings review and important counterevidence

The default pair returns the same 11 findings after normalizing project identities, including two findings classified as test-assertion bugs and one permission warning. They are not treated as false positives or evidence of precision detection.

The comprehensive pair returns 844 issues each: 841 code smells, one vulnerability and two bugs. The accessor has exactly two findings on each revision:
- python:S1172: unused item parameter (before line 63, after line 86).
- python:S3776: cognitive complexity 37 versus configured limit 15 (before line 88, after line 111).

Their primary and secondary locations do not identify numerical loss through int(float(...)). All reported rule families and findings touching the accessor were reviewed. The 844 totals alone are not the basis of the non-detection assessment; source-line shifts also mean the comprehensive raw issue sets are not byte-identical. The required semantic obligation was frozen in the protocols before comparison.

The comprehensive run also exports both security-hotspot result sets: zero each. It retrieves each accessor directly from Sonar's indexed-source API and verifies every byte of code against the pinned upstream source. That API appends exactly one terminal LF; both raw SHA-256 values and the disclosed one-LF comparison are retained. No other source difference is accepted.

Every first-analysis quality gate reports OK with an empty conditions array. These are vacuous first-analysis gates, not numerical correctness evidence. The finding exports, active profiles, indexed source and independent numerical observations are the relevant evidence.

## Independent replay and preserved lineage

A separate local replay reproduced the hosted cohort and all returned observations. audit_evidence.py recomputes all 1,038 exactness/structural classifications, verifies source Git blobs and the frozen probe, checks native test exits, complete issue pagination and profile rule counts, source-API comparison, zero hotspot totals and all eight downloaded ZIP digests. This is a separate implementation/process within the same investigation, not external human review.

Final raw evidence:
- [Native artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/45709621108/artifacts/15066043851): SHA-256 b4634256b20dce1709e37b33708bff3791725410d1c28d992ba828fbefbd5eb7.
- [Default Sonar artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/45709621108/artifacts/15067520834): SHA-256 96e16dbfdb459aec5722773ae861c9687b27d6f405d98e2d761f0f30e6f731e9.
- [Comprehensive Sonar artifact](https://github.com/metalogiclabs/mathgraph/actions/runs/45712111737/artifacts/15069040058): SHA-256 c134dee33ab80e89308e999211302c8bea7843f4c5ce2f026c30225a902ec52d.

Preserve the failed apparatus attempts: 45708282432 (all-hex password did not satisfy server policy), 45710441956 (indexed API terminal LF), 45711086622 (removed hotspot projectKey parameter), 45711660711 (unsupported optional metadata endpoint). These do not establish analyzer detection or non-detection. Their raw archives and exact corrections remain in the evidence package and SENSITIVITY_PROTOCOL.md. No test target, numerical expectation or analyzer profile was changed to obtain a desired result.

## Current residual and next experiment

The bounded comparative UNKNOWN has been resolved: neither tested static profile identifies this known precision defect. General MathGraph capability, automation, economics, blind discovery and commercial advantage remain UNKNOWN. A competent requirement-specific unit/property test has access to the same oracle; this experiment gives no evidence that MathGraph is cheaper or stronger than that comparator.

The existing [blind-transfer preregistration #288](https://github.com/metalogiclabs/mathgraph/pull/288) remains CANDIDATE / NOT_RUN and explicitly requires an independent held-out target and hidden labels. The smallest decisive product experiment is an unchanged detector on that independently chosen target, with positive/negative/UNKNOWN outputs, independent replay and full acquisition/verification costs against an equally informed property-testing baseline.

The ONNX, Nyx, L4YAML and OpenMDAO cases in PROTOCOL.md remain source-pinned but not run in this comparative campaign. More retrospective cases can establish breadth; they do not by themselves settle unseen discovery or economic reuse.
