# Resolve bundle and trust-policy contracts v1

MathGraph Resolve v1 publishes two distinct protocol objects:

- `mathgraph.resolve-bundle.v1` is a transport envelope for exactly
  `record.json`, `history.md`, and `jpl-record.json`.
- `mathgraph.resolve-trust-policy.v1` pins those members and admits exactly the
  four historical receipts used by record
  `mg-living-warrant-openai-jpl-20261010`.

The normative JSON Schema Draft 2020-12 sources are:

- [Resolve bundle schema](../protocol/schemas/resolve-bundle-v1.schema.json)
  ([public copy](https://mathgraph.org/schemas/resolve-bundle-v1.schema.json))
- [Resolve trust-policy schema](../protocol/schemas/resolve-trust-policy-v1.schema.json)
  ([public copy](https://mathgraph.org/schemas/resolve-trust-policy-v1.schema.json))

The files under `website/public/schemas/` are byte-identical publication
projections. The protocol copies are authoritative. These schemas describe
structure; they do not authenticate records or replace the separately pinned
trust policy and semantic replay.

## Validation boundary

The standalone `conformance/protocol_v1/consumer.py` uses only the Python
standard library. It rejects duplicate JSON keys before structural validation,
rejects unknown or missing fields, decodes every base64 member independently,
recomputes each size and SHA-256 digest, compares bundle pins with policy pins,
and checks receipt kind, scope, source, verifier, assumptions, and outcome.

The trust-policy SHA-256 must be supplied through an independent trust channel.
For the published v1 policy it is:

```text
09e8d5ba97bca126a81dfe0fcbd5d57f3915ffe71402a497ece4d5e6117f2b4a
```

The published bundle SHA-256 remains:

```text
957080db79555f982fd3a314c263cf5177ef506969229e856897f0b19ccc1d62
```

Hash agreement protects integrity. It does not authenticate a publisher,
authorize actions, establish freshness or current applicability, rerun the JPL
Lean proof, or turn a candidate into an accepted mathematical claim. Consistent
rehashing of changed member bytes is rejected by the frozen v1 authorization
profile.

## Relationship to semantic replay

Structural/admission validation and semantic replay are orthogonal gates. A
successful protocol report contains `semantic_replay: NOT_PERFORMED`. The
existing `conformance/resolve_v1/consumer.py` remains the independent semantic
replay and is still required to reproduce the historical resolution states.
Neither gate changes the terminal-form contract of the MathGraph kernel.

## Reason codes

Failures are fail-closed and expose stable machine codes. Structural examples
include `DUPLICATE_JSON_KEY`, `UNEXPECTED_FIELD`, `MISSING_MEMBER`,
`INVALID_BASE64`, `MEMBER_SIZE_MISMATCH`, `MEMBER_HASH_MISMATCH`, and
`UNSUPPORTED_BUNDLE_VERSION`. Admission examples include
`UNKNOWN_SEMANTIC_KIND`, `ADMISSION_SOURCE_MISMATCH`,
`ADMISSION_SCOPE_MISMATCH`, `ADMISSION_VERIFIER_MISMATCH`,
`ADMISSION_ASSUMPTIONS_MISMATCH`, `UNAUTHORIZED_MEMBER`, and
`UNAUTHORIZED_PROVENANCE`.

Reason codes classify rejection; they are not claims of successful replay.
