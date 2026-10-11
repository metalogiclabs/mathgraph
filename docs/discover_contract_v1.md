# MathGraph Discover v1

Discover v1 is a local, deterministic advisory operation:

```python
from mathgraph_protocol.discover_v1 import discover

result = discover(request)  # dictionary or strict JSON text/bytes
```

It ranks proposed continuations and allocates attention. It does not contact a
solver, run a route, perform semantic verification, or call a hosted service.
It depends only on the Python standard library and the pure ranking/parser
primitives in `mathgraph_protocol`; it does not import `mathgraph`.

## Contracts and boundary

The normative Draft 2020-12 schemas are:

- `protocol/schemas/discover-request-v1.schema.json`
- `protocol/schemas/discover-result-v1.schema.json`

The corresponding `website/public/schemas/` files are byte-identical projections.
The exact versions are `mathgraph.discover-request.v1` and
`mathgraph.discover-result.v1`. Unknown fields and versions are errors.

Every result, including an error, contains `advisory_only: true`,
`can_promote_truth: false`, `verification_status: NOT_CHECKED`, and
`attention_interpretation: ALLOCATION_NOT_TRUTH_CONFIDENCE`. No terminal-form
field is permitted. A high score, a selected candidate, or an attention
probability of 1.0 does not establish a mathematical claim.

Candidate text is descriptive data, never an executable instruction or an
accepted claim. Statements such as “not a VERIFIED_PROOF” are legitimate
boundary disclaimers. Eligibility checks use typed fields rather than scanning
prose for truth-related words. Discover cannot determine the truth of arbitrary
candidate descriptions.

## Request and ranking

A request contains its ID, a policy (`mode` and nonnegative finite `beta`),
nonnegative integer `top_k`, candidates, source references, source diagnostics,
and reported historical metrics. All collections may be empty. Candidate and
source IDs and metric names must be unique; candidate source references and
metric source references must resolve within the request.

The policy modes are `balanced`, `harvest`, `frontier`, and `architectonic`.
The single implementation of their weights, score expression, softmax attention,
and tie ordering lives in `mathgraph_protocol/discovery_ranking.py` and is also
used by the existing research scheduler. Missing numeric candidate features
default to zero. Numeric features must be nonnegative and finite. Overflow in
otherwise finite inputs returns `ERROR` with `NUMERIC_OVERFLOW`.

Ranking covers all eligible candidates. `top_k` controls only the `selected`
flag, so `top_k=0` returns a ranking with no selected rows. Probabilities are
normalized across all eligible candidates, never across rejected candidates.
Ties follow descending probability, descending score, then ascending candidate
ID. Unique IDs remove any input-position ambiguity.

Eligible descension targets are `finite_countermodel_attempt`,
`lean_verifier_contact_candidate`, `lean_digest_repair`,
`obstruction_naming_attempt`, `obstruction_naming`,
`constructor_synthesis_attempt`, `constructor_synthesis`, `projection_test`,
`representation_repair`, `evidence_replay`, `replay_validation`,
`lawbook_ingestion`, `reason_atlas_route_test`, and `trust_audit`.
These are proposed routes, not observed outcomes.

The strict wire profile additionally rejects duplicate JSON object keys,
nonfinite numbers, and booleans in numeric fields. Integer fields require Python
integers after decoding, so a floating JSON token such as `1.0` is rejected for
`top_k` even though generic JSON Schema validators may treat it as an integer.
JSON Schema alone cannot enforce duplicate-key rejection or cross-row ID and
reference relationships; the executable validator enforces these rules.

## Outcomes and exit status

| Status | Meaning | CLI exit |
| --- | --- | --- |
| `OK` | At least one eligible candidate; no candidate rejection or incomplete source observation | 0 |
| `PARTIAL` | Eligible candidates remain, but some candidates were rejected or source material is incomplete/unchecked | 0 |
| `UNKNOWN` | No eligible candidates, including empty input | 0 |
| `ERROR` | Structural, decoding, arithmetic, or operational failure | 1 |

An unknown descension target, `advisory_only: false`, or
`can_promote_truth: true` rejects that candidate. Rejection codes are
`INVALID_DESCENSION_TARGET`, `ADVISORY_ONLY_REQUIRED`, and
`TRUTH_PROMOTION_FORBIDDEN`. Malformed field types, extra fields, duplicate IDs,
or unresolved source references reject the whole request structurally.

Aggregate semantic reasons are `NO_ELIGIBLE_CANDIDATES`,
`CANDIDATES_REJECTED`, and `SOURCE_MATERIAL_INCOMPLETE`. Structural reasons
include `DUPLICATE_KEY`, `DUPLICATE_ID`, `UNSUPPORTED_VERSION`, `MISSING_FIELD`,
`UNKNOWN_FIELD`, `INVALID_FIELD_TYPE`, `INVALID_FIELD`, `INVALID_NUMBER`,
`INVALID_TOP_K`, `INVALID_POLICY`, `INVALID_DIGEST`, `INVALID_SIZE`,
`UNKNOWN_SOURCE_ID`, `INVALID_JSON`, and `NUMERIC_OVERFLOW`. CLI/source failures
include `SOURCE_IO_ERROR`, `SOURCE_SIZE_MISMATCH`, `SOURCE_DIGEST_MISMATCH`,
`INVALID_SOURCE`, and `INVALID_ARGUMENTS`.

The pure operation performs no I/O and cannot check source bytes supplied by a
caller. `sources[].availability` and `integrity_check` are reported local
observations; it preserves them without upgrading their authority. `OK` means
an advisory ranking was formed, not that external data was authenticated.
Diagnostics are descriptive; structured source state determines incompleteness.

## Real example and provenance

The first request is derived by `request_from_recursive_transfer(pack_dir)` in
`mathgraph_protocol/discover_sources_v1.py` from the checked local
`recursive_residual_transfer_v1_20260523` pack. It pins the manifest and metrics:

- Manifest SHA-256: `449e9f9378a90ffb975f21cd5d534455f0d03bc393bf821daefdc000950509c5`
- Metrics SHA-256: `83c9a568d2fc3f9c06bd4487c51a7a6af1ba44323a33e6b3e3b86e23d1bf0b2c`

The adapter verifies the manifest-declared size and SHA-256 of every present
artifact before deriving a candidate. All nine declared local copies, including
the seven small CSVs, are tracked so a clean checkout can reproduce the request.
Existing source bytes are retained exactly. No historical experiment is rerun,
and no historical claim is requalified.

Each artifact retains its exact source path, repository path (including null),
bundle name, bundle-relative path, size, and hash. The unavailable full candidate
score CSV and SQLite ledger retain their references and `NOT_CHECKED` state.
The SQLite ledger is required for full replay; the result explicitly reports
`FULL_REPLAY_UNAVAILABLE`. Missing expected artifacts from the original manifest
are also retained as diagnostics. Equations, the original matrix, and toolchain
qualification are not supplied by this adapter.

The candidate uses the existing advisory route-memory feature mapping:
constructor reuse is `min(0.95, 0.45 + reported_transfer_gain / 500)`, with the
remaining documented example feature values fixed in the adapter. These are
heuristic ranking inputs. Reported zero contamination and passed historical
gates remain `reported_metrics`; they are not new verification results.

The committed request/result pair lives in `conformance/discover_v1/fixtures/`.
The example yields `PARTIAL`, one ranked replay candidate, and `NOT_CHECKED`.

```bash
python -I -S scripts/mathgraph_discover_v1.py --request conformance/discover_v1/fixtures/request.json
python -I -S scripts/mathgraph_discover_v1.py --source-pack examples/evidence_packs/recursive_residual_transfer_v1_20260523
```

Both commands emit the committed result bytes: sorted JSON keys, two-space
indentation, ASCII escaping, finite numbers, and one trailing newline. There are
no timestamps, random IDs, absolute checkout paths, or network fetches in output.

## Conformance

```bash
python -m pytest conformance/discover_v1/test_discover.py tests/test_mathgraph_protocol_import.py tests/test_discovery_scheduler.py tests/test_discovery_candidate_sources.py -q
```

The suite covers strict errors, semantic rejection, deterministic ties and
selection, source tampering, missing material, CLI exit codes, exact fixture
bytes, and an isolated `python -I -S` process with optional/other MathGraph
imports and network/process execution blocked. No unrelated experiment suite
or hosted runtime is required.
