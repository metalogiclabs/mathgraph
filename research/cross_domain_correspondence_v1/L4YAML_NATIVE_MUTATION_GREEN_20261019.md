# Native source-change and restoration qualification — 2026-10-19

**WARRANTED_BOUNDED: L4YAML controlled source mutation and native recovery, with independent YAML semantic witness.**

GitHub Actions GREEN: https://github.com/metalogiclabs/mathgraph/actions/runs/39192635360

Raw artifact: https://github.com/metalogiclabs/mathgraph/actions/runs/39192635360/artifacts/12160483329

Archive digest: `sha256:6b842e6e247251fa36a530bb8af3372d133415652cd1e7622ef580d00ef7002d`.

## Frozen original
- `nasa-jpl/L4YAML@fdef03caf19e8862792034793da11020b39d6110`
- Lean 4.34 source toolchain
- Original probe: `research/l4yaml_schema_style_v1/Probe.lean`
- Frozen general protocol stays unchanged at `9c8b427c679398fd80ea56d9a91a1627b2e96b6d`.

## Intervention
Temporary checkout only, source `L4YAML/Output/Dump.lean`: uniquely replace `allowReservedPlain : Bool := false` with `allowReservedPlain : Bool := true`. The exact patch and checksum are archived. Rebuild relevant native Lean modules and execute unchanged native probe. Restore the pinned file using `git restore --source=fdef03c...`, assert clean diff, rebuild and run probe again.

## Observed result
The independent YAML 1.2 consumer changes its reading of exactly `none`, `qNone`, `qStringNull`, and `true`, as expected. Their original emitted semantics were strings, the mutation emits null/bool semantics as applicable. The mutation **does not repair** the equality/collision of `qNone` and `qStringNull`. All 11 native CHECK booleans remained unchanged. Source restoration reproduced the original CHECKs, dumps, and independent reader semantics.

All CI stages completed successfully. The final marker was:
`NATIVE_SOURCE_MUTATION_AND_RESTORATION_VERIFIED ['none', 'qNone', 'qStringNull', 'true']`.

## Boundaries and next experiment
This verifies causal response to an isolated policy edit and replay after source restoration, **not** selective warrant graph retraction automatically triggered by observed native digest changes. The observer verifies concrete semantic outcomes, while the previously qualified protocol has a separate dependency withdrawal test. Connect these via receipt-driven fingerprint comparison, fail closed on a changed source and restore warrant only after actual matching native re-verification. That is the cheapest unresolved integration.

The more ambitious general transfer claim and unsolicited interpretation discovery remain UNKNOWN.
