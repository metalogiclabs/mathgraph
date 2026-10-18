# PKC V5: full source-native SysML text → OpenSysML API JSON → Lean ingest

## Predeclared scope (before any V5 converter result)

- Source: `nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824`
- Toolchain: exact repo `leanprover/lean4:v4.34.0` and pinned locked dependencies
- External converter: [Open-MBEE/OpenSysML v0.9.1](https://github.com/Open-MBEE/OpenSysML/releases/tag/v0.9.1),
  released 30 September 2026; verify Linux binary with published `SHA256SUMS.txt`
- Prior real importer scientific warrant: [V4 native 13-case audit #39176658515](https://github.com/metalogiclabs/mathgraph/actions/runs/39176658515)
- NEW gate: must qualify **actual external SysML notation conversion**, previously not executed.

The two cases are the exact V4 `no_statement` and `false_statement`
`PkcModel` pivot records, emitted by the real JPL `EmitSysml.emit` into
`.sysml` files. The CLI parses each model alongside its real
`sysml/PKC.sysml` DSL and converts to `api-json`. The JPL
`scripts/ingest-sysml.sh` then invokes the same converter, real
`ApiJson.read`, `Harvest.unverifiedCitations`, emits generated Lean,
and kernel-checks the result. No mocked parser, no hand-substituted
converter output, no JPL repository modifications.

## Frozen hypotheses and controls

1. Valid statement-free citation: OpenSysML validates model; actual converted
   JSON contains the cited declaration; native JPL ingest succeeds.
2. Contradictory `@Checked.statement = "False"`: OpenSysML validates text and
   preserves the value in element JSON; the **original** PKC importer still
   succeeds and emits a generated `-- checked: ... — False` comment without
   proving `False`.
3. Apply the exact one-site fail-closed policy from V4 in ephemeral target
   checkout, build; **strict** importer continues to accept statement-free
   model and rejects the `False` model for the precise unchecked-text reason.
4. Physically withdraw the one-site policy, rebuild, show that full SysML
   `False` path is accepted again.
5. If OpenSysML rejects this input, drops metadata, or loses source identity,
   **do not call this an importer refutation**. Report `CONVERTER_BOUNDARY`
   and preserve original output and errors; the V4 API result remains intact.
6. Unexpected build/dependency/tool errors are `UNKNOWN_APPARATUS`, not
   scientific negatives. No hand adjustment of the SysML text after opening
   outcomes. No additional test cases or version changes to force a positive.

## Mandatory frozen evidence

- Exact `sysml --version` and release archive checksum from authoritative release manifest
- Source pin SHA and code hashes
- Full emitted SysML text and converter-produced API JSON on both cases
- Original, strict and withdrawn real ingest exit vectors and causal rejection reasons
- Generated original Lean file with `False` only in unverified metadata/comment
- Dependency and Lean build results; artifact hash and no JPL source changes

## Claim bounds

A PASS establishes a **small, concrete whole-text-to-Lean claim-boundary
witness**, not a general property of arbitrary SysML models, not all PKC
theorems, not a numerical correctness claim, and not Lean proving `False`.

This V5 is **source-aware**. Human-designed controls use previously known
V3/V4 source metadata. No blind general method transfer or productivity
multiplier claim is made.

No NASA/JPL writes, upstream PR or unsolicited external contact.
