# Prospective source-only pairwise pointer-admission audit

Pinned original C from ZoneOut12/C2VerifiableRust commit
6c8b35b5dd8e94473b713b7edcf4bf4142f214e3.

Nine hand-selected, source-only ACSL files. Target path existence was
confirmed but no translated Rust target content inspected before this
preregistration. Freeze the source-only pairwise alias / explicit separation
/ optional-null obligations and accompanying test cases now.

Boundaries: absence of explicit \separated is only a *necessary syntax
condition* for allowing a same-pointer call. Other requires clauses can
make particular input states ineligible; do not overclaim full C
admissibility. A pair explicitly separated cannot alias on the C side.
Rust direct safe call probes must use unmodified translated functions,
without unsafe, casting, or invented implementation changes. A compiler
borrow error is API call-domain evidence, not a runtime bug.
Read-only / mutability and nullable cases act as controls, not as
assumed positive/negative target labels. Conditional behaviors and source
postconditions are outside this narrow signature-only scope.

Experimental sequence: source-only CI produces frozen packet and digest
without checking out generated Rust; only after GREEN unblind Rust.
Native C executes selected same-pointer calls where actual preconditions
are demonstrably satisfiable. Native rustc tests direct same-pointer and
distinct-pointer calls where signatures are in the supported grammar.
Independent comparator receives same C, source packet, Rust code and
compiler outputs, and must not use MathGraph analyzer code. Report all
ties and UNKNOWN separately. No superior detection/cost claim by default.
