# L4YAML V8 — physical scalar-style policy intervention and source-native requalification

**Pre-registered CANDIDATE, not an upstream repair.** This is the second independent domain under MathGraph's unchanged `cross_domain_correspondence_v1/protocol.py`.

## Original authorities
- Exact JPL source `nasa-jpl/L4YAML@fdef03caf19e8862792034793da11020b39d6110`, Lean 4.34.0, `L4YAML/Output/Dump.lean` original blob `e6495cba339246b1954f3d4be9dd286a564cb4c0`.
- Frozen original 2026-10-19 [source-native RED #39183206058](https://github.com/metalogiclabs/mathgraph/actions/runs/39183206058), original evidence artifact #12156807544 digest `dbe762c882a78e6e49889a7b81d4cd211e6e52dbc17f506fac420bce4e7f298b`. Freeze original independent [Probe.lean](https://github.com/metalogiclabs/mathgraph/blob/03f8b16d24f4641483f7b3cc1004812dfefb4dbc/research/l4yaml_schema_style_v1/Probe.lean), blob `81659ba21ccfdf6e1a43879c2318a8010f58ae55`, and [analyze.py](https://github.com/metalogiclabs/mathgraph/blob/03f8b16d24f4641483f7b3cc1004812dfefb4dbc/research/l4yaml_schema_style_v1/analyze.py), blob `1e701edbfac8ef6cd6f2b92dac28d6bc6639e7e2`.
- Two independent external readers fixed at `ruamel.yaml==0.18.17` (YAML1.2 safe) and `PyYAML==6.0.3` (shared Core Schema cases); reuse the original independent comparison algorithm **byte-for-byte**, not a new general YAML oracle.
- Do not modify the Lean probe, observer, YAML schema, or frozen core warrant engine.

## Exact physical source mutation

One line of an ephemeral checkout of JPL `L4YAML/Output/Dump.lean`:

```diff
-  allowReservedPlain : Bool := false
+  allowReservedPlain : Bool := true
```

This changes only the **default dump presentation policy**, not the meaning of source typed values or the input test corpus. It is intentionally a *nonrepair*, expected to make some external interpretations better and another worse.

## Pre-committed three-lane observation vector

| case | BASE | MUTANT | RESTORED |
|---|---|---|---|
| Native 7 known semantic-preservation checks | 7 FALSE | 7 FALSE | 7 FALSE |
| Native 4 ordinary controls | 4 TRUE | 4 TRUE | 4 TRUE |
| External bool `true` remains Boolean in both readers | FALSE | TRUE | FALSE |
| External optional `none` remains YAML null in both | FALSE | TRUE | FALSE |
| External struct `qNone.x` remains YAML null in both | FALSE | TRUE | FALSE |
| External struct `qStringNull.x` remains string `"null"` in both | TRUE | FALSE | TRUE |

Expected source-native raw dumps:
- BASE/RESTORED: `DUMP:true="true"`, `DUMP:none="null"`, `DUMP:qNone=x: "null"`, `DUMP:qStringNull=x: "null"`.
- MUTANT: `DUMP:true=true`, `DUMP:none=null`, `DUMP:qNone=x: null`, `DUMP:qStringNull=x: null`.

The existing original-red gate must pass in BASE and RESTORED, and **reject MUTANT** rather than falsely admit the altered result as the original negative vector. MUTANT cannot count as fixed-GREEN: the original native 7 deficits are still present and the previously valid `qStringNull` external interpretation is now broken.

## Evidence sequence and warrant semantics

1. Check original Git revision, exact blob and toolchain; source-native build `L4YAML.Schema.Api L4YAML.Schema.Deriving L4YAML.Output.Dump` and replay unchanged original Lean probe; independently interpret exact dumped YAML using both frozen readers.
2. Physically mutate only that one source line, hash the edited blob, **rebuild original Lean module**, replay exactly same source-native probe; independent external-reader decision matrix must match the frozen predicted reversal without retuning.
3. Physically restore the original one-line source, verify byte-exact original file and clean diff, rebuild, replay; all raw and reader observables must return to BASE.
4. Apply unchanged `cross_domain_correspondence_v1/protocol.py`: changing full source rev invalidates previous source-bound warrants until native replay, then four external semantic consequences requalify or reverse while parser-native checks remain stable. Withdrawing specifically dump-style authority invalidates only dump-meaning claims, not independent native parse controls; withdrawing an external reader invalidates dependent YAML-schema interpretation claims, not Lean parse checks.
5. Preserve source diff, hashes, raw logs, reader versions, unchanged observer identities, all three compiled native source results, warrant lineage, success and any negative apparatus lineage.

**GREEN claim only:** `WARRANTED_BOUNDED_CROSS_DOMAIN_PHYSICAL_CHANGE_SENSITIVE_REQUALIFICATION` for two already-known, human-interpreted source families (PKC V7 + this L4YAML V8). Does not establish a fixed YAML implementation, all-schema YAML 1.2 correctness, arbitrary input semantic acquisition, autonomous invention of new observation grammar, or superiority over equally informed bespoke comparators. No JPL writes, contact, claimed endorsement, or production merge.
