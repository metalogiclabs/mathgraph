# V3 prospective verified change-impact selection — immutable protocol

Date 2026-10-21. Uses previously authenticated real production source rewrite mathgraph_check/warrant_resolution.py (old Git blob ab4fc71cb90ee5c1c7435f0f32643673c0ee49d8; new 85de97a95f225ad564feb29faec24ce67f3f2e0e), same branch ancestry as property preservation V2.

## Question
Can we safely *omit* any of the actual five broad Python test files while protecting all source-dependent behavior, with an independently checkable source-level reachability argument? No guessing from test filenames. Compare to an equally informed conventional change-impact baseline.

## Frozen actual test universe
1. tests/test_mathgraph_warrant_resolution_core.py
2. tests/test_mathgraph_living_warrants_v1.py
3. tests/test_mathgraph_resolve_publication_v1.py
4. conformance/protocol_v1/test_consumer.py
5. conformance/resolve_v1/test_consumer.py

## Fixed authority / semantics
AST-based import-reachability checker starts from changed mathgraph_check.warrant_resolution; examines direct import from/import of local code plus imports performed inside functions. Recursively tracks local .py imports in the files touched by the static graph. Any unresolved dynamic import, opaque execution, imported package side effects, pathlib-discovered source, subprocess, or test whose imported dependency graph is incomplete returns UNKNOWN: do NOT omit. Otherwise a test may be omitted only if a fully enumerated import path proves no reference to changed module or its public API (including indirect dynamic use); absence of imports alone is not a general semantic independence theorem, so claim only the syntactically closed, controlled test scope.

Conventional full-info comparator: static filename/explicit-import selector (common incremental CI heuristic), BUT evaluate false negative risks with a deliberate dependency shadow. Full native five-file suite run once as independent conformance control and cost floor. A selector which cannot justify safe omission should return NO_SAFE_SKIP and make zero savings claims.

## Negative controls
- Insert, in a separate synthetic temporary test source (not product), dynamic import of changed module using importlib.import_module: must cause UNKNOWN/KEEP rather than silent omission.
- Insert imported helper module which reexports resolver function: must retain dependent test.
- Insert harmless independent pure test: may demonstrate narrow exemption only if the source graph and no dynamic/hardware effects are statically closed. This synthetic exemption cannot be promoted to omitting authentic existing test files.
- Withdraw source-identity pin or completeness assumption: protected test-skip permission UNKNOWN, and broad suite remains required.

## Report
Number of actual tests safely omittable; number conservatively retained; all source provenance and CI overhead, original native regression result, and difference from conventional heuristic. Real production release/merge protected decision remains UNKNOWN until protected test obligations can be proven preserved; do not turn source graph into proof of unobserved test independence. Leave R7.2/CLC and MathGraph warrant code unchanged.
