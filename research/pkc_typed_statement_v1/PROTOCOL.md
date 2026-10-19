# PKC V6 — first typed nonempty statement-to-kernel-type correspondence

**Frozen before V6 execution. CANDIDATE, never upstream/JPL semantics.**

## Existing authorities / reused native fixtures

- Original NASA/JPL PKC: `nasa-jpl/PropertyKindCalculus@e0deb453e05ffa63297d9704ceb47d0855193824` with source-locked Lean 4.34.
- Existing verified V5 fixture generator, source scripts and source emitters: `metalogiclabs/mathgraph@4691ae2de91958d5a366f636b4a329a938b76116`; native original [V5 #39177893785](https://github.com/metalogiclabs/mathgraph/actions/runs/39177893785).
- Real OpenSysML v0.9.1 external release, checksum-matched against publisher manifest; real `scripts/ingest-sysml.sh` and native Lean checker.
- Independent V6 statement interpreter: **not** the upstream importer. A deliberately bounded typed language `PKC:Edge(X,Y)` with tokens `width`, `length`, `height`, interpreting each as the named *original* PKC `Iso80000.Part3` kind, and the edge relation as the original `Iso80000.Part3.Edge`. `False` maps to the actual Lean `False` proposition; arbitrary text is unsupported. The interpreter is human-authored, fixed before outcomes. It is not natural-language autoformalization or arbitrary Lean string evaluation.

## Frozen native case matrix

All cases use one authentic SysML source-generated model. Exactly one `statement` field and, where specified, the `decl` string is changed as the SysML *input data* before external conversion. No upstream source code changed.

| case | author statement | cited original PKC declaration | expected interpreter result |
|---|---|---|---|
| typed_match | `PKC:Edge(width,length)` | `...Edge.width_length` | MATCH to actual kernel proposition type |
| false_mismatch | `False` | `...Edge.width_length` | MISMATCH |
| typed_mismatch | `PKC:Edge(width,height)` | `...Edge.width_length` | MISMATCH |
| wrong_citation | `PKC:Edge(width,length)` | `...Edge.height_length` | MISMATCH even though cited declaration is valid |
| unsupported | `The width is a length` | `...Edge.width_length` | UNKNOWN_UNSUPPORTED |
| true_unsupported | `True` | `...Edge.width_length` | UNKNOWN_UNSUPPORTED, even though True is provable |
| no_statement | optional statement absent | `...Edge.width_length` | NO_ASSERTION |

Native ORIGINAL JPL importer should accept all seven as citations (if OpenSysML and native importer are functioning). This *does not* qualify attributed statements. The added **independent** bounded type checker reads original converter-produced API JSON with the original JPL parser, retrieves actual declaration types from the pinned Lean environment and compares a typed proposition using `Lean.Meta.isDefEq`. It must emit exactly the frozen 7-case decision vector and disallow changed citations, missing declarations, malformed metadata and fallback to raw string equality.

A `#check`/Lean-compiled `width_length` witness and the official declaration type provide kernel-native positive evidence in the frozen context. A mere substring or matching declaration name is not a valid witness.

## Promotion boundary

If full native path, Lean Meta type comparisons, independent output verifier and pin controls pass at exact commit: **WARRANTED_BOUNDED_POSITIVE_NONEMPTY_TYPED_PKCSOURCE_STATEMENT_CORRESPONDENCE** for this constructed, explicitly interpreted grammar on these original objects only. User-provided optional strings remain commentary as far as the *current JPL importer* is concerned. Author's intended `@Checked.statement` contract stays UNKNOWN. Current source is not changed. Broader semantically equivalent alternative propositions, arbitrary statements and newly changed declaration types remain UNKNOWN until new native evidence.

If the original importer does not accept a variant, return source-native failure or CONVERTER_BOUNDARY; do not silently replace with fixture JSON, retune syntax, or remove the case after seeing failures. Failed builds are apparatus/UNKNOWN, not semantic counterexamples. Results are intended for private coauthor-side research, not an unsolicited JPL communication or paper endorsement.
