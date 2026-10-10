# L4YAML independent corpus normalization: exact-source V2

The first real compiled JPL parser run completed with 47/48 agreement against
the public yaml-test-suite test metadata. The sole discrepancy was test
26DV:0. The upstream descriptor uses U+2423 visible-space glyphs as a
serialization convention, which MathGraph's first importer mistakenly sent
to the parser verbatim. This is a MathGraph **input adapter** error, not
evidence of a JPL parser conformance bug.

The published yaml/yaml-test-suite/ReadMe.md explicitly defines the
visible-space marker. The existing JPL Tests/SuiteRunner/Meta.lean also
implements that decoding. Independent PyYAML accepts the decoded 26DV input
and rejects the original unconverted visible-glyph form.

V2 freezes the original 48 selected inputs from
yaml/yaml-test-suite@da267a5c4782e7361e82889e76c0dc7df0e1e870.
Precisely one selected input requires source decoding, 26DV:0.
The decoder is deliberately scoped to U+2423 visible spaces only; other
visible marker types must earn separate contracts and return UNKNOWN here.

Instead of rebuilding the full 487-task JPL package for this correction, CI
compiles the actual L4YAML.Parser.Composition at
nasa-jpl/L4YAML@62bf7077910e888a0bc8adfc8e08a5f500ff3ca3
with its original Lean 4.34.0 toolchain. It generates and evaluates 48 native
Lean #guard assertions over the actual TokenParser.parseYaml function and
the 31 expected accepts / 17 expected rejects from the third-party corpus.
Four further #guards check the previously unconverted 26DV rejection, current
self-recursive anchor rejection, valid sibling alias and undefined alias
rejection.

A green result qualifies the executable Lean *function* on that exact
finite corpus; it is not a general theorem about YAML semantics, not a
machine certification of source-to-event extraction, and not a public
MathGraph badge. V1's independently built tryparse CLI evidence remains
separate; the two verification environments must not be conflated.

No changes, issues, PRs, comments, tags, review requests or messages are
sent to JPL or Nicolas Rouquette.
