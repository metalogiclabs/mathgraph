# MathGraph Check — real JPL L4YAML executable versus semantic boundary

## Independent external qualification intent

Work on MathGraph's own branch, without contacting, tagging, commenting on,
opening a PR in, or requesting action from Nicolas Rouquette or upstream JPL
maintainers. Read only public exact source pins.

The first real-world target is not arbitrary parser verification. It is the
specific document-scoped anchor and custom tag handle distinction present
in the merged JPL fix-a-grammar-completeness branch, together with a small
independent YAML 1.2.2 test-suite acceptance sample.

- Upstream reference nasa-jpl/L4YAML@62bf7077910e888a0bc8adfc8e08a5f500ff3ca3
  (this is the merged PR #1 target branch, not the L4YAML default main).
- Toolchain leanprover/lean4:v4.34.0; manifest bytes and original CommitTrace,
  SerializationWellFormed, ExecutableBoundary, and TryParse blob identities are
  checked before any parser execution.
- Independent public test corpus yaml/yaml-test-suite@da267a5c4782e7361e82889e76c0dc7df0e1e870,
  selected deterministically from src files by alias/anchor/directive/tag
  tags, including valid and invalid cases. We parse test metadata with
  PyYAML 6.0.2; its own YAML parse decision is not taken as the oracle.
- The actual tryparse executable is built from the exact original JPL
  repository, run on temporary YAML files, and its exit 0/1 is recorded.
  Crashes/timeouts are explicit unknown execution outcomes, not rejections.

## Separating semantic witness

The independent (restricted) source-event model commits an anchor at node start,
as the YAML spec's normative policy requires. The pinned source's
CommitTrace defines current L4YAML's collection anchor commitment at node
completion. For &x [*x] this yields the decisive distinction:

- start commitment: anchor x exists when *x is used — allowed;
- completion commitment: alias is encountered before x exists — rejected.

The CI imports and checks the exact original Lean lemmas for both, plus
the source theorem factoring actual parseYaml acceptance through its scanner
and token parser. This is independent of the Python policy evaluator; it
does not prove the missing whole-input traversal or exact YAML surface bridge.
Only the fixed templates have explicit source-to-event interpretations; a
general extraction algorithm remains UNKNOWN.

## Additional controls

Self-referential collections, later sibling aliases, undefined and mutated
alias names, cross-document alias isolation, TAG declarations and missing
handles, tag-handle reset, and quoted/commented/literal strings that must not
be mistaken for aliases.

The official YAML test-suite labels provide an external behavioural
comparison. Differences are recorded as diagnostics, not silently repaired,
filtered out or recast as correct L4YAML behaviour. The selected suite may
expose unsupported features or downstream exceptions, which must be reported
before claims of YAML standard compliance. It does not prove a universal
specification theorem from finite tests.

## Qualification and boundaries

A successful exact-head GitHub Actions run is required before promoting an
executable comparison result. Merely running the independent event model or
fetching source blobs does not establish executable equivalence.

Claim only the exact fixed fixture corpus and independently sourced test cases
with their pinned identities. Preserve separate axes:
- native Lean theorem check (checked only when the kernel job succeeds);
- actual JPL executable observation (checked only when the compiled binary runs);
- independent normative event semantics (closed template dialect);
- source-to-event correspondence (UNKNOWN outside the manually specified cases);
- universal parse acceptance iff exact surface grammar and serialization
  well-formedness (UNKNOWN);
- Palomar source-fidelity superiority or verified public badge (NOT TESTED).

No changes are made to nasa-jpl/L4YAML. Use only the Metalogic-controlled
repository's workflow and artifact surfaces.
