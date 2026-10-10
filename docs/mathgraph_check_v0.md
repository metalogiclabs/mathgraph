# MathGraph Check v0 — source/formal preflight

**Status: experimental, diagnostic only.** This is the first lightweight product
interface over the independently qualified comparator in PR #141. It deliberately
does not certify natural-language statement fidelity, Lean kernel verification,
source-claim extraction, or theorem truth.

## Run (Python 3.10+, no optional dependencies)

    python -m mathgraph_check examples/mathgraph_check_v0_navier.json --json /tmp/mathgraph-check.json --markdown /tmp/mathgraph-check.md

The output says CANDIDATE_CONTRACT_DIVERGENCE for two **manually extracted**
source and Lean contracts: derivative loss 4 versus 5 on the pinned historical
Navier-Stokes comparison. The cited anchors are source references, not
automatically verified downloads. Accordingly both pins say PIN_NOT_REPLAYED
and **no checked badge is issued**. Research branches later prove stronger,
more precise results; this fixture is a deliberately frozen regression from
the original V1 discrepancy, not the current mathematical frontier.

## Contract manifest

- schema: mathgraph.check.v0 (required).
- title: human-readable claim title.
- source_contract_origin: MANUAL_UNREVIEWED (the only accepted v0 value).
- source and formal: anchor, dimensions, and optional argument_route.
- protected_dimensions: nonempty list of unique dimension names.
- Optional file and sha256 on either contract: hashes **local bytes only**,
  relative to the manifest directory. Arbitrary URL fetching and code execution
  are explicitly absent. A remote anchor is never trusted by itself.

Permitted typed dimension values: string, exact integer, boolean or string array.
The comparator is structural, not an implication prover. Agreement only means
NO_DECLARED_SEPARATOR_FOUND. Missing dimensions mean UNKNOWN. Even an explicit
contract mismatch remains a **candidate** until the source extraction and
theorem interpretation are independently reviewed.

Unlike Palomar, this v0 tool does not run Comparator or issue a formal
registry certificate. It can coexist with Palomar/Mathlib/Tau Ceti and must not
misrepresent their endorsement.

## Integration design and protected boundaries

- Stable JSON and human-readable Markdown are generated from the same report.
- Formal verification, source-to-formal fidelity, and truth promotion are
  separate; all remain UNKNOWN / false until separately qualified.
- Content hashes bind the input manifest and optional checked local source files.
- Unknown keys and unsupported value types fail closed.
- Source-file path escapes, hash changes, and self-declared verification are rejected.
- The mathgraph.semantic_correspondence import is retained as a compatibility
  facade; the exact existing comparator now resides in lightweight
  mathgraph_check.contracts for standalone clients.
- No GitHub comment, submission, signed badge, or production authority mutation
  occurs from this checker.

## Current benchmark status

Existing PR #141 established bounded separator fixtures and pinned Lean source
tests. This v0 CLI adds failure controls, JSON/Markdown presentation and a
CI artifact. **It has not outperformed Palomar's statement-alignment reviewer.**
A fair study must freeze independently labelled source/theorem examples
(including vacuity and genuinely clean negatives), execute the current
PalomarPolicy statement-alignment baseline and this system on untouched
examples, and measure diagnostic precision/recall, false alarms, reviewer
minutes, model tokens and total cost. Comparing this zero-LLM typed comparator
with full automatic source interpretation would be an invalid cost comparison.

References:
- Palomar statement-alignment policy:
  https://github.com/PalomarRegistry/PalomarPolicy/blob/main/prompts/02-statement-alignment.md
- Existing MathGraph draft research:
  https://github.com/metalogiclabs/mathgraph/pull/141
- Original pinned V1 mathematical regression:
  https://github.com/metalogiclabs/mathgraph/actions/runs/37894847275

## Next decisive gate

Human-label a frozen public benchmark and bind proposed source-dimension
extractions to exact original source spans, formal declaration bytes, and
independently checked semantics. Only after a held-out, cost-controlled
evaluation should MathGraph claim improved source-fidelity diagnostics or
publish an automated verified badge.


## Pinned first-party manuscript replay (separate CI job)

The workflow's real-original-surface job downloads the original public OpenAI
Navier-Stokes manuscript and two exact historical Lean source files, confirms
the PDF SHA-256 and Git blob identities, and runs the already-qualified V4
original-source/declaration probe. It converts the selected four-derivative
source wording and five-jet formal theorem surface to the same Check v0
manifest. The new report records both actual source inputs as
LOCAL_SHA256_CHECKED, but deliberately retains MANUAL_UNREVIEWED source
interpretation, UNKNOWN formal proof replay, and NO VERIFIED BADGE.

This is real original-source identity and selected-text/Lean-declaration
corroboration, **not** a proof that the manuscript-to-formal translation is
incorrect in all interpretations. It is not a cost-controlled head-to-head
against Palomar; a dedicated independently labelled benchmark is still needed.
