# Exact-declaration proof-use binding — operator-only design

## Why

The existing native ProofChecker can return PASS on an operator-authored hypothetical fixture, but the fixture is UNBOUND_ADVISORY: a different assumption/goal may be audited than the trusted candidate/reference source. Before claiming that an actual candidate matters to the actual target, bind the fixture's selected antecedent and goal to the *elaborated Lean theorem types* in independently byte-pinned source modules.

## Approaches

- **Selected: native two-pass module-origin/type binding.** Compile the exact trusted reference source and fixture as separate modules, then use a generated Lean audit to verify the original declaration belongs to `Reference`, the fixture goal belongs to `ProofFixture`, both are theorems, and their types are definitionally equal. Repeat independently for candidate and fixture assumption. This avoids collisions when original/candidate have identical names and never infers type equivalence from text alone.
- Future: compile all sides into a SemantEq-style shared environment with namespace virtualization. This can handle cross-source local notation/name collisions and more complex module layouts, but introduces significant elaboration/transformation machinery.
- Rejected: trust a textual theorem fingerprint, `#check` printout, caller-provided `PASS`, or mere compilation. These do not prove that the selected declarations or binder types match.

## Exact contract

Optional CLI names `--proof-reference-name`, `--proof-candidate-name`, `--proof-assumption-name`, `--proof-goal-name` must all appear with the existing byte-pinned fixture. Reference/candidate names may use dotted Lean identifiers; fixture names must match the actual names returned by the native ProofChecker. A missing, mismatched or unsafe name is UNKNOWN or rejected, never guessed. Sources are first-party operator-reviewed only.

Run in pinned SemantEq v1.4.0/Lean 4.30.0-rc1/Mathlib environment already required by generic claim audit. The binding runner separately pins exact fixture bytes and the same reference SHA, stages exact source buffers under ignored `.lake/build`, compiles `Reference.lean`, `Candidate.lean`, `ProofFixture.lean` to native `.olean`s, and compiles two generated Lean audits. In each audit, `Environment.getModuleIdxFor?` confirms the declaration actually originates from the named staged module; `ConstantInfo.isTheorem` refuses axiom/def impersonation; `Meta.isDefEq` checks the full theorem types, including quantifiers and hypotheses. Retain full commands, compiler stdout/stderr, exit codes, elapsed times, source hashes, environment metadata and output hashes.

Two `true` comparisons and matching native ProofChecker names, result and same-run toolchain pins can promote only a new bounded status `bound_fixture_proof_use: NATIVE_TYPE_BOUND_FIXTURE_USE`. A ProofChecker `FAIL`, missing receipt, theorem-origin failure, Type `false` or environment error retains this status UNKNOWN; do not fabricate `ALTERED`. **Actual candidate proof-artifact dependence remains UNKNOWN even on PASS:** the fixture assumed a proposition of the same type but did not replay the real candidate constant through the proof term. Native `false` means **not definitionally equal**, not a proof of semantic inequivalence. The independent source-to-research-intent interpretation and `evidence_warrant` remain UNKNOWN in all cases. The source theorem's own proof/axiom quality is a separate obligation.

## Supported boundary and limitations

Sources must compile as independently staged `Reference.lean` and `Candidate.lean` modules under the pinned project, and the fixture as `ProofFixture.lean`; if imported names clash, private module dependencies cannot resolve, or the ProofChecker fails to identify the selected names, return UNKNOWN. This is not yet a general Kakeya importer or authenticated human approval. Lean elaboration of operator-selected sources is inherently executable: never expose the runner to arbitrary GitHub PR content without a separately reviewed isolation sandbox. The existing GitHub App remains unchanged, publication disabled by default.

## Controls

Positive: identical full theorem types and genuinely used assumed theorem → NATIVE_TYPE_BOUND_FIXTURE_USE, never actual candidate dependence. Negatives: strengthened assumption, weaker goal, wrong theorem name/imported library theorem, stale fixture hash, missing environment, forged raw PASS, library bypass and dead candidate touch → no fixture-use promotion. Preserve prior CLI results and native receipts byte-for-byte where options are omitted.
