# Portable capability contracts v1

A capability descriptor describes an exact candidate capability. It cannot
declare itself verified, qualified, applicable, fresh, or authorized. Qualification
is a separate consumer evaluation. Structural rejection rejects the artifact; it
does not refute the mathematical claim. Capability qualification adds no fourth
mathematical terminal form.

## Normative artifacts

- `protocol/schemas/capability-contract-v1.schema.json`
- `protocol/schemas/capability-evaluation-v1.schema.json`
- `protocol/schemas/capability-registry-v1.schema.json`
- `protocol/registries/capabilities-v1.json`

The public schemas under `website/public/schemas/` are byte-identical projections.
The registry projects byte-for-byte to `website/public/capabilities/index-v1.json`.
These are local/static contracts, not hosted service endpoints.

## Descriptor

`schema_version` is exactly `mathgraph.capability-contract.v1`. Required fields:

| Field | Meaning |
| --- | --- |
| `id`, `version`, `profile` | Immutable identity and versioned semantic profile identifier |
| `claim` | Exact `id`, `kind`, and textual `scope` |
| `inputs`, `outputs` | Nonempty lists of `type_id` and pinned `schema` references |
| `preconditions`, `guarantees`, `assumptions` | Explicit lists of statements; guarantees are nonempty |
| `boundary` | Pinned exact claim-boundary artifact |
| `implementation` | Pinned candidate implementation artifact |
| `evidence` | List of pinned evidence references; empty does not mean qualified |
| `limitations` | Nonempty list of explicit limitations |
| `extensions` | List of `id`, `version`, Boolean `critical`, and opaque object `payload` |

Every artifact reference has a nonblank `id`, `locator`, `media_type`, lowercase
64-character SHA-256 `sha256`, and a nonnegative integer `size_bytes`. Locators
are opaque transport hints. They are never fetched or executed. Pins describe
expected bytes; descriptor validation alone does not check their presence,
integrity, authenticity, or mathematical content.

Identifiers, versions, claim scope, assumption statements, and reference fields
are compared exactly: no URL rewriting, case folding, trimming, aliases, subset
inference, or extrapolation. Snapshot comparison recursively preserves scalar
types (including Boolean versus integer/float), object keys, and array ordering;
object member ordering does not matter. Changed content requires a new version and new pins;
the evaluator can detect a rebind against a consumer-owned expected descriptor,
but it does not maintain global identity history.

The normative JSON schemas use Draft 2020-12 and closed objects. The strict
consumer additionally rejects duplicate JSON keys, nonfinite values, repeated
type IDs within an input/output list, repeated evidence IDs, repeated extension
IDs, and conflicting references that reuse an artifact ID. Identical artifact
references may be reused across fields. Registry `(id, version)` pairs must be
unique across both indices. These key-dependent constraints are supplemental to
JSON Schema `uniqueItems`. Python integer fields reject Boolean and float values.

Only extension payloads allow arbitrary members. A nested `status` in an opaque
payload has no authority. All critical extensions are currently unsupported and
yield `UNKNOWN`; noncritical extensions are ignored and reported. Known-field
status injection, missing extension versions, unknown core fields, and malformed
types are structural errors.

## Evaluation and the independent admission boundary

`mathgraph_protocol.capability_v1.evaluate_contract(document, expected_contract=None)`
accepts strict JSON bytes/text or a Python dictionary. It has no I/O, executes no
implementation, and imports only standard-library modules and the shared strict
JSON decoder. It does not mutate inputs.

Every result uses `mathgraph.capability-evaluation.v1` and independently exposes:

| Dimension | Initial evaluator result |
| --- | --- |
| `validation` | `VALID` or `INVALID` |
| `qualification` | `UNKNOWN` |
| `qualification_receipt`, `trust_policy` | `null` |
| `freshness`, `revocation`, `supersession` | `NOT_CHECKED` |
| `current_applicability` | `UNKNOWN` |
| `action_authorization` | `NONE` |
| `reason_codes` | Stable structural or semantic diagnostics |

Valid evaluations bind the exact supplied bytes through `contract_sha256` and
`contract_size_bytes` and retain exact `id`, `version`, and `profile` under
`contract`. Dictionary inputs are serialized using `encode_result` before hashing
(sorted keys, two-space indentation, ASCII JSON escapes, one trailing newline).
Invalid inputs expose no unvalidated identity and return null byte bindings.
Callers that need an external artifact hash should supply its exact bytes.

The initial evaluator admits **zero profiles or verifier receipts**, including
`mathgraph.finite-representation-refinement.v1`. Thus even a well-formed descriptor
reports `UNSUPPORTED_PROFILE` and `NO_ADMITTED_RECEIPT`. A matching expected
descriptor is an exact binding check, not qualification or authentication.
Changed identities, profiles, claim scopes, assumptions, sources, boundaries, or
other contract fields add `IDENTITY_MISMATCH`, `PROFILE_MISMATCH`,
`CLAIM_SCOPE_MISMATCH`, `ASSUMPTIONS_MISMATCH`, `SOURCE_MISMATCH`,
`BOUNDARY_MISMATCH`, or `CONTRACT_MISMATCH` respectively, and remain `UNKNOWN`.

The evaluation schema reserves `QUALIFIED_BOUNDED` for independent profile
replay. Such an evaluation requires structural validity, a pinned qualification
receipt, and a pinned consumer trust policy. Merely supplying these fields or
passing schema validation does not admit the receipt. A profile consumer must
independently replay evidence, bind the exact descriptor bytes and every source,
scope and assumption, interpret supported critical extensions, and apply the
explicit policy before producing or admitting qualification. Unsupported or
mismatched evidence remains `UNKNOWN`; failed finite search is not proof.
Freshness, revocation, supersession, and present applicability need their own
checks and must not be inferred from historical bounded qualification.
`action_authorization` is always `NONE` in this contract version.

## Registry

The versioned registry accepts empty `qualified_entries`. It now contains one
finite-developmental entry, admitted after exact finite replay by the separate
standard-library consumer in `conformance/capability_v1/consumer.py`. Its pinned
evaluation says `QUALIFIED_BOUNDED`; its receipt and descriptor state the finite
scope and deny universal invention, autonomous improvement, and external
adoption. This is same-owner implementation-independent qualification. See
[`conformance/capability_v1/README.md`](../conformance/capability_v1/README.md).
The general descriptor evaluator remains unqualified as described above.
The separate VDN Lean research pointer remains `EXPERIMENTAL`; Lean admission
awaits pinned native replay and independent contract-to-declaration correspondence.

A qualified row must pin its contract, evaluation, qualification receipt,
and trust policy as well as the exact capability identity/profile. An admission
process must validate and authenticate the relevant pins and independently check
the profile before publishing that row. `validate_registry` checks index
structure and uniqueness only: reading a producer-supplied index grants no trust.

## Local CLI and checks

```bash
python -I -S scripts/mathgraph_capability_v1.py --contract /path/to/contract.json
python -I -S scripts/mathgraph_capability_v1.py --contract /path/to/contract.json \
  --expected-contract /path/to/consumer-expected-contract.json
python -m pytest -q conformance/capability_v1/test_contract.py
```

The CLI writes one JSON evaluation. `INVALID` exits 1, including malformed JSON,
duplicate keys, missing local files, and invalid arguments. Structurally valid
`UNKNOWN` exits 0; exit 0 never means qualification or mathematical truth.
No source artifact, registry, evidence record, or deployment is mutated.
