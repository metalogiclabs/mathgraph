# API semantic-obligation proposal V1 — irrevocable prospective freeze

**State:** PRESELECTED CANDIDATE, no held-out implementation/test source observed in this experiment. This freeze is separate from and DOES NOT change MathGraph's [cross-domain evidence protocol V1](https://github.com/metalogiclabs/mathgraph/commit/9c8b427c679398fd80ea56d9a91a1627b2e96b6d).

## Objective and truthful claim boundary
Test whether an unchanged, human-authored **API-surface grammar** can propose a finite semantic-correspondence obligation without any human target-specific adapter, and then let native tests + a separate independent Python equality observer decide it. This is *automatic obligation instantiation inside an already specified grammar*, not invention of a new relation family, autonomous research G2/L7 or a universal semantics theorem. A negative is retained.

## Frozen metadata-only selection
Ordered pool (not statistically representative; enriched for codecs and protocol APIs):
1. `python-hyper/hpack`
2. `python-hyper/h11`
3. `python-hyper/h2`

Inspect repo metadata ONLY after committing the exact generator and comparator: choose the **first** repo that exists, has `archived=false`, `language=Python`, and a public default-branch HEAD commit. Pin full SHA. No inspection of files, API signatures, tests, PRs, issues or source until this frozen method commit exists. No fallback after outcomes: if chosen source yields no eligible relation or native setup fails, record UNKNOWN/REJECTED; do not advance to second source. We choose module name from repository basename; if import fails, UNKNOWN_UNSUPPORTED_MODULE_LAYOUT, not a bespoke fix.

## Frozen proposal grammar
Only public, no-required-extra-argument pairs are eligible:
- top-level exported function pairs with exact names `encode/decode`, `compress/decompress`, `dump/load`, `dumps/loads`, `escape/unescape`, `pack/unpack`, `serialize/deserialize`;
- public class pairs whose names end `Encoder/Decoder` with public instance `.encode/.decode` methods accepting one required payload plus any optional parameters; constructors must have no required arguments. Fresh instances for each evaluation.
- No private members, manual package-specific rules, source-specific AST transformations or dynamic imports of unrelated packages. Require module provenance inside checked-out source.

Generated obligation per pair: **exact Python value identity** `decode(encode(x)) == x` for every seed actually accepted by the first function, with fresh instances. Exceptions from encoder are ineligible seeds; decoder exceptions are counterexamples. This is a strict *value/type* relation, not "same human meaning" and not proof of cryptographic roundtrip. The full finite seed pool is frozen before source access: `'hello'`, `b'hello'`, `''`, `b''`, `0`, `1`, `{'x-mg':'v-mg'}`, `[('x-mg','v-mg')]`, `[(b'x-mg',b'v-mg')]`, `[(':method','GET')]`, `[(b':method',b'GET')]`, and two-pair variants. All first-step eligible seeds must be checked and reported; no adaptive fixture changes.

Verdicts for each proposed obligation: **UNKNOWN_NO_APPLICABILITY** if zero seeds accepted; **REJECTED_BOUNDED** if any accepted seed fails strict exact identity; **WARRANTED_BOUNDED_FINITE** if at least one accepted seed and every one passes. An unsupported semantic interpretation returns UNKNOWN; any positive individual witness never repairs a failed finite universal relation. Distinguish exceptions/ineligible seeds from counterexamples.

## Equal-information, expert-authored comparator
A distinct implementation `baseline_reference.py` runs the *same* visible API, methods, original installed package, seeded inputs, independent equality oracle and read-only tests. It does not import the proposer or its output, and applies a conventional exhaustive encode/decode pair rule. It may use inspect signatures and docs. Compare candidate coverage, per-input success/rejection, invocation count, false promotions, evidence completeness and source-native test result. This is an **expert-authored rule baseline**, NOT a hired independent human expert; no claimed advantage over competent human review or coding agents.

## Native / prospective controls
- First run synthetic self-tests of both methods without any held-out repository checkout.
- Freeze method commit and SHA; later runner must check out that exact immutable commit to execute both methods.
- Separately after freeze, obtain only candidate GitHub metadata and HEAD SHA; record selection before code access.
- Read-only checkout to the exact selected commit, install it in ephemeral runner, run its **original native pytest suite** and record pass/fail/skips; run both frozen evaluator and comparator. A native suite that cannot execute is UNKNOWN_NATIVE, not proof of method failure.
- Source identity, import origin, native JUnit/log, full JSON output and candidate tests archived; no upstream writes.
- Negative/zero-applicability, source-only API mismatch and unequal baseline outputs are retained, not hidden.
- The result can become REUSABLE_BOUNDED only for this **proposer grammar** after a second independent frozen held-out source plus matched comparison; a single pass cannot establish general transfer.

## Stop/no-retrofit
No modifications to this protocol, proposer, comparator, or seed corpus after any selected source files or outcomes are accessed. Apparatus-only fixes (workflow quoting, dependency install) require separate commits and retain failed runs; do not alter selection. If a target-specific adaptation would be required, emit UNKNOWN_GENERATOR_GAP.
