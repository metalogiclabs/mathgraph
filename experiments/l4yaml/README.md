# L4YAML grammar-completeness parser-boundary probe

MathGraph public experiment against `nasa-jpl/L4YAML` commit
`16562a74421f94cc0f8216eecf21f1ff58166fa7`.

## Problem

The remaining capstone is the converse needed for:

```lean
(∃ docs, parseYaml input = .ok docs) ↔ InYamlLanguage input
```

Upstream has already removed `directiveDrop`. The remaining
`SLYamlStream.scannerDrop` exists because `scan_strict_proof` is asked to
turn *scanner success alone* into whole-YAML surface grammar evidence.

But the scanner intentionally accepts/tokenizes some inputs that the parser
rejects, including adjacent flow entries without required separators.

## Hypothesis

The proof boundary is one layer too early.

Keep scanner evidence lexical. For exact YAML membership, consume both:

```
scanFiltered input = .ok tokens
parseStream tokens = .ok docs
```

Those witnesses are already available from every successful `parseYaml`
through `parseYamlRaw_ok_decompose`; current `parse_strict_proof` extracts
both and discards the `parseStream` witness.

## Decisive probe

`ParserBoundaryProbe.lean` kernel-checks the executable separator:

* `[[a][b]]`: scan yes / parse no
* `[[a]b]`: scan yes / parse no
* `["a""b"]`: scan yes / parse no
* `{a: b: c}`: scan yes / parse no
* `[a,b]`: scan yes / parse yes

It also proves that every full parse success retains the
`scanFiltered + parseStream` witness.

The second theorem goes one step farther: once a flow sequence already contains
an item, any successful parser-loop result that grows the item array must have
crossed an explicit `flowEntry` token. This identifies parser success as the
missing adjacency distinction that `scannerDrop` currently hides.

## Interpretation

This rejects the design assumption that the scanner itself should be
strengthened into an exact syntax recognizer. The next proof object should be a
parser-guided surface reconstruction, with parser transitions providing the
missing flow adjacency/separator structure and existing scanner `*_prod`
lemmas providing character-span witnesses.

This is an architectural experiment, not yet the final `parse_iff_grammar`
proof.

## Lineage

The first public reproduction ran green in `heathsanchez/test`:
https://github.com/heathsanchez/test/actions/runs/36361994375

This MathGraph branch is the canonical continuation of that experiment.

## Qualification

This branch replays the pinned L4YAML build and kernel-check on Metalogic Labs infrastructure.
