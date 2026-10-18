# L4YAML source-native refute-first V2: legacy/indexed event/parse boundary

## Frozen before opening native outcomes

- **Target authority:** `nasa-jpl/L4YAML@bca37392fdcb80481342a186a37ab37a5ede6e46`, Lean `v4.35.0`.
- **Selected claim:** the independently duplicated legacy/indexed event-emitter and parse-stream paths should agree on acceptance, document counts, and successful event bytes within the input domain they both implement. Source: `L4YAML/Output/EventsIx.lean`, which explicitly says the indexed emitter emits the **same** yaml-test-suite event notation and mirrors the independently indexed loop.
- **Additional normative controls:** YAML 1.2.2 document-scoped aliases and tag handles, seven frozen expected accept/reject cases. Treat any disagreement as `SCOPED_SPEC_CANDIDATE` until independently checked against the normative text and upstream history.
- **Inputs:** `frozen_cases.json`, 796 unique source-preselected inputs, containing grammar/body combinations, document marker variants, whitespace, directives, anchors, aliases, custom tag handles, multi-document segments and edge cases.
- **Design blindness:** input fixture set and comparator source are frozen *before native outcomes* in this isolated research branch. **Not** a source-blind or method-transfer experiment: the target program and API layout were inspected to design the test. No new automatic grammar-discovery claim.
- **Hypothesis:** all eight source-native observations (legacy raw parse, legacy marked parse, legacy comments, indexed raw, indexed marked, indexed comments, two event streams) have matching success/failure statuses; when successful, outputs have the same document count, and legacy/indexed event strings agree byte-for-byte. A mismatch is a candidate defect unless the precise contract permits it.
- **Truth source:** execute actual pinned Lean `parseYamlRaw`, `parseYamlWithComments`, `parseYamlRawIx`, `parseYamlWithCommentsIx`, `parseYamlRawMarked`, `parseYamlRawMarkedIx`, `streamToEvents`, `streamToEventsIx`. No fabricated parser outputs or proxy mock.
- **Negative observer control:** deliberately different event strings `GOOD` and `MUTANT` must compare unequal; identical strings must compare equal.
- **Fail-closed verdict:** no mismatch means only `BOUNDED_FINITE_PARITY` on this corpus; mismatch prints exact pinned YAML, index and observation status and fails CI as `CANDIDATE` until independently minimized/reproduced. Harness/build failure `UNKNOWN_APPARATUS`.
- **Baseline:** the author's pre-existing YAML suite, indexed pipeline tests and known source issues remain legitimate comparators; don't call a result novel until documented coverage is checked. Cases already appearing in known L4YAML issues do not count as new.
- **Scope of claims:** this experiment cannot prove full YAML 1.2.2 specification equivalence, safety of all bindings, theorem correctness, FGM transfer, or MathGraph time/quality advantage.
- **Stop rule:** never modify the NASA-JPL source, open a JPL PR, or contact Nicolas on behalf of the user. Correct harness bugs only with corpus/source freeze retained, keep original failed runs and classify apparatus separately.

## Execution

The independent GitHub Actions workflow uses a clean Ubuntu runner, checks out
the exact upstream SHA without credentials, installs Lean `v4.35.0`, derives a
static Lean source from the **already committed** corpus, builds native upstream
modules, runs all pairs, archives logs and the generated corpus receipt.

Both admitted output comparisons and deliberate negative controls are
**executable**. They are not Lean proofs about unbounded input strings.
