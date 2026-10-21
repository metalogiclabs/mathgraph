# Prospective closed-boundary transfer V5 — protocol frozen before source content

2026-10-22. Previous V4 success in Resolve consumer was exact-pin, two-suite and conventional TIE. This is a separate prospective source family.

## Locked unseen target and paired actual suites
New production-like component: conformance/capability_v1/consumer.py (only directory metadata inspected before protocol).
Protected source-adjacent test: conformance/capability_v1/test_contract.py. Independent comparator test: tests/test_mathgraph_warrant_resolution_core.py.
Chosen before reading either capability source or tests. No substituting another candidate after exposure.

## Frozen implementation-change eligibility
Exactly one real behavior-preserving function-level source change, if possible without adding rules after seeing source:
- First SHA-256 hexdigest() conversion found in consumer.py, replace it with digest().hex(). Match source shape and positional uniqueness, else STOP UNKNOWN_INELIGIBLE_SOURCE. Do not change protected tests.
- Compare original/new callable on five bytes-like vectors and run existing native tests.
No other edits to original component.

## Frozen module-independence compiler
Scan transitive imports of BOTH test files and local production modules from actual source, using a fixed conservative AST interpreter. The independent suite is skippable ONLY if exact pinned source hashes, no reference/opaque dynamic loading to changed module, no nonlisted local package import, and no unknown side effects. Any ambiguity returns KEEP. Separately run both test suites on altered source with original Python runtime.
Strong equal-info conventional selector receives identical exact module/import tree and chooses same eligibility; novelty/cost win cannot be claimed on TIE.
Negative controls: dynamically import target from independent test -> REVOKE; transitive helper import target -> REVOKE; mutated unauthorized source diff -> REVOKE; false SHA implementation -> native parity reject.
Five paired fresh-process selective vs full regressions, all qualification executions charged. Project-wide release stays UNKNOWN irrespective of selective success.

## Outcomes
Primary: after freezing rules, does the unchanged selector acquire one genuine source-specific closed impact boundary and omit a genuine independent suite? Secondary: is there a fair equal-info cost improvement, after all costs? If file lacks allowed primitive or closed import envelope, record UNKNOWN/REJECTED, no retrofit. Do not run a replacement project or fabricate protected evidence.
R7.2, CLC and MathGraph warrant_resolution not modified; use actual resolver only for scoped documentary skip authority.
