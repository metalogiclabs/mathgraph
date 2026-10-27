# Prospective source-only ACSL old-state/frame and alias assurance

Pinned source: ZoneOut12/C2VerifiableRust at commit 6c8b35b5dd8e94473b713b7edcf4bf4142f214e3.

This source-only preregistration seals seven C source files, exact Git blobs,
six narrow old-state/frame contract types, one unsupported relational control,
finite test ranges and exactly three probes per recognized contract. Only
translated target PATH EXISTENCE was checked before this preregistration.

Keep essential distinctions:
- The separated reset's condition uses pre-state of pointer b and assigns
  only pointer a. b is protected from modification.
- Increment's source postcondition constrains pointer a's new value and b's
  unchanged value. Do NOT invent a specification for its return value.
- The two-pointer swap source does NOT require separation; a distinct-pointer
  test leaves overlapping calls UNKNOWN. An adapter cannot pretend otherwise.
- The array-swap ACSL mistakenly repeats the arr[n2] condition and lacks an
  assigns clause. Do NOT infer whole-swap or preservation of other elements.
- Pointer sum and plus-five explicitly specify assigns nothing.
- Two-label relation/lemma semantics involving at(...) remain UNKNOWN.
- Test only valid small inputs with no signed integer overflow.

Source-only CI first seals the packet and negative/positive contract tests,
then Rust generated targets may be unblinded in a separate native-run stage.
C and Rust original implementations must remain untouched; only minimally
typed test adapters are permitted. Cases that are impossible to execute
unchanged remain UNKNOWN, not semantic defects. Conventional baseline has
identical input evidence and independently written contract logic.

A mutation of copied evidence is synthetic, not an authentic translation
defect. No universal ACSL equivalence, measured economic advantage, or
competitive superiority is asserted without further evidence.
